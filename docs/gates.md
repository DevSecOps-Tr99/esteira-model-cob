# Os 3 gates

Baseado no desenho "Esteira de JCL / Esteira Mainframe" hoje em uso — a nova
esteira precisa reproduzir estes 3 gates, não apenas "GitHub executando um
arquivo".

## 1. Gate de Qualidade

Equivalente ao "Dresscode" atual. Implementado em `rules_engine.py` +
`quality_gate.py`, antes do build/deploy:

- Sintaxe JCL: JOB/EXEC/DD válidos, PROC resolvida (`parser.py`)
- Naming convention de dataset (`JCL002`, contra `config/datasets.yml`)
- Ausência de comandos proibidos / programas fora da lista permitida (`JCL004`)
- MSGCLASS obrigatório (`JCL005`)
- Score de qualidade (0-100), publicado no JCL Pipeline Report

## 2. Gate de Execução

Equivalente ao gate hoje "em desenvolvimento" no desenho atual —
`simulator.py` só chama o adapter de execução se o Quality Gate não estiver
`FAILED`:

```
PR aprovado → JCL validado → dry-run (simulate) → dependências (proc/) → Execution Gate → Submit Job
```

No z/OS real (Fase 2), o próprio JES pode validar o JCL sem executar via
`TYPRUN=SCAN` no JOB statement — ver `integracao-zos.md`. Isso torna a
validação independente da nossa própria interpretação.

## 3. Gate pré-produção

Mapeado 1:1 para GitHub Environments:

```yaml
environment: TU
environment: TI
environment: PRD
```

PRD exige required reviewer, change aprovado, Quality Gate e testes
aprovados, artefato imutável — ver `config/environments.yml` e
`gitflow.md`.

## JCL Pipeline Report

Não existe no desenho atual — evidência gerada por `report.py` para
Auditoria/Risco/Change: commit, autor, resultado de cada validação, score,
job/RC por ambiente e veredito final (`APPROVED` / `BLOCKED`).

Exemplo (gerado por `python -m esteira_model_cob report jcl/poc003_bloqueado.jcl`):

```
JCL PIPELINE REPORT
========================================

JCL .................. jcl/poc003_bloqueado.jcl
Job name ............. POC003

QUALITY
----------------------------------------
[CRITICAL] JCL003 prod_dataset_delete: Exclusao de dataset em qualifier de producao (PROD.*) e proibida.
Score ................ 0/100

SECURITY
----------------------------------------
Status ............... FAILED
  BLOQUEANTE: JCL003 - Exclusao de dataset em qualifier de producao (PROD.*) e proibida.

EXECUTION
----------------------------------------
Execucao ............. NAO EXECUTADO (Bloqueado pelo Quality/Security Gate antes da submissao.)

STATUS
========================================
BLOCKED
```
