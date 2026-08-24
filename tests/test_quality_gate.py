from esteira_model_cob.quality_gate import compute_score
from esteira_model_cob.rules_engine import Finding
from esteira_model_cob.security import evaluate_security


def test_no_findings_is_pass_with_full_score():
    result = compute_score([])
    assert result.status == "PASS"
    assert result.score == 100


def test_medium_finding_is_warning():
    findings = [Finding("JCL002", "naming_convention", "medium", "fora do padrao")]
    result = compute_score(findings)
    assert result.status == "WARNING"
    assert result.score == 90


def test_critical_finding_is_failed_and_blocks_security():
    findings = [Finding("JCL003", "prod_dataset_delete", "critical", "delete em PROD")]
    result = compute_score(findings)
    assert result.status == "FAILED"
    assert result.score == 0

    security = evaluate_security(findings)
    assert security.status == "FAILED"
    assert security.blocking_findings == findings
