"""Classificação Artigo vs. redirecionamento/não-artigo (Caminho A, passo 6).

Regra justificada em `docs/experiments.md` ("Classificação Artigo vs.
redirecionamento/não-artigo" e, para o sinal de URL, "Classificação sem a
Fase 2", 2026-10-20). Usa só o CSV de capturas da Fase 1 (o título vem nos
resultados da pesquisa) — não faz pedidos à API nem depende da Fase 2.

Antes de classificar, agrupa `originalURL` que só diferem no esquema
(`http://`/`https://`) ou em parâmetros de rastreio (`ref`, `utm_*`, `act`,
`est`; ver `url_identity.py`) num único recurso. O URL canónico guardado é um
dos URLs reais do grupo: prefere `https://`, depois o URL sem parâmetros de
rastreio, depois o de mais capturas. Variantes só de esquema devolveram os
mesmos `tstamp` na Fase 2 (não se somam); variantes de rastreio devolveram
capturas distintas (somam-se). As outras formas ficam na coluna `variantes`,
para `corpus_rdf` juntar o raw de todas.

Um recurso é classificado como `Artigo` só se nenhuma das três condições
seguintes se verificar:

1. `/sabermais/` no caminho do URL — página de referência/perfil.
2. `title` igual a ou começado por "Object moved" — página de
   redirecionamento arquivada.
3. O URL não segue nenhum dos esquemas de página de artigo
   (`ARTICLE_URL_SCHEMES`): `/detalhe/` ou `/amp/` no caminho (site atual),
   `interior.aspx?content_id=` (site antigo; o `=` aparece também codificado,
   `content_id/x3d`) ou `tn0cs.asp?nid=`/`tn1cs.asp?nid=` (1999–2000).

O sinal 3 substitui o anterior "mais de 100 capturas na Fase 2"
(`version_history`), que deixou de existir para o corpus alargado.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from .url_identity import has_tracking_params, strip_scheme, without_tracking

REASON_ARTIGO = "artigo"
REASON_SABERMAIS = "sabermais"
REASON_OBJECT_MOVED = "object_moved"
REASON_URL_NOT_ARTICLE = "url_nao_artigo"


def _query_starts(path_end: str, *prefixes: str):
    def matches(path: str, query: str) -> bool:
        return path.endswith(path_end) and query.startswith(prefixes)
    return matches


# (nome, teste sobre o caminho e a query em minúsculas)
ARTICLE_URL_SCHEMES = (
    ("detalhe", lambda path, query: "/detalhe/" in path),
    ("amp", lambda path, query: "/amp/" in path),
    ("interior.aspx?content_id", _query_starts("/interior.aspx", "content_id=", "content_id/x3d")),
    ("tn0cs.asp?nid", _query_starts("/tn0cs.asp", "nid=")),
    ("tn1cs.asp?nid", _query_starts("/tn1cs.asp", "nid=")),
)


def article_url_scheme(url: str) -> str | None:
    """Nome do esquema de URL de artigo a que `url` corresponde, ou `None`."""

    parts = urlsplit(url)
    path, query = parts.path.lower(), parts.query.lower()
    return next((name for name, matches in ARTICLE_URL_SCHEMES if matches(path, query)), None)


@dataclass(frozen=True)
class ClassificationResult:
    original_url: str
    title: str
    captures: int
    is_artigo: bool
    reason: str
    variantes: str = ""


def canonical_key(url: str) -> str:
    """Chave de agrupamento: sem esquema e sem parâmetros de rastreio."""

    return strip_scheme(without_tracking(url))


def choose_canonical_url(urls: list[str], captures_by_url: dict[str, int] | None = None) -> str:
    """Prefere https, depois sem parâmetros de rastreio, depois mais capturas."""

    captures_by_url = captures_by_url or {}
    return min(urls, key=lambda url: (
        not url.startswith("https://"),
        has_tracking_params(url),
        -captures_by_url.get(url, 0),
        url,
    ))


def group_captures(urls: list[str], captures_by_url: dict[str, int]) -> int:
    """Capturas do grupo: variantes só de esquema contam uma vez; as de rastreio somam-se."""

    by_scheme_free: dict[str, int] = {}
    for url in urls:
        key = strip_scheme(url)
        by_scheme_free[key] = max(by_scheme_free.get(key, 0), captures_by_url.get(url, 0))
    return sum(by_scheme_free.values())


def classify(original_url: str, title: str | None, captures: int = 0) -> ClassificationResult:
    path = urlsplit(original_url).path
    normalized_title = (title or "").strip().lower()

    if "/sabermais/" in path:
        reason = REASON_SABERMAIS
    elif normalized_title.startswith("object moved"):
        reason = REASON_OBJECT_MOVED
    elif article_url_scheme(original_url) is None:
        reason = REASON_URL_NOT_ARTICLE
    else:
        reason = REASON_ARTIGO

    return ClassificationResult(
        original_url=original_url,
        title=title or "",
        captures=captures,
        is_artigo=(reason == REASON_ARTIGO),
        reason=reason,
    )


def load_phase1_titles(captures_csv: Path) -> dict[str, dict[str, str]]:
    """Um registo por `originalURL`, mantendo o de maior `num_queries_matched`."""

    csv.field_size_limit(1 << 30)
    by_url: dict[str, dict[str, str]] = {}
    with captures_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            url = row["original_url"]
            existing = by_url.get(url)
            if existing is None or int(row["num_queries_matched"]) > int(
                existing["num_queries_matched"]
            ):
                by_url[url] = row
    return by_url


def load_phase1_capture_counts(captures_csv: Path) -> dict[str, int]:
    """Capturas distintas por `originalURL` na Fase 1 (informativo; não classifica)."""

    csv.field_size_limit(1 << 30)
    tstamps: dict[str, set[str]] = {}
    with captures_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            tstamps.setdefault(row["original_url"], set()).add(row["tstamp"])
    return {url: len(values) for url, values in tstamps.items()}


def classify_corpus(captures_csv: Path) -> list[ClassificationResult]:
    phase1 = load_phase1_titles(captures_csv)
    captures_by_url = load_phase1_capture_counts(captures_csv)

    groups: dict[str, list[str]] = {}
    for url in phase1:
        groups.setdefault(canonical_key(url), []).append(url)

    results: list[ClassificationResult] = []
    for urls in groups.values():
        chosen = choose_canonical_url(urls, captures_by_url)
        title = phase1[chosen]["title"]
        result = classify(chosen, title, group_captures(urls, captures_by_url))
        variants = "|".join(sorted(url for url in urls if url != chosen))
        results.append(replace(result, variantes=variants))

    results.sort(key=lambda result: result.original_url)
    return results


def write_csv(results: list[ClassificationResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0])), lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


def first_path_pattern(url: str) -> str:
    """Host, primeiro segmento do caminho e primeiro parâmetro (para resumir exclusões)."""

    parts = urlsplit(url)
    segments = [segment for segment in parts.path.split("/") if segment]
    first = segments[0].lower() if segments else ""
    param = re.split(r"[=/]", parts.query, maxsplit=1)[0].lower() if parts.query else ""
    return f"{parts.hostname or ''}/{first}" + (f"?{param}" if param else "")


def write_summary_markdown(
    results: list[ClassificationResult], path: Path, source_name: str, csv_name: str
) -> None:
    by_reason: dict[str, list[ClassificationResult]] = {}
    for result in results:
        by_reason.setdefault(result.reason, []).append(result)

    artigos = by_reason.get(REASON_ARTIGO, [])
    sabermais = by_reason.get(REASON_SABERMAIS, [])
    moved = by_reason.get(REASON_OBJECT_MOVED, [])
    not_article = by_reason.get(REASON_URL_NOT_ARTICLE, [])
    schemes = Counter(article_url_scheme(r.original_url) for r in artigos)

    lines = [
        "# Classificação Artigo vs. redirecionamento/não-artigo (passo 6)\n",
        "Regra e justificação em `docs/experiments.md`. Execução real sobre "
        f"`output/{source_name}` (Fase 1), sem pedidos à API e sem a Fase 2.\n",
        "## Resumo\n",
        f"- Recursos distintos (depois de agrupar variantes de esquema http/https "
        f"e de parâmetros de rastreio): {len(results)}",
        f"- Recursos com variantes de URL agrupadas: "
        f"{sum(1 for r in results if r.variantes)}",
        f"- **Classificados como Artigo: {len(artigos)}**",
        f"- Excluídos — `/sabermais/`: {len(sabermais)}",
        f"- Excluídos — `Object moved`: {len(moved)}",
        f"- Excluídos — URL fora dos esquemas de artigo: {len(not_article)}",
        "\n## Artigos por esquema de URL\n",
        "| Esquema | Artigos |",
        "| --- | ---: |",
    ]
    for name, _ in ARTICLE_URL_SCHEMES:
        lines.append(f"| `{name}` | {schemes.get(name, 0)} |")

    lines.extend([
        "\n## Excluídos por URL — padrões mais frequentes\n",
        "Host, primeiro segmento do caminho e primeiro parâmetro; os 40 mais "
        "frequentes.\n",
        "| Padrão | Recursos |",
        "| --- | ---: |",
    ])
    for pattern, count in Counter(first_path_pattern(r.original_url) for r in not_article).most_common(40):
        lines.append(f"| `{pattern}` | {count} |")

    lines.extend([
        "\n## Excluídos — Object moved\n",
        f"{len(moved)} recursos; lista completa em `output/{csv_name}`.",
    ])

    lines.append(
        f"\nLista completa (incluindo os classificados como Artigo) em `output/{csv_name}`."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_classification(
    project_root: Path | None = None,
    captures_csv: Path | None = None,
    label: str = "por_ano",
) -> list[ClassificationResult]:
    """Classifica a Fase 1 `label`; escreve `output/corpus_classification_<label>.*`.

    Não reescreve `output/corpus_classification.csv`, a classificação do
    corpus de 125 artigos de que dependem `corpus_rdf` (reconstrução offline)
    e os Caminhos D e B.
    """

    root = project_root or Path(__file__).resolve().parents[2]
    captures_csv = captures_csv or root / "output" / f"corpus_phase1_{label}_captures.csv"
    csv_path = root / "output" / f"corpus_classification_{label}.csv"

    results = classify_corpus(captures_csv)

    write_csv(results, csv_path)
    write_summary_markdown(
        results, root / "output" / f"corpus_classification_{label}_summary.md",
        captures_csv.name, csv_path.name,
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_classification")
    parser.add_argument("--label", default="por_ano",
                        help="Fase 1 a classificar (output/corpus_phase1_<label>_captures.csv)")
    parser.add_argument("--captures-csv", type=Path, help="CSV de capturas explícito")
    args = parser.parse_args(argv)
    results = run_classification(captures_csv=args.captures_csv, label=args.label)
    artigos = [r for r in results if r.is_artigo]
    print(f"Recursos distintos: {len(results)}")
    print(f"Classificados como Artigo: {len(artigos)}")
    print(f"Relatórios: output/corpus_classification_{args.label}.csv, "
          f"output/corpus_classification_{args.label}_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
