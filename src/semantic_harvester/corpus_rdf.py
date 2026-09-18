"""Passo final do Caminho A — grafo RDF único dos artigos retidos.

Generaliza `build_article_history_graph()` (`rdf_mapper.py`, hoje usada só
para o artigo único do M3) para os artigos classificados como `Artigo` em
`output/corpus_classification.csv` (passo 6).

Não repete pedidos de `version_history`: a Fase 2 já preservou esse raw em
`data/raw/version_history/`; a lista de capturas de cada artigo é
reconstruída a partir desses ficheiros. O único pedido novo à API por
artigo é o download do texto extraído de cada captura
(`build_manifest_records()`, que já reutiliza texto existente em
`data/raw/texts/` via `skip_existing=True`).

Achado durante a implementação, documentado em `docs/experiments.md`: o
`version_history` de um único `originalURL` pode devolver capturas cujo
próprio campo `originalURL` difere em esquema (`http`/`https`) ou em barras
duplicadas/finais no caminho — variantes cosméticas da mesma página, com
`tstamp` genuinamente distintos entre si (não duplicados). Sem normalizar
estas variantes para um único identificador antes de mapear,
`build_article_history_graph()` rejeita o manifesto (exige um único
`original_url`) e o artigo perderia essas capturas. `normalize_for_grouping()`
resolve isto reatribuindo o `originalURL` canónico às variantes cosméticas,
preservando todas as capturas reais.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rdflib import RDF, RDFS, Graph, XSD

from .arquivo_client import ArquivoClient
from .history_pipeline import build_manifest_records
from .rdf_mapper import SDH, build_article_history_graph

LOGGER = logging.getLogger(__name__)

PROGRESS_EVERY = 10


def url_hash16(original_url: str) -> str:
    """Mesmo hash truncado que `ArquivoClient` usa para nomear o raw de version_history."""

    return hashlib.sha256(original_url.encode("utf-8")).hexdigest()[:16]


def load_captures_from_raw(
    original_url: str, version_history_dir: Path
) -> list[dict[str, Any]]:
    """Reconstrói a lista de capturas a partir do raw já preservado pela Fase 2."""

    prefix = f"version_history_{url_hash16(original_url)}_all-all_offset-"
    files = sorted(version_history_dir.glob(f"{prefix}*.json"))
    if not files:
        raise FileNotFoundError(
            f"Raw de version_history não encontrado para {original_url!r} "
            f"em {version_history_dir}"
        )

    captures: list[dict[str, Any]] = []
    for path in files:
        payload = json.loads(path.read_bytes())
        captures.extend(payload.get("response_items", []))
    return captures


def normalize_for_grouping(url: str) -> str:
    """Remove esquema, colapsa barras repetidas e uma barra final.

    Usado só para decidir se dois URLs são a mesma página modulo variação
    cosmética — nunca para gerar identificadores (esses continuam a usar o
    `originalURL` canónico tal como veio da descoberta/classificação).
    """

    scheme_stripped = url.split("://", 1)[-1]
    collapsed = re.sub(r"/{2,}", "/", scheme_stripped)
    return collapsed.rstrip("/")


def normalize_captures_to_canonical_url(
    captures: list[dict[str, Any]], canonical_url: str
) -> tuple[list[dict[str, Any]], int, int]:
    """Reatribui `originalURL` ao valor canónico quando só varia em esquema/barras.

    Descarta (e conta) capturas cujo `originalURL` nem sequer seja uma
    variante cosmética do URL canónico — não observado nos dados desta
    execução, mas evita misturar um recurso diferente por engano. Devolve
    `(capturas_normalizadas, descartadas, variantes_reescritas)`.
    """

    canonical_normalized = normalize_for_grouping(canonical_url)
    normalized: list[dict[str, Any]] = []
    dropped = 0
    rewritten = 0
    for capture in captures:
        capture_url = str(capture.get("originalURL", ""))
        if normalize_for_grouping(capture_url) != canonical_normalized:
            dropped += 1
            continue
        if capture_url != canonical_url:
            capture = {**capture, "originalURL": canonical_url}
            rewritten += 1
        normalized.append(capture)
    return normalized, dropped, rewritten


def load_retained_articles(classification_csv: Path) -> list[dict[str, str]]:
    """Lê a classificação do passo 6 e devolve só os artigos retidos."""

    retained = []
    with classification_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["is_artigo"] == "True":
                retained.append(row)
    return retained


@dataclass(frozen=True)
class ArticleGraphResult:
    original_url: str
    captures_used: int
    captures_url_variants_normalized: int
    captures_dropped_mismatched_url: int
    texts_downloaded_now: int
    texts_reused: int
    texts_failed: int
    error: str | None


def build_one_article_graph(
    client: ArquivoClient,
    original_url: str,
    title: str,
    version_history_dir: Path,
    project_root: Path,
) -> tuple[Graph | None, ArticleGraphResult]:
    try:
        raw_captures = load_captures_from_raw(original_url, version_history_dir)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return None, ArticleGraphResult(original_url, 0, 0, 0, 0, 0, 0, str(exc))

    captures, dropped, variants_normalized = normalize_captures_to_canonical_url(
        raw_captures, original_url
    )
    if dropped:
        LOGGER.warning(
            "%s: %d captura(s) descartada(s) por originalURL não ser variante "
            "cosmética do URL canónico.",
            original_url,
            dropped,
        )

    records = build_manifest_records(client, captures, project_root)
    try:
        graph = build_article_history_graph(records, title, project_root)
    except ValueError as exc:
        LOGGER.error("Falha ao mapear %s: %s", original_url, exc)
        return None, ArticleGraphResult(
            original_url, len(records), variants_normalized, dropped, 0, 0, 0, str(exc)
        )

    downloaded_now = sum(1 for r in records if r["text_downloaded_now"])
    reused = sum(
        1 for r in records if r["text_download_success"] and not r["text_downloaded_now"]
    )
    failed = sum(1 for r in records if not r["text_download_success"])

    return graph, ArticleGraphResult(
        original_url=original_url,
        captures_used=len(records),
        captures_url_variants_normalized=variants_normalized,
        captures_dropped_mismatched_url=dropped,
        texts_downloaded_now=downloaded_now,
        texts_reused=reused,
        texts_failed=failed,
        error=None,
    )


def write_report_csv(results: list[ArticleGraphResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0])))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


def write_summary_markdown(
    results: list[ArticleGraphResult], graph_size: int, path: Path
) -> None:
    successes = [r for r in results if r.error is None]
    failures = [r for r in results if r.error is not None]
    total_captures = sum(r.captures_used for r in successes)
    total_downloaded = sum(r.texts_downloaded_now for r in successes)
    total_reused = sum(r.texts_reused for r in successes)
    total_failed = sum(r.texts_failed for r in successes)
    total_variants = sum(r.captures_url_variants_normalized for r in successes)
    total_dropped = sum(r.captures_dropped_mismatched_url for r in results)
    articles_with_variants = sum(
        1 for r in successes if r.captures_url_variants_normalized > 0
    )

    lines = [
        "# Grafo RDF do corpus do Caminho A (passo final)\n",
        f"Execução real sobre os {len(results)} artigos classificados como "
        "`Artigo` em `output/corpus_classification.csv`. As capturas foram "
        "reconstruídas a partir do raw de `version_history` já preservado "
        "pela Fase 2 (`data/raw/version_history/`), sem pedidos novos; só o "
        "download dos textos extraídos fez pedidos reais à API.\n",
        "## Resumo\n",
        f"- Artigos mapeados com sucesso: {len(successes)} de {len(results)}",
        f"- Artigos com falha (raw em falta ou manifesto inválido): {len(failures)}",
        f"- Total de capturas incluídas no grafo: {total_captures}",
        f"- Textos descarregados nesta execução: {total_downloaded}",
        f"- Textos reutilizados (já existentes em `data/raw/texts/`): {total_reused}",
        f"- Textos indisponíveis (falha ou 404): {total_failed}",
        f"- Triplos no grafo final (`output/corpus_articles.ttl`): {graph_size}",
        f"- Capturas com `originalURL` normalizado (variante de esquema ou "
        f"barras da mesma página): {total_variants}, em {articles_with_variants} "
        "artigos",
        f"- Capturas descartadas por `originalURL` não ser variante cosmética "
        f"do URL canónico: {total_dropped}",
    ]

    if failures:
        lines.extend(
            [
                "\n## Artigos com falha\n",
                "| originalURL | erro |",
                "| --- | --- |",
            ]
        )
        for result in failures:
            lines.append(f"| {result.original_url} | {result.error} |")

    lines.append(
        "\nEstes valores são o resultado real desta execução, não uma "
        "estimativa. Detalhe por artigo em `output/corpus_rdf_report.csv`."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_corpus_graph(
    project_root: Path | None = None,
    client: ArquivoClient | None = None,
) -> tuple[Graph, list[ArticleGraphResult]]:
    root = project_root or Path(__file__).resolve().parents[2]
    classification_csv = root / "output" / "corpus_classification.csv"
    version_history_dir = root / "data" / "raw" / "version_history"

    articles = load_retained_articles(classification_csv)
    if client is None:
        client = ArquivoClient(data_dir=root / "data" / "raw", timeout=(15.0, 120.0))

    combined = Graph()
    combined.bind("sdh", SDH)
    combined.bind("rdf", RDF)
    combined.bind("rdfs", RDFS)
    combined.bind("xsd", XSD)

    results: list[ArticleGraphResult] = []
    start = time.monotonic()
    for index, row in enumerate(articles, start=1):
        url = row["original_url"]
        title = row["title"]
        graph, result = build_one_article_graph(
            client, url, title, version_history_dir, root
        )
        if graph is not None:
            combined += graph
        results.append(result)

        if index % PROGRESS_EVERY == 0 or index == len(articles):
            elapsed = time.monotonic() - start
            rate = elapsed / index
            remaining = (len(articles) - index) * rate
            failures_so_far = sum(1 for r in results if r.error)
            captures_so_far = sum(r.captures_used for r in results)
            LOGGER.info(
                "Progresso: %d/%d artigos, %d capturas processadas, "
                "%.0fs decorridos, ~%.0fs restantes, %d falhas até agora.",
                index,
                len(articles),
                captures_so_far,
                elapsed,
                remaining,
                failures_so_far,
            )

    return combined, results


def run(project_root: Path | None = None) -> tuple[Graph, list[ArticleGraphResult]]:
    root = project_root or Path(__file__).resolve().parents[2]
    graph, results = build_corpus_graph(root)

    output_path = root / "output" / "corpus_articles.ttl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format="turtle")

    write_report_csv(results, root / "output" / "corpus_rdf_report.csv")
    write_summary_markdown(results, len(graph), root / "output" / "corpus_rdf_summary.md")
    return graph, results


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).resolve().parents[2] / "output" / "corpus_rdf_progress.log",
                mode="a",
                encoding="utf-8",
            ),
        ],
    )
    graph, results = run()
    successes = [r for r in results if r.error is None]
    print(f"Artigos mapeados: {len(successes)} de {len(results)}")
    print(f"Triplos no grafo: {len(graph)}")
    print("Turtle: output/corpus_articles.ttl")
    print(
        "Relatórios: output/corpus_rdf_report.csv, output/corpus_rdf_summary.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
