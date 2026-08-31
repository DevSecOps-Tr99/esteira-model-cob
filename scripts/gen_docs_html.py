#!/usr/bin/env python3
"""Gera docs-html/ a partir do README.md, COMO-RODAR-MANUALMENTE.md e docs/*.md.

Mantem o docs-html/ (site estatico simples, sem build step no CI) em sincronia
com as fontes em Markdown, evitando o drift manual que gerou paginas
desatualizadas ou ausentes no espelho HTML. Uso:

    python scripts/gen_docs_html.py
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
OUT_DIR = ROOT / "docs-html"

# (arquivo fonte relativo ao repo, arquivo de saida em docs-html/, titulo no nav)
PAGES = [
    ("README.md", "index.html", "esteira-model-cob"),
    ("COMO-RODAR-MANUALMENTE.md", "como-rodar-manualmente.html", "Como rodar manualmente"),
    ("docs/arquitetura.md", "arquitetura.html", "Arquitetura"),
    ("docs/gates.md", "gates.html", "Os 3 gates"),
    ("docs/seguranca.md", "seguranca.html", "Seguranca"),
    ("docs/integracao-zos.md", "integracao-zos.html", "Integracao z/OS"),
    ("docs/gitflow.md", "gitflow.html", "Gitflow"),
    ("docs/ambiente-validacao.md", "ambiente-validacao.html", "Ambiente de validacao (VM)"),
    ("docs/poc-demo.md", "poc-demo.html", "Roteiro de demo"),
    ("docs/kickoff-perguntas.md", "kickoff-perguntas.html", "Perguntas de kickoff"),
    ("docs/validacao-tecnica.md", "validacao-tecnica.html", "Validacao tecnica"),
    (
        "docs/pre-requisitos-ambiente-real.md",
        "pre-requisitos-ambiente-real.html",
        "Pre-requisitos ambiente real",
    ),
    (
        "docs/reuniao-endevor-jcl-binarios.md",
        "reuniao-endevor-jcl-binarios.html",
        "Reuniao Endevor - binarios",
    ),
]

CSS = """
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #5b6270; --border: #e2e5eb;
  --code-bg: #f4f5f7; --accent: #2f5fd6; --nav-bg: #f7f8fa;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #14161a; --fg: #e7e9ec; --muted: #9aa1ad; --border: #2b2f37;
    --code-bg: #1d2026; --accent: #7fa4ff; --nav-bg: #1a1d23; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif;
  display: flex; min-height: 100vh; }
nav { width: 260px; flex-shrink: 0; background: var(--nav-bg); border-right: 1px solid var(--border);
  padding: 24px 16px; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
nav h1 { font-size: 15px; margin: 0 0 16px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
nav a { display: block; padding: 6px 8px; border-radius: 6px; color: var(--fg); text-decoration: none; font-size: 14px; }
nav a:hover { background: var(--code-bg); }
nav a.active { background: var(--accent); color: #fff; }
main { flex: 1; max-width: 860px; margin: 0 auto; padding: 40px 32px 80px; overflow-x: auto; }
h1, h2, h3 { line-height: 1.3; }
h1 { font-size: 28px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
h2 { font-size: 21px; margin-top: 40px; }
h3 { font-size: 17px; }
p, li { line-height: 1.6; }
a { color: var(--accent); }
code { background: var(--code-bg); padding: 2px 5px; border-radius: 4px; font-size: 0.9em; }
pre { background: var(--code-bg); padding: 14px 16px; border-radius: 8px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; overflow-x: auto; display: block; }
th, td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; font-size: 14px; }
th { background: var(--code-bg); }
blockquote { border-left: 3px solid var(--accent); margin: 0; padding: 4px 16px; color: var(--muted); }
.mermaid-note { color: var(--muted); font-size: 13px; font-style: italic; }
""".strip()


def slugify(text: str, sep: str = "-") -> str:
    """Replica o slug do GitHub: remove acentos, minusculo, espacos -> hifen."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", sep, text).strip(sep)
    return text or "section"


def build_nav(active_out_name: str) -> str:
    links = ['<h1>esteira-model-cob</h1>']
    for _, out_name, title in PAGES:
        cls = "active" if out_name == active_out_name else ""
        links.append(f'<a href="{out_name}" class="{cls}">{title}</a>')
    return "<nav>" + "".join(links) + "</nav>"


def fix_relative_md_links(html: str) -> str:
    """href="arquivo.md" (mesma pasta, sem barra) -> href="arquivo.html"

    Mantem inalterados os links tipo href="docs/arquivo.md" (usados no
    README/index para apontar para o repositorio no GitHub) e links
    externos (http...).
    """

    def repl(match: re.Match[str]) -> str:
        href = match.group(1)
        if re.fullmatch(r"[\w.-]+\.md", href):
            return f'href="{href[:-3]}.html"'
        return match.group(0)

    return re.sub(r'href="([^"]+)"', repl, html)


def render(md_path: Path, out_name: str, title: str) -> str:
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"slugify": slugify}},
    )
    text = md_path.read_text(encoding="utf-8")
    # markdown core nao tem strikethrough (~~texto~~) - o resto do
    # pipeline (GitHub) ja renderiza via GFM, so precisamos supri-lo aqui.
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    body = md.convert(text)
    body = fix_relative_md_links(body)
    nav = build_nav(out_name)
    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>{title} - esteira-model-cob</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{CSS}
</style>
</head>
<body>
{nav}
<main>
{body}
</main>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for src_rel, out_name, title in PAGES:
        src_path = ROOT / src_rel
        html = render(src_path, out_name, title)
        (OUT_DIR / out_name).write_text(html, encoding="utf-8", newline="\n")
        print(f"{src_rel} -> docs-html/{out_name}")


if __name__ == "__main__":
    main()
