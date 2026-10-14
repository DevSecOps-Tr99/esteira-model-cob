"""Integracao minima com o runner do GitHub Actions (workflow commands e
arquivos de ambiente). Fora do Actions (rodando local) tudo aqui vira no-op,
exceto a mascara, que so imprime uma linha que o terminal ignora.
"""

from __future__ import annotations

import os


def add_mask(value: str) -> None:
    """Pede ao runner para mascarar o valor em todo o log do job. Valores
    com varias linhas (chave privada) sao mascarados linha a linha - o
    runner nao mascara um bloco multi-linha como um todo."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    for line in value.splitlines():
        if line.strip():
            print(f"::add-mask::{line.strip()}", flush=True)


def append_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(markdown.rstrip() + "\n\n")


def set_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")
