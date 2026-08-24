# Roteiro de demonstração

A POC não usa 1 JCL — usa 3, para provar que a esteira **governa** o JCL e
não apenas o executa.

| JCL | Cenário | Resultado esperado |
|---|---|---|
| `jcl/poc001_sucesso.jcl` | `IEFBR14` criando dataset dentro do padrão `ESTM.<APP>.<ENV>.<RESOURCE>` | Quality Gate PASS 100/100, Security Gate PASSED, RC 0000 |
| `jcl/poc002_warning.jcl` | Dataset fora do padrão (`POC.TEST.DATA`) | Quality Gate WARNING (90/100), pipeline segue |
| `jcl/poc003_bloqueado.jcl` | `IDCAMS DELETE PROD.*` | Security Gate FAILED, regra crítica `JCL003` (`prod_dataset_delete`), deploy bloqueado antes do adapter |

## Passo a passo

```bash
pip install -e ".[dev]"

# 1. Validação (Rules Engine + Quality Gate)
python -m esteira_model_cob validate jcl/

# 2. Simulação (MockZosAdapter) - poc003 é bloqueado antes de chegar aqui
python -m esteira_model_cob simulate jcl/

# 3. Evidência (JCL Pipeline Report) por arquivo
python -m esteira_model_cob report jcl/poc001_sucesso.jcl
python -m esteira_model_cob report jcl/poc002_warning.jcl
python -m esteira_model_cob report jcl/poc003_bloqueado.jcl
```

## Roteiro de apresentação ponta a ponta

Dev altera JCL no VS Code → `git push` → Pull Request → GitHub Actions
(`jcl-validation.yml`) → Gitleaks (segredos) → Syntax/Quality Gate → Security
Gate → Simulação (JOBID, RC) → JCL Pipeline Report publicado como artifact
do job → Deploy TU (`develop`) → Aprovação TI (`release/*`) → Aprovação PRD
(`main`) → Audit trail (commit, autor, PR, aprovador, artefato, ambiente,
job, RC, timestamp).

## Por que o workflow não falha "de verdade" no `poc003`

Os passos "Validar JCLs" e "Simular submissão" do workflow usam
`continue-on-error: true` de propósito: eles são a saída *ao vivo* da demo
(mostrar o bloqueio acontecendo), não o gate de saúde do repositório. Quem
garante a saúde do código é o `pytest`, que já testa esse mesmo bloqueio via
assert (`tests/test_rules_engine.py`, `tests/test_adapters.py`) e falha a
build de verdade se a regra parar de funcionar.
