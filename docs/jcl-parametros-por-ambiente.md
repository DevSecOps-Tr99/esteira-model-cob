# Parâmetros de JCL por ambiente (achado testando contra JCL real)

Testamos o parser e o motor contra 6 JCLs reais cedidos pelo banco (3 jobs
× TU/TI/PRD — arquivos ficam em `jcl/real/`, **não versionado**, contém
nomes reais de job/dataset). Isso revelou um padrão real de como o banco
lida com diferenças entre ambientes, e 2 bugs no parser que nossos 3 JCLs
sintéticos (`poc001`-`poc003`) nunca exercitaram.

## O padrão encontrado

Comparando o mesmo job nos 3 ambientes: **TU e TI eram byte-a-byte
idênticos**; **PRD diferia em exatamente um parâmetro** (o `SPACE=`
alocado para o dataset de saída — produção aloca mais espaço que TU/TI).
Todo o resto — job card, nomes de dataset, `DISP=`, `DCB=`, a lógica do
step — era idêntico nos três.

O importante: isso não estava implementado como *um* JCL parametrizado.
Eram **3 arquivos completos, mantidos como cópias manuais** — um por
ambiente. Ou seja, para saber que só o `SPACE=` deveria mudar, alguém
precisa comparar os 3 arquivos inteiros; não há nenhuma garantia estrutural
de que uma cópia não vai divergir em algo além do pretendido.

## Isso é "configuração de environment como no .NET"?

Conceitualmente sim — é exatamente o mesmo problema que
`appsettings.{Environment}.json` (.NET), `values-<env>.yaml` (Helm) ou
`.env.production` (Node) resolvem: **um artefato, valores diferentes por
ambiente**. A diferença é que o banco resolve isso hoje da forma mais
simples possível — arquivo inteiro duplicado — em vez de um template único
com override por ambiente.

`esteira-model-cob` agora modela isso como um template único +
config por ambiente, do mesmo jeito que essas ferramentas fazem:

| Conceito | .NET / Helm | `esteira-model-cob` |
|---|---|---|
| Artefato-base | `appsettings.json` / `deployment.yaml` (com `{{ .Values.x }}`) | `jcl/poc005_por_ambiente.jcl` (com `${SPACE_PRIMARY}`) |
| Override por ambiente | `appsettings.Production.json` / `values-prod.yaml` | `config/jcl_env_params.yml` (chave `POC005.PRD.SPACE_PRIMARY`) |
| Quando é aplicado | build/deploy time | `validate`/`simulate`/`report --env` (`esteira_model_cob/templating.py`) |

## Como usar

Um `.jcl` só precisa de um placeholder `${VAR}` onde o valor variar por
ambiente:

```jcl
//SORTOUT  DD DSN=ESTM.POC.TU.SORTOUT,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(${SPACE_PRIMARY},${SPACE_SECONDARY}),RLSE)
```

E uma entrada em `config/jcl_env_params.yml`, com o nome do job (não o
nome do arquivo) como chave:

```yaml
POC005:
  TU:
    SPACE_PRIMARY: "5"
    SPACE_SECONDARY: "1"
  TI:
    SPACE_PRIMARY: "5"
    SPACE_SECONDARY: "1"
  PRD:
    SPACE_PRIMARY: "50"
    SPACE_SECONDARY: "10"
```

```bash
python -m esteira_model_cob validate jcl/poc005_por_ambiente.jcl --env PRD
python -m esteira_model_cob report jcl/poc005_por_ambiente.jcl --env PRD
```

Um job **sem** entrada em `config/jcl_env_params.yml` passa direto, sem
nenhuma substituição — `poc001`-`poc003` continuam se comportando
exatamente como antes deste mecanismo existir. `--env` também resolve a
biblioteca-alvo do deploy (`config/deploy_targets.yml`, ver
`docs/reuniao-endevor-jcl-binarios.md`) — as duas coisas variam pelo mesmo
flag, exatamente como a "config de environment" cobre tanto valores quanto
destino de deploy no .NET/Helm.

`esteira_model_cob/templating.py` usa `Template.substitute` (não
`safe_substitute`) de propósito: se faltar um valor no
`jcl_env_params.yml` para o ambiente pedido, a build quebra com um erro
claro em vez de gerar um JCL com `${VAR}` sem substituir — que pareceria
válido e falharia só no mainframe.

## Os 2 bugs de parser encontrados (e corrigidos)

Nenhum dos 3 JCLs sintéticos originais exercitava esses casos — só
apareceram testando contra JCL real.

1. **`CLASS=` capturava o valor de `MSGCLASS=` quando `CLASS=` não
   existia.** O job real só tinha `MSGCLASS=Z` no job card (sem `CLASS=`
   próprio). A busca por `CLASS=` era uma regex sem delimitador, e
   `"CLASS="` é um substring literal de `"MSGCLASS="` — a busca achava
   esse trecho escondido e atribuía `Z` a `job_class` por engano.
   Corrigido com `(?<![A-Z0-9])` antes da chave em
   `esteira_model_cob/parser.py` (`_PARAM_RE_TEMPLATE`).
2. **Dataset com geração relativa de GDG perdia o `)` final.** Um DSN como
   `NOME.BASE(0)` ou `NOME.BASE(+1)` (notação de GDG) tinha o parêntese de
   fechamento cortado. Causa: `_extract_param` fazia
   `match.group(1).strip("()")` incondicionalmente — `.strip()` remove os
   caracteres dados de **ambas as pontas**, então o `)` final de
   `NOME.BASE(0)` era removido mesmo o valor inteiro não estando entre
   parênteses (só o sufixo de geração). Corrigido: só remove os parênteses
   quando eles envolvem o valor inteiro (`DISP=(NEW,CATLG,DELETE)` →
   `NEW,CATLG,DELETE`), preservando sufixos como `(0)`/`(+1)` que
   coincidem em terminar com `)`.

Ambos com teste de regressão em `tests/test_parser.py` (dados fictícios,
não os nomes reais).

## O que ainda não foi modelado (conhecido, não urgente)

DDs de concatenação sem nome próprio (ex.: `JOBLIB` com múltiplas
bibliotecas, uma por linha `// DD DSN=...` sem nome) não são capturados
pelo parser hoje — `JclJob` não tem conceito de DD em nível de JOB (só DDs
dentro de um `step`), e essas linhas específicas também não batem com a
regex de DD (que exige um nome logo após `//`). Não corrigido nesta rodada
porque não afeta nenhuma regra hoje (`JOBLIB` são bibliotecas de sistema —
`ESTM.GERAL.LOADLIB`, `ESTM.DB2.DSNLOAD` etc. — não datasets de aplicação
sujeitos a naming convention), mas fica registrado como simplificação
conhecida.
