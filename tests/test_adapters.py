from pathlib import Path

from esteira_model_cob.adapters.mock_zos import MockZosAdapter
from esteira_model_cob.parser import parse_jcl_file
from esteira_model_cob.quality_gate import compute_score
from esteira_model_cob.rules_engine import evaluate, load_dataset_naming_pattern, load_rules
from esteira_model_cob.simulator import simulate

_ROOT = Path(__file__).resolve().parents[1]
_JCL_DIR = _ROOT / "jcl"
_RULES = load_rules(_ROOT / "config" / "rules.yml")
_NAMING = load_dataset_naming_pattern(_ROOT / "config" / "datasets.yml")


def _quality_for(filename: str):
    job = parse_jcl_file(_JCL_DIR / filename)
    findings = evaluate(job, _RULES, _NAMING)
    return job, compute_score(findings)


def test_mock_adapter_returns_rc_0000_for_approved_job():
    job, quality = _quality_for("poc001_sucesso.jcl")
    result = simulate(job, quality, MockZosAdapter())

    assert result.executed is True
    assert result.job_result.rc == "0000"
    assert result.job_result.jobid.startswith("JOB")
    assert "COND CODE 0000" in result.job_result.spool


def test_simulation_blocks_before_adapter_for_critical_job():
    job, quality = _quality_for("poc003_bloqueado.jcl")
    result = simulate(job, quality, MockZosAdapter())

    assert result.executed is False
    assert result.job_result is None
    assert "Bloqueado" in result.reason
