# Ambiente da POC na Azure (Key Vault + SSH)

Substitui a VM de validação antiga (`docs/ambiente-validacao.md`). O objetivo
é mostrar, de ponta a ponta, a publicação de um JCL no mesmo padrão da
esteira corporativa para Linux:

1. `azure/login` com o JSON do SPN (`secrets.SPN_KV_DEV_SECRET`);
2. leitura das credenciais no Key Vault, pelo nome guardado em uma variable
   (`G_DEPLOYMENT_TARGET_LINUX_<ENV>_KEY`);
3. SSH no servidor de destino com o usuário da variable
   `G_DEPLOYMENT_TARGET_LINUX_<ENV>_USER`;
4. transferência e "submissão" do JCL, renderizado com as variables do
   GitHub Environment.

## Topologia

```
GitHub (DevSecOps-Tr99/esteira-model-cob)
  │  job validate  -> ubuntu-latest (gitleaks, pytest, gate, ProLeap)
  │  job deploy    -> runner self-hosted  [aprovação em TI e PRD]
  ▼
rg-esteira-model-cob-poc (brazilsouth)
  ├─ vnet-estm-poc 10.60.0.0/16 · snet-poc 10.60.1.0/24 · nsg sem entrada da internet
  ├─ vm-estm-runner   runner self-hosted (labels self-hosted,linux,x64,estm-runner), az CLI
  │        │ SSH :22 (só dentro da VNet)
  │        ▼
  ├─ vm-estm-alvo     10.60.1.10, sem IP público, managed identity
  │        usuários estmtu / estmti / estmprd  ->  /srv/estm/TU | TI | PRD
  │        /usr/local/bin/estm-submit  (valida o token no Key Vault e "submete")
  └─ kv-estm-poc-*    chaves SSH e tokens fictícios por ambiente (RBAC)
```

Os três ambientes usam as mesmas VMs e o mesmo Key Vault, mas cada um tem as
próprias credenciais: usuário, chave SSH, token e pasta. O `estm-submit`
recusa quando um usuário tenta publicar em outro ambiente (`estmtu` só
publica em TU).

As duas VMs desligam automaticamente às 22h (horário de Brasília). Com o
runner desligado, o job `deploy` fica na fila até a VM voltar:
`az vm start -g rg-esteira-model-cob-poc -n vm-estm-runner` e
`az vm start -g rg-esteira-model-cob-poc -n vm-estm-alvo`.

## Key Vault

| Segredo | Conteúdo | Quem lê |
|---|---|---|
| `estm-tu-ssh-key` / `estm-ti-ssh-key` / `estm-prd-ssh-key` | chave privada SSH do usuário de deploy do ambiente | SPN da esteira |
| `estm-tu-token` / `estm-ti-token` / `estm-prd-token` | token fictício do ambiente | SPN da esteira e a managed identity do destino |
| `estm-admin-ssh-key` | chave do administrador das VMs (uso de emergência) | só quem provisiona |

O valor do segredo nunca aparece no log. O passo `Key Vault - credenciais`
mascara o valor e publica no Job Summary o nome, a versão, a data e os 12
primeiros caracteres do SHA-256 do segredo. Para conferir no portal, compare
a versão com a mostrada no summary.

## GitHub

**Secret (repositório)**

| Nome | Conteúdo |
|---|---|
| `SPN_KV_DEV_SECRET` | `{"clientId","clientSecret","subscriptionId","tenantId"}` do SPN `sp-esteira-model-cob-poc-kv`, com papel *Key Vault Secrets User* só no Key Vault |

**Variables (repositório), com os mesmos nomes da esteira corporativa**

| Nome | Exemplo |
|---|---|
| `GH_KV_DEV` | `kv-estm-poc-xxxxxxxxxx` |
| `DEPLOY_SERVERS_TU` / `_TI` / `_PRD` | `10.60.1.10` |
| `G_DEPLOYMENT_TARGET_LINUX_<ENV>_USER` | `estmtu` / `estmti` / `estmprd` |
| `G_DEPLOYMENT_TARGET_LINUX_<ENV>_KEY` | `estm-tu-ssh-key` ... (nome do segredo, não o valor) |
| `G_DEPLOYMENT_TARGET_LINUX_<ENV>_TOKEN` | `estm-tu-token` ... |
| `G_DEPLOYMENT_TARGET_<ENV>_PATH` | `/srv/estm/TU` ... |
| `G_DEPLOYMENT_TARGET_LINUX_KNOWN_HOSTS` | `10.60.1.10 ssh-ed25519 AAAA...` (host key do destino; o SSH roda com `StrictHostKeyChecking=yes`) |

**Variables por Environment (TU, TI e PRD), injetadas no JCL**

O mesmo nome tem um valor diferente em cada Environment. O `${HLQ}` do JCL
vem da variable `JCL_HLQ`.

| Variable | TU | TI | PRD |
|---|---|---|---|
| `JCL_ACCT` | `ESTM,0001,TU01` | `ESTM,0001,TI01` | `ESTM,0001,PR01` |
| `JCL_PROGRAMMER` / `JCL_NOTIFY` | `ESTMTU` | `ESTMTI` | `ESTMPRD` |
| `JCL_CLASS` | `A` | `A` | `P` |
| `JCL_MSGCLASS` | `X` | `X` | `Z` |
| `JCL_SCHENV` | `BATCHTU` | `BATCHTI` | `BATCH` |
| `JCL_HLQ` | `ESTM.POC.TU` | `ESTM.POC.TI` | `ESTM.POC.PRD` |
| `JCL_UNIT` | `SYSDA` | `SYSDA` | `DISCO` |
| `JCL_SPACE_PRIMARY` / `_SECONDARY` | `000600` / `0240` | `000600` / `0240` | `006000` / `2400` |
| `JCL_DATACLAS` | `DCTESTE` | `DCTESTE` | `DCPRODX` |

Os mesmos valores estão em `config/jcl_env_params.yml` (entrada `ESTMX001`),
que serve como padrão para rodar local e no job `validate`. Quando a
variable do GitHub existe, ela tem precedência, e o summary mostra a origem
de cada valor. Para demonstrar, mude `JCL_SPACE_PRIMARY` no Environment TI e
rode de novo: o JCL de TI muda e o de TU não. Se um placeholder ficar sem
valor nos dois lugares, o build quebra antes de chegar ao servidor.

**Environments**

| Environment | Aprovação | Quando roda |
|---|---|---|
| `TU` | nenhuma | push em `develop`/`feature`, ou o seletor com TU |
| `TI` | 1 aprovador | push em `release/*`, ou o seletor com TI |
| `PRD` | 1 aprovador | push em `main`/`hotfix/*`, ou o seletor com PRD |

## Nome do arquivo por ambiente

O modelo versionado é um só: `jcl/ESTMX001.jcl`, no padrão `<SISTEMA>X<NNN>`
dos jobs reais. A esteira gera um arquivo por ambiente com o sufixo do
ambiente, no mesmo padrão das cópias por ambiente dos JCLs reais
(`config/deploy_targets.yml`, `file_naming`):

```
build/TU/ESTMX001TU.jcl    -> /srv/estm/TU/<run>-<sha>/ESTMX001TU.jcl
build/TI/ESTMX001TI.jcl    -> /srv/estm/TI/<run>-<sha>/ESTMX001TI.jcl
build/PRD/ESTMX001PRD.jcl  -> /srv/estm/PRD/<run>-<sha>/ESTMX001PRD.jcl
```

No destino, o `estm-submit` grava o conteúdo como membro **sem** sufixo da
biblioteca do ambiente, `/srv/estm/<ENV>/ESTM.POC.<ENV>.JCLLIB/ESTMX001`. É o
equivalente a mover o membro para a PDS do ambiente.

## Fluxo do job `deploy` (o que mostrar na demo)

| Passo | Evidência no Job Summary |
|---|---|
| Renderizar JCL | tabela placeholder → valor → origem (GitHub variables ou config) + o JCL final |
| Quality/Security Gate | `PASS 100` no arquivo final; FAILED bloqueia antes de qualquer credencial |
| Azure Login | login do SPN (padrão corporativo) |
| Key Vault - credenciais | nome, versão, data e SHA-256 parcial da chave SSH e do token |
| SSH - publicar e submeter | `hostname`/`whoami`/horário **do servidor**, arquivos transferidos por SCP, JOBID/RC/membro/biblioteca e o spool |
| Limpar credenciais | apaga a chave e o token do disco do runner e faz `az logout` |

O token vai para o servidor pelo stdin do SSH, nunca como argumento. O
`estm-submit` busca o token esperado no mesmo Key Vault, usando a managed
identity da VM, e compara os dois. Isso prova que a credencial lida pela
esteira é a mesma que o destino aceita para "logar". Toda submissão, aceita
ou recusada, fica registrada em `/var/lib/estm/auditoria.log` no destino.

### Roteiro

1. **Seletor:** em Actions → *JCL Pipeline* → *Run workflow*, escolha
   `ambiente = TU`. O job roda direto.
2. Rode de novo com `TI`. O job `deploy` para em *Waiting for review*.
   Aprove e veja o JCL de TI (HLQ, SCHENV etc. diferentes) publicado com o
   usuário `estmti`.
3. Rode com `PRD`. Também pede aprovação, e o JCL tem `CLASS=P`,
   `MSGCLASS=Z`, `UNIT=DISCO` e `SPACE` maior.
4. **Gitflow:** um merge em `develop` publica em TU automaticamente.
5. **Bloqueio:** um PR que introduz `DELETE PROD.` em um JCL falha no job
   `validate` e nunca chega ao `deploy`.

## Infra como código

| Arquivo | O que faz |
|---|---|
| `infra/main.bicep` | VNet, NSG, Key Vault (RBAC), as duas VMs, auto-shutdown e papéis no Key Vault |
| `infra/alvo/cloud-init.yaml` | usuários por ambiente, pastas, `sshd` só com chave, `estm-submit` |
| `infra/alvo/estm-submit.py` | a "submissão" do lado do servidor |
| `infra/runner/cloud-init.yaml` | dependências do runner (Python, az CLI, git, jq) |
| `infra/runner/registrar-runner.sh` | registra o runner no repositório como serviço systemd |

Custo aproximado, com as VMs ligadas 24h, em brazilsouth: B2s + B1s + discos
+ Key Vault, na faixa de US$ 60–70/mês. O auto-shutdown reduz bastante esse
valor. Para apagar tudo: `az group delete -n rg-esteira-model-cob-poc`,
depois `az keyvault purge -n <kv>` e `az ad sp delete --id <appId>`.
