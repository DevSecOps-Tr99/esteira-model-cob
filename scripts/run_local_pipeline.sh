#!/usr/bin/env bash
# Script de apoio a construcao - nunca importado pela esteira em si.
# Roda localmente a mesma sequencia de comandos que o workflow do GitHub
# Actions executa contra a pasta jcl/.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== validate =="
python -m esteira_model_cob validate jcl/ || true

echo
echo "== simulate =="
python -m esteira_model_cob simulate jcl/ || true

echo
echo "== report (por arquivo) =="
for jcl in jcl/*.jcl; do
  python -m esteira_model_cob report "$jcl"
done
