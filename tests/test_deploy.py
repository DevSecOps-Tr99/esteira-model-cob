import json
import subprocess
from pathlib import Path

import pytest

from esteira_model_cob.deploy import DeployError, deploy, render_summary
from esteira_model_cob.deploy_targets import file_name_for, load_deploy_targets
from esteira_model_cob.remote import SshTarget

_ROOT = Path(__file__).resolve().parents[1]

_SUBMIT_OUTPUT = {
    "jobid": "JOB00001",
    "jobname": "ESTMX001",
    "rc": "0000",
    "member": "ESTMX001",
    "library": "ESTM.POC.TU.JCLLIB",
    "spool": "JES2 JOB LOG",
}


class FakeServer:
    """Responde aos comandos ssh/scp como o servidor da POC responderia."""

    def __init__(self, submit_rc=0):
        self.calls = []
        self.submit_rc = submit_rc

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        remote_command = cmd[-1]
        if cmd[0] == "scp":
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if remote_command.startswith("printf"):
            return subprocess.CompletedProcess(cmd, 0, stdout="vm-estm-alvo|estmtu|2026-10-14T12:00:00Z", stderr="")
        if remote_command.startswith("estm-submit"):
            if self.submit_rc:
                return subprocess.CompletedProcess(cmd, self.submit_rc, stdout="", stderr="token invalido")
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(_SUBMIT_OUTPUT), stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def _target(server, tmp_path):
    return SshTarget(
        host="10.60.1.10",
        user="estmtu",
        key_path=tmp_path / "ssh-key",
        known_hosts_path=tmp_path / "known_hosts",
        runner=server,
    )


def _deploy(server, tmp_path):
    jcl = tmp_path / "ESTMX001TU.jcl"
    jcl.write_text("//ESTMX001 JOB 'A','B',MSGCLASS=X\n//STEP01 EXEC PGM=SORT\n", encoding="utf-8")
    return deploy(
        [jcl],
        environment="TU",
        target=_target(server, tmp_path),
        remote_base="/srv/estm/TU",
        publication="7-abcdef12",
        token="token-ficticio-tu",
        library="ESTM.POC.TU.JCLLIB",
        manifest={"ambiente": "TU", "commit": "abcdef1234"},
        workdir=tmp_path / "publicacao",
    )


def test_deploy_logs_in_copies_and_submits_with_token_on_stdin(tmp_path):
    server = FakeServer()
    report = _deploy(server, tmp_path)

    assert report.login.remote_user == "estmtu"
    assert report.remote_dir == "/srv/estm/TU/7-abcdef12"
    assert report.transferred == ["ESTMX001TU.jcl", "MANIFEST.txt"]
    assert report.submits[0].jobid == "JOB00001"

    ssh_cmd = server.calls[0][0]
    assert "StrictHostKeyChecking=yes" in ssh_cmd
    assert "estmtu@10.60.1.10" in ssh_cmd

    submit_cmd, submit_kwargs = server.calls[-1]
    assert submit_cmd[-1] == (
        "estm-submit --env TU --library ESTM.POC.TU.JCLLIB --member ESTMX001 /srv/estm/TU/7-abcdef12/ESTMX001TU.jcl"
    )
    # token so pelo stdin, nunca na linha de comando
    assert submit_kwargs["input"] == "token-ficticio-tu\n"
    assert all("token-ficticio-tu" not in " ".join(cmd) for cmd, _ in server.calls)

    manifest = (tmp_path / "publicacao" / "MANIFEST.txt").read_text(encoding="utf-8")
    assert "ambiente=TU" in manifest and "arquivo=ESTMX001TU.jcl" in manifest

    summary = render_summary(report)
    assert "vm-estm-alvo" in summary and "JOB00001" in summary


def test_deploy_fails_when_server_rejects_token(tmp_path):
    with pytest.raises(DeployError, match="token invalido"):
        _deploy(FakeServer(submit_rc=3), tmp_path)


def test_file_name_per_environment_follows_config():
    config = load_deploy_targets(_ROOT / "config" / "deploy_targets.yml")
    assert file_name_for(config, "jcl", "ESTMX001", "TU") == "ESTMX001TU.jcl"
    assert file_name_for(config, "jcl", "ESTMX001", "PRD") == "ESTMX001PRD.jcl"
