"""Transporte SSH/SCP para o servidor de destino.

Mesmo padrao da esteira corporativa para Linux: usuario de deploy em uma
variable do GitHub, chave privada no Key Vault, host key conferida contra um
known_hosts fixo (nunca StrictHostKeyChecking=no). Usa os binarios `ssh` e
`scp` do runner - sem dependencia Python extra.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

Runner = Callable[..., subprocess.CompletedProcess]


class RemoteError(RuntimeError):
    pass


@dataclass
class SshTarget:
    host: str
    user: str
    key_path: Path
    known_hosts_path: Path
    port: int = 22
    runner: Runner = field(default=subprocess.run, repr=False)

    def _options(self) -> list[str]:
        return [
            "-i", str(self.key_path),
            "-o", "IdentitiesOnly=yes",
            "-o", f"UserKnownHostsFile={self.known_hosts_path}",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=15",
            "-o", "LogLevel=ERROR",
        ]

    @property
    def address(self) -> str:
        return f"{self.user}@{self.host}"

    def run(self, command: str, stdin: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["ssh", *self._options(), "-p", str(self.port), self.address, command]
        proc = self.runner(cmd, input=stdin, capture_output=True, text=True)
        if check and proc.returncode != 0:
            raise RemoteError(f"ssh {self.address} '{command}' saiu com {proc.returncode}: {proc.stderr.strip()}")
        return proc

    def copy(self, files: list[Path], remote_dir: str) -> None:
        cmd = ["scp", *self._options(), "-P", str(self.port), *map(str, files), f"{self.address}:{remote_dir}/"]
        proc = self.runner(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RemoteError(f"scp para {self.address}:{remote_dir} saiu com {proc.returncode}: {proc.stderr.strip()}")
