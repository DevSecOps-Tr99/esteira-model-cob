"""Cliente Python para o wrapper Java em tools/proleap-runner (ProLeap
COBOL Parser - https://github.com/uwol/proleap-cobol-parser, MIT).

Nao roda a JVM embutida em Python: chama `mvn ... exec:java` via subprocess
e le um resumo em JSON impresso no stdout pelo AstDump.java. Se java/mvn
nao estiverem no PATH (caso desta maquina de desenvolvimento), levanta
ProLeapUnavailableError - o restante da esteira (validate/simulate de JCL)
continua funcionando normalmente sem isso. No GitHub Actions o workflow
instala o JDK sob demanda via actions/setup-java, entao o comando roda de
verdade em CI.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parents[2] / "tools" / "proleap-runner"
_MAIN_CLASS = "com.esteiramodelcob.proleap.AstDump"


class ProLeapUnavailableError(RuntimeError):
    """java e/ou mvn nao encontrados no PATH."""


def dump_ast(cobol_file: str | Path) -> dict:
    if shutil.which("java") is None or shutil.which("mvn") is None:
        raise ProLeapUnavailableError(
            "java e/ou mvn nao encontrados no PATH. Instale um JDK 17+ e o Maven para "
            "rodar localmente, ou execute via GitHub Actions (actions/setup-java)."
        )

    cobol_path = Path(cobol_file).resolve()
    if not cobol_path.exists():
        raise FileNotFoundError(f"Arquivo COBOL nao encontrado: {cobol_path}")

    result = subprocess.run(
        [
            "mvn",
            "-q",
            "-f",
            str(_RUNNER_DIR / "pom.xml"),
            "compile",
            "exec:java",
            f"-Dexec.mainClass={_MAIN_CLASS}",
            f"-Dexec.args={cobol_path}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Falha ao executar o ProLeap runner:\n{result.stderr}")

    json_line = next(
        (line for line in reversed(result.stdout.strip().splitlines()) if line.startswith("{")),
        None,
    )
    if json_line is None:
        raise RuntimeError(f"Saida inesperada do ProLeap runner:\n{result.stdout}")

    return json.loads(json_line)
