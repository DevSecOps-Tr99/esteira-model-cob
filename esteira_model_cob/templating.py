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

import json
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

import yaml

# Prefixo das variables do GitHub (repo ou Environment) que viram parametro
# de JCL: JCL_HLQ -> ${HLQ}. O workflow so repassa toJSON(vars); a escolha
# do que entra no JCL fica aqui, nao no YAML do workflow.
GITHUB_VARS_PREFIX = "JCL_"

ORIGIN_CONFIG = "config/jcl_env_params.yml"
ORIGIN_GITHUB = "GitHub variables"


@dataclass
class ResolvedParams:
    values: dict[str, str] = field(default_factory=dict)
    origins: dict[str, str] = field(default_factory=dict)


def load_env_params(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def params_from_github_vars(raw_json: str | None, prefix: str = GITHUB_VARS_PREFIX) -> dict[str, str]:
    """Extrai de `toJSON(vars)` so as variables com o prefixo `JCL_`,
    sem o prefixo."""
    if not raw_json:
        return {}
    data = json.loads(raw_json) or {}
    return {key[len(prefix):]: str(value) for key, value in data.items() if key.startswith(prefix)}


def resolve_params(config_params: dict, github_params: dict) -> ResolvedParams:
    """GitHub variables tem precedencia sobre config/jcl_env_params.yml - o
    yml fica como valor padrao para rodar local e no job validate (que nao
    roda dentro de um GitHub Environment)."""
    resolved = ResolvedParams()
    for key, value in config_params.items():
        resolved.values[key] = str(value)
        resolved.origins[key] = ORIGIN_CONFIG
    for key, value in github_params.items():
        resolved.values[key] = value
        resolved.origins[key] = ORIGIN_GITHUB
    return resolved


def placeholders(template_text: str) -> list[str]:
    """Nomes dos `${VAR}` usados no template, na ordem em que aparecem."""
    names: list[str] = []
    for match in Template.pattern.finditer(template_text):
        name = match.group("braced") or match.group("named")
        if name and name not in names:
            names.append(name)
    return names


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
