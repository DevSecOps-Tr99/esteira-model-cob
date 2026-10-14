"""Leitura de segredos do Azure Key Vault via `az` CLI.

Mesmo contrato da esteira corporativa (azure/login com o JSON do SPN e
depois leitura dos segredos pelo nome guardado em uma variable do GitHub -
ver docs/ambiente-poc-azure.md): o workflow so faz o `azure/login`; quem le
o Key Vault, mascara o valor no log e registra a evidencia e esta camada.

O valor do segredo nunca e impresso. A evidencia de que ele foi lido e o
nome, a versao, a data de atualizacao e os 12 primeiros caracteres do
SHA-256 do valor - suficiente para conferir contra o portal do Azure sem
expor o segredo.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

Runner = Callable[..., subprocess.CompletedProcess]


class KeyVaultError(RuntimeError):
    pass


@dataclass
class Secret:
    vault: str
    name: str
    value: str
    version: str
    updated: str

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()[:12]


def fetch_secret(vault: str, name: str, runner: Runner = subprocess.run) -> Secret:
    az = shutil.which("az") or "az"
    cmd = [az, "keyvault", "secret", "show", "--vault-name", vault, "--name", name, "-o", "json"]
    proc = runner(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise KeyVaultError(f"falha ao ler '{name}' do Key Vault '{vault}': {proc.stderr.strip()}")

    data = json.loads(proc.stdout)
    return Secret(
        vault=vault,
        name=name,
        value=data["value"],
        version=data["id"].rstrip("/").rsplit("/", 1)[-1],
        updated=(data.get("attributes") or {}).get("updated") or "",
    )
