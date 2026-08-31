"""JCL Pipeline Report: evidencia textual de um run, no formato usado na
discussao de arquitetura original (Quality / Security / Execution / Status).
Grava em reports/ (gitignored) para auditoria local; no GitHub Actions, o
workflow sobe esse diretorio como artifact do job.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .deploy_targets import DeployTarget
from .parser import JclJob
from .quality_gate import QualityGateResult
from .security import SecurityVerdict
from .simulator import SimulationResult


def render_report(
    job: JclJob,
    quality: QualityGateResult,
    security: SecurityVerdict,
    simulation: SimulationResult,
    deploy: DeployTarget | None = None,
) -> str:
    lines: list[str] = []
    lines.append("JCL PIPELINE REPORT")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"JCL .................. {job.source_path or '-'}")
    lines.append(f"Job name ............. {job.job_name or '-'}")
    lines.append("")

    lines.append("QUALITY")
    lines.append("-" * 40)
    if quality.findings:
        for finding in quality.findings:
            lines.append(f"[{finding.severity.upper():<8}] {finding.rule_id} {finding.name}: {finding.message}")
    else:
        lines.append("Nenhum achado - todas as validacoes PASS.")
    lines.append(f"Score ................ {quality.score}/100")
    lines.append("")

    lines.append("SECURITY")
    lines.append("-" * 40)
    lines.append(f"Status ............... {security.status}")
    for finding in security.blocking_findings:
        lines.append(f"  BLOQUEANTE: {finding.rule_id} - {finding.message}")
    lines.append("")

    lines.append("EXECUTION")
    lines.append("-" * 40)
    if simulation.executed and simulation.job_result:
        lines.append(f"Job .................. {simulation.job_result.jobid}")
        lines.append(f"RC ................... {simulation.job_result.rc}")
    else:
        lines.append(f"Execucao ............. NAO EXECUTADO ({simulation.reason})")
    lines.append("")

    if deploy is not None:
        lines.append("DEPLOY")
        lines.append("-" * 40)
        lines.append(f"Ambiente ............. {deploy.environment}")
        lines.append(f"Biblioteca-alvo ...... {deploy.library}")
        lines.append(f"Modo de transferencia . {deploy.copy_mode.upper()}")
        lines.append("")

    overall = "APPROVED" if security.passed and quality.status != "FAILED" else "BLOCKED"
    lines.append("STATUS")
    lines.append("=" * 40)
    lines.append(overall)
    lines.append("")
    lines.append(f"Gerado em: {datetime.now(timezone.utc).isoformat()}")

    return "\n".join(lines)


def write_report(report_text: str, job_name: str | None, reports_dir: str | Path = "reports") -> Path:
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    out_file = reports_path / f"{job_name or 'job'}_report.txt"
    out_file.write_text(report_text, encoding="utf-8")
    return out_file
