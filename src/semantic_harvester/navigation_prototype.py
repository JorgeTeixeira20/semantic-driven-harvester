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
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 72rem;
       padding: 0 1rem; color: #1f2328; background: #fff; }
h1 { font-size: 1.5rem; } h2 { font-size: 1.2rem; margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; }
th, td { border-bottom: 1px solid #d0d7de; padding: .35rem .5rem; text-align: left;
         vertical-align: top; }
th { background: #f6f8fa; }
th.n, td.n { text-align: center; font-variant-numeric: tabular-nums; }
p.meta, footer { color: #59636e; font-size: .85rem; }
code { font-size: .85rem; }
.filtros { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; margin: .5rem 0 1rem; }
.filtros input { flex: 1 1 20rem; padding: .4rem .6rem; font-size: .95rem;
                 border: 1px solid #d0d7de; border-radius: 6px; }
.filtros select { padding: .4rem; font-size: .95rem; border: 1px solid #d0d7de; border-radius: 6px; }
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
) -> str:
    head = "".join(
        f'<th class="n">{html.escape(h)}</th>' if i in numeric else f"<th>{html.escape(h)}</th>"
        for i, h in enumerate(headers)
    )
    attrs = row_attrs or [""] * len(rows)
    body = "".join(
        f"<tr{attr}>" + "".join(
            f'<td class="n">{cell}</td>' if i in numeric else f"<td>{cell}</td>"
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


def page(title: str, body: str, script: str = "") -> str:
    return (
        "<!doctype html>\n<html lang=\"pt\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head><body>"
        f"{body}<footer><p>Gerado por <code>semantic_harvester.navigation_prototype</code> "
        f"a partir de <code>output/corpus_articles.ttl</code> com as queries de "
        f"<code>queries/</code>.</p></footer>"
        + (f"<script>{script}</script>" if script else "")
        + "</body></html>\n"
    )


def index_page(
    articles: list[dict], top: list[dict], per_year: list[dict], per_status: list[dict],
) -> str:
    total_captures = sum(a["capturas"] for a in articles)
    total_texts = sum(a["textos"] for a in articles)
    body = [
        "<h1>Semantic Driven Harvester — protótipo de navegação</h1>",
        f"<p class=\"meta\">{len(articles)} artigos do Record, {total_captures} capturas "
        f"arquivadas, {total_texts} com texto extraído disponível. Cada linha da lista "
        "de artigos leva ao histórico de capturas desse artigo.</p>",
        "<h2>Capturas por ano</h2>",
        table(["Ano", "Capturas", "Com texto", "Artigos"],
              [[esc(r["ano"]), esc(r["capturas"]), esc(r["textos"]), esc(r["artigos"])]
               for r in per_year], numeric={1, 2, 3}),
        "<h2>Texto disponível por <code>statusCode</code></h2>",
        table(["statusCode", "Capturas", "Com texto"],
              [[esc(r["status"]), esc(r["capturas"]), esc(r["com_texto"])] for r in per_status],
              numeric={1, 2}),
        "<h2>Os 10 artigos com mais capturas</h2>",
        table(["Artigo", "Capturas", "Primeira", "Última"],
              [[link(f"{ARTICLES_DIR}/{article_id(r['artigo'])}.html", r["titulo"]),
                esc(r["capturas"]), esc(r["primeira"]), esc(r["ultima"])] for r in top],
              numeric={1}),
        "<h2>Todos os artigos</h2>",
        '<div class="filtros"><input id="pesquisa" type="search" '
        'placeholder="Pesquisar no título ou no URL…" aria-label="Pesquisar artigos">'
        '<select id="secao" aria-label="Filtrar por secção"><option value="">Todas as secções</option>'
        + "".join(f'<option value="{esc(sec)}">{esc(sec)} ({n})</option>'
                  for sec, n in sorted(Counter(section_of(r["url"]) for r in articles).items()))
        + '</select><span id="contagem" class="meta"></span></div>',
        table(["Artigo", "URL original (RecursoWeb)", "Capturas", "Com texto", "Primeira", "Última"],
              [[link(f"{ARTICLES_DIR}/{article_id(r['artigo'])}.html", r["titulo"]),
                link(r["url"], r["url"]), esc(r["capturas"]), esc(r["textos"]),
                esc(r["primeira"]), esc(r["ultima"])] for r in articles],
              numeric={2, 3}, table_id="artigos",
              row_attrs=[f' data-secao="{esc(section_of(r["url"]))}"'
                         f' data-texto="{html.escape(search_text(r["titulo"], r["url"]), quote=True)}"'
                         for r in articles]),
    ]
    return page("Protótipo de navegação", "".join(body), FILTER_SCRIPT)


def article_page(article: dict, history: list[dict]) -> str:
    rows = [
        [esc(r["data"]), esc(r["tstamp"]), esc(r["status"]), f"<code>{esc(r['digest'])}</code>",
         esc(r["tamanho"]), "sim" if r["ficheiro"] else "não",
         link(r["arquivo"], "Arquivo.pt") if r["arquivo"] else "—"]
        for r in history
    ]
    body = [
        f"<p><a href=\"../{INDEX}\">← todos os artigos</a></p>",
        f"<h1>{esc(article['titulo'])}</h1>",
        f"<p class=\"meta\">URL original: {link(article['url'], article['url'])}<br>"
        f"{article['capturas']} capturas, {article['textos']} com texto; de "
        f"{esc(article['primeira'])} a {esc(article['ultima'])}.</p>",
        "<h2>Histórico de capturas (ordem cronológica)</h2>",
        table(["Data", "tstamp", "statusCode", "digest", "Tamanho", "Texto", "Captura"],
              rows, numeric={4}),
    ]
    return page(fmt(article["titulo"]), "".join(body))


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
