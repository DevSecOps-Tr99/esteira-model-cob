"""Deploy do JCL renderizado no servidor de destino da POC, via SSH.

Fluxo (ver docs/ambiente-poc-azure.md):

1. login SSH com a chave lida do Key Vault - prova de que a credencial
   funcionou (hostname, usuario remoto e horario do servidor);
2. cria a pasta da publicacao (`<base>/<run>-<sha>`) e transfere os JCLs
   renderizados + MANIFEST.txt por SCP;
3. chama o `estm-submit` do servidor para cada JCL, passando o token lido do
   Key Vault pelo stdin (nunca por argumento, que apareceria no `ps`). O
   servidor confere o token contra o mesmo Key Vault com a managed identity
   dele antes de "submeter" - e o equivalente, na POC, a autenticar no
   z/OSMF e submeter o job (Fase 2, docs/integracao-zos.md).
"""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from .parser import parse_jcl
from .remote import RemoteError, SshTarget

SUBMIT_COMMAND = "estm-submit"


class DeployError(RuntimeError):
    pass


@dataclass
class LoginEvidence:
    hostname: str
    remote_user: str
    remote_time: str


@dataclass
class SubmitResult:
    file: str
    jobid: str
    jobname: str
    rc: str
    member: str
    library: str
    spool: str


@dataclass
class DeployReport:
    environment: str
    address: str
    remote_dir: str
    login: LoginEvidence
    transferred: list[str] = field(default_factory=list)
    submits: list[SubmitResult] = field(default_factory=list)


def ssh_login(target: SshTarget) -> LoginEvidence:
    proc = target.run('printf "%s|%s|%s" "$(hostname)" "$(whoami)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"')
    parts = proc.stdout.strip().split("|")
    if len(parts) != 3:
        raise DeployError(f"resposta inesperada do login SSH: {proc.stdout!r}")
    return LoginEvidence(*parts)


def render_manifest(manifest: dict[str, str], files: list[Path]) -> str:
    lines = [f"{key}={value}" for key, value in manifest.items()]
    lines.extend(f"arquivo={path.name}" for path in files)
    return "\n".join(lines) + "\n"


def deploy(
    files: list[Path],
    *,
    environment: str,
    target: SshTarget,
    remote_base: str,
    publication: str,
    token: str,
    library: str,
    manifest: dict[str, str],
    workdir: Path,
) -> DeployReport:
    try:
        login = ssh_login(target)

        remote_dir = f"{remote_base.rstrip('/')}/{publication}"
        target.run(f"mkdir -p {shlex.quote(remote_dir)}")

        workdir.mkdir(parents=True, exist_ok=True)
        manifest_path = workdir / "MANIFEST.txt"
        manifest_path.write_text(render_manifest(manifest, files), encoding="utf-8")
        target.copy([*files, manifest_path], remote_dir)

        report = DeployReport(
            environment=environment,
            address=f"{target.address}:{target.port}",
            remote_dir=remote_dir,
            login=login,
            transferred=[path.name for path in [*files, manifest_path]],
        )

        for path in files:
            member = parse_jcl(path.read_text(encoding="utf-8")).job_name or path.stem
            command = " ".join(
                [
                    SUBMIT_COMMAND,
                    "--env", shlex.quote(environment),
                    "--library", shlex.quote(library),
                    "--member", shlex.quote(member),
                    shlex.quote(f"{remote_dir}/{path.name}"),
                ]
            )
            proc = target.run(command, stdin=token + "\n", check=False)
            if proc.returncode != 0:
                raise DeployError(
                    f"{SUBMIT_COMMAND} recusou {path.name} (rc {proc.returncode}): "
                    f"{(proc.stderr or proc.stdout).strip()}"
                )
            data = json.loads(proc.stdout)
            report.submits.append(
                SubmitResult(
                    file=path.name,
                    jobid=data["jobid"],
                    jobname=data["jobname"],
                    rc=data["rc"],
                    member=data["member"],
                    library=data["library"],
                    spool=data["spool"],
                )
            )
    except RemoteError as exc:
        raise DeployError(str(exc)) from exc

    return report


def render_summary(report: DeployReport) -> str:
    lines = [
        f"### SSH - login no servidor de destino ({report.environment})",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Destino | `{report.address}` |",
        f"| hostname (remoto) | `{report.login.hostname}` |",
        f"| whoami (remoto) | `{report.login.remote_user}` |",
        f"| Horario do servidor | `{report.login.remote_time}` |",
        f"| Pasta da publicacao | `{report.remote_dir}` |",
        f"| Arquivos transferidos (SCP) | {', '.join(f'`{name}`' for name in report.transferred)} |",
        "",
        "### Submissao (token do Key Vault validado pelo servidor)",
        "",
        "| JCL | JOBID | Job | RC | Membro | Biblioteca |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(
        f"| `{s.file}` | `{s.jobid}` | `{s.jobname}` | `{s.rc}` | `{s.member}` | `{s.library}` |"
        for s in report.submits
    )
    for submit in report.submits:
        lines.extend(["", f"<details><summary>Spool {submit.jobid}</summary>", "", "```", submit.spool, "```", "", "</details>"])
    return "\n".join(lines)
