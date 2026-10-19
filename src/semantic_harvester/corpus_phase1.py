"""Fase 1 do protocolo de queries do Caminho A — descoberta via TextSearch.

Implementa a Opção 2 (Moderada) decidida em `docs/experiments.md`
("Protocolo de queries para o corpus do Caminho A"): 13 termos de pesquisa
(4 modalidades, 4 clubes, 5 atletas conhecidos), `siteSearch=record.pt`,
`maxItems=50`, `dedupField=url`/`dedupValue=1` explícitos, 2 repetições por
termo, com paginação por `offset` só quando uma página vier cheia (decisão
da Experiência 2).

Alargado em `docs/experiments.md` ("Download do HTML em bruto da captura
mais antiga e lista alargada de termos", 2026-10-19): mais 11 termos (5
modalidades, 6 competições), com `from=1999`/`to=2026` em vez de
`2015`/`2020` — a investigação do limite de 2000 resultados mostrou que não
há parede que justifique dividir por datas. A paragem por página deixou de
depender de `next_page` (não fiável mesmo a grande escala), só de página
incompleta/vazia.

Preserva o raw de cada pedido, depois agrega/deduplica os `response_items`
de todos os pedidos por `(originalURL, tstamp)` (captura) e por
`originalURL` (artigo), seguindo exatamente o método descrito em
`docs/experiments.md`. Não avança para a Fase 2 (`version_history`); esse é
um passo manual seguinte, condicional à confirmação do valor de `N`.
"""

from __future__ import annotations

import csv
import logging
import re
import time
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from .arquivo_client import ArquivoClient, SearchResponse

LOGGER = logging.getLogger(__name__)

SITE_SEARCH = "record.pt"
FROM_DATE = "1999"
TO_DATE = "2026"
MAX_ITEMS = 50
REPETITIONS = 2
MAX_PAGES_PER_TERM = 6
RETRY_ATTEMPTS = 3
RETRY_SLEEP_SECONDS = 10.0

MODALIDADES = (
    "futebol", "basquetebol", "andebol", "voleibol",
    # Alargamento de 2026-10-19 (docs/experiments.md): valores reais já no
    # vocabulário do Caminho B (sdh:Tema, categoria "modalidade").
    "atletismo", "ciclismo", "judo", "motores", "natação",
)
CLUBES = ("Benfica", "Sporting", "Porto", "SC Braga")
ATLETAS = (
    "Cristiano Ronaldo",
    "Bruno Fernandes",
    "Telma Monteiro",
    "João Félix",
    "Nelson Évora",
)
# Faceta nova de 2026-10-19 (docs/experiments.md): valores reais já no
# vocabulário do Caminho B (sdh:Tema, categoria "competicao").
COMPETICOES = (
    "2.ª Liga", "CAN", "Europeu", "Liga Jovem da UEFA",
    "Taça das Confederações", "Taça de Portugal",
)

TERMS: tuple[tuple[str, str], ...] = (
    tuple(("modalidade", termo) for termo in MODALIDADES)
    + tuple(("clube", termo) for termo in CLUBES)
    + tuple(("atleta", termo) for termo in ATLETAS)
    + tuple(("competicao", termo) for termo in COMPETICOES)
)


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()


@dataclass(frozen=True)
class TermRunStats:
    facet: str
    query: str
    repetition: int
    requests_made: int
    results_received: int


def _search_with_retries(client: ArquivoClient, **kwargs: Any) -> SearchResponse:
    last_exc: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return client.search(**kwargs)
        except requests.RequestException as exc:
            last_exc = exc
            LOGGER.warning(
                "Pedido falhou (tentativa %d/%d): %s", attempt, RETRY_ATTEMPTS, exc
            )
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_SLEEP_SECONDS)
    assert last_exc is not None
    raise last_exc


def collect_term_repetition(
    client: ArquivoClient,
    facet: str,
    query: str,
    repetition: int,
    raw_dir: Path,
) -> tuple[list[dict[str, Any]], list[Path]]:
    """Pede páginas para um termo/repetição, só avançando offset se a página vier cheia.

    Pára só quando a página vem incompleta (ou vazia); não depende de
    `next_page`, que a investigação de 2026-10-19 (`docs/experiments.md`)
    mostrou não ser um sinal fiável de fim mesmo a grande escala (continua
    presente em páginas já vazias).
    """

    items: list[dict[str, Any]] = []
    raw_paths: list[Path] = []
    offset = 0
    slug = slugify(query)

    for page_num in range(1, MAX_PAGES_PER_TERM + 1):
        raw_path = raw_dir / (
            f"{facet}_{slug}_rep{repetition}_offset-{offset:04d}.json"
        )
        response = _search_with_retries(
            client,
            query=query,
            site_search=SITE_SEARCH,
            from_date=FROM_DATE,
            to_date=TO_DATE,
            max_items=MAX_ITEMS,
            offset=offset,
            dedup_field="url",
            dedup_value=1,
            raw_path=raw_path,
        )
        raw_paths.append(raw_path)
        items.extend(response.results)

        page_full = len(response.results) == MAX_ITEMS
        if not page_full:
            break
        offset += len(response.results)
    else:
        LOGGER.warning(
            "Atingido o limite de %d páginas para %s/%s (rep %d); a parar.",
            MAX_PAGES_PER_TERM,
            facet,
            query,
            repetition,
        )

    return items, raw_paths


@dataclass
class CaptureRecord:
    original_url: str
    tstamp: str
    title: str | None
    item: dict[str, Any]
    facets: set[str]
    queries: set[str]
    divergent: bool = False


def aggregate(
    records: list[tuple[str, str, dict[str, Any]]]
) -> tuple[dict[tuple[str, str], CaptureRecord], list[tuple[str, str]]]:
    """Deduplica por (originalURL, tstamp); sinaliza divergências de metadados."""

    captures: dict[tuple[str, str], CaptureRecord] = {}
    divergent_keys: list[tuple[str, str]] = []

    for facet, query, item in records:
        original_url = str(item.get("originalURL"))
        tstamp = str(item.get("tstamp"))
        key = (original_url, tstamp)

        if key not in captures:
            captures[key] = CaptureRecord(
                original_url=original_url,
                tstamp=tstamp,
                title=item.get("title"),
                item=item,
                facets={facet},
                queries={query},
            )
            continue

        existing = captures[key]
        existing.facets.add(facet)
        existing.queries.add(query)
        if existing.item != item and not existing.divergent:
            existing.divergent = True
            divergent_keys.append(key)

    return captures, divergent_keys


def write_term_stats_csv(stats: list[TermRunStats], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(asdict(stats[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in stats)


def write_captures_csv(
    captures: dict[tuple[str, str], CaptureRecord], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            [
                "original_url",
                "tstamp",
                "title",
                "facets",
                "queries",
                "num_queries_matched",
                "divergent",
            ]
        )
        for record in captures.values():
            writer.writerow(
                [
                    record.original_url,
                    record.tstamp,
                    record.title or "",
                    ";".join(sorted(record.facets)),
                    ";".join(sorted(record.queries)),
                    len(record.queries),
                    record.divergent,
                ]
            )


def write_aggregation_markdown(
    stats: list[TermRunStats],
    captures: dict[tuple[str, str], CaptureRecord],
    divergent_keys: list[tuple[str, str]],
    path: Path,
) -> None:
    total_requests = sum(row.requests_made for row in stats)
    total_raw_items = sum(row.results_received for row in stats)
    total_captures = len(captures)
    articles: dict[str, set[str]] = defaultdict(set)
    for record in captures.values():
        articles[record.original_url].add(record.tstamp)
    n_articles = len(articles)
    multi_query_articles = sum(
        1
        for record in captures.values()
        if len(record.queries) > 1
    )

    lines = [
        "# Fase 1 — descoberta via TextSearch (Opção 2, corpus do Caminho A)\n",
        f"Execução real. Parâmetros comuns: `siteSearch=record.pt`, "
        f"`from={FROM_DATE}`, `to={TO_DATE}`, `maxItems={MAX_ITEMS}`, "
        f"`dedupField=url`/`dedupValue=1` explícitos. {len(TERMS)} termos "
        f"({len(MODALIDADES)} modalidades, {len(CLUBES)} clubes, "
        f"{len(ATLETAS)} atletas, {len(COMPETICOES)} competições), "
        f"{REPETITIONS} repetições por termo, offset só quando a página "
        "anterior veio cheia.\n",
        "## Resumo\n",
        f"- Pedidos reais efetuados: {total_requests}",
        f"- Itens brutos recebidos (antes de deduplicar): {total_raw_items}",
        f"- Capturas únicas por `(originalURL, tstamp)`: {total_captures}",
        f"- **N (artigos únicos por `originalURL`): {n_articles}**",
        f"- Capturas encontradas por mais do que uma query: {multi_query_articles}",
        f"- Divergências de metadados para a mesma `(originalURL, tstamp)`: "
        f"{len(divergent_keys)}",
        "\n## Pedidos e resultados por termo\n",
        "| Faceta | Termo | Repetição | Pedidos | Resultados |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in stats:
        lines.append(
            f"| {row.facet} | {row.query} | {row.repetition} | "
            f"{row.requests_made} | {row.results_received} |"
        )

    if divergent_keys:
        lines.extend(
            [
                "\n## Divergências de metadados\n",
                "| originalURL | tstamp |",
                "| --- | --- |",
            ]
        )
        for url, tstamp in divergent_keys:
            lines.append(f"| {url} | {tstamp} |")
        lines.append(
            "\nAmbas as versões do item ficam preservadas no raw de origem; "
            "esta tabela só sinaliza a divergência, não a resolve."
        )

    lines.append(
        "\nEstes valores são o resultado real desta execução, não uma "
        "estimativa. Corpus agregado em `output/corpus_phase1_captures.csv` "
        "(uma linha por captura única, com proveniência de faceta/termo)."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase1(project_root: Path | None = None) -> tuple[
    list[TermRunStats], dict[tuple[str, str], CaptureRecord], list[tuple[str, str]]
]:
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / "data" / "raw" / "corpus_queries"
    client = ArquivoClient(data_dir=root / "data" / "raw", timeout=(15.0, 120.0))

    stats: list[TermRunStats] = []
    records: list[tuple[str, str, dict[str, Any]]] = []

    for facet, query in TERMS:
        for repetition in range(1, REPETITIONS + 1):
            items, raw_paths = collect_term_repetition(
                client, facet, query, repetition, raw_dir
            )
            stats.append(
                TermRunStats(
                    facet=facet,
                    query=query,
                    repetition=repetition,
                    requests_made=len(raw_paths),
                    results_received=len(items),
                )
            )
            for item in items:
                records.append((facet, query, item))

    captures, divergent_keys = aggregate(records)

    write_term_stats_csv(stats, root / "output" / "corpus_phase1_per_term.csv")
    write_captures_csv(captures, root / "output" / "corpus_phase1_captures.csv")
    write_aggregation_markdown(
        stats, captures, divergent_keys, root / "output" / "corpus_phase1_aggregation.md"
    )
    return stats, captures, divergent_keys


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        stats, captures, divergent_keys = run_phase1()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("A Fase 1 falhou: %s", exc)
        return 1

    articles = {record.original_url for record in captures.values()}
    print(f"Pedidos efetuados: {sum(row.requests_made for row in stats)}")
    print(f"Capturas únicas: {len(captures)}")
    print(f"N (artigos únicos): {len(articles)}")
    print(f"Divergências: {len(divergent_keys)}")
    print("Relatórios: output/corpus_phase1_per_term.csv, "
          "output/corpus_phase1_captures.csv, output/corpus_phase1_aggregation.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
