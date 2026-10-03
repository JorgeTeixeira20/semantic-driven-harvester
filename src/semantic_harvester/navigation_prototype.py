"""Protótipo de navegação — páginas HTML estáticas geradas por SPARQL.

Implementa a proposta de `docs/experiments.md` ("Protótipo de navegação").
Corre as queries versionadas em `queries/*.rq` com `rdflib` (SPARQL em
memória) sobre `output/corpus_articles.ttl` e gera `output/prototipo/`:

- `index.html`: capturas por ano, textos por `statusCode`, os 10 artigos com
  mais capturas e a lista de todos os artigos (estrutura);
- `artigos/<id>.html`: o histórico de capturas de cada artigo, por ordem
  cronológica, com ligação para cada captura no Arquivo.pt.

Sem servidor nem dependências novas: abre-se `index.html` no browser. Não
faz pedidos à rede nem altera o grafo. Os dados de D e B (só CSV) não entram.
"""

from __future__ import annotations

import argparse
import html
import shutil
from collections import Counter
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from rdflib import Graph, URIRef

INDEX = "index.html"
ARTICLES_DIR = "artigos"

STYLE = """
:root {
  --bg: #f5f6f8; --surface: #ffffff; --text: #0f172a; --muted: #64748b;
  --border: #e2e8f0; --row-hover: #f8fafc; --accent: #4f46e5; --accent-soft: #eef2ff;
  --ok: #047857; --ok-bg: #d1fae5; --warn: #b45309; --warn-bg: #fef3c7;
  --bad: #b91c1c; --bad-bg: #fee2e2; --bar: #c7d2fe; --bar-strong: #6366f1;
  --shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 4px 16px rgba(15, 23, 42, .06);
  --radius: 14px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1020; --surface: #121a2e; --text: #e2e8f0; --muted: #94a3b8;
    --border: #23304d; --row-hover: #18223a; --accent: #a5b4fc; --accent-soft: #1e2546;
    --ok: #6ee7b7; --ok-bg: #0f3b2e; --warn: #fcd34d; --warn-bg: #3b2f10;
    --bad: #fca5a5; --bad-bg: #3f1a1a; --bar: #2e3a6b; --bar-strong: #818cf8;
    --shadow: 0 1px 2px rgba(0, 0, 0, .3), 0 4px 16px rgba(0, 0, 0, .25);
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; overflow-x: hidden; background: var(--bg); color: var(--text); line-height: 1.5;
       font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 3px; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
              font-size: .8rem; }
.wrap { max-width: 76rem; margin: 0 auto; padding: 0 1.25rem; }
header.hero { background: linear-gradient(135deg, #312e81 0%, #4f46e5 55%, #7c3aed 100%);
              color: #fff; padding: 2.5rem 0 4.5rem; }
header.hero .eyebrow { text-transform: uppercase; letter-spacing: .12em; font-size: .72rem;
                       opacity: .8; margin: 0 0 .6rem; }
header.hero h1 { font-size: clamp(1.5rem, 3vw, 2.2rem); line-height: 1.2; margin: 0 0 .6rem;
                 letter-spacing: -.02em; font-weight: 700; }
header.hero p { margin: 0; max-width: 46rem; opacity: .9; }
header.hero a { color: #fff; opacity: .85; }
.crumb { font-size: .85rem; margin: 0 0 1rem; }
main { margin-top: -3rem; padding-bottom: 3rem; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(9.5rem, 100%), 1fr));
         gap: 1rem; margin-bottom: 1.5rem; }
.stat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
        box-shadow: var(--shadow); padding: 1rem 1.2rem; }
.stat .label { color: var(--muted); font-size: .78rem; text-transform: uppercase;
               letter-spacing: .06em; }
.stat .value { font-size: 1.7rem; font-weight: 700; letter-spacing: -.02em; margin-top: .15rem;
               font-variant-numeric: tabular-nums; }
.stat .value.small { font-size: 1.1rem; }
.stat .hint { color: var(--muted); font-size: .8rem; }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(22rem, 100%), 1fr));
          gap: 1.5rem; }
.grid-2 { margin-bottom: 1.5rem; } .grid-2 > .card { margin-bottom: 0; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
        box-shadow: var(--shadow); padding: 1.25rem 1.25rem .75rem; margin-bottom: 1.5rem;
        min-width: 0; }
.card h2 { font-size: 1.05rem; margin: 0 0 .25rem; letter-spacing: -.01em; }
.card .sub { color: var(--muted); font-size: .85rem; margin: 0 0 .9rem; }
.table-wrap { overflow: auto; margin: 0 -1.25rem; }
.table-wrap.tall { max-height: 70vh; }
table { border-collapse: separate; border-spacing: 0; width: 100%; font-size: .88rem; }
th, td { padding: .6rem .9rem; text-align: left; vertical-align: middle;
         border-bottom: 1px solid var(--border); }
th:first-child, td:first-child { padding-left: 1.25rem; }
th:last-child, td:last-child { padding-right: 1.25rem; }
thead th { position: sticky; top: 0; z-index: 1; background: var(--surface); color: var(--muted);
           font-weight: 600; font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; }
tbody tr { transition: background-color .12s ease; }
tbody tr:hover { background: var(--row-hover); }
tbody tr:last-child td { border-bottom: 0; }
th.n, td.n { text-align: center; font-variant-numeric: tabular-nums; }
thead th, td.date { white-space: nowrap; }
td.date { color: var(--muted); font-variant-numeric: tabular-nums; }
td.url { color: var(--muted); max-width: 26rem; overflow: hidden; text-overflow: ellipsis;
         white-space: nowrap; }
td.url a { color: inherit; }
td.title a { font-weight: 550; }
.rank { display: inline-grid; place-items: center; width: 1.6rem; height: 1.6rem; margin-right: .5rem;
        border-radius: 999px; background: var(--accent-soft); color: var(--accent);
        font-size: .75rem; font-weight: 700; }
.badge { display: inline-block; padding: .12rem .55rem; border-radius: 999px; font-size: .76rem;
         font-weight: 600; font-variant-numeric: tabular-nums; }
.badge.ok { color: var(--ok); background: var(--ok-bg); }
.badge.warn { color: var(--warn); background: var(--warn-bg); }
.badge.bad { color: var(--bad); background: var(--bad-bg); }
.badge.muted { color: var(--muted); background: var(--row-hover); }
.bar { position: relative; height: .5rem; min-width: 6rem; border-radius: 999px; background: var(--bar);
       overflow: hidden; }
.bar span { position: absolute; inset: 0 auto 0 0; border-radius: 999px; background: var(--bar-strong); }
.filtros { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; margin: 0 0 1rem; }
.filtros input, .filtros select { font: inherit; color: var(--text); background: var(--bg);
       border: 1px solid var(--border); border-radius: 10px; padding: .6rem .8rem; outline: none;
       transition: border-color .12s ease, box-shadow .12s ease; }
.filtros input { flex: 1 1 20rem; padding-left: 2.2rem;
       background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%2364748b' stroke-width='2' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E");
       background-repeat: no-repeat; background-position: .75rem center; }
.filtros input:focus, .filtros select:focus { border-color: var(--accent);
       box-shadow: 0 0 0 3px var(--accent-soft); }
#contagem { color: var(--accent); background: var(--accent-soft); border-radius: 999px;
            padding: .3rem .75rem; font-size: .82rem; font-weight: 600; white-space: nowrap; }
.chip { display: inline-flex; align-items: center; gap: .35rem; max-width: 100%;
        background: rgba(255, 255, 255, .14); border: 1px solid rgba(255, 255, 255, .25);
        border-radius: 999px; padding: .3rem .8rem; font-size: .82rem; margin-top: 1rem;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
footer { color: var(--muted); font-size: .8rem; padding: 0 0 2.5rem; }
@media (max-width: 640px) {
  header.hero { padding: 1.75rem 0 4rem; }
  td.url { max-width: 12rem; }
  .table-wrap { margin: 0 -1.25rem; }
}
"""

# Filtro do lado do cliente: só a lista de artigos; sem bibliotecas externas.
FILTER_SCRIPT = """
(function () {
  const fold = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
  const input = document.getElementById('pesquisa');
  const select = document.getElementById('secao');
  const rows = Array.from(document.querySelectorAll('#artigos tbody tr'));
  const count = document.getElementById('contagem');
  function apply() {
    const terms = fold(input.value).split(/\\s+/).filter(Boolean);
    const section = select.value;
    let shown = 0;
    for (const row of rows) {
      const ok = (!section || row.dataset.secao === section) &&
                 terms.every(t => row.dataset.texto.includes(t));
      row.hidden = !ok;
      if (ok) shown++;
    }
    count.textContent = shown + ' de ' + rows.length + ' artigos';
  }
  input.addEventListener('input', apply);
  select.addEventListener('change', apply);
  apply();
})();
"""


# --- Queries -----------------------------------------------------------------


def load_query(queries_dir: Path, name: str) -> str:
    return (queries_dir / f"{name}.rq").read_text(encoding="utf-8")


def _value(term: Any) -> Any:
    if term is None:
        return None
    if isinstance(term, URIRef):
        return str(term)
    return term.toPython()


def run_query(
    graph: Graph, queries_dir: Path, name: str, bindings: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    result = graph.query(load_query(queries_dir, name), initBindings=bindings or {})
    names = [str(v) for v in result.vars]
    return [{n: _value(row[n]) for n in names} for row in result]


# --- HTML --------------------------------------------------------------------


def article_id(article_uri: str) -> str:
    """Primeiros 16 caracteres do SHA-256 que já identifica o artigo no grafo."""

    return article_uri.rsplit("/", 1)[-1][:16]


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def esc(value: Any) -> str:
    return html.escape(fmt(value))


def link(href: str, text: Any) -> str:
    return f'<a href="{html.escape(href, quote=True)}">{esc(text)}</a>'


def table(
    headers: list[str], rows: list[list[str]], numeric: set[int] = frozenset(),
    table_id: str = "", row_attrs: list[str] | None = None,
    cell_classes: dict[int, str] | None = None,
) -> str:
    classes = {i: "n" for i in numeric} | (cell_classes or {})
    head = "".join(
        f'<th class="n">{html.escape(h)}</th>' if i in numeric else f"<th>{html.escape(h)}</th>"
        for i, h in enumerate(headers)
    )
    attrs = row_attrs or [""] * len(rows)
    body = "".join(
        f"<tr{attr}>" + "".join(
            f'<td class="{classes[i]}">{cell}</td>' if i in classes else f"<td>{cell}</td>"
            for i, cell in enumerate(row)
        ) + "</tr>"
        for row, attr in zip(rows, attrs)
    )
    ident = f' id="{table_id}"' if table_id else ""
    return f"<table{ident}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def section_of(url: str) -> str:
    """Primeiro segmento do caminho do URL (secção do site)."""

    parts = [p for p in urlsplit(url).path.split("/") if p]
    return parts[0].lower() if parts else ""


def search_text(*values: Any) -> str:
    """Texto sem acentos e em minúsculas, para o filtro do lado do cliente."""

    text = " ".join(fmt(v) for v in values).casefold()
    return "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))


def badge_status(status: Any) -> str:
    if status is None:
        return '<span class="badge muted">—</span>'
    kind = "ok" if 200 <= int(status) < 300 else "warn" if int(status) < 400 else "bad"
    return f'<span class="badge {kind}">{esc(status)}</span>'


def badge_text(available: bool) -> str:
    return ('<span class="badge ok">sim</span>' if available
            else '<span class="badge muted">não</span>')


def short_url(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path + (f"?{parts.query}" if parts.query else "")) or url


def bar(value: int, maximum: int) -> str:
    width = 100 * value / maximum if maximum else 0
    return f'<div class="bar" aria-hidden="true"><span style="width:{width:.1f}%"></span></div>'


def stat(label: str, value: Any, hint: str = "", small: bool = False) -> str:
    cls = "value small" if small else "value"
    hint_html = f'<div class="hint">{html.escape(hint)}</div>' if hint else ""
    return (f'<div class="stat"><div class="label">{html.escape(label)}</div>'
            f'<div class="{cls}">{esc(value)}</div>{hint_html}</div>')


def card(title: str, content: str, sub: str = "") -> str:
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return f'<section class="card"><h2>{title}</h2>{sub_html}{content}</section>'


def page(title: str, hero: str, body: str, script: str = "") -> str:
    return (
        "<!doctype html>\n<html lang=\"pt\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<meta name=\"color-scheme\" content=\"light dark\">"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head><body>"
        f'<header class="hero"><div class="wrap">{hero}</div></header>'
        f'<main class="wrap">{body}</main>'
        '<footer class="wrap"><p>Gerado por <code>semantic_harvester.navigation_prototype</code> '
        "a partir de <code>output/corpus_articles.ttl</code> com as queries SPARQL de "
        "<code>queries/</code>.</p></footer>"
        + (f"<script>{script}</script>" if script else "")
        + "</body></html>\n"
    )


def index_page(
    articles: list[dict], top: list[dict], per_year: list[dict], per_status: list[dict],
) -> str:
    total_captures = sum(a["capturas"] for a in articles)
    total_texts = sum(a["textos"] for a in articles)
    share = f"{100 * total_texts / total_captures:.1f}% das capturas".replace(".", ",") if total_captures else ""
    years = [r["ano"] for r in per_year if r["ano"] is not None]
    period = f"{min(years)}–{max(years)}" if years else "—"
    max_year = max((r["capturas"] for r in per_year), default=0)
    hero = (
        '<p class="eyebrow">Semantic Driven Harvester · Arquivo.pt · RDF</p>'
        "<h1>Protótipo de navegação do corpus</h1>"
        "<p>Artigos do Record recolhidos do Arquivo.pt e representados em RDF. "
        "Cada artigo leva ao seu histórico de capturas, por ordem cronológica.</p>"
    )
    sections = Counter(section_of(r["url"]) for r in articles)
    body = [
        '<div class="stats">',
        stat("Artigos", len(articles), "jornal Record"),
        stat("Capturas arquivadas", total_captures),
        stat("Com texto extraído", total_texts, share),
        stat("Período das capturas", period, small=True),
        "</div>",
        '<div class="grid-2">',
        card("Capturas por ano", '<div class="table-wrap">' + table(
            ["Ano", "Capturas", "Com texto", "Artigos", ""],
            [[f"<strong>{esc(r['ano'])}</strong>", esc(r["capturas"]), esc(r["textos"]),
              esc(r["artigos"]), bar(r["capturas"], max_year)] for r in per_year],
            numeric={1, 2, 3}) + "</div>"),
        card("Texto disponível por <code>statusCode</code>", '<div class="table-wrap">' + table(
            ["statusCode", "Capturas", "Com texto"],
            [[badge_status(r["status"]), esc(r["capturas"]), esc(r["com_texto"])]
             for r in per_status], numeric={1, 2}) + "</div>",
            "Só as respostas 200 têm texto extraído."),
        "</div>",
        card("Os 10 artigos com mais capturas", '<div class="table-wrap">' + table(
            ["Artigo", "Capturas", "Primeira", "Última"],
            [[f'<span class="rank">{i}</span>'
              + link(f"{ARTICLES_DIR}/{article_id(r['artigo'])}.html", r["titulo"]),
              esc(r["capturas"]), esc(r["primeira"]), esc(r["ultima"])]
             for i, r in enumerate(top, start=1)], numeric={1},
            cell_classes={2: "date", 3: "date"}) + "</div>"),
        card("Todos os artigos",
             '<div class="filtros"><input id="pesquisa" type="search" '
             'placeholder="Pesquisar no título ou no URL…" aria-label="Pesquisar artigos">'
             '<select id="secao" aria-label="Filtrar por secção">'
             '<option value="">Todas as secções</option>'
             + "".join(f'<option value="{esc(sec)}">{esc(sec)} ({n})</option>'
                       for sec, n in sorted(sections.items()))
             + '</select><span id="contagem"></span></div>'
             + '<div class="table-wrap tall">' + table(
                 ["Artigo", "URL original", "Capturas", "Com texto", "Primeira", "Última"],
                 [[link(f"{ARTICLES_DIR}/{article_id(r['artigo'])}.html", r["titulo"]),
                   link(r["url"], short_url(r["url"])), esc(r["capturas"]), esc(r["textos"]),
                   esc(r["primeira"]), esc(r["ultima"])] for r in articles],
                 numeric={2, 3}, table_id="artigos",
                 row_attrs=[f' data-secao="{esc(section_of(r["url"]))}"'
                            f' data-texto="{html.escape(search_text(r["titulo"], r["url"]), quote=True)}"'
                            for r in articles],
                 cell_classes={0: "title", 1: "url", 4: "date", 5: "date"}) + "</div>",
             f"{len(sections)} secções do site. Pesquisa sem distinguir maiúsculas nem acentos."),
    ]
    return page("Protótipo de navegação", hero, "".join(body), FILTER_SCRIPT)


def article_page(article: dict, history: list[dict]) -> str:
    rows = [
        [esc(r["data"]), f'<span class="mono">{esc(r["tstamp"])}</span>', badge_status(r["status"]),
         f'<span class="mono">{esc(r["digest"])}</span>', esc(r["tamanho"]),
         badge_text(bool(r["ficheiro"])),
         link(r["arquivo"], "Abrir ↗") if r["arquivo"] else "—"]
        for r in history
    ]
    hero = (
        f'<p class="crumb"><a href="../{INDEX}">← Todos os artigos</a></p>'
        f"<h1>{esc(article['titulo'])}</h1>"
        f'<a class="chip" href="{html.escape(article["url"], quote=True)}">'
        f"{esc(short_url(article['url']))} ↗</a>"
    )
    body = [
        '<div class="stats">',
        stat("Capturas", article["capturas"]),
        stat("Com texto", article["textos"]),
        stat("Primeira captura", article["primeira"], small=True),
        stat("Última captura", article["ultima"], small=True),
        "</div>",
        card("Histórico de capturas", '<div class="table-wrap">' + table(
            ["Data", "tstamp", "statusCode", "digest", "Tamanho (bytes)", "Texto", "Arquivo.pt"],
            rows, numeric={2, 4, 5}, cell_classes={0: "date"}) + "</div>",
            "Por ordem cronológica, uma linha por captura."),
    ]
    return page(fmt(article["titulo"]), hero, "".join(body))


# --- Geração -----------------------------------------------------------------


def generate(
    ttl_path: Path, queries_dir: Path, out_dir: Path
) -> dict[str, Any]:
    graph = Graph().parse(ttl_path, format="turtle")
    articles = run_query(graph, queries_dir, "artigos")
    top = run_query(graph, queries_dir, "mais_capturados")
    per_year = run_query(graph, queries_dir, "capturas_por_ano")
    per_status = run_query(graph, queries_dir, "textos_por_status")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / ARTICLES_DIR).mkdir(parents=True)
    (out_dir / INDEX).write_text(
        index_page(articles, top, per_year, per_status), encoding="utf-8"
    )
    history_rows = 0
    for article in articles:
        history = run_query(graph, queries_dir, "historico_artigo",
                            {"artigo": URIRef(article["artigo"])})
        history_rows += len(history)
        path = out_dir / ARTICLES_DIR / f"{article_id(article['artigo'])}.html"
        path.write_text(article_page(article, history), encoding="utf-8")
    return {
        "artigos": articles, "mais_capturados": top, "capturas_por_ano": per_year,
        "textos_por_status": per_status, "linhas_de_historico": history_rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.navigation_prototype",
        description=__doc__.splitlines()[0],
    )
    parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    out_dir = root / "output" / "prototipo"
    result = generate(root / "output" / "corpus_articles.ttl", root / "queries", out_dir)
    print(f"Artigos: {len(result['artigos'])}; linhas de histórico: "
          f"{result['linhas_de_historico']}")
    print(f"Abrir no browser: {out_dir / INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
