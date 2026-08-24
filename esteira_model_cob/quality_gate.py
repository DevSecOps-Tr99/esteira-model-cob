"""Quality Gate: agrega achados do Rules Engine em um score e veredito."""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules_engine import Finding

_PENALTY = {"critical": 100, "high": 20, "medium": 10, "low": 5}


@dataclass
class QualityGateResult:
    score: int
    status: str  # PASS | WARNING | FAILED
    findings: list[Finding] = field(default_factory=list)


def compute_score(findings: list[Finding]) -> QualityGateResult:
    score = 100
    has_critical = False

    for finding in findings:
        score -= _PENALTY.get(finding.severity, 0)
        has_critical = has_critical or finding.severity == "critical"

    score = max(score, 0)

    if has_critical:
        status = "FAILED"
    elif findings:
        status = "WARNING"
    else:
        status = "PASS"

    return QualityGateResult(score=score, status=status, findings=findings)
