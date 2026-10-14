from pathlib import Path

import pytest

from esteira_model_cob.templating import (
    ORIGIN_CONFIG,
    ORIGIN_GITHUB,
    load_env_params,
    params_for,
    params_from_github_vars,
    placeholders,
    render,
    resolve_params,
)

_ROOT = Path(__file__).resolve().parents[1]
_ENV_PARAMS_PATH = _ROOT / "config" / "jcl_env_params.yml"
_POC005 = _ROOT / "jcl" / "poc005_por_ambiente.jcl"
_ESTMX001 = _ROOT / "jcl" / "ESTMX001.jcl"


def test_params_from_github_vars_keeps_only_jcl_prefix():
    raw = '{"JCL_HLQ": "ESTM.POC.TI", "JCL_SPACE_PRIMARY": 600, "GH_KV_DEV": "kv-x"}'
    assert params_from_github_vars(raw) == {"HLQ": "ESTM.POC.TI", "SPACE_PRIMARY": "600"}
    assert params_from_github_vars(None) == {}
    assert params_from_github_vars("") == {}


def test_github_vars_override_config_and_record_origin():
    resolved = resolve_params({"HLQ": "ESTM.POC.TU", "UNIT": "SYSDA"}, {"HLQ": "ESTM.POC.TI"})
    assert resolved.values == {"HLQ": "ESTM.POC.TI", "UNIT": "SYSDA"}
    assert resolved.origins == {"HLQ": ORIGIN_GITHUB, "UNIT": ORIGIN_CONFIG}


def test_placeholders_in_order_without_duplicates():
    assert placeholders("${HLQ}.A ${UNIT} ${HLQ}.B $X") == ["HLQ", "UNIT", "X"]


def test_estmx001_has_values_for_every_placeholder_in_every_env():
    config = load_env_params(_ENV_PARAMS_PATH)
    template_text = _ESTMX001.read_text(encoding="utf-8")
    for env in ("TU", "TI", "PRD"):
        rendered = render(template_text, params_for(config, "ESTMX001", env))
        assert "${" not in rendered
        assert f"DSN=ESTM.POC.{env}.CLIENTES(+1)" in rendered


def test_render_substitutes_placeholders():
    assert render("SPACE=(TRK,(${A},${B}),RLSE)", {"A": "5", "B": "1"}) == "SPACE=(TRK,(5,1),RLSE)"


def test_render_raises_on_missing_param():
    with pytest.raises(KeyError):
        render("SPACE=(TRK,(${A},${B}),RLSE)", {"A": "5"})


def test_params_for_returns_empty_dict_when_job_or_env_unknown():
    config = {"POC005": {"TU": {"SPACE_PRIMARY": "5"}}}
    assert params_for(config, "POC005", "PRD") == {}
    assert params_for(config, "OUTRO_JOB", "TU") == {}
    assert params_for(config, None, "TU") == {}


def test_poc005_renders_smaller_space_in_tu_and_ti_bigger_in_prd():
    """Espelha o padrao encontrado em JCL real cedido pelo banco (jcl/real/,
    nao versionado): mesmo job/dataset/logica, so o SPACE alocado muda -
    TU e TI identicos, PRD maior."""
    config = load_env_params(_ENV_PARAMS_PATH)
    template_text = _POC005.read_text(encoding="utf-8")

    rendered = {
        env: render(template_text, params_for(config, "POC005", env))
        for env in ("TU", "TI", "PRD")
    }

    space_line = {env: next(line for line in text.splitlines() if "SPACE=" in line) for env, text in rendered.items()}

    assert space_line["TU"] == space_line["TI"]
    assert space_line["PRD"] != space_line["TU"]
    assert "(5,1)" in space_line["TU"]
    assert "(50,10)" in space_line["PRD"]
