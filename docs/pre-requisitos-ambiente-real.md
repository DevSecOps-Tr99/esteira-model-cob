# Pré-requisitos para montar esta POC no ambiente real

O que precisa existir ou ser provisionado para portar esta POC do ambiente
de demonstração atual (VM Azure fora da rede do banco, repositório em
`DevSecOps-Tr99/esteira-model-cob`) para o ambiente real do banco. Ver
também [`validacao-tecnica.md`](validacao-tecnica.md) para as perguntas
que definem várias dessas decisões.

## 1. GitHub (plataforma)

- Org/instância definida: GitHub Enterprise Cloud ou Server — muda tudo
  abaixo.
- Permissão para criar o repositório real.
- GitHub Actions habilitado na org, com decisão sobre actions de
  terceiros: `actions/checkout`, `actions/setup-python`,
  `actions/setup-java`, `gitleaks/gitleaks-action`,
  `actions/upload-artifact` — permitidos direto do marketplace, ou
  precisam de allowlist/mirror interno?
- Permissão de admin no repositório para criar GitHub Environments com
  protection rules (reviewers, branch policy) — nesta POC isso ficou
  pendente por falta desse nível de permissão.
- CODEOWNERS definido com usuários/grupos reais.

## 2. Runner self-hosted (dentro da rede do banco)

- Uma VM/servidor dentro da rede que alcança o mainframe (a VM usada
  nesta POC é Azure fora da rede do banco — só prova o conceito, não
  substitui isso).
- Especificação mínima replicada: Linux, Python 3.12+, git, JDK 17 +
  Maven (para o ProLeap), acesso root/sudo para instalar o runner como
  serviço.
- Squad de infra definida como dona dessa VM (patch, hardening,
  monitoramento).
- Token de registro do runner (gerado por um admin do repositório em
  Settings → Actions → Runners).
- Regra de firewall: outbound HTTPS liberado dessa VM para
  `github.com`/GHE Server (o runner só faz polling, não precisa de
  inbound).

## 3. Conectividade com o mainframe

- Caminho de rede da VM do runner até o z/OSMF (porta HTTPS, normalmente
  443) ou até onde a Zowe CLI/SDK/RSE API residem.
- Confirmação de qual dessas três interfaces está de fato disponível e
  homologada.
- Um ambiente z/OS não-produtivo (LPAR de teste) para validar o
  `ZosmfAdapter` real antes de tocar TU/TI/PRD de verdade.
- Conta de serviço no mainframe com permissão de submeter job (JES) e
  ler spool — e definição de quem provisiona/rotaciona essa credencial.

## 4. Insumos reais para o Rules Engine (Fase 2, mas para preparar já)

- 10 JCLs reais + 5 que falharam (pedido já formal no kickoff).
- Catálogo de regras do HexaVision/Dresscode: quais são bloqueantes vs.
  warning.
- Padrão real de nomenclatura de dataset (hoje usamos
  `ESTM.<APP>.<ENV>.<RESOURCE>` fictício).
- Lista de PROCs/copybooks compartilhados que essas JCLs referenciam.

## 5. Governança e aprovação

- Nomes/papéis reais dos required reviewers de TI e de PRD (hoje é só o
  dono do repositório).
- Decisão: a aprovação no GitHub Environment substitui a GMUD, ou
  precisa integrar com a ferramenta de Change (ServiceNow etc.)?

## 6. Segurança

- Decisão sobre stack: Gitleaks + ProLeap + Rules Engine Python (grátis,
  testados nesta POC fora do ambiente do banco — ainda não avaliados
  pela política de segurança real) são suficientes, ou o banco exige
  SonarQube Enterprise/Veracode/Checkmarx por política?
- Cofre de segredos real para as credenciais do mainframe (GitHub
  Secrets é aceitável, ou precisa CyberArk/Azure Key Vault já em uso no
  banco?).

## 7. Ambiente Python/Java

- Versão de Python homologada pelo banco.
- PyPI liberado, ou precisa de mirror interno (Artifactory/Nexus) — sem
  isso `pip install -e ".[dev]"` não funciona na rede do banco.
- Mesma pergunta para o Maven: o `proleap-cobol-parser` não está no
  Maven Central e é compilado da fonte
  (`scripts/install_proleap.sh` clona do GitHub) — isso precisa de
  outbound liberado para GitHub e Maven Central, ou de um artefato
  pré-compilado hospedado internamente.

## 8. Dados de exemplo (LGPD)

- Se os JCLs/COBOL reais cedidos para a POC tocarem dados de cliente,
  precisam vir sanitizados/mascarados antes de entrar neste repositório
  — confirmar isso explicitamente com quem for ceder os exemplos.
