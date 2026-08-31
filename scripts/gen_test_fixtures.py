#!/usr/bin/env python3
"""Gera as fixtures binarias de tests/fixtures/ usadas por
tests/test_binary_guard.py.

Duas fixtures, ambas bytes EBCDIC (codec cp037) genuinos - nao ASCII/UTF-8,
nao digitados a mao, para garantir os valores exatos:

  - copybook_ebcdic_limpo.bin: um trecho de copybook comum, sem nenhum byte
    de controle (todo caractere imprimivel em EBCDIC cai em 0x40-0xFF) -
    prova que o guard nao falso-positiva em EBCDIC legitimo.
  - copybook_ebcdic_hex_declarado.bin: o mesmo trecho com 2 bytes de
    controle inseridos no meio (um "non-printable", um
    "non-roundtrippable" - ver esteira_model_cob/binary_guard.py) -
    simula o achado da esteira Endevor real: alguem ligou o modo hex do
    editor do ISPF/3270 e digitou um valor hexadecimal direto no
    componente.

Ver docs/reuniao-endevor-jcl-binarios.md para o contexto completo. Uso:

    python scripts/gen_test_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "tests" / "fixtures"

_SAMPLE_TEXT = "01  WS-CAMPO       PIC X(10) VALUE SPACES."

# 0x01 = nao imprimivel; 0x25 = nao roundtrippable (ver binary_guard.py)
_NON_PRINTABLE_BYTE = 0x01
_NON_ROUNDTRIPPABLE_BYTE = 0x25


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    clean = _SAMPLE_TEXT.encode("cp037")
    assert not any(b < 0x40 for b in clean), "sample text nao deveria gerar bytes de controle em EBCDIC"

    anomalous = bytearray(clean)
    insert_at = len(anomalous) // 2
    anomalous[insert_at:insert_at] = bytes([_NON_PRINTABLE_BYTE, _NON_ROUNDTRIPPABLE_BYTE])

    clean_path = FIXTURES_DIR / "copybook_ebcdic_limpo.bin"
    hex_path = FIXTURES_DIR / "copybook_ebcdic_hex_declarado.bin"

    clean_path.write_bytes(clean)
    hex_path.write_bytes(bytes(anomalous))

    print(f"Gerado {clean_path} ({len(clean)} bytes)")
    print(f"Gerado {hex_path} ({len(anomalous)} bytes)")


if __name__ == "__main__":
    main()
