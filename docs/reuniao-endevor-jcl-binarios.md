# Alinhamento com a esteira Endevor real e o risco dos binários/hexadecimais

Registro da reunião **"Reunião alinhamento JCL banco"** de 31/08/2026
(Ana Exemplo, Bruno Exemplo, Carlos Exemplo) —
primeiro contato com quem já opera uma esteira real de migração do Endevor no
banco. Objetivo deste documento: 1) traçar o paralelo entre o que a Ana
descreveu e o que `esteira-model-cob` propõe hoje, e 2) registrar o ponto de
atenção mais importante que ela levantou — **componentes com caracteres
hexadecimais não roundtrippable, que só podem trafegar como binário** — e o
plano de ação para tratar isso aqui.

## 1. O paralelo: a esteira que a Ana já opera

O time dela migra uma esteira Endevor (escopo maior que o nosso: COBOL,
Assembler, mapas BMS, Control-M e JCL) para um pipeline com ferramental
oficial da IBM. Fluxo descrito na reunião:

```
Analista altera componente (baixa do Git para o mainframe)
        ↓
Z Builder                  ← "nasce" aqui; builda o componente e marca o deployType
        ↓
DBB (Dependency Based Build) ← empacota os artefatos gerados
        ↓
JFrog Artifactory           ← repositório dos pacotes
        ↓
Wazi Deploy ("AZ/OZ Deploy")← consulta o deployType, decide biblioteca-alvo por
                               ambiente, executa jobs de validação antes/depois
        ↓
Biblioteca-alvo no mainframe (ex.: HBBR.PR1.DECKLIB para JCL, .PROCLIB, .PARMLIB…)
```

A configuração real que ela mostrou (`reusable-configurations/mainframe/instances/cwb/dbb/`)
tem um `Transfer.yaml` por tipo de componente (`copyJCL` → `copyMode: TEXT`,
`deployType: JCL`; `copyZCFG` → `deployType: CONFIG`; etc.) e um `info.toml`
que mapeia `deployType` → dataset-alvo por ambiente
(`[cwbp.deploy.lib.jcl] target = "HBBR.PR1.DECKLIB"`, `lib.dbrmb`/`lib.dbrmo`
já vêm com `spec = "binary"`, `lib.debugb/o` com `spec = "debug"`). Conexão
com o mainframe: **Zowe** ("Ozzy"/RC API), que ela descreveu como a porta de
entrada — não necessariamente amarrada ao DBB/Wazi Deploy.

### Mapeamento contra `esteira-model-cob`

| Etapa (esteira da Ana) | Ferramenta dela | Equivalente hoje em `esteira-model-cob` | Situação |
|---|---|---|---|
| Marcar tipo de artefato p/ deploy (`deployType`) | Z Builder | — | **Não existe.** `parser.py` extrai JOB/EXEC/DD, mas não classifica o componente para deploy. |
| Empacotar artefatos | DBB | — | **Não existe** (Fase 1 não empacota nada; só valida e simula). |
| Repositório de artefatos | JFrog Artifactory | GitHub Artifacts/Releases (citado em `arquitetura.md`, não implementado) | Equivalente já mapeado, falta implementar. |
| Gravar o fonte na biblioteca-alvo do mainframe | Wazi Deploy (`deployType` → dataset) | — | **Gap real** — ver seção 3. |
| Submeter/acompanhar execução do job | (fora do escopo dela nesta conversa) | `ExecutionAdapter` / `ZosmfAdapter` (Fase 2, `docs/integracao-zos.md`) | Já desenhado — mas cobre só a **execução**, não a gravação do fonte. |
| Conectividade com o mainframe | Zowe (RSE API / z/OSMF) | Zowe CLI / Zowe Client Python SDK / z/OSMF (já em `integracao-zos.md`) | Alinhado — ela confirma que Zowe é o caminho recomendado, **independente** de usar DBB/Wazi Deploy. |
| Control-M | Também tratado como binário (mesmos caracteres especiais) | "Permanece inalterado" (`arquitetura.md`) | Falta cobrir o transporte binário desses componentes — ver seção 3. |

Ponto que ela deixou explícito duas vezes: **não precisamos usar o mesmo
ferramental** (DBB/Wazi Deploy). Como nosso escopo é só JCL (o dela cobre
COBOL, Assembler e mapas também), ela sugeriu que possamos simplificar —
por exemplo, ir direto com Python + Zowe/z/OSMF para o teste de conectividade,
sem precisar do DBB.

> **Decisão fechada em 31/08/2026:** `esteira-model-cob` segue com
> **Zowe/z/OSMF + Python direto**, sem DBB/Wazi Deploy. Repositório de
> artefatos: **GitHub Artifacts/Releases** (a princípio, não JFrog
> Artifactory). Ver seção 5.

## 2. O ponto de atenção: hexadecimais "hard-coded" e caracteres não roundtrippable

Achado dela na migração do Endevor (instância CWB): existem componentes —
**JCL, copybooks (COPY) e PROC** — em que alguém, no terminal 3270/ISPF,
ligou o modo hex do editor (`HEX ON`) e digitou um valor hexadecimal
diretamente dentro do componente, no lugar de, por exemplo, escrever
`VALUE X'...'` em COBOL. O resultado visual no editor é um espaço em branco,
mas o byte gravado ali não tem correspondência em ASCII/UTF-8.

Consequência prática, nas palavras dela: **qualquer transporte desses
componentes que não seja binário corrompe o conteúdo** — ela testou baixar
via zFS/USS, via Zowe e via RSE API, e as três formas corromperam o dado.
Isso vale tanto para os componentes de aplicação (JCL/COPY/PROC) quanto para
os componentes de Control-M, pelo mesmo motivo.

Contingência que o time dela adotou (ainda sem solução definitiva — depende
de uma refatoração futura do código-fonte para eliminar esses hexadecimais
hard-coded):

1. O desenvolvedor altera o componente **diretamente no mainframe**.
2. Baixa o componente **como binário** (não como texto).
3. Inclui esse binário na branch e trafega normalmente pelo Git.
4. No deploy, o binário é **restabelecido para EBCDIC** para o componente
   voltar a ser executável/legível no mainframe.

Recomendação dela para não sermos surpreendidos: fazer uma **busca
hexadecimal** (hex search) nas bibliotecas reais que vão entrar no escopo,
via ISPF/3270, procurando por esses caracteres antes de migrar qualquer
componente — foi assim que o time dela encontrou o problema na instância CWB.

> **Decisão fechada em 31/08/2026:** diferente do time da Ana (que
> trata isso como contingência temporária até uma refatoração futura do
> código-fonte), em `esteira-model-cob` o tratamento binário é adotado como
> **parte definitiva do desenho** — não como stopgap. O guard de binário, o
> `.gitattributes` e o caminho de deploy em modo `binary` (seção 4) não são
> descartados quando/se a refatoração acontecer; continuam sendo a forma
> permanente de tratar qualquer componente hex-declarado que apareça no
> escopo.

### A tabela de bytes (`desafios-binarios.txt`)

O arquivo que ela indicou como referência (`desafios-binarios.txt`, na raiz
de `C:\Projetos\cliente\`) lista os pontos de código problemáticos, em duas
classes:

- **Non-roundtrippable**: `0D`, `0E`, `0F`, `15`, `25`
- **Non-printable**: `00`–`0C`, `10`–`14`, `16`–`24`, `26`–`3F`

Isto é essencial a faixa de controle (`C0`) do code page EBCDIC usado no
mainframe (tipicamente IBM-037/1047) — bytes que, ao serem tratados como
texto e convertidos para ASCII/UTF-8 (ou vice-versa), não têm mapeamento
seguro de ida-e-volta. Qualquer pipeline que abra esses arquivos em modo
texto (decode/encode, normalização de fim de linha do Git, etc.) já
corrompe o dado — não é um problema de ferramenta específica, é inerente ao
byte em si.

## 3. Gap identificado em `esteira-model-cob` hoje

1. **Todo o motor lê os componentes como texto.** `parser.py` e o restante
   do pipeline assumem `.read_text()`/UTF-8. Nunca foi desenhado (nem
   testado) para bytes fora do intervalo seguro de texto.
2. **Não existe `.gitattributes`.** Sem ele, o Git pode normalizar fim de
   linha e tratar como texto qualquer arquivo — risco real de corromper um
   componente binário assim que ele entrar no repositório.
3. **Falta uma camada de "gravar o fonte na biblioteca-alvo".** Hoje
   `ExecutionAdapter`/`ZosmfAdapter` (Fase 2, `docs/integracao-zos.md`) cobre
   **só a submissão e o acompanhamento do job** (`z/OSMF Jobs REST API`).
   Não existe nada equivalente ao papel do Wazi Deploy: decidir a
   biblioteca-alvo por ambiente e **gravar** o JCL/COPY/PROC lá — inclusive
   em modo binário quando necessário. São duas responsabilidades distintas
   até na própria z/OSMF (`restjobs/jobs` vs. `restfiles/ds`), e hoje só a
   primeira está desenhada.
4. **Não existe detecção de componentes "hex-declarados".** Nenhum gate
   verifica, byte a byte, se um componente contém os valores listados em
   `desafios-binarios.txt` antes de decidir tratá-lo como texto.
5. **Não existe um equivalente ao `deployType`/`Transfer.yaml` dela.** Nosso
   `config/` não tem hoje uma classificação de artefato → biblioteca-alvo
   por ambiente (mesmo que bem mais simples, já que nosso escopo é só JCL).

## 4. Plano de ação

### Curto prazo — dentro do escopo atual da POC (sem depender de acesso real)

1. **Guarda de binário no pipeline.** Novo módulo (`binary_guard.py` ou
   verificação em `rules_engine.py`) que lê cada componente em modo binário
   e verifica a presença dos bytes de `desafios-binarios.txt` **antes** de
   qualquer decodificação para texto. Se detectado, o componente é marcado
   `requires_binary_transfer` e vira um finding no Quality Gate (hoje o
   pipeline nem chegaria a rodar sem quebrar, se um desses componentes
   entrasse como texto). Tratamento **definitivo** (ver decisão na seção 2),
   não um workaround a remover depois. **→ Implementado:**
   `esteira_model_cob/binary_guard.py` + comando `binary-guard`
   (`esteira_model_cob/cli.py`). Contrato importante descoberto ao
   implementar: os valores da tabela só fazem sentido sobre bytes EBCDIC
   crus — os mesmos números (0x00-0x3F) são dígitos e pontuação comuns em
   ASCII/UTF-8, então o guard **não** roda sobre o JCL versionado em `jcl/`
   (isso seria falso positivo); ele é um comando/caminho separado, para
   bytes ainda não convertidos vindos do mainframe. Ver docstring do
   módulo.
2. **`.gitattributes`.** Definir JCL/COPY/PROC como texto por padrão, com
   instrução documentada de como marcar um componente específico como
   binário (`-text -diff`) quando o guard do item 1 o sinalizar — até termos
   automação completa disso. **→ Implementado:** `.gitattributes` na raiz
   do repositório.
3. **Massa de teste com hex embutido.** Como nenhum JCL/PROC real do nosso
   escopo tem hoje esse tipo de caractere, criar 1–2 fixtures sintéticos
   cobrindo o caso `non-roundtrippable` e o caso `non-printable` (gerados
   via script, não digitados à mão — para garantir os bytes exatos). É o
   que valida de ponta a ponta o guard do item 1, o `.gitattributes` do
   item 2 e o caminho de deploy binário do item 5, sem depender de acesso
   real ao mainframe. **→ Implementado, com um ajuste em relação ao plano
   original:** as fixtures não ficam em `jcl/`/`proc/` como texto ASCII com
   bytes embutidos — pelo motivo explicado no item 1 (os mesmos valores
   numéricos são inofensivos em ASCII), elas precisam ser bytes EBCDIC
   genuínos. `scripts/gen_test_fixtures.py` codifica um trecho de copybook
   em `cp037` e grava duas versões em `tests/fixtures/`: uma limpa
   (`copybook_ebcdic_limpo.bin`) e uma com 2 bytes de controle inseridos
   (`copybook_ebcdic_hex_declarado.bin`) — cobertas por
   `tests/test_binary_guard.py`.
4. **Modelar a segunda API do z/OSMF.** Atualizar `docs/integracao-zos.md`
   com a distinção Jobs REST API (execução, já documentada) vs. **Files
   REST API** (`PUT /zosmf/restfiles/ds/...`, parâmetro de encoding
   `binary`) ou `zowe zos-files upload file-to-data-set --binary` — caminho
   **confirmado** (seção 1): Zowe/z/OSMF + Python direto, sem DBB/Wazi
   Deploy. **→ Documentado** (seção "Gravação do fonte..." em
   `integracao-zos.md`); implementação de código só na Fase 2, quando
   houver acesso real ao mainframe (item 9b).
5. **Classificação de artefato → biblioteca-alvo.** Adicionar ao `config/`
   um equivalente enxuto do `deployType`/`Transfer.yaml`/`info.toml` da
   Ana (nosso escopo é só JCL, então bem mais simples): mapear
   ambiente (`TU`/`TI`/`PRD`) → dataset-alvo, e permitir marcar
   `copyMode: binary` por componente. **→ Implementado:**
   `config/deploy_targets.yml` + `esteira_model_cob/deploy_targets.py`,
   exibido na nova seção DEPLOY do JCL Pipeline Report
   (`python -m esteira_model_cob report jcl/poc001_sucesso.jcl --env TI`).
6. **Repositório de artefatos: GitHub Artifacts/Releases.** Confirmado
   (seção 1) como caminho inicial, sem JFrog Artifactory — implementar
   como parte do empacotamento (item ainda em aberto na Fase 1: não existe
   empacotamento hoje, só validação/simulação). Continua pendente — não
   há estágio de build/empacotamento nesta rodada (ver seção 6, item 1).
7. **Referenciar este documento** a partir de `integracao-zos.md`,
   `pre-requisitos-ambiente-real.md` e `validacao-tecnica.md` (feito).

### Médio prazo — depende de acesso real ao mainframe/L2

8. **Varredura hexadecimal no escopo real.** Pedir/repetir, para os
   componentes que vão entrar no nosso escopo (JCL, e PROCs referenciadas),
   a mesma busca hexadecimal que a Ana fez na instância CWB — para não
   sermos surpreendidos por um componente já hex-declarado. Confirmado:
   nenhum componente real conhecido tem isso hoje (ver seção 5) — a
   varredura é preventiva, não corretiva.
9. **Teste de round-trip binário — em duas etapas, não uma só:**
   - **9a. Contra o "mainframe simulado" da nossa própria VM — não
     bloqueado, fazer já.** O job `publish` do workflow (`docs/ambiente-validacao.md`)
     já promove artefatos validados para `~/publicado/<AMBIENTE>/...` na VM
     self-hosted (equivalente atual a "mover o membro para a PDS do
     ambiente"). Hoje esse passo é um `cp -r` simples — não passa pelo
     codepage EBCDIC, então não reproduz a corrupção que a Ana
     descreveu, mas serve para provar que **o resto da nossa própria
     esteira** (git → binary_guard → `.gitattributes` → Python →
     publicação) preserva os bytes exatos da massa de teste do item 3, sem
     nenhuma reconversão UTF-8 acidental no caminho. Isso é validável agora,
     sem depender de credencial nenhuma do banco.
   - **9b. Contra um z/OS real (Zowe/z/OSMF Files REST API).** Só essa
     etapa depende do acesso/credenciais ao mainframe do banco (bloqueado,
     ver `plano-inicial.md`) — é a única forma de provar que o
     `PUT /zosmf/restfiles/ds/...` em modo `binary` realmente preserva o
     byte EBCDIC original num dataset de verdade, o que nenhuma simulação
     em VM Linux consegue reproduzir.
10. **Estrutura DBB/Zowe própria, sem depender da L2 corporativa.** Ainda
    sem acesso ao que Diego/Eduardo/Gustavo têm validado na L2 (ver seção 5).
    Como a decisão é Zowe/z/OSMF direto (sem DBB), o que falta provisionar
    é Zowe CLI/SDK na VM de validação já existente
    (`docs/ambiente-validacao.md`) — não a estrutura DBB deles. Se a VM
    atual não tiver recurso/alcance de rede suficiente para o teste de
    conectividade real, sinalizar para provisionar mais recursos antes de
    travar nesse ponto.

## 5. Decisões registradas em 31/08/2026 (fechamento desta rodada)

| Pergunta | Decisão |
|---|---|
| Algum componente real do nosso escopo já tem caracteres hex? | **Não conhecido hoje.** Construir massa de teste sintética para validar o tratamento (item 3) em vez de esperar um caso real aparecer. |
| Time corporativo (Diego/Eduardo/Gustavo) compartilha a estrutura DBB/Zowe da L2? | **Sem acesso ainda.** Não bloqueia: como a decisão é Zowe direto (sem DBB), provisionar Zowe CLI/SDK na nossa própria VM de validação; pedir mais recursos de VM se necessário em vez de esperar o acesso corporativo. |
| Ferramental de deploy: DBB + Wazi Deploy ou Zowe/z/OSMF + Python direto? | **Zowe/z/OSMF + Python direto**, dado o escopo menor (só JCL). |
| Repositório de artefatos: JFrog Artifactory ou GitHub Artifacts/Releases? | **GitHub Artifacts/Releases**, a princípio. |
| Tratar o binário como contingência temporária ou definitiva? | **Definitiva** — parte permanente do desenho de `esteira-model-cob`, não um stopgap para remover após refatoração (diferente da postura do time da Ana para a esteira deles). |

Com essas decisões, a arquitetura de deploy de `esteira-model-cob` fica
fechada como: **Python + Zowe/z/OSMF (Jobs REST API para execução, Files
REST API em modo binário para gravar o fonte na biblioteca-alvo) +
GitHub Artifacts/Releases como repositório de artefatos**, sem DBB/Wazi
Deploy/JFrog — não é mais uma decisão de ferramental em aberto.

Correção importante em relação à versão anterior deste documento: **nem
tudo depende de acesso real ao mainframe do banco.** Já existe uma
"publicação simulada" rodando na VM self-hosted (job `publish`,
`docs/ambiente-validacao.md`) — o equivalente atual a mover o membro para a
PDS do ambiente. Ela permite validar agora (item 9a) que a nossa própria
esteira preserva bytes binários ponta a ponta, sem esperar credencial
nenhuma do banco. O que continua genuinamente bloqueado por
acesso/credenciais é só a prova final contra um z/OS real via Zowe/z/OSMF
(item 9b) — porque a simulação em VM Linux não passa pelo codepage EBCDIC e
não reproduz a corrupção que a Ana descreveu.

## 6. Re-análise: diferenças da nossa POC em relação à esteira real (além do "mainframe" simulado em VM Linux)

Já é sabido e aceito que o nosso "mainframe" hoje é uma simulação: o
`MockZosAdapter` gera JOBID/spool/RC em Python, e o job `publish`
(`docs/ambiente-validacao.md`) "publica" o artefato validado com um
`cp -r` para uma pasta comum de Linux (`~/publicado/<AMBIENTE>/...`) — sem
JES, sem codepage EBCDIC, sem dataset de verdade. Essa é uma diferença já
conhecida e endereçada no roadmap (Fase 2 = `ZosmfAdapter` real). A pergunta
desta rodada foi: **que outras diferenças existem**, além dessa. Revisando a
reunião inteira (não só o ponto do binário) contra o estado atual do
código, ficam estas:

| # | Diferença / gap | O que a Ana tem | O que `esteira-model-cob` tem hoje | Categoria |
|---|---|---|---|---|
| 1 | **Estágio de build/empacotamento** | Z Builder builda o componente e já marca o `deployType` | Não existe — Fase 1 só valida (`rules_engine.py`) e simula (`MockZosAdapter`); nenhum artefato é empacotado | Gap real |
| 2 | **Repositório de artefatos** | JFrog Artifactory | Decidido GitHub Artifacts/Releases, mas **nada é publicado como artifact hoje** — é só um mapeamento no doc | Gap real (decisão fechada, implementação pendente) |
| 3 | **Gravar o fonte na biblioteca-alvo (deploy)** | Wazi Deploy: consulta `deployType`, decide dataset por ambiente, grava | Só existe o desenho da `Jobs REST API` (execução); a `Files REST API` (gravação do fonte, modo binário) está documentada agora mas **não implementada** | Gap real — já registrado nas seções 3–4 |
| 4 | **Classificação artefato → biblioteca-alvo por ambiente** | `Transfer.yaml` + `info.toml` (`deployType` → dataset por ambiente) | **Implementado:** `config/deploy_targets.yml` + `esteira_model_cob/deploy_targets.py`, exibido na seção DEPLOY do JCL Pipeline Report | Fechado |
| 5 | **Hooks configuráveis pré-build / pós-deploy** | Wazi Deploy permite anexar jobs de validação antes do build ("se não tiver nesses critérios, eu não deixo sequenciar") e jobs adicionais de validação/transformação depois do deploy | Pipeline fixo (`parser → rules_engine → security → dependencies → quality_gate → simulator`), sem mecanismo plugável de "jobs adicionais" por componente/ambiente | Achado novo — não bloqueia o escopo atual (só JCL, regras simples), mas falta se entrarem regras específicas por aplicação na Fase 2 |
| 6 | **Tratamento de binário/hex** | Contingência (deles) para componentes hex-declarados | **Implementado:** `esteira_model_cob/binary_guard.py` + comando `binary-guard` + `.gitattributes` + massa de teste EBCDIC sintética (`tests/fixtures/`, `scripts/gen_test_fixtures.py`) | Fechado — o achado principal, mantido aqui por completude |
| 7 | **Escopo de componentes** | COBOL + Assembler + mapas BMS + Control-M + JCL, com build por componente controlado por variáveis (`Cobol.yaml`: padrões de arquivo → opções de compilação por variável) | Só JCL (mais um protótipo de AST de COBOL via ProLeap, **não ligado a build/deploy**) | Diferença de escopo **deliberada** — a própria Ana recomendou simplificar. Mas se o projeto crescer para COBOL de verdade (compilar, não só parsear), falta a camada de build com dependências entre COBOL/copybook/DB2 (o papel do DBB) |
| 8 | **Control-M** | Tratado pela mesma esteira, também como binário pelos mesmos motivos | "Permanece inalterado" — nem entra no nosso repositório/pipeline | Diferença de escopo deliberada — mas se Control-M entrar no escopo algum dia, herda o mesmo problema de binário que JCL/COPY/PROC |
| 9 | **Prova real de entrega numa biblioteca do mainframe** | Já é a pergunta padrão dela para validar qualquer abordagem nova ("conseguiu conectar e distribuir um componente numa biblioteca?") | Ainda não feito — item 9b (seção 4), bloqueado por acesso/credenciais | Bloqueio real, não gap de desenho |
| 10 | **Usuário sistêmico dedicado** | Ela reforçou a importância de um usuário técnico/sistêmico (não pessoal) para toda a cadeia de conectividade | Já citado de forma genérica em `pre-requisitos-ambiente-real.md` (seção 3: "conta de serviço... quem provisiona/rotaciona"), nunca destacado como decisão própria | Já coberto, reforçado aqui por completude |

Itens 4 e 6 foram fechados nesta rodada (código + testes, ver seção 4).
Itens 1–3 e 5 seguem como **gaps reais de implementação** (a arquitetura já
foi decidida nas seções anteriores, falta código). Itens 7–8 são
**diferenças de escopo deliberadas**, não pendências. Item 9 é um
**bloqueio de acesso**, não de
desenho. Item 10 já estava coberto, só não estava em destaque.