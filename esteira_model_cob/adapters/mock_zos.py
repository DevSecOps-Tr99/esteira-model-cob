"""MockZosAdapter: simula o JES2 para a POC, sem tocar em z/OS real.

Gera JOBID, spool e RC no mesmo formato do exemplo usado na discussao de
arquitetura original, para que a demo (docs/poc-demo.md) funcione ponta a
ponta antes de existir acesso ao mainframe real.
"""

from __future__ import annotations

import itertools

from ..parser import JclJob
from .base import ExecutionAdapter, JobResult

_jobid_sequence = itertools.count(123)


class MockZosAdapter(ExecutionAdapter):
    def submit_job(self, job: JclJob) -> JobResult:
        jobid = f"JOB{next(_jobid_sequence):05d}"
        job_name = job.job_name or "UNKNOWN"

        spool_lines = ["JES2 JOB LOG", "-" * 14, "", jobid, ""]
        for step in job.steps:
            spool_lines.extend(
                [
                    f"IEF236I ALLOC. FOR {job_name} {step.name}",
                    f"IEF142I {job_name} {step.name} - STEP WAS EXECUTED - COND CODE 0000",
                    f"IEF373I STEP/{step.name}/START",
                    f"IEF374I STEP/{step.name}/STOP",
                ]
            )
        spool_lines.extend(["", "COND CODE 0000"])

        return JobResult(jobid=jobid, jobname=job_name, rc="0000", spool="\n".join(spool_lines))
