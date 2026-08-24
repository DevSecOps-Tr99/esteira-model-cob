# Segurança & qualidade

Nenhuma ferramenta comercial de nível "SonarQube para COBOL" é gratuita —
todas exigem licença ou trial mediante contato comercial. Isto separa o que
dá para testar hoje, sem procurement, do que depende de aprovação de compra.

| Ferramenta | O que faz | Custo | Testável agora |
|---|---|---|---|
| **ProLeap COBOL Parser** ([uwol/proleap-cobol-parser](https://github.com/uwol/proleap-cobol-parser), MIT) | Parser ANTLR4 de COBOL → gera AST/ASG real (não regex). Passa no NIST test suite. Base para regras semânticas próprias no Rules Engine | Grátis · MIT | Sim |
| **Gitleaks** ([gitleaks.io](https://gitleaks.io/)) | Scanner de segredos (senhas, tokens, chaves) em qualquer arquivo texto — cobre JCL, PROC, COBOL, YAML. GitHub Action oficial, saída em SARIF | Grátis · open source | Sim |
| **GitHub CodeQL** | SAST para o motor Python da esteira (não analisa COBOL) | Grátis (repos públicos) / GH Advanced Security | Sim |
| SonarQube Enterprise | Analisador dedicado SonarCOBOL, quality gate nativo no PR. **A Community Edition não suporta COBOL** | Trial 14 dias mediante contato comercial | Só por trial |
| Veracode Static Analysis | SAST COBOL "enterprise-grade" | Comercial | Só por trial |
| IBM ZCodeScan | Nativo do IBM Z Open Editor — 30 regras de code review COBOL + 5 de segurança (SQL injection, buffer overflow, credenciais), CLI com quality gate por baseline | Pago · parte do IBM Developer for z/OS Enterprise Edition | Só com licença |

## Decisão para a POC

Pilotar **ProLeap + Gitleaks + Rules Engine em Python
(`config/rules.yml`)** — stack real e testável sem esperar aprovação de
compra, coerente com o princípio de o motor Python ser o dono da lógica de
qualidade/segurança em vez de depender de uma ferramenta fechada. Em
paralelo, é possível abrir um trial do SonarQube Enterprise ou pedir demo do
IBM ZCodeScan apenas para comparar cobertura de regras, sem bloquear a POC.

O Rules Engine não é opcional mesmo com uma ferramenta comercial: regras de
negócio (padrão de dataset, ambientes autorizados, datasets proibidos) são
específicas demais para um analisador genérico e precisam viver em YAML
versionado — ver `config/rules.yml`.

## Estado atual da integração com o ProLeap (`tools/proleap-runner/`)

Nesta primeira entrega, `AstDump.java` usa apenas a parte da API do ProLeap
confirmada na documentação oficial: `CobolParserRunnerImpl().analyzeFile(...)`,
`Program.getCompilationUnit(programId)`, `CompilationUnit.getProgramUnit()`,
`ProgramUnit.getDataDivision()` e `DataDivision.getWorkingStorageSection()`.
Isso prova que a esteira gera um AST/ASG real a partir de um COBOL
(`cobol/payroll_sample.cbl`) e resolve a DATA DIVISION do programa.

**Não implementado ainda:** enumeração genérica de todos os parágrafos da
PROCEDURE DIVISION e de todos os itens de dado da WORKING STORAGE (as regras
semânticas reais da Fase 2 — variável não inicializada, SQL embutido sem
bind, etc.). A API de travessia completa do ProLeap
(`io.proleap.cobol.asg.metamodel.procedure.*` e `data.datadescription.*`)
precisa ser levantada com mais profundidade (código-fonte/testes do próprio
projeto) antes de escrever essas regras — registrado aqui em vez de
adivinhado, para não travar a build com métodos inexistentes.

## O proleap-cobol-parser não está no Maven Central

Descoberto na primeira execução real (fora desta máquina de dev, numa VM
com JDK/Maven instalados — ver `ambiente-validacao.md`): o
`io.github.uwol:proleap-cobol-parser` **não é publicado no Maven Central em
nenhuma versão** — nem a `4.0.0` que o `pom.xml` do projeto declara hoje,
nem a última tag realmente lançada (`v2.4.0`). Confirmado consultando
`https://repo.maven.apache.org` e a Maven Central Search API diretamente
(ambos retornam vazio/404 para as duas versões).

A biblioteca só existe como código-fonte no GitHub — é preciso compilar e
instalar no repositório Maven local (`~/.m2`) antes de qualquer `mvn` que a
declare como dependência conseguir resolvê-la. Isso está resolvido por
`scripts/install_proleap.sh`, que clona o repositório num commit fixo
(`d1bfe75b...`, escolhido por não haver uma tag alinhada com a versão atual
do `pom.xml`) e roda `mvn -DskipTests install`. O workflow do GitHub Actions
chama esse script logo após o `actions/setup-java`, antes do `pytest`.

`esteira_model_cob/cobol_ast/proleap_client.py` expõe `is_available()`, que
checa `java`, `mvn` **e** a presença do jar em `~/.m2` — usado tanto pelo
`tests/test_proleap_client.py` (skip automático) quanto por `dump_ast()`
(erro claro apontando para o script, em vez de uma falha genérica do
Maven).

## Por que rodar via CI/VM e não nesta máquina de dev

Esta máquina de desenvolvimento não tem `java`/`mvn` instalados. O teste
`tests/test_proleap_client.py` é pulado automaticamente nesse caso — ele
roda de verdade no workflow do GitHub Actions (que instala o JDK sob
demanda via `actions/setup-java`) e na VM de validação
(`ambiente-validacao.md`), onde o bug acima foi encontrado e corrigido via
`hotfix/0.1.1`.
