# Perguntas para o kickoff e matriz de funções

Antes de desligar qualquer parte do fluxo atual, estas frentes precisam de
respostas de quem opera Jira e HexaVision hoje. O maior risco do projeto não
é a integração técnica GitHub↔mainframe: é retirar Jira e HexaVision sem
mapear antes todos os controles que eles executam.

## Jira

- Controla demanda, defeito, projeto ou mudança (GMUD)?
- Integra com HexaVision ou com alguma ferramenta de produção?
- GitHub Issues/Projects é aceito como substituto?
- Existe exigência de auditoria relacionada ao Jira? O histórico precisa ser migrado?

## HexaVision — criação

- O que "criação" cobre: membro COBOL, JCL, versão, application/system/subsystem?
- Faz checkout/check-in? Gera identificadores? Integra com ChangeMan?

## HexaVision — SCM

- É repositório oficial ou só interface? Onde o fonte realmente fica?
- Existe bloqueio pessimista de edição? O histórico é exportável?
- O MVP migra o histórico completo ou só uma baseline?

## HexaVision — validações

- Quais regras são bloqueantes vs. apenas alerta?
- As regras são exportáveis? Existe API ou só UI?
- Existe validação de COBOL, JCL, DB2, documentação, impacto?

## JCLs e execução

- Como são submetidos hoje? Existe z/OSMF, Zowe ou RSE API disponível?
- Quais RC são aceitáveis por job? Tratamento diferente para RC 4?
- Quais PROCs são compartilhadas? Os parâmetros variam por ambiente?

## Plataforma

- GitHub Enterprise Cloud ou Server? Self-hosted runner é permitido e chega ao mainframe?
- Versão de Python homologada? Acesso a PyPI liberado ou precisa mirror interno?

**Pedido concreto para o kickoff:** 10 JCLs reais, 5 JCLs que falharam, as
regras do HexaVision/Dresscode e um exemplo de JCL aprovado vs. um
rejeitado, com o motivo da rejeição — base para engenharia reversa das
regras da Fase 2.

**Recebido em 31/08/2026 (primeira amostra, não versionada em `jcl/real/`,
ver `.gitignore`):** 2 jobs reais × TU/TI/PRD (6 arquivos). Já deu para
extrair um achado de arquitetura real (mesmo job, só um parâmetro varia
por ambiente — ver `docs/jcl-parametros-por-ambiente.md`) e corrigir 2
bugs de parser que os JCLs sintéticos não expunham. Ainda faltam: JCLs
rejeitados (nenhum dos 2 recebidos falha em nada), as regras reais do
HexaVision/Dresscode, e mais volume/variedade para validar o Rules Engine
contra padrões de nomenclatura reais (os 2 jobs recebidos usam qualifiers
de 5 níveis com geração relativa de GDG, bem diferente do
`ESTM.<APP>.<ENV>.<RESOURCE>` fictício de 4 níveis usado nesta POC — e o
**ambiente não fica codificado no nome do dataset**: o mesmo DSN aparece
nos 3 arquivos TU/TI/PRD, só a biblioteca-alvo do deploy muda).

## Matriz de funções

| Função atual | Jira | HexaVision | Nova solução | Fase |
|---|---|---|---|---|
| Registro da demanda | Sim | Não | GitHub Issues ou ferramenta corporativa de mudança | MVP |
| Armazenamento do fonte | Não | A confirmar | GitHub Repository | MVP |
| Criação do componente | Não | Sim | GitHub + Python | MVP |
| Versionamento | Não | A confirmar | Git | MVP |
| Revisão | Parcial | A confirmar | Pull Request | MVP |
| Validação técnica | Não | Sim | HexaVision, temporariamente | Transição |
| Validação de regras | Não | Sim | Rules Engine em Python | Fase 2 |
| Aprovação de produção | A confirmar | A confirmar | GitHub Environment / ITSM | MVP |
| Evidência | Sim | Sim | GitHub + Python + JCL Pipeline Report | MVP |
| Deploy | Não | A confirmar | Ferramenta atual + Python | A definir |

## Critérios de sucesso do MVP

- Fonte COBOL e JCL armazenados no GitHub, desenvolvidos via VS Code
- Jira ausente do fluxo definido; HexaVision ausente da etapa de criação
- Pull Request com revisão obrigatória (CODEOWNERS)
- GitHub Actions acionando o motor Python, que executa toda a lógica
- Motor Python submetendo o JCL atual, sem reescrita
- Execução (ou simulação, na POC) com leitura de spool e RC
- Resultado publicado automaticamente no Pull Request
- Promoção controlada TU → TI → PRD com aprovação obrigatória
- Rastreabilidade completa sem depender do Jira
- Convivência controlada com as validações do HexaVision ainda não substituídas
