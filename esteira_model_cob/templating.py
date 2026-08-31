"""Templating de JCL por ambiente: um unico `.jcl` versionado com
placeholders `${VAR}`, mais os valores por ambiente em
`config/jcl_env_params.yml` - a mesma ideia do `appsettings.{Environment}.json`
do .NET ou de um `values-<env>.yaml` do Helm, aplicada a JCL.

Motivacao: JCLs reais cedidos pelo banco (`jcl/real/`, nao versionado)
mostraram esse padrao ao vivo - o mesmo job (mesmo dataset, mesma logica de
SORT), variando *um* parametro (SPACE alocado) entre TU/TI e PRD, mas
mantido hoje como 3 copias inteiras do arquivo editadas a mao. Copias
manuais nao dao nenhuma garantia de que so a diferenca pretendida existe
entre elas - um template unico + valores por ambiente elimina esse risco de
divergencia silenciosa, e o PR passa a mostrar exatamente qual parametro
muda por ambiente.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

import yaml


def load_env_params(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def render(template_text: str, params: dict) -> str:
    """Substitui `${VAR}` pelos valores de `params`.

    Usa `Template.substitute` (nao `safe_substitute`) de proposito: preferimos
    quebrar a build com um `KeyError` claro a gerar um JCL com um
    placeholder `${VAR}` sem substituir, que pareceria valido e falharia
    silenciosamente so no mainframe.
    """
    return Template(template_text).substitute(params)


def params_for(config: dict, job_name: str | None, environment: str) -> dict:
    return config.get(job_name or "", {}).get(environment, {})
