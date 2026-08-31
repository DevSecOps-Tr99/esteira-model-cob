"""CLI da esteira-model-cob: python -m esteira_model_cob <comando> ...

Comandos espelham o desenho original (python main.py validate/simulate/...):
GitHub Actions e uma camada fina que so chama esses comandos - a logica
inteira vive aqui, nao no YAML do workflow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, binary_guard
from .adapters.mock_zos import MockZosAdapter
from .cobol_ast.proleap_client import ProLeapUnavailableError, dump_ast
from .dependencies import resolve_dependencies
from .deploy_targets import load_deploy_targets, resolve as resolve_deploy_target
from .parser import parse_jcl
from .quality_gate import compute_score
from .report import render_report, write_report
from .rules_engine import evaluate, load_dataset_naming_pattern, load_rules
from .security import evaluate_security
from .simulator import simulate
from .templating import load_env_params, params_for, render as render_template

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RULES_PATH = _REPO_ROOT / "config" / "rules.yml"
_DATASETS_PATH = _REPO_ROOT / "config" / "datasets.yml"
_DEPLOY_TARGETS_PATH = _REPO_ROOT / "config" / "deploy_targets.yml"
_JCL_ENV_PARAMS_PATH = _REPO_ROOT / "config" / "jcl_env_params.yml"
_PROC_DIR = _REPO_ROOT / "proc"


def _iter_jcl_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.glob("*.jcl"))


def _iter_any_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*") if p.is_file())


def _render_for_environment(jcl_path: Path, environment: str) -> str:
    """Aplica esteira_model_cob/templating.py quando o job tiver entrada em
    config/jcl_env_params.yml para este ambiente (ver
    docs/reuniao-endevor-jcl-binarios.md - achado testando contra JCL real:
    mesmo job, so um parametro como SPACE varia por ambiente). Um job sem
    placeholder ${VAR}/sem entrada no config passa direto, sem mudanca.
    """
    raw_text = jcl_path.read_text(encoding="utf-8")
    preview = parse_jcl(raw_text, source_path=str(jcl_path))
    env_config = load_env_params(_JCL_ENV_PARAMS_PATH)
    job_params = params_for(env_config, preview.job_name, environment)
    return render_template(raw_text, job_params) if job_params else raw_text


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
