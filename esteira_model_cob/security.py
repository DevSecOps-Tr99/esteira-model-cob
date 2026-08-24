"""Security Gate: isola achados criticos do Rules Engine como bloqueantes."""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules_engine import Finding


@dataclass
class SecurityVerdict:
    blocking_findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.blocking_findings

    @property
    def status(self) -> str:
        return "PASSED" if self.passed else "FAILED"


def evaluate_security(findings: list[Finding]) -> SecurityVerdict:
    return SecurityVerdict(blocking_findings=[f for f in findings if f.severity == "critical"])
