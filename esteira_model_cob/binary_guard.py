"""Guarda de binario: detecta bytes de controle EBCDIC hard-coded (o
"caractere declarado em hexadecimal no editor do ISPF/3270" relatado pela
esteira Endevor real do banco - ver docs/reuniao-endevor-jcl-binarios.md)
dentro de um componente, antes de qualquer decodificacao para texto.

Contexto: em EBCDIC (IBM-037/1047, o code page do mainframe), todo
caractere imprimivel - letras, digitos, pontuacao e o proprio espaco
(0x40) - fica no intervalo 0x40-0xFF. O intervalo 0x00-0x3F e inteiramente
controle. Um componente real (JCL, COPY, PROC) nunca deveria ter um byte
nesse intervalo dentro do seu conteudo; se tiver, e porque alguem digitou
um valor hexadecimal diretamente no modo hex do editor do ISPF (HEX ON),
no lugar de, por exemplo, escrever `VALUE X'...'` em COBOL. Nao existe
correspondencia segura desses bytes em ASCII/UTF-8 - qualquer transporte
que nao seja binario corrompe o dado.

A tabela de bytes flagados vem de `desafios-binarios.txt` (compartilhado
pela esteira Endevor real): os 5 valores "non-roundtrippable" e os 59
"non-printable" cobrem juntos, sem sobra, todo o intervalo 0x00-0x3F.

IMPORTANTE - contrato deste modulo: as funcoes aqui assumem bytes EBCDIC
crus (como os lidos direto de um dataset via z/OSMF Files REST API em modo
binario, ou baixados como binario do mainframe). Elas NAO devem ser
chamadas sobre o JCL ASCII/UTF-8 ja versionado em jcl/ desta POC - nesse
alfabeto, os mesmos valores de byte 0x00-0x3F sao digitos ('0'-'9' =
0x30-0x39), pontuacao comum ('%','&', etc.) e outros caracteres
inteiramente legitimos, e o guard geraria falso positivo. Por isso ele
nao e chamado por `cli.py cmd_validate`/`cmd_report` (que operam sobre o
JCL ASCII) - so pelo comando dedicado `binary-guard` e pelos testes, ambos
sobre bytes EBCDIC genuinos (ver `tests/fixtures/`,
`scripts/gen_test_fixtures.py`). A Fase 2 chama isto no ponto exato em que
bytes crus chegam do mainframe, antes de decidir se o componente pode
seguir por um caminho de texto ou precisa permanecer binario ate o deploy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .rules_engine import Finding

NON_ROUNDTRIPPABLE: frozenset[int] = frozenset({0x0D, 0x0E, 0x0F, 0x15, 0x25})
NON_PRINTABLE: frozenset[int] = frozenset(
    set(range(0x00, 0x0D))
    | set(range(0x10, 0x15))
    | set(range(0x16, 0x25))
    | set(range(0x26, 0x40))
)
FLAGGED_BYTES: frozenset[int] = NON_ROUNDTRIPPABLE | NON_PRINTABLE


@dataclass
class BinaryGuardResult:
    path: Path
    flagged_bytes: list[int]

    @property
    def requires_binary_transfer(self) -> bool:
        return bool(self.flagged_bytes)

    @property
    def has_non_roundtrippable(self) -> bool:
        return any(b in NON_ROUNDTRIPPABLE for b in self.flagged_bytes)


def scan_bytes(data: bytes) -> list[int]:
    """Retorna, em ordem, os valores de byte flagados encontrados em `data`.

    `data` deve ser bytes EBCDIC crus - ver contrato no docstring do modulo.
    """
    return sorted({b for b in data if b in FLAGGED_BYTES})


def scan_file(path: str | Path) -> BinaryGuardResult:
    path = Path(path)
    return BinaryGuardResult(path=path, flagged_bytes=scan_bytes(path.read_bytes()))


def to_finding(result: BinaryGuardResult) -> Finding | None:
    if not result.requires_binary_transfer:
        return None
    hex_list = ", ".join(f"0x{b:02X}" for b in result.flagged_bytes)
    kind = "nao roundtrippable" if result.has_non_roundtrippable else "nao imprimivel"
    return Finding(
        rule_id="BIN001",
        name="hex_hardcoded_requires_binary",
        severity="critical",
        message=(
            f"Byte(s) de controle EBCDIC {kind} hard-coded no componente "
            f"({hex_list}) - transporte deve ser binario, nunca texto/UTF-8. "
            "Ver docs/reuniao-endevor-jcl-binarios.md."
        ),
    )


def evaluate(path: str | Path) -> list[Finding]:
    finding = to_finding(scan_file(path))
    return [finding] if finding else []
