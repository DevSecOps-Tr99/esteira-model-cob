#!/usr/bin/env bash
# Script de apoio a construcao - nunca importado pela esteira em si.
#
# O proleap-cobol-parser (https://github.com/uwol/proleap-cobol-parser,
# MIT) NAO e publicado no Maven Central em nenhuma versao - confirmado
# consultando https://repo.maven.apache.org e a Maven Central Search API
# diretamente (nem a 4.0.0 do pom.xml atual, nem a ultima tag v2.4.0
# retornam nada). A biblioteca so existe como codigo-fonte no GitHub e
# precisa ser compilada e instalada no repositorio Maven local (~/.m2)
# antes de tools/proleap-runner conseguir resolve-la como dependencia.
#
# Pinado num commit especifico (nao "main" solto) por reprodutibilidade,
# ja que o projeto nao tagueia releases alinhadas com o pom.xml atual.
set -euo pipefail

PROLEAP_REPO="https://github.com/uwol/proleap-cobol-parser.git"
PROLEAP_COMMIT="d1bfe75bdd6d480f70c74c6345bcc02610ac30d3"

REPO_DIR="$HOME/.m2/repository/io/github/uwol/proleap-cobol-parser"

if compgen -G "$REPO_DIR"/*/*.jar > /dev/null 2>&1; then
  echo "proleap-cobol-parser ja esta instalado em ~/.m2/repository - nada a fazer."
  exit 0
fi

# Limpa cache de falha do Maven (diretorio com so *.lastUpdated de uma
# tentativa anterior contra o Maven Central, que nao tem esse artefato).
rm -rf "$REPO_DIR"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

git clone --quiet "$PROLEAP_REPO" "$WORKDIR"
git -C "$WORKDIR" checkout --quiet "$PROLEAP_COMMIT"
mvn -q -f "$WORKDIR/pom.xml" -DskipTests install

echo "proleap-cobol-parser instalado em ~/.m2/repository (commit $PROLEAP_COMMIT)"
