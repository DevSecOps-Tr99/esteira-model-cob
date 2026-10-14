import hashlib
import json
import subprocess

import pytest

from esteira_model_cob.keyvault import KeyVaultError, fetch_secret

_SHOW_OUTPUT = {
    "id": "https://kv-estm-poc.vault.azure.net/secrets/estm-tu-token/0123456789abcdef",
    "value": "token-ficticio-tu",
    "attributes": {"updated": "2026-10-14T12:00:00+00:00"},
}


def _runner(returncode=0, stdout="", stderr=""):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    return run, calls


def test_fetch_secret_reads_value_version_and_fingerprint():
    run, calls = _runner(stdout=json.dumps(_SHOW_OUTPUT))
    secret = fetch_secret("kv-estm-poc", "estm-tu-token", runner=run)

    assert calls[0][1:] == ["keyvault", "secret", "show", "--vault-name", "kv-estm-poc", "--name", "estm-tu-token", "-o", "json"]
    assert secret.value == "token-ficticio-tu"
    assert secret.version == "0123456789abcdef"
    assert secret.updated == "2026-10-14T12:00:00+00:00"
    assert secret.fingerprint == hashlib.sha256(b"token-ficticio-tu").hexdigest()[:12]


def test_fetch_secret_raises_with_az_error_message():
    run, _calls = _runner(returncode=1, stderr="ERROR: (Forbidden) Caller is not authorized")
    with pytest.raises(KeyVaultError, match="Forbidden"):
        fetch_secret("kv-estm-poc", "estm-tu-token", runner=run)
