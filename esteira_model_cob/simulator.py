"""Dry-run / simulacao: so submete ao adapter se o Quality Gate nao FAILED.

Para poc003_bloqueado.jcl isso significa que o deploy e bloqueado antes de
chegar no adapter - o mesmo comportamento descrito no documento original
para o cenario "SECURITY GATE FAILED / Deployment blocked".
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapters.base import ExecutionAdapter, JobResult
from .parser import JclJob
from .quality_gate import QualityGateResult


@dataclass
class SimulationResult:
    executed: bool
    job_result: JobResult | None = None
    reason: str | None = None


def simulate(job: JclJob, quality: QualityGateResult, adapter: ExecutionAdapter) -> SimulationResult:
    if quality.status == "FAILED":
        return SimulationResult(
            executed=False,
            reason="Bloqueado pelo Quality/Security Gate antes da submissao.",
        )
    return SimulationResult(executed=True, job_result=adapter.submit_job(job))
