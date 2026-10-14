# Ambiente de validação (VM)

## Por que precisamos de uma VM

Esta máquina de desenvolvimento tem restrições reais, encontradas durante a
construção desta POC:

- Sem `winget`/`choco`/`scoop` — não dá para instalar JDK, Maven ou o `gh`
  CLI sem um instalador manual.
- Sem `java`/`mvn` no PATH — a integração com o **ProLeap COBOL Parser**
  (`tools/proleap-runner/`) só roda no GitHub Actions, nunca localmente
  (`tests/test_proleap_client.py` fica `SKIPPED` aqui).
- O serviço `ssh-agent` do Windows vem **parado e desabilitado** por
  política — cada uso da chave SSH exige reabilitar o serviço manualmente.

Nenhum desses blocos impede a POC (o CI cobre o que a máquina local não
cobre), mas também significa que **ninguém consegue rodar a esteira
completa, ponta a ponta, fora do GitHub Actions** para validar ou
demonstrar ao vivo. Uma VM de validação resolve isso e formaliza o nó
"Self-hosted Runner dentro da rede do banco" que já existia no desenho de
arquitetura original.

## Proposta

Uma VM (local via Hyper-V/VirtualBox/WSL2, ou uma VM de nuvem já
disponível para o time) com:

- Git
- Python 3.12+
- JDK 17 (Temurin) + Maven — para rodar o `AstDump.java` de verdade
- Registrada como **GitHub Actions self-hosted runner** deste repositório

## O que essa VM prova que o GitHub-hosted runner não prova

| Capacidade | GitHub-hosted runner (`ubuntu-latest`) | VM self-hosted |
|---|---|---|
| Rodar `pytest` e o Rules Engine | Sim | Sim |
| Rodar o ProLeap (Java/Maven) | Sim, via `actions/setup-java` | Sim |
| Alcançar rede interna (mainframe, z/OSMF) | **Não** | **Sim** — é o pré-requisito real da Fase 2 |
| Demonstrar a esteira rodando "dentro da rede do banco" | Não | Sim |

Ou seja: a VM não substitui o CI hospedado pela GitHub — ela é o próximo
passo necessário quando a Fase 2 precisar falar com o z/OSMF/Zowe real
(`docs/integracao-zos.md`), e serve desde já como ambiente limpo para
validar manualmente tudo o que esta máquina de desenvolvimento não
consegue (Java/Maven, `gh` CLI, `ssh-agent` sem restrição de política).

## Setup

```bash
git clone git@github.com:DevOpsRaizOficial/esteira-model-cob.git
cd esteira-model-cob
bash scripts/setup_dev_env.sh

pytest -q
# com java/mvn presentes, test_proleap_client.py roda de verdade (nao skip)

python -m esteira_model_cob validate jcl/
python -m esteira_model_cob simulate jcl/
python -m esteira_model_cob cobol-ast cobol/payroll_sample.cbl

# JCL com parametro por ambiente (docs/jcl-parametros-por-ambiente.md)
python -m esteira_model_cob validate jcl/poc005_por_ambiente.jcl --env PRD

# guarda de binario (docs/reuniao-endevor-jcl-binarios.md)
python -m esteira_model_cob binary-guard tests/fixtures/
```

Para registrar como self-hosted runner, seguir o fluxo padrão do GitHub em
**Settings → Actions → Runners → New self-hosted runner** no repositório, e
trocar `runs-on: ubuntu-latest` por `runs-on: self-hosted` no job desejado
de `.github/workflows/jcl-validation.yml` quando a Fase 2 precisar de
alcance de rede interna.

## Status

> **Substituído pelo ambiente da POC na Azure** (`docs/esteira-poc-como-funciona.md`
> e o repositório `esteira-model-cob-infra`). A VM `VM-COBOL-POC` foi
> removida. O job `publish` deu lugar ao job `deploy` do workflow reutilizável
> `jcl-pipeline.yml`, que lê as credenciais no Key Vault e publica por SSH em
> um servidor de destino. O histórico abaixo fica só como referência.

A VM `VM-COBOL-POC` estava registrada como self-hosted runner
(`vm-cobol-poc`, labels `self-hosted,linux,x64,vm-cobol-poc`), rodando
como serviço systemd (`actions.runner.DevSecOps-Tr99-esteira-model-cob.vm-cobol-poc.service`,
sobrevive a reboot).

O job `publish` em `.github/workflows/jcl-validation.yml` roda nela a cada
`push` em `develop`/`release/*`/`hotfix/*`/`main` (nunca em PR), gated por
GitHub Environment (`TU`/`TI`/`PRD`, mapeado 1:1 pelo nome da branch, ver
`gitflow.md` e `config/environments.yml`). Ele repete testes/validate/
simulate/report já rodando com Java/Maven reais (`test_proleap_client.py`
não é mais `SKIPPED` aqui) e "publica" o commit validado em
`~/publicado/<AMBIENTE>/<run>-<sha>/` na própria VM, com um `MANIFEST.txt`
(commit, autor, ambiente, timestamp) — o equivalente desta fase a mover o
membro para a PDS do ambiente; a Fase 2 troca isso pela submissão real via
z/OSMF (`integracao-zos.md`).
