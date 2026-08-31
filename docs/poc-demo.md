# Roteiro de demonstração

A POC não usa 1 JCL — usa 3, para provar que a esteira **governa** o JCL e
não apenas o executa.

| JCL | Cenário | Resultado esperado |
|---|---|---|
| `jcl/poc001_sucesso.jcl` | `IEFBR14` criando dataset dentro do padrão `ESTM.<APP>.<ENV>.<RESOURCE>` | Quality Gate PASS 100/100, Security Gate PASSED, RC 0000 |
| `jcl/poc002_warning.jcl` | Dataset fora do padrão (`POC.TEST.DATA`) | Quality Gate WARNING (90/100), pipeline segue |
| `jcl/poc003_bloqueado.jcl` | `IDCAMS DELETE PROD.*` | Security Gate FAILED, regra crítica `JCL003` (`prod_dataset_delete`), deploy bloqueado antes do adapter |
| `jcl/poc005_por_ambiente.jcl` | Mesmo job/dataset em TU/TI/PRD, só o `SPACE=` varia por ambiente (`--env`) — ver `docs/jcl-parametros-por-ambiente.md` | Quality Gate PASS 100/100 nos 3 ambientes; `SPACE=` renderizado diferente em PRD |

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

## 4º cenário: mesmo JCL, parâmetro diferente por ambiente

`poc005_por_ambiente.jcl` tem um placeholder `${SPACE_PRIMARY}`/`${SPACE_SECONDARY}`
no `SPACE=` do `SORTOUT` — sem `--env`, ou com um job sem entrada em
`config/jcl_env_params.yml`, nada muda. Com `--env`, o valor renderizado
muda:

```bash
python -m esteira_model_cob validate jcl/poc005_por_ambiente.jcl --env TU   # SPACE=(TRK,(5,1),RLSE)
python -m esteira_model_cob validate jcl/poc005_por_ambiente.jcl --env PRD  # SPACE=(TRK,(50,10),RLSE)
```

Isso reproduz um padrão real encontrado testando o parser contra JCL
cedido pelo banco (`jcl/real/`, não versionado): TU e TI idênticos, PRD
alocando mais espaço — hoje mantido lá como 3 cópias inteiras do arquivo.
Ver `docs/jcl-parametros-por-ambiente.md` para a explicação completa
(inclusive por que isso é conceitualmente o mesmo problema que
`appsettings.{Environment}.json` no .NET resolve).

## 5º cenário: guarda de binário (achado da esteira Endevor real)

Diferente dos 3 JCLs acima (texto ASCII versionado normalmente), este
cenário prova a mitigação para o ponto de atenção trazido pela Ana
(esteira real de migração do Endevor do banco — ver
`docs/reuniao-endevor-jcl-binarios.md`): componentes com caracteres
hexadecimais hard-coded (`HEX ON` no editor do ISPF/3270) só podem
trafegar como binário — qualquer conversão para texto/UTF-8 corrompe o
dado. `binary_guard.py` varre bytes EBCDIC crus em busca desses valores,
**antes** de qualquer decodificação para texto.

Como nenhum JCL/PROC real do escopo atual tem esse problema hoje,
`scripts/gen_test_fixtures.py` gera duas massas de teste sintéticas —
bytes EBCDIC (`cp037`) genuínos, não digitados à mão — em
`tests/fixtures/`: uma limpa e outra com 2 bytes de controle inseridos
(simulando o achado real).

```bash
python scripts/gen_test_fixtures.py

python -m esteira_model_cob binary-guard tests/fixtures/
# copybook_ebcdic_limpo.bin            -> Quality Gate PASS (100/100)
# copybook_ebcdic_hex_declarado.bin    -> Quality Gate FAILED (0/100), BIN001, Security Gate FAILED
```

Importante: este comando **não** roda sobre o JCL ASCII em `jcl/` — os
mesmos valores de byte 0x00-0x3F são dígitos e pontuação legítimos em
ASCII (ver contrato documentado no topo de
`esteira_model_cob/binary_guard.py`). `validate`/`simulate`/`report`
continuam intocados; o guard é um caminho separado, para bytes crus
vindos do mainframe.

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
