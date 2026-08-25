# Validação técnica e alinhamento com o ambiente real

Este documento é complementar ao `kickoff-perguntas.md` (que cobre a
retirada de Jira/HexaVision e a matriz de funções). Aqui o foco é
diferente: confirmar se as **escolhas técnicas já implementadas** nesta
POC (o motor Python, os gates, a esteira GitHub Actions → VM self-hosted,
os ambientes TU/TI/PRD) fazem sentido quando confrontadas com o ambiente
real do banco — e onde estão as suposições que precisam ser validadas ou
corrigidas antes de qualquer coisa ir para produção.

## 1. Plataforma GitHub real

- GitHub Enterprise **Cloud ou Server** (on-prem)? Isso muda onde os
  runners ficam, se `github.com` é alcançável diretamente, e se actions de
  terceiros precisam de allowlist/mirror interno.
- Já existe **GitHub Advanced Security** licenciado (secret scanning,
  CodeQL nativos)? Se sim, o Gitleaks que usamos nesta POC pode ser
  redundante.
- A squad de infra já opera self-hosted runners hoje, ou a VM que
  registramos nesta POC (fora da rede do banco, sem alcance real ao
  mainframe) é o primeiro caso?

## 2. Runner e rede real

- Onde o runner "de produção" vai rodar de fato — dentro da rede que
  alcança o mainframe? Quem administra isso (infra? segurança?), qual
  política de hardening/patch se aplica?
- O runner real vai herdar as credenciais que hoje o ChangeMan/HexaVision
  usam para tocar o z/OS, ou é um usuário técnico novo?

## 3. Ambientes TU/TI/PRD e aprovação

- Nesta POC o único required reviewer configurável é o próprio dono do
  repositório — na vida real, quem aprova TI e quem aprova PRD? Líder
  técnico? Change Manager? Precisa ser mais de uma pessoa?
- A aprovação no GitHub Environment **substitui** a GMUD ou só
  **reflete** ela (precisa integrar com ServiceNow ou outra ferramenta de
  change)?
- `Prevent self-review`/`can_admins_bypass` devem ficar desligados em PRD
  (nem o admin do repositório pula a aprovação)?

## 4. As regras que a POC usa são fictícias — quais são as reais?

- `config/rules.yml` tem regras de exemplo (`JCL002 naming_convention`,
  `JCL003 prod_dataset_delete`). Qual é o padrão real de nomenclatura de
  dataset do banco (usamos `ESTM.<APP>.<ENV>.<RESOURCE>` só por causa do
  codinome)?
- Quais regras do HexaVision/Dresscode são bloqueantes vs. warning de
  fato? (já pedido no kickoff, mas vale repriorizar — sem isso o Rules
  Engine da Fase 2 não sai do papel)

## 5. Stack de segurança

- Validamos Gitleaks + ProLeap + Rules Engine Python (grátis, testáveis
  hoje) em vez de SonarQube Enterprise/Veracode/Checkmarx — o banco já
  tem alguma dessas ferramentas obrigatória por política? Se sim, integra
  em paralelo ou substitui?
- Como credenciais para o mainframe chegam ao runner em produção — cofre
  corporativo (CyberArk?), Azure Key Vault, GitHub Secrets mesmo?

## 6. Execução real no mainframe

- z/OSMF, Zowe CLI/SDK ou RSE API — qual está disponível e alcançável
  pela rede onde o runner vai ficar? (pergunta já no kickoff, mas agora é
  bloqueante para sair do `MockZosAdapter`)
- Existe um ambiente z/OS não-produtivo para testar o `ZosmfAdapter` real
  antes de ir para TU/TI/PRD de verdade?

## 7. Auditoria e retenção

- Quanto tempo o `JCL Pipeline Report`/spool/logs precisam ficar
  retidos? Já existe requisito formal (auditoria interna, BACEN)?
- O audit log nativo do GitHub Actions basta, ou precisa exportar para um
  SIEM?

## 8. Ambiente Python

- Versão de Python homologada pelo banco?
- PyPI liberado, ou precisa de mirror interno (Artifactory/Nexus)?

Ver também [`pre-requisitos-ambiente-real.md`](pre-requisitos-ambiente-real.md)
para a lista do que precisa ser provisionado para responder e aplicar
essas respostas.
