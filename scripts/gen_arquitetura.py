"""Gera o diagrama de arquitetura da esteira da POC a partir de uma unica
definicao: docs/arquitetura/esteira-poc.excalidraw (editavel no
excalidraw.com ou na extensao do VS Code) e docs/arquitetura/esteira-poc.svg
(renderizado direto pelo GitHub no Markdown).

Os icones vem de docs/arquitetura/icones/ (Azure Architecture Icons e
Primer Octicons) e sao embutidos nos dois arquivos.

Uso: python scripts/gen_arquitetura.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "arquitetura"
ICON_DIR = OUT_DIR / "icones"

FONT = "Segoe UI, Helvetica, Arial, sans-serif"
INK = "#1f2328"
MUTED = "#57606a"
BLUE = "#0078d4"
GREEN = "#107c10"
PURPLE = "#8250df"
RED = "#cf222e"

random.seed(7)


def _nonce() -> int:
    return random.randint(1, 2**31 - 1)


def _text_size(text: str, size: float) -> tuple[float, float]:
    lines = text.split("\n")
    width = max(len(line) for line in lines) * size * 0.56
    return width, len(lines) * size * 1.25


@dataclass
class Diagram:
    elements: list[dict] = field(default_factory=list)
    files: dict[str, dict] = field(default_factory=dict)
    svg: list[str] = field(default_factory=list)
    _seq: int = 0

    def _id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"

    def _base(self, kind: str, x: float, y: float, w: float, h: float, **extra) -> dict:
        element = {
            "id": self._id(kind),
            "type": kind,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": INK,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": _nonce(),
            "version": 1,
            "versionNonce": _nonce(),
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
        }
        element.update(extra)
        self.elements.append(element)
        return element

    # ------------------------------------------------------------ primitivas

    def rect(self, x, y, w, h, *, fill="#ffffff", stroke=INK, dashed=False, width=1.5, group=None):
        self._base(
            "rectangle", x, y, w, h,
            backgroundColor=fill, strokeColor=stroke, strokeWidth=width,
            strokeStyle="dashed" if dashed else "solid",
            roundness={"type": 3}, groupIds=[group] if group else [],
        )
        dash = ' stroke-dasharray="8 6"' if dashed else ""
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{dash}/>'
        )

    def text(self, x, y, value, *, size=13, color=INK, bold=False, group=None, anchor="start"):
        w, h = _text_size(value, size)
        ex = x - w / 2 if anchor == "middle" else x
        self._base(
            "text", ex, y, w, h,
            strokeColor=color, text=value, originalText=value, fontSize=size, fontFamily=2,
            textAlign="center" if anchor == "middle" else "left", verticalAlign="top",
            containerId=None, lineHeight=1.25, autoResize=True, groupIds=[group] if group else [],
        )
        weight = ' font-weight="600"' if bold else ""
        spans = "".join(
            f'<tspan x="{x}" dy="{size * 1.25 if i else size}">{escape(line)}</tspan>'
            for i, line in enumerate(value.split("\n"))
        )
        self.svg.append(
            f'<text font-family="{FONT}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}"{weight} y="{y}">{spans}</text>'
        )

    def icon(self, path: str, x, y, size=34, group=None):
        raw = (ICON_DIR / path).read_bytes()
        data_url = "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")
        file_id = hashlib.sha1(raw).hexdigest()
        self.files[file_id] = {"mimeType": "image/svg+xml", "id": file_id, "dataURL": data_url, "created": 1}
        self._base("image", x, y, size, size, fileId=file_id, status="saved", scale=[1, 1],
                   groupIds=[group] if group else [])
        self.svg.append(f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="{data_url}"/>')

    def arrow(self, points, *, color=INK, label=None, label_at=None, dashed=False, width=2, both=False):
        (x0, y0) = points[0]
        rel = [[px - x0, py - y0] for px, py in points]
        xs = [p[0] for p in rel]
        ys = [p[1] for p in rel]
        self._base(
            "arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys),
            strokeColor=color, strokeWidth=width, strokeStyle="dashed" if dashed else "solid",
            points=rel, lastCommittedPoint=None, startBinding=None, endBinding=None,
            startArrowhead="arrow" if both else None, endArrowhead="arrow", elbowed=False,
            roundness={"type": 2},
        )
        marker = f"m{color.strip('#')}"
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        start = f' marker-start="url(#{marker}s)"' if both else ""
        pts = " ".join(f"{px},{py}" for px, py in points)
        self.svg.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"{dash}'
            f'{start} marker-end="url(#{marker})"/>'
        )
        if label:
            lx, ly = label_at or ((points[0][0] + points[-1][0]) / 2, (points[0][1] + points[-1][1]) / 2)
            lw, lh = _text_size(label, 12)
            self._base("rectangle", lx - 3, ly - 2, lw + 6, lh + 4, backgroundColor="#ffffff",
                       strokeColor="transparent", opacity=90)
            self.svg.append(f'<rect x="{lx - 3}" y="{ly - 2}" width="{lw + 6}" height="{lh + 4}" fill="#ffffff" opacity="0.9"/>')
            self.text(lx, ly, label, size=12, color=color, bold=True)

    def node(self, x, y, w, h, icons, title, body, *, fill="#ffffff", stroke=INK):
        group = self._id("grupo")
        self.rect(x, y, w, h, fill=fill, stroke=stroke, group=group)
        ix = x + 12
        for path in icons:
            self.icon(path, ix, y + 10, group=group)
            ix += 40
        self.text(ix + 4, y + 16, title, size=15, bold=True, group=group)
        self.text(x + 14, y + 58, body, size=12.5, color=INK, group=group)

    # ---------------------------------------------------------------- saida

    def write(self, width: int, height: int) -> None:
        excalidraw = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": self.elements,
            "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
            "files": self.files,
        }
        (OUT_DIR / "esteira-poc.excalidraw").write_text(
            json.dumps(excalidraw, ensure_ascii=False, indent=1), encoding="utf-8"
        )

        colors = sorted({e["strokeColor"] for e in self.elements if e["type"] == "arrow"})
        markers = "".join(
            f'<marker id="m{c.strip("#")}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            f'<marker id="m{c.strip("#")}s" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="{c}"/></marker>'
            for c in colors
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><defs>{markers}</defs>'
            f'<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(self.svg) + "</svg>\n"
        )
        (OUT_DIR / "esteira-poc.svg").write_text(svg, encoding="utf-8")


def build() -> Diagram:
    d = Diagram()

    d.text(40, 24, "esteira-model-cob · arquitetura da esteira da POC", size=26, bold=True)
    d.text(
        40, 62,
        "Validação de JCL no GitHub Actions e publicação por ambiente (TU/TI/PRD) em um servidor "
        "de destino na Azure, com credenciais no Key Vault e acesso por SSH.",
        size=14, color=MUTED,
    )

    # Desenvolvedor
    d.node(70, 100, 360, 84, ["github/person.svg"], "Desenvolvedor",
           "VS Code + git · Gitflow (feature → develop → release → main)")

    # ------------------------------------------------------------- GitHub
    d.rect(40, 200, 840, 880, fill="#f6f8fa", stroke=INK, width=2)
    d.icon("github/mark-github.svg", 290, 212, size=30)
    d.text(330, 216, "GitHub · DevSecOps-Tr99 (3 repositórios públicos)", size=17, bold=True)

    d.node(70, 260, 360, 130, ["github/git-branch.svg"], "Repositórios",
           "esteira-model-cob-jcl: JCLs + parâmetros + caller\nesteira-model-cob: motor + reutilizável + regras\nesteira-model-cob-infra: Bicep + provisionamento\nGitflow e tags vX.Y.Z")
    d.node(470, 260, 380, 130, ["github/workflow.svg"], "Caller → workflow reutilizável",
           "jcl: esteira.yml (gatilhos + seletor TU|TI|PRD)\n  uses: esteira-model-cob/…/jcl-pipeline.yml@main\n  secrets: inherit\nPR → validate · push/seletor → validate + deploy")
    d.node(70, 440, 360, 210, ["github/shield-check.svg"], "Job validate · ubuntu-latest",
           "checkout do repo jcl + motor (.esteira)\ngitleaks (histórico completo)\nRules Engine + Quality/Security Gate\n  em TU, TI e PRD\nJCL Pipeline Report (artifact)\n\nFinding crítico → FAILED → não publica\n(testes/ProLeap: CI do próprio motor)")
    d.node(470, 440, 380, 210, ["github/person.svg", "github/lock.svg"], "Environments (repo jcl)",
           "TU   · sem aprovação\nTI   · 1 aprovador\nPRD · 1 aprovador\n\nVariables por Environment (JCL_*):\nACCT · PROGRAMMER · CLASS · MSGCLASS\nSCHENV · NOTIFY · HLQ · UNIT\nSPACE_PRIMARY/SECONDARY · DATACLAS")
    d.node(70, 700, 360, 200, ["github/key.svg"], "Secret e variables (repo jcl)",
           "secret SPN_KV_DEV_SECRET (JSON do SPN)\nGH_KV_DEV · DEPLOY_SERVERS_<ENV>\nG_DEPLOYMENT_TARGET_LINUX_<ENV>_USER\nG_DEPLOYMENT_TARGET_LINUX_<ENV>_KEY\nG_DEPLOYMENT_TARGET_LINUX_<ENV>_TOKEN\nG_DEPLOYMENT_TARGET_<ENV>_PATH\nG_DEPLOYMENT_TARGET_LINUX_KNOWN_HOSTS")
    d.node(470, 700, 380, 250, ["github/terminal.svg"], "Job deploy · runs-on estm-runner",
           "1  render → build/<ENV>/ESTMX001<ENV>.jcl\n2  gate no JCL final (PASS obrigatório)\n3  azure/login com o SPN\n4  kv-fetch: chave SSH + token (mascarados)\n5  deploy: SSH + SCP + estm-submit\n6  upload do JCL publicado (artifact)\n7  apaga credenciais + az logout\n\nJob Summary: origem de cada variável,\nversões no Key Vault, whoami remoto, JOBID")
    d.node(70, 950, 360, 100, ["github/package.svg"], "Artifacts do run",
           "jcl-pipeline-reports · jcl-publicado-<ENV>")

    # ------------------------------------------------------------- Azure
    d.rect(920, 200, 800, 880, fill="#eff6fc", stroke=BLUE, width=2)
    d.icon("azure/subscription.svg", 936, 212, size=30)
    d.text(976, 216, "Azure · subscription da POC (tenant TR99)", size=17, bold=True, color=INK)

    d.node(950, 260, 340, 136, ["azure/app-registration.svg"], "Entra ID · SPN da esteira",
           "sp-esteira-model-cob-poc-kv\nusado pelo azure/login\npapel: Key Vault Secrets User (só no KV)", stroke=BLUE)
    d.node(1330, 260, 360, 136, ["github/file-code.svg"], "Infra como código",
           "repo esteira-model-cob-infra\nmain.bicep + cloud-init + estm-submit\nprovisionar.ps1 (idempotente)\nauto-shutdown 22h (Brasília) nas 2 VMs", stroke=BLUE)

    d.rect(950, 420, 740, 640, fill="#ffffff", stroke=BLUE, dashed=True)
    d.icon("azure/resource-group.svg", 1084, 430, size=28)
    d.text(1120, 434, "rg-esteira-model-cob-poc · brazilsouth", size=15, bold=True, color=BLUE)

    d.node(1330, 470, 340, 170, ["azure/key-vault.svg"], "Key Vault kv-estm-poc-*",
           "RBAC · soft delete 7 dias\nestm-tu | ti | prd-ssh-key\nestm-tu | ti | prd-token (fictício)\nestm-admin-ssh-key (emergência)", stroke=BLUE)

    d.rect(970, 680, 700, 360, fill="#f3faf3", stroke=GREEN, dashed=True)
    d.icon("azure/virtual-network.svg", 984, 690, size=28)
    d.icon("azure/nsg.svg", 1018, 690, size=28)
    d.text(1072, 692, "vnet-estm-poc · 10.60.0.0/16\nNSG: sem entrada da internet",
           size=13, bold=True, color=GREEN)

    d.node(990, 740, 280, 280, ["azure/virtual-machine.svg", "github/server.svg"], "vm-estm-runner",
           "Standard_D2s_v4 · Ubuntu 24.04\nsem IP público\n\nGitHub Actions runner (systemd)\nlabels: self-hosted, linux, x64,\n            estm-runner\naz CLI · Python 3.12 · ssh/scp\n\nsó saída HTTPS para o GitHub\ne para o Key Vault", stroke=GREEN)
    d.node(1370, 740, 290, 280, ["azure/virtual-machine.svg", "azure/managed-identity.svg"], "vm-estm-alvo",
           "10.60.1.10 · Standard_D2s_v4\nsem IP público · managed identity\n\nusuários estmtu | estmti | estmprd\n(1 chave SSH por ambiente)\n/srv/estm/<ENV>/<run>-<sha>/\nESTM.POC.<ENV>.JCLLIB/<MEMBRO>\n\nestm-submit: valida o token,\ngera JOBID e spool JES2", stroke=GREEN)

    # ------------------------------------------------------------- fluxo
    d.arrow([(250, 184), (250, 260)], color=PURPLE, label="① push / PR", label_at=(160, 205))
    d.arrow([(430, 325), (470, 325)], color=PURPLE)
    d.arrow([(250, 390), (250, 440)], color=PURPLE, label="②", label_at=(258, 405))
    d.arrow([(430, 545), (470, 545)], color=PURPLE, label="③", label_at=(440, 520))
    d.arrow([(660, 650), (660, 700)], color=PURPLE, label="aprovação TI/PRD", label_at=(668, 664))
    d.arrow([(430, 800), (470, 800)], color=MUTED, dashed=True)
    d.arrow([(990, 880), (850, 880)], color=GREEN, label="④ runner busca o job\n(HTTPS 443, só saída)",
            label_at=(858, 890))
    d.arrow([(1060, 740), (1060, 396)], color=BLUE, label="⑤ azure/login\n(SPN)", label_at=(1068, 540))
    d.arrow([(1270, 760), (1380, 640)], color=BLUE, label="⑥ lê chave SSH\n+ token", label_at=(1150, 600))
    d.arrow([(1270, 880), (1370, 880)], color=RED, width=2.5, label="⑦ SSH :22\n+ SCP", label_at=(1280, 840))
    d.arrow([(1500, 740), (1500, 640)], color=BLUE, label="⑧ valida token\n(managed identity)",
            label_at=(1508, 650))

    legend = (
        "①  Push ou PR no repositório (Gitflow). O seletor do workflow_dispatch escolhe TU, TI ou PRD na hora de publicar.\n"
        "②  O caller do repositório de JCL chama o workflow reutilizável: gitleaks e Quality/Security Gate em TU, TI e PRD. Finding crítico bloqueia.\n"
        "③  deploy depende do validate e do GitHub Environment: TU segue direto, TI e PRD esperam aprovação.\n"
        "④  O runner self-hosted dentro da VNet busca o job no GitHub (conexão de saída, nenhuma porta aberta).\n"
        "⑤  azure/login com o JSON do SPN (padrão corporativo SPN_KV_DEV_SECRET).\n"
        "⑥  kv-fetch lê a chave SSH e o token do ambiente pelo nome guardado nas variables; valores mascarados no log.\n"
        "⑦  SSH/SCP com known_hosts fixo: publica ESTMX001<ENV>.jcl e chama estm-submit, que recebe o token pelo stdin.\n"
        "⑧  O destino confere o token no Key Vault com a própria managed identity e devolve JOBID, RC e spool ao Job Summary."
    )
    d.rect(40, 1110, 1680, 190, fill="#ffffff", stroke=MUTED)
    d.text(60, 1124, "Fluxo", size=15, bold=True)
    d.text(60, 1150, legend, size=13)
    return d


if __name__ == "__main__":
    build().write(1760, 1320)
    print(f"Gerado: {OUT_DIR / 'esteira-poc.excalidraw'}")
    print(f"Gerado: {OUT_DIR / 'esteira-poc.svg'}")
