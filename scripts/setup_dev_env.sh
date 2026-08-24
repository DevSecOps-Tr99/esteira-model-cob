#!/usr/bin/env bash
# Script de apoio a construcao - nunca importado pela esteira em si.
# Cria um virtualenv local e instala o motor Python em modo editavel.
set -euo pipefail

cd "$(dirname "$0")/.."

python -m venv .venv
if [ -f .venv/Scripts/activate ]; then
  source .venv/Scripts/activate  # Windows (venv criado com python.exe do Windows)
else
  source .venv/bin/activate      # Linux/macOS
fi

pip install --upgrade pip
pip install -e ".[dev]"

echo "Ambiente pronto. Ative com: source .venv/Scripts/activate (Windows) ou source .venv/bin/activate"
