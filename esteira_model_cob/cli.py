"""CLI da esteira-model-cob: python -m esteira_model_cob <comando> ...

Comandos espelham o desenho original (python main.py validate/simulate/...):
GitHub Actions e uma camada fina que so chama esses comandos - a logica
inteira vive aqui, nao no YAML do workflow.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, binary_guard
from .adapters.mock_zos import MockZosAdapter
from .cobol_ast.proleap_client import ProLeapUnavailableError, dump_ast
from .dependencies import resolve_dependencies
from .deploy import DeployError, deploy, render_summary
from .deploy_targets import file_name_for, load_deploy_targets, resolve as resolve_deploy_target
from .gh_actions import add_mask, append_summary, set_output
from .keyvault import KeyVaultError, fetch_secret
from .parser import parse_jcl
from .quality_gate import compute_score
from .remote import SshTarget
from .report import render_report, write_report
from .rules_engine import evaluate, load_dataset_naming_pattern, load_rules
from .security import evaluate_security
from .simulator import simulate
from .templating import (
    ResolvedParams,
    load_env_params,
    params_for,
    params_from_github_vars,
    placeholders,
    render as render_template,
    resolve_params,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RULES_PATH = _REPO_ROOT / "config" / "rules.yml"
_DATASETS_PATH = _REPO_ROOT / "config" / "datasets.yml"
_DEPLOY_TARGETS_PATH = _REPO_ROOT / "config" / "deploy_targets.yml"
_JCL_ENV_PARAMS_PATH = _REPO_ROOT / "config" / "jcl_env_params.yml"
_PROC_DIR = _REPO_ROOT / "proc"

# O workflow repassa toJSON(vars) nesta variavel de ambiente; so as
# variables JCL_* viram parametro de JCL (ver templating.py).
_GITHUB_VARS_ENV = "ESTM_GITHUB_VARS"
_ENV_PARAMS_ENV = "ESTM_JCL_ENV_PARAMS"

_ENVIRONMENTS = ["TU", "TI", "PRD"]


def _iter_jcl_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.glob("*.jcl"))


def _iter_any_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*") if p.is_file())


def _env_params_path() -> Path:
    """Os parametros por ambiente pertencem ao repositorio de JCL (o caller
    do workflow reutilizavel), nao ao motor: o workflow aponta
    ESTM_JCL_ENV_PARAMS para o config/jcl_env_params.yml de la. Sem a
    variavel, usa o do proprio motor (JCLs de demonstracao em jcl/)."""
    override = os.environ.get(_ENV_PARAMS_ENV)
    return Path(override) if override else _JCL_ENV_PARAMS_PATH


def _resolve_params(raw_text: str, job_name: str | None, environment: str) -> ResolvedParams:
    path = _env_params_path()
    env_config = load_env_params(path) if path.exists() else {}
    config_params = params_for(env_config, job_name, environment)
    # GitHub variables so entram em JCL que de fato tem placeholder - um JCL
    # sem ${VAR} pode ter "$" legitimo em nome de dataset/membro.
    github_params = params_from_github_vars(os.environ.get(_GITHUB_VARS_ENV)) if placeholders(raw_text) else {}
    return resolve_params(config_params, github_params)


def _render_for_environment(jcl_path: Path, environment: str) -> str:
    """Aplica esteira_model_cob/templating.py quando o job tiver parametros
    para este ambiente - em config/jcl_env_params.yml ou nas GitHub
    variables JCL_* (ver docs/reuniao-endevor-jcl-binarios.md - achado
    testando contra JCL real: mesmo job, so alguns parametros variam por
    ambiente). Um job sem placeholder ${VAR}/sem parametros passa direto.
    """
    raw_text = jcl_path.read_text(encoding="utf-8")
    preview = parse_jcl(raw_text, source_path=str(jcl_path))
    resolved = _resolve_params(raw_text, preview.job_name, environment)
    return render_template(raw_text, resolved.values) if resolved.values else raw_text


def _run_gates(jcl_path: Path, environment: str = "TU"):
    text = _render_for_environment(jcl_path, environment)
    job = parse_jcl(text, source_path=str(jcl_path))
    rules = load_rules(_RULES_PATH)
    naming_pattern = load_dataset_naming_pattern(_DATASETS_PATH)

    findings = evaluate(job, rules, naming_pattern)
    quality = compute_score(findings)
    security = evaluate_security(findings)
    deps = resolve_dependencies(job, _PROC_DIR)

    return job, quality, security, deps


def cmd_validate(args: argparse.Namespace) -> int:
    target = Path(args.path)
    exit_code = 0

    for jcl_path in _iter_jcl_files(target):
        job, quality, security, deps = _run_gates(jcl_path, args.env)

        print(f"\n{jcl_path.name}")
        print(f"  Job .............. {job.job_name}")
        print(f"  Quality Gate ..... {quality.status} ({quality.score}/100)")
        for finding in quality.findings:
            print(f"    [{finding.severity.upper():<8}] {finding.rule_id} {finding.name}: {finding.message}")
        print(f"  Security Gate .... {security.status}")
        if deps.missing:
            print(f"  Dependencias ..... FALTANDO: {', '.join(deps.missing)}")

        if quality.status == "FAILED":
            exit_code = 1

    return exit_code


def cmd_simulate(args: argparse.Namespace) -> int:
    target = Path(args.path)
    adapter = MockZosAdapter()
    exit_code = 0

    for jcl_path in _iter_jcl_files(target):
        job, quality, security, _deps = _run_gates(jcl_path, args.env)
        result = simulate(job, quality, adapter)

        print(f"\n{jcl_path.name}")
        if result.executed and result.job_result:
            print(f"  JOBID ............ {result.job_result.jobid}")
            print(f"  RC ............... {result.job_result.rc}")
        else:
            print(f"  BLOQUEADO: {result.reason}")
            exit_code = 1

    return exit_code


def cmd_report(args: argparse.Namespace) -> int:
    target = Path(args.path)
    adapter = MockZosAdapter()
    deploy_config = load_deploy_targets(_DEPLOY_TARGETS_PATH)

    for jcl_path in _iter_jcl_files(target):
        job, quality, security, _deps = _run_gates(jcl_path, args.env)
        simulation = simulate(job, quality, adapter)
        deploy = resolve_deploy_target(deploy_config, "jcl", args.env)
        report_text = render_report(job, quality, security, simulation, deploy)
        out_file = write_report(report_text, job.job_name)
        print(f"Relatorio gerado: {out_file}")

    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Gera um arquivo por ambiente a partir do modelo (ESTMX001.jcl ->
    build/TU/ESTMX001TU.jcl) e mostra de onde veio cada valor."""
    deploy_config = load_deploy_targets(_DEPLOY_TARGETS_PATH)
    out_dir = Path(args.out) / args.env
    out_dir.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    written: list[str] = []

    for jcl_path in _iter_jcl_files(Path(args.path)):
        raw_text = jcl_path.read_text(encoding="utf-8")
        job_name = parse_jcl(raw_text).job_name or jcl_path.stem.upper()
        resolved = _resolve_params(raw_text, job_name, args.env)
        names = placeholders(raw_text)

        missing = [name for name in names if name not in resolved.values]
        if missing:
            print(
                f"\n{jcl_path.name}: sem valor em {args.env} para {', '.join(missing)} - defina "
                f"{', '.join('JCL_' + name for name in missing)} nas variables do Environment "
                f"{args.env} ou em config/jcl_env_params.yml",
                file=sys.stderr,
            )
            exit_code = 1
            continue

        text = render_template(raw_text, resolved.values) if resolved.values else raw_text
        out_file = out_dir / file_name_for(deploy_config, "jcl", job_name, args.env)
        out_file.write_text(text, encoding="utf-8")
        written.append(out_file.as_posix())

        print(f"\n{jcl_path.name} -> {out_file.as_posix()}")
        for name in names:
            print(f"  {name:<16} = {resolved.values[name]:<20} ({resolved.origins[name]})")

        rows = "\n".join(f"| `{name}` | `{resolved.values[name]}` | {resolved.origins[name]} |" for name in names)
        append_summary(
            f"### JCL renderizado para {args.env}: `{out_file.name}`\n\n"
            f"Modelo `{jcl_path.as_posix()}`, membro `{job_name}`.\n\n"
            f"| Placeholder | Valor | Origem |\n|---|---|---|\n{rows}\n\n"
            f"<details><summary>{out_file.name}</summary>\n\n```jcl\n{text.rstrip()}\n```\n\n</details>"
        )

    set_output("arquivos", " ".join(written))
    return exit_code


def cmd_kv_fetch(args: argparse.Namespace) -> int:
    """Le os segredos do Key Vault (az CLI ja autenticado pelo azure/login),
    mascara no log e grava cada um em <out>/<apelido> com permissao 0600."""
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    rows: list[str] = []

    for spec in args.secret:
        alias, _, name = spec.partition("=")
        if not alias or not name:
            print(f"--secret '{spec}' invalido: use <apelido>=<nome-do-segredo> (variable vazia?)", file=sys.stderr)
            return 1
        try:
            secret = fetch_secret(args.vault, name)
        except KeyVaultError as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            return 1

        add_mask(secret.value)
        value = secret.value if secret.value.endswith("\n") else secret.value + "\n"
        path = out_dir / alias
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)

        print(
            f"  {alias:<8} <- {secret.vault}/{secret.name}  versao {secret.version[:8]}  "
            f"atualizado {secret.updated}  sha256:{secret.fingerprint}"
        )
        rows.append(
            f"| {alias} | `{secret.name}` | `{secret.version[:8]}` | {secret.updated} | `{secret.fingerprint}` |"
        )

    append_summary(
        f"### Key Vault `{args.vault}` - credenciais obtidas\n\n"
        "O valor nunca aparece no log (mascarado). A impressao digital e o inicio do "
        "SHA-256 do valor, para conferir contra o segredo no portal do Azure.\n\n"
        "| Credencial | Segredo | Versao | Atualizado em | SHA-256 (12) |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
    )
    return 0


def cmd_deploy(args: argparse.Namespace) -> int:
    files = _iter_jcl_files(Path(args.path))
    if not files:
        print(f"Nenhum .jcl em {args.path}", file=sys.stderr)
        return 1

    # Gate de novo, sobre o arquivo final: nada chega ao servidor sem passar.
    for jcl_path in files:
        _job, quality, _security, _deps = _run_gates(jcl_path, args.env)
        if quality.status == "FAILED":
            print(f"{jcl_path.name}: Quality Gate FAILED - deploy bloqueado", file=sys.stderr)
            return 1

    cred_dir = Path(args.cred_dir)
    known_hosts = cred_dir / "known_hosts"
    known_hosts.write_text(args.known_hosts.strip() + "\n", encoding="utf-8")
    target = SshTarget(
        host=args.host,
        user=args.user,
        key_path=cred_dir / "ssh-key",
        known_hosts_path=known_hosts,
        port=args.port,
    )
    token = (cred_dir / "token").read_text(encoding="utf-8").strip()
    library = resolve_deploy_target(load_deploy_targets(_DEPLOY_TARGETS_PATH), "jcl", args.env).library

    sha = os.environ.get("GITHUB_SHA", "local")
    manifest = {
        "ambiente": args.env,
        "commit": sha,
        "ref": os.environ.get("GITHUB_REF_NAME", ""),
        "autor": os.environ.get("GITHUB_ACTOR", ""),
        "run": os.environ.get("GITHUB_RUN_ID", ""),
        "publicado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        report = deploy(
            files,
            environment=args.env,
            target=target,
            remote_base=args.remote_dir,
            publication=f"{os.environ.get('GITHUB_RUN_NUMBER', '0')}-{sha[:8]}",
            token=token,
            library=library,
            manifest=manifest,
            workdir=cred_dir / "publicacao",
        )
    except DeployError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(f"Login SSH ........ {report.address} (hostname {report.login.hostname}, whoami {report.login.remote_user})")
    print(f"Publicado em ..... {report.remote_dir}")
    for submit in report.submits:
        print(f"{submit.file}: JOBID {submit.jobid} RC {submit.rc} -> {submit.library}({submit.member})")
    append_summary(render_summary(report))
    return 0


def cmd_binary_guard(args: argparse.Namespace) -> int:
    """Varre bytes crus (EBCDIC) em busca de caracteres de controle
    hard-coded - ver esteira_model_cob/binary_guard.py. Nao roda sobre o
    JCL ASCII/UTF-8 de jcl/ (validate/report cuidam desse caminho); e para
    bytes ja baixados do mainframe (ou, nesta POC, as fixtures em
    tests/fixtures/ geradas por scripts/gen_test_fixtures.py).
    """
    target = Path(args.path)
    exit_code = 0

    for file_path in _iter_any_files(target):
        findings = binary_guard.evaluate(file_path)
        quality = compute_score(findings)
        security = evaluate_security(findings)

        print(f"\n{file_path}")
        print(f"  Quality Gate ..... {quality.status} ({quality.score}/100)")
        for finding in findings:
            print(f"    [{finding.severity.upper():<8}] {finding.rule_id} {finding.name}: {finding.message}")
        print(f"  Security Gate .... {security.status}")

        if quality.status == "FAILED":
            exit_code = 1

    return exit_code


def cmd_cobol_ast(args: argparse.Namespace) -> int:
    try:
        result = dump_ast(args.path)
    except ProLeapUnavailableError as exc:
        print(f"AVISO: {exc}", file=sys.stderr)
        return 0
    print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="esteira-model-cob")
    parser.add_argument("--version", action="version", version=__version__)

    subparsers = parser.add_subparsers(dest="command", required=True)

    _env_help = "Ambiente (resolve config/jcl_env_params.yml e config/deploy_targets.yml)"

    p_validate = subparsers.add_parser("validate", help="Roda o Rules Engine e o Quality Gate")
    p_validate.add_argument("path", help="Arquivo .jcl ou pasta com JCLs")
    p_validate.add_argument("--env", default="TU", choices=["TU", "TI", "PRD"], help=_env_help)
    p_validate.set_defaults(func=cmd_validate)

    p_simulate = subparsers.add_parser("simulate", help="Simula a submissao no MockZosAdapter")
    p_simulate.add_argument("path", help="Arquivo .jcl ou pasta com JCLs")
    p_simulate.add_argument("--env", default="TU", choices=["TU", "TI", "PRD"], help=_env_help)
    p_simulate.set_defaults(func=cmd_simulate)

    p_report = subparsers.add_parser("report", help="Gera o JCL Pipeline Report em reports/")
    p_report.add_argument("path", help="Arquivo .jcl ou pasta com JCLs")
    p_report.add_argument("--env", default="TU", choices=["TU", "TI", "PRD"], help=_env_help)
    p_report.set_defaults(func=cmd_report)

    p_render = subparsers.add_parser("render", help="Gera o JCL final de um ambiente (um arquivo por ambiente)")
    p_render.add_argument("path", help="Arquivo .jcl modelo ou pasta com JCLs")
    p_render.add_argument("--env", default="TU", choices=_ENVIRONMENTS, help=_env_help)
    p_render.add_argument("--out", default="build", help="Pasta de saida (gera <out>/<ENV>/<MEMBRO><ENV>.jcl)")
    p_render.set_defaults(func=cmd_render)

    p_kv = subparsers.add_parser("kv-fetch", help="Le segredos do Azure Key Vault para arquivos 0600 (az ja autenticado)")
    p_kv.add_argument("--vault", required=True, help="Nome do Key Vault")
    p_kv.add_argument(
        "--secret",
        action="append",
        required=True,
        help="<apelido>=<nome-do-segredo>; grava em <out>/<apelido> (repetivel)",
    )
    p_kv.add_argument("--out", required=True, help="Pasta de saida das credenciais")
    p_kv.set_defaults(func=cmd_kv_fetch)

    p_deploy = subparsers.add_parser("deploy", help="Publica o JCL renderizado no servidor de destino via SSH")
    p_deploy.add_argument("path", help="Arquivo .jcl renderizado ou pasta")
    p_deploy.add_argument("--env", required=True, choices=_ENVIRONMENTS, help=_env_help)
    p_deploy.add_argument("--host", required=True)
    p_deploy.add_argument("--user", required=True)
    p_deploy.add_argument("--port", type=int, default=22)
    p_deploy.add_argument("--remote-dir", required=True, help="Pasta base do ambiente no servidor")
    p_deploy.add_argument("--known-hosts", required=True, help="Conteudo do known_hosts do servidor")
    p_deploy.add_argument("--cred-dir", required=True, help="Pasta gerada pelo kv-fetch (ssh-key, token)")
    p_deploy.set_defaults(func=cmd_deploy)

    p_cobol_ast = subparsers.add_parser("cobol-ast", help="Gera o AST de um COBOL via ProLeap")
    p_cobol_ast.add_argument("path", help="Arquivo .cbl")
    p_cobol_ast.set_defaults(func=cmd_cobol_ast)

    p_binary_guard = subparsers.add_parser(
        "binary-guard",
        help="Varre bytes EBCDIC crus em busca de caracteres de controle hard-coded (nao roda sobre JCL ASCII)",
    )
    p_binary_guard.add_argument("path", help="Arquivo ou pasta com bytes EBCDIC crus")
    p_binary_guard.set_defaults(func=cmd_binary_guard)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
