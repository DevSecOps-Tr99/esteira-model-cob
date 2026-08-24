"""Testa a integracao real com o ProLeap COBOL Parser (via tools/proleap-runner).

Pulado automaticamente quando java/mvn nao estao no PATH, ou quando o
proleap-cobol-parser ainda nao foi instalado no repositorio Maven local
(rode scripts/install_proleap.sh - a biblioteca nao e publicada no Maven
Central, ver esteira_model_cob/cobol_ast/proleap_client.py).
"""

from pathlib import Path

import pytest

from esteira_model_cob.cobol_ast.proleap_client import dump_ast, is_available

_COBOL_SAMPLE = Path(__file__).resolve().parents[1] / "cobol" / "payroll_sample.cbl"

pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="java/mvn ausentes ou proleap-cobol-parser nao instalado - rode scripts/install_proleap.sh",
)


def test_dump_ast_resolves_program_id_and_data_division():
    result = dump_ast(_COBOL_SAMPLE)
    assert result["programId"] == "PAYROLL-SAMPLE"
    assert result["parsedOk"] is True
    assert result["hasDataDivision"] is True
    assert result["hasWorkingStorage"] is True
