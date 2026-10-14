"""Parser de JCL baseado em linhas/regex.

Nao implementa a gramatica JCL completa (isso pertenceria a uma ferramenta
como o ProLeap, hoje usado apenas para COBOL - ver cobol_ast/). O objetivo
aqui e extrair o suficiente de um JOB/EXEC/DD para alimentar o rules engine:
nome do job, CLASS/MSGCLASS, steps, PGM/PROC executado e DSNs referenciados.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_JOB_RE = re.compile(r"^//(?P<name>\S+)\s+JOB\b(?P<params>.*)$")
_EXEC_RE = re.compile(r"^//(?P<step>\S+)\s+EXEC\s+(?P<params>.*)$")
_DD_RE = re.compile(r"^//(?P<dd>\S+)\s+DD\s+(?P<params>.*)$")
# (?<![A-Z0-9]) evita casar "CLASS=" dentro de "MSGCLASS=" quando so o
# segundo esta presente - achado testando contra JCL real (job card so com
# MSGCLASS=, sem CLASS=).
_PARAM_RE_TEMPLATE = r"(?<![A-Z0-9]){key}=(\([^)]*\)|[^,\s]+)"


@dataclass
class Dd:
    name: str
    dsn: str | None = None
    disp: str | None = None


@dataclass
class Step:
    name: str
    pgm: str | None = None
    proc: str | None = None
    dds: list[Dd] = field(default_factory=list)


@dataclass
class JclJob:
    job_name: str | None
    job_class: str | None
    msgclass: str | None
    steps: list[Step]
    raw_text: str
    source_path: str | None = None

    def all_dsns(self) -> list[str]:
        return [dd.dsn for step in self.steps for dd in step.dds if dd.dsn]


def _join_continuations(lines: list[str]) -> list[str]:
    """Junta linhas de JCL continuadas (linha anterior termina em vírgula)."""
    logical: list[str] = []
    buffer: str | None = None
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            continue
        if buffer is not None:
            cont = line[2:].lstrip() if line.startswith("//") else line.lstrip()
            buffer += cont
        else:
            buffer = line
        if buffer.endswith(","):
            continue
        logical.append(buffer)
        buffer = None
    if buffer is not None:
        logical.append(buffer)
    return logical


def _extract_param(params: str, key: str) -> str | None:
    match = re.search(_PARAM_RE_TEMPLATE.format(key=key), params)
    if not match:
        return None
    value = match.group(1)
    # So remove os parenteses quando eles envolvem o valor inteiro
    # (DISP=(NEW,CATLG,DELETE) -> NEW,CATLG,DELETE). Um .strip("()") cego
    # corrompe DSNs com geracao relativa de GDG (DSN.NOME(0), DSN.NOME(+1)) -
    # achado testando contra JCL real.
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    return value.strip("'\"")


def parse_jcl(text: str, source_path: str | None = None) -> JclJob:
    logical_lines = _join_continuations(text.splitlines())

    job_name: str | None = None
    job_class: str | None = None
    msgclass: str | None = None
    steps: list[Step] = []
    current_step: Step | None = None

    for line in logical_lines:
        if not line.startswith("//") or line.startswith("//*"):
            continue  # comentario ou dado inline (ex.: conteudo de SYSIN DD *)

        job_match = _JOB_RE.match(line)
        if job_match:
            job_name = job_match.group("name")
            params = job_match.group("params")
            job_class = _extract_param(params, "CLASS")
            msgclass = _extract_param(params, "MSGCLASS")
            continue

        exec_match = _EXEC_RE.match(line)
        if exec_match:
            params = exec_match.group("params")
            pgm = _extract_param(params, "PGM")
            proc = _extract_param(params, "PROC")
            if pgm is None and proc is None:
                bare = params.strip().split(",")[0].strip()
                if bare and "=" not in bare:
                    proc = bare
            current_step = Step(name=exec_match.group("step"), pgm=pgm, proc=proc)
            steps.append(current_step)
            continue

        dd_match = _DD_RE.match(line)
        if dd_match and current_step is not None:
            params = dd_match.group("params")
            current_step.dds.append(
                Dd(
                    name=dd_match.group("dd"),
                    dsn=_extract_param(params, "DSN"),
                    disp=_extract_param(params, "DISP"),
                )
            )
            continue

    return JclJob(
        job_name=job_name,
        job_class=job_class,
        msgclass=msgclass,
        steps=steps,
        raw_text=text,
        source_path=source_path,
    )


def parse_jcl_file(path: str | Path) -> JclJob:
    path = Path(path)
    return parse_jcl(path.read_text(encoding="utf-8"), source_path=str(path))
