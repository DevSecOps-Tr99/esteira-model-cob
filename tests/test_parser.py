from pathlib import Path

from esteira_model_cob.parser import parse_jcl, parse_jcl_file

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


# Regressoes encontradas testando o parser contra JCL real cedido pelo banco
# (jcl/real/ - nao versionado, contem nomes reais de job/dataset). Os casos
# abaixo replicam os padroes com dados ficticios.


def test_msgclass_without_class_is_not_mistaken_for_class():
    """CLASS=" e um substring de "MSGCLASS=" - sem um CLASS= proprio no job
    card, a busca antiga achava o "CLASS=" escondido dentro de MSGCLASS e
    atribuia esse valor a job_class por engano."""
    job = parse_jcl("//JOBX001 JOB 'ACCT,INFO','USER01',MSGCLASS=Z,SCHENV=BATCH\n")
    assert job.job_class is None
    assert job.msgclass == "Z"


def test_bare_proc_name_after_exec_is_captured_as_proc():
    job = parse_jcl("//JOBX001 JOB 'ACCT,INFO','USER01',MSGCLASS=Z\n//STEP01 EXEC SORTPRC\n")
    assert job.steps[0].pgm is None
    assert job.steps[0].proc == "SORTPRC"


def test_dsn_with_gdg_relative_generation_keeps_full_suffix():
    """DSN.NOME(0)/(+1) e uma geracao relativa de GDG - um .strip("()") as
    cegas cortava o ")" final porque ele calha de ser o ultimo caractere,
    mesmo o valor inteiro nao estando entre parenteses."""
    jcl_text = (
        "//JOBX001 JOB 'ACCT,INFO','USER01',MSGCLASS=Z\n"
        "//STEP01  EXEC PGM=IEFBR14\n"
        "//DD01    DD DSN=ESTM.POC.TU.GDGBASE(0),\n"
        "//           DISP=SHR\n"
    )
    job = parse_jcl(jcl_text)
    assert job.all_dsns() == ["ESTM.POC.TU.GDGBASE(0)"]
