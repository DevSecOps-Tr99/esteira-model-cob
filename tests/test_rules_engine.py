from pathlib import Path

import pytest

from esteira_model_cob.parser import parse_jcl_file
from esteira_model_cob.rules_engine import evaluate, load_dataset_naming_pattern, load_rules

_ROOT = Path(__file__).resolve().parents[1]
_JCL_DIR = _ROOT / "jcl"
_RULES = load_rules(_ROOT / "config" / "rules.yml")
_NAMING = load_dataset_naming_pattern(_ROOT / "config" / "datasets.yml")


def _evaluate(filename: str):
    job = parse_jcl_file(_JCL_DIR / filename)
    return evaluate(job, _RULES, _NAMING)


def test_poc001_sucesso_has_no_findings():
    findings = _evaluate("poc001_sucesso.jcl")
    assert findings == []


def test_poc002_warning_flags_naming_convention():
    findings = _evaluate("poc002_warning.jcl")
    rule_ids = {f.rule_id for f in findings}
    assert "JCL002" in rule_ids
    naming_finding = next(f for f in findings if f.rule_id == "JCL002")
    assert naming_finding.severity == "medium"
    assert not any(f.severity == "critical" for f in findings)


def test_poc003_bloqueado_flags_prod_delete_as_critical():
    findings = _evaluate("poc003_bloqueado.jcl")
    rule_ids = {f.rule_id for f in findings}
    assert "JCL003" in rule_ids
    prod_delete_finding = next(f for f in findings if f.rule_id == "JCL003")
    assert prod_delete_finding.severity == "critical"


@pytest.mark.parametrize(
    "filename,expected_rule_id",
    [
        ("poc002_warning.jcl", "JCL002"),
        ("poc003_bloqueado.jcl", "JCL003"),
    ],
)
def test_expected_rule_present(filename, expected_rule_id):
    findings = _evaluate(filename)
    assert any(f.rule_id == expected_rule_id for f in findings)
