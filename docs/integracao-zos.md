# Integração com z/OS

A submissão e o acompanhamento de jobs em z/OS têm caminho oficial e
documentado pela IBM — não é necessário um protocolo proprietário.

| Componente | Função | Uso previsto no motor |
|---|---|---|
| **z/OSMF Jobs REST API** | API REST oficial da IBM para submeter, consultar status e ler spool de jobs (`PUT /zosmf/restjobs/jobs`) | `ZosmfAdapter.submit_job()` (Fase 2) |
| **Zowe CLI** | CLI open source (Linux Foundation) sobre o z/OSMF — `zowe zos-jobs submit local-file` | Alternativa de linha de comando no runner |
| **Zowe Client Python SDK** ([zowe/zowe-client-python-sdk](https://github.com/zowe/zowe-client-python-sdk)) | SDK Python oficial do projeto Zowe para chamar z/OSMF sem subprocess | Biblioteca de base do `ZosmfAdapter` |
| **`TYPRUN=SCAN`** | Parâmetro do JOB statement (JCL) que faz o JES converter/validar sintaxe sem executar os steps | Gate de execução, sem gastar tempo de CPU do mainframe |
| **z/OSMF Files REST API** (`restfiles/ds`) | API REST da IBM para gravar/ler membros de dataset — com modo `binary` | Camada de deploy do fonte (JCL/COPY/PROC) na biblioteca-alvo, separada da submissão de job (Fase 2) |

## Sequência de adapters

1. **`MockZosAdapter`** (esta Fase 1 / POC) — simula JOBID, spool JES2 e RC
   em `esteira_model_cob/adapters/mock_zos.py`, sem tocar em z/OS real.
2. **`ZosmfAdapter`** (Fase 2) — implementação real via Zowe Client Python
   SDK ou chamadas diretas à z/OSMF Jobs REST API. Implementa a mesma
   interface `ExecutionAdapter` (`adapters/base.py`), então `simulator.py`
   não precisa mudar — só a instância de adapter passada a ele.
3. **Control-M** — permanece inalterado; a integração final de agendamento
   continua fora do escopo desta esteira.

## O que muda ao trocar o adapter

```python
from esteira_model_cob.adapters.mock_zos import MockZosAdapter
# troca por, quando a Fase 2 chegar:
# from esteira_model_cob.adapters.zosmf import ZosmfAdapter

adapter = MockZosAdapter()
result = simulate(job, quality, adapter)
```

Nenhuma outra parte da esteira (parser, rules engine, quality gate, report)
precisa ser alterada.

## Gravação do fonte na biblioteca-alvo (deploy) vs. submissão do job

A `Jobs REST API` acima cobre só a **execução**. Falta ainda desenhar a
camada equivalente ao papel do Wazi Deploy na esteira Endevor real do
banco: decidir a biblioteca-alvo por ambiente e **gravar** o JCL/COPY/PROC
lá — usando a `Files REST API` (`restfiles/ds`) em modo `binary` quando o
componente tiver caracteres hexadecimais não roundtrippable. Ver
[`reuniao-endevor-jcl-binarios.md`](reuniao-endevor-jcl-binarios.md) para o
paralelo completo e o plano de ação.
