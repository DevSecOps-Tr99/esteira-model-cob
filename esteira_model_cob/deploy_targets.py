"""Classificacao de artefato -> biblioteca-alvo por ambiente.

Carrega config/deploy_targets.yml (nao hardcoded em Python, mesmo padrao de
rules_engine.py) e resolve, para um tipo de componente e um ambiente
(TU/TI/PRD), qual dataset e o alvo do deploy e qual e o modo de
transferencia (text/binary). Ver docs/reuniao-endevor-jcl-binarios.md.

Fase 1 (esta POC): so usado para exibir a intencao no JCL Pipeline Report
(report.py) - nao existe ainda um adapter que grave de fato no dataset (Fase
2, via z/OSMF Files REST API - ver docs/integracao-zos.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class DeployTarget:
    component_type: str
    environment: str
    library: str
    copy_mode: str  # "text" | "binary"


def load_deploy_targets(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def resolve(
    config: dict,
    component_type: str,
    environment: str,
    *,
    force_binary: bool = False,
) -> DeployTarget:
    entry = config["deploy_targets"][component_type]
    library = entry["library"][environment]
    copy_mode = "binary" if force_binary else entry.get("copyMode", "text")
    return DeployTarget(
        component_type=component_type,
        environment=environment,
        library=library,
        copy_mode=copy_mode,
    )


def file_name_for(config: dict, component_type: str, member: str, environment: str) -> str:
    """Nome do arquivo renderizado por ambiente (ex.: ESTMX001TU.jcl), no
    mesmo padrao das copias por ambiente dos JCLs reais - o membro com o
    sufixo do ambiente."""
    entry = config["deploy_targets"][component_type]
    pattern = entry.get("file_naming", "{member}{env}.jcl")
    return pattern.format(member=member, env=environment)
