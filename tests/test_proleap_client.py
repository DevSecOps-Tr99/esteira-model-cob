"""Testa a integracao real com o ProLeap COBOL Parser (via tools/proleap-runner).

Pulado automaticamente quando java/mvn nao estao no PATH - e o caso desta
maquina de desenvolvimento. Roda de verdade no GitHub Actions, onde o
workflow instala o JDK sob demanda com actions/setup-java.
"""

from pathlib import Path
import shutil

import pytest

from esteira_model_cob.cobol_ast.proleap_client import dump_ast

_COBOL_SAMPLE = Path(__file__).resolve().parents[1] / "cobol" / "payroll_sample.cbl"

pytestmark = pytest.mark.skipif(
    shutil.which("java") is None or shutil.which("mvn") is None,
    reason="java e/ou mvn nao disponiveis nesta maquina - integracao ProLeap roda no CI",
)


def test_dump_ast_resolves_program_id_and_data_division():
    result = dump_ast(_COBOL_SAMPLE)
    assert result["programId"] == "PAYROLL-SAMPLE"
    assert result["parsedOk"] is True
    assert result["hasDataDivision"] is True
    assert result["hasWorkingStorage"] is True
