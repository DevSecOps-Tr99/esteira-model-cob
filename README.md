# esteira-model-cob

POC de uma esteira de CI/CD para JCL/COBOL usando **VS Code + GitHub + GitHub Actions + um motor de esteira em Python**, no lugar da orquestração hoje baseada em Jira + HexaVision + ChangeMan ZMF.

O princípio central: **o JCL não muda**. A esteira nova troca apenas a camada de orquestração e governança — versionamento, gates de qualidade/segurança/execução e promoção entre ambientes — preservando a lógica atual e o Control-M.

Veja `docs/arquitetura.md` para o desenho completo. Este repositório é a Fase 1 (MVP): novo SCM e nova esteira, convivendo com as validações do HexaVision ainda não substituídas.

## Quickstart

```bash
pip install -e ".[dev]"

# valida todos os JCLs da pasta jcl/ (parser + rules engine + quality gate)
python -m esteira_model_cob validate jcl/

# simula a submissão de um job aprovado no MockZosAdapter
python -m esteira_model_cob simulate jcl/poc001_sucesso.jcl

# gera o JCL Pipeline Report em reports/
python -m esteira_model_cob report jcl/poc001_sucesso.jcl

# proleap-cobol-parser nao esta no Maven Central - compila da fonte uma vez
bash scripts/install_proleap.sh

# gera o AST de um COBOL de exemplo via ProLeap (precisa de java + mvn no PATH)
python -m esteira_model_cob cobol-ast cobol/payroll_sample.cbl
```

Rodar os testes:

```bash
pytest -q
```

O teste `tests/test_proleap_client.py` é pulado automaticamente se `java`/`mvn` não estiverem instalados — ele roda de verdade no workflow do GitHub Actions, que instala o JDK sob demanda.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `jcl/`, `proc/`, `cobol/` | Fontes versionados — JCLs de exemplo, PROC e um COBOL de demonstração |
| `config/` | Regras (`rules.yml`), ambientes e padrões de dataset — **versionado, não hardcoded em Python** |
| `esteira_model_cob/` | O motor da esteira (pacote Python instalável) |
| `tools/proleap-runner/` | Wrapper Java/Maven em torno do [ProLeap COBOL Parser](https://github.com/uwol/proleap-cobol-parser) |
| `scripts/` | Scripts de apoio à construção — nunca importados pela esteira |
| `tests/` | Testes do motor (pytest) |
| `docs/` | Documentação completa do processo, gates, segurança, integração com z/OS, Gitflow e roteiro de kickoff |

## Documentação

- [`docs/arquitetura.md`](docs/arquitetura.md) — visão geral e mapeamento esteira atual → nova esteira
- [`docs/gates.md`](docs/gates.md) — os 3 gates e o JCL Governance Report
- [`docs/seguranca.md`](docs/seguranca.md) — ferramentas de segurança avaliadas (ProLeap, Gitleaks, CodeQL, SonarQube, Veracode, IBM ZCodeScan)
- [`docs/integracao-zos.md`](docs/integracao-zos.md) — caminho para integração real com z/OS (z/OSMF, Zowe)
- [`docs/gitflow.md`](docs/gitflow.md) — como este repositório usa Gitflow
- [`docs/poc-demo.md`](docs/poc-demo.md) — roteiro de demonstração ponta a ponta
- [`docs/kickoff-perguntas.md`](docs/kickoff-perguntas.md) — perguntas em aberto e matriz de funções
