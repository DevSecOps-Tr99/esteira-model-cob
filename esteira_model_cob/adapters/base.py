"""Interface de execucao - trocada entre Mock (POC) e Zosmf (Fase 2) sem
tocar no motor de regras. Ver docs/integracao-zos.md."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..parser import JclJob


@dataclass
class JobResult:
    jobid: str
    jobname: str
    rc: str
    spool: str


class ExecutionAdapter(ABC):
    @abstractmethod
    def submit_job(self, job: JclJob) -> JobResult:
        raise NotImplementedError
