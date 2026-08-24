"""Cliente Python para o wrapper Java em tools/proleap-runner (ProLeap
COBOL Parser - https://github.com/uwol/proleap-cobol-parser, MIT).

Nao roda a JVM embutida em Python: chama `mvn ... exec:java` via subprocess
e le um resumo em JSON impresso no stdout pelo AstDump.java. Se java/mvn
nao estiverem no PATH, ou se o proleap-cobol-parser ainda nao tiver sido
instalado no repositorio Maven local, levanta ProLeapUnavailableError - o
restante da esteira (validate/simulate de JCL) continua funcionando
normalmente sem isso.

IMPORTANTE: o proleap-cobol-parser NAO e publicado no Maven Central em
nenhuma versao (nem a 4.0.0 do pom.xml atual, nem a ultima tag v2.4.0 -
confirmado consultando https://repo.maven.apache.org e a Maven Central
Search API diretamente). Por isso e preciso compilar e instalar a
biblioteca no repositorio Maven local antes de usar este modulo - rode
scripts/install_proleap.sh uma vez (localmente ou no workflow de CI, apos
o actions/setup-java).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parents[2] / "tools" / "proleap-runner"
_MAIN_CLASS = "com.esteiramodelcob.proleap.AstDump"
_PROLEAP_LOCAL_REPO = (
    Path.home() / ".m2" / "repository" / "io" / "github" / "uwol" / "proleap-cobol-parser"
)


class ProLeapUnavailableError(RuntimeError):
    """java/mvn ausentes no PATH, ou proleap-cobol-parser nao instalado no ~/.m2."""


def _proleap_jar_installed() -> bool:
    # So a presenca do diretorio nao basta: uma tentativa anterior do Maven
    # contra o Central deixa para tras um diretorio com apenas arquivos
    # ".lastUpdated" (cache de falha), sem nenhum .jar de verdade.
    return _PROLEAP_LOCAL_REPO.exists() and any(_PROLEAP_LOCAL_REPO.glob("*/*.jar"))


def is_available() -> bool:
    return (
        shutil.which("java") is not None
        and shutil.which("mvn") is not None
        and _proleap_jar_installed()
    )


def dump_ast(cobol_file: str | Path) -> dict:
    if shutil.which("java") is None or shutil.which("mvn") is None:
        raise ProLeapUnavailableError(
            "java e/ou mvn nao encontrados no PATH. Instale um JDK 17+ e o Maven para "
            "rodar localmente, ou execute via GitHub Actions (actions/setup-java)."
        )
    if not _proleap_jar_installed():
        raise ProLeapUnavailableError(
            "proleap-cobol-parser nao esta instalado no repositorio Maven local "
            f"({_PROLEAP_LOCAL_REPO}). Rode scripts/install_proleap.sh primeiro - a "
            "biblioteca nao e publicada no Maven Central, precisa ser compilada da fonte."
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
