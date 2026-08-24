"""Checagem de dependencias: PROCs referenciadas por EXEC PROC=/EXEC <nome>."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .parser import JclJob


@dataclass
class DependencyFinding:
    proc_name: str
    found: bool


@dataclass
class DependencyReport:
    findings: list[DependencyFinding] = field(default_factory=list)

    @property
    def missing(self) -> list[str]:
        return [f.proc_name for f in self.findings if not f.found]


def resolve_dependencies(job: JclJob, proc_dir: str | Path) -> DependencyReport:
    proc_dir = Path(proc_dir)
    findings = [
        DependencyFinding(proc_name=step.proc, found=(proc_dir / f"{step.proc.lower()}.proc").exists())
        for step in job.steps
        if step.proc
    ]
    return DependencyReport(findings=findings)
