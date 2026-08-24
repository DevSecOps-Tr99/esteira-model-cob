# Como rodar a esteira manualmente

Sequência de comandos para validar o POC localmente, sem depender do GitHub Actions.

## 1. Instalar

```bash
pip install -e ".[dev]"
```

## 2. Rodar os testes

```bash
pytest -q
```

Esperado: todos os testes passam. `tests/test_proleap_client.py` aparece como `SKIPPED` se `java`/`mvn` não estiverem no PATH — ele só roda de verdade no GitHub Actions (ou na VM de validação, ver `docs/ambiente-validacao.md`).

## 3. Validar os JCLs

```bash
python -m esteira_model_cob validate jcl/
```

Esperado (os 3 JCLs de exemplo cobrem os 3 veredictos possíveis):

| JCL | Quality Gate | Security Gate |
|---|---|---|
| `poc001_sucesso.jcl` | PASS (100/100) | PASSED |
| `poc002_warning.jcl` | WARNING (90/100) — dataset fora do padrão `ESTM.<APP>.<ENV>.<RESOURCE>` | PASSED |
| `poc003_bloqueado.jcl` | FAILED (0/100) — CRITICAL: delete de dataset em qualifier `PROD.*` | FAILED |

O comando sai com exit code `1` por causa do `poc003` — comportamento esperado, é o que trava o pipeline no CI.

## 4. Simular o deploy

```bash
python -m esteira_model_cob simulate jcl/
```

Esperado: `poc001` e `poc002` são "submetidos" ao `MockZosAdapter` (JOBID + RC `0000` simulados). `poc003` é bloqueado **antes** de chegar no adapter, pelo Quality/Security Gate. Exit code `1`.

## 5. Gerar os relatórios

```bash
python -m esteira_model_cob report jcl/
```

Gera um `reports/<JOB>_report.txt` por JCL (pasta `reports/` é gitignored). Cada relatório traz quality, security, execução e status final (PASS / WARNING / BLOCKED).

## Atalho

`scripts/run_local_pipeline.sh` roda os passos 3–5 em sequência (sem instalar nem testar).

## ProLeap (opcional, precisa de java + mvn)

```bash
bash scripts/install_proleap.sh
python -m esteira_model_cob cobol-ast cobol/payroll_sample.cbl
```
