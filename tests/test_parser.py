from pathlib import Path

from esteira_model_cob.parser import parse_jcl_file

_JCL_DIR = Path(__file__).resolve().parents[1] / "jcl"


def test_parses_job_name_and_class():
    job = parse_jcl_file(_JCL_DIR / "poc001_sucesso.jcl")
    assert job.job_name == "POC001"
    assert job.job_class == "A"
    assert job.msgclass == "X"


def test_parses_step_and_dsn():
    job = parse_jcl_file(_JCL_DIR / "poc001_sucesso.jcl")
    assert len(job.steps) == 1
    step = job.steps[0]
    assert step.pgm == "IEFBR14"
    assert job.all_dsns() == ["ESTM.POC.TU.TESTDATA"]


def test_inline_sysin_data_is_not_parsed_as_statement():
    job = parse_jcl_file(_JCL_DIR / "poc003_bloqueado.jcl")
    assert job.job_name == "POC003"
    assert len(job.steps) == 1
    assert job.steps[0].pgm == "IDCAMS"
    # "DELETE PROD.CLIENTES" e dado inline do SYSIN, nao vira um step/DD
    assert job.all_dsns() == []
    assert "DELETE PROD.CLIENTES" in job.raw_text
