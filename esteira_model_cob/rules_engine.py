"""Rules Engine: aplica config/rules.yml sobre um JclJob.

As regras vivem em YAML (nao hardcoded em Python) para que o banco possa
ajustar padroes de nomenclatura, severidades e programas permitidos sem
alterar codigo - ver docs/seguranca.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .parser import JclJob

# Programas batch de uso comum liberados por padrao para a POC. Em producao
# isso viria de config/rules.yml por aplicacao, nao hardcoded aqui.
_ALLOWED_PROGRAMS = {"IEFBR14", "IDCAMS", "IEBGENER", "SORT", "ICEMAN"}


@dataclass
class Finding:
    rule_id: str
    name: str
    severity: str
    message: str


@dataclass
class Rule:
    id: str
    name: str
    kind: str
    severity: str
    message: str
    pattern: str | None = None
    check: str | None = None
    invert: bool = False


def load_rules(path: str | Path) -> list[Rule]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [
        Rule(
            id=rule["id"],
            name=rule["name"],
            kind=rule["kind"],
            severity=rule["severity"],
            message=rule["message"],
            pattern=rule.get("pattern"),
            check=rule.get("check"),
            invert=rule.get("invert", False),
        )
        for rule in data.get("rules", [])
    ]


def load_dataset_naming_pattern(path: str | Path) -> re.Pattern:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return re.compile(data["naming"]["pattern"])


def evaluate(job: JclJob, rules: list[Rule], naming_pattern: re.Pattern) -> list[Finding]:
    findings: list[Finding] = []

    for rule in rules:
        if rule.kind == "pattern":
            matched = re.search(rule.pattern, job.raw_text) is not None
            violated = (not matched) if rule.invert else matched
            if violated:
                findings.append(Finding(rule.id, rule.name, rule.severity, rule.message))

        elif rule.kind == "structural":
            findings.extend(_evaluate_structural(rule, job, naming_pattern))

    return findings


def _evaluate_structural(rule: Rule, job: JclJob, naming_pattern: re.Pattern) -> list[Finding]:
    if rule.check == "job_name_present":
        if not job.job_name:
            return [Finding(rule.id, rule.name, rule.severity, rule.message)]
        return []

    if rule.check == "dataset_naming":
        return [
            Finding(rule.id, rule.name, rule.severity, f"{rule.message} ({dsn})")
            for dsn in job.all_dsns()
            if not naming_pattern.match(dsn)
        ]

    if rule.check == "program_allowed":
        return [
            Finding(rule.id, rule.name, rule.severity, f"{rule.message} (PGM={step.pgm})")
            for step in job.steps
            if step.pgm and step.pgm not in _ALLOWED_PROGRAMS
        ]

    return []
