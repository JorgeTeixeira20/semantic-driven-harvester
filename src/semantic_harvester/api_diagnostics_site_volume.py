"""Experiência 3 — volume de queries genéricas dentro de siteSearch=record.pt.

Testa se substituir uma query específica (nome de jogador/equipa, como
`Sporting` na Experiência 1) por um termo genérico (`futebol`, `desporto`)
aumenta a probabilidade de encher uma página quando a pesquisa continua
restrita a `siteSearch=record.pt` — condição necessária para o corpus do
Caminho A, que é especificamente sobre artigos do Record.

Cada query é repetida `TRIALS` vezes com os mesmos parâmetros para observar
variação entre pedidos idênticos: sondagens diretas feitas antes de escrever
este módulo mostraram contagens diferentes (`results_received` e
`estimated_nr_results`) em pedidos consecutivos com os mesmos parâmetros.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from .arquivo_client import ArquivoClient

LOGGER = logging.getLogger(__name__)
SITE_SEARCH = "record.pt"
FROM_DATE = "2015"
TO_DATE = "2020"
MAX_ITEMS = 20
TRIALS = 3
QUERIES = ("Sporting", "futebol", "desporto")


@dataclass(frozen=True)
class DiagnosticRow:
    query: str
    trial: int
    max_items_requested: int
    max_items_reported_by_api: int | None
    dedup_field_reported_by_api: str | None
    dedup_value_reported_by_api: int | None
    estimated_nr_results: int | None
    results_received: int
    page_full: bool
    distinct_original_urls: int
    next_page: bool


def diagnose_payload(query: str, trial: int, payload: dict[str, Any]) -> DiagnosticRow:
    results = payload.get("response_items", [])
    urls = [str(item["originalURL"]) for item in results if item.get("originalURL")]
    estimated = payload.get("estimated_nr_results")
    parameters = payload.get("request_parameters", {})
    reported_max_items = parameters.get("maxItems")
    reported_dedup_value = parameters.get("dedupValue")

    return DiagnosticRow(
        query=query,
        trial=trial,
        max_items_requested=MAX_ITEMS,
        max_items_reported_by_api=(
            int(reported_max_items) if reported_max_items is not None else None
        ),
        dedup_field_reported_by_api=parameters.get("dedupField"),
        dedup_value_reported_by_api=(
            int(reported_dedup_value)
            if reported_dedup_value is not None
            else None
        ),
        estimated_nr_results=int(estimated) if estimated is not None else None,
        results_received=len(results),
        page_full=len(results) == MAX_ITEMS,
        distinct_original_urls=len(set(urls)),
        next_page=bool(payload.get("next_page")),
    )


def summarize_query(rows: list[DiagnosticRow]) -> dict[str, Any]:
    received = [row.results_received for row in rows]
    estimated = [
        row.estimated_nr_results
        for row in rows
        if row.estimated_nr_results is not None
    ]
    return {
        "query": rows[0].query,
        "trials": len(rows),
        "received_min": min(received),
        "received_max": max(received),
        "any_full_page": any(row.page_full for row in rows),
        "estimated_min": min(estimated) if estimated else None,
        "estimated_max": max(estimated) if estimated else None,
    }


def write_csv(rows: list[DiagnosticRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_markdown(
    rows: list[DiagnosticRow], summaries: list[dict[str, Any]], path: Path
) -> None:
    lines = [
        "# Volume de queries genéricas em siteSearch=record.pt (Experiência 3)\n",
        f"Parâmetros comuns: `siteSearch=record.pt` (o cliente inclui também "
        f"`www.record.pt`), `from={FROM_DATE}`, `to={TO_DATE}`, "
        f"`maxItems={MAX_ITEMS}`, sem `dedupField`/`dedupValue` explícitos. "
        f"Cada query foi repetida {TRIALS} vezes com os mesmos parâmetros para "
        "observar variação entre pedidos idênticos.\n",
        "| Query | Tentativa | maxItems pedido/API | dedup reportado pela API | "
        "estimated | recebidos | página cheia | URLs únicas | next_page |",
        "| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | --- |",
    ]
    for row in rows:
        dedup_display = (
            f"{row.dedup_field_reported_by_api}/{row.dedup_value_reported_by_api}"
        )
        lines.append(
            f"| {row.query} | {row.trial} | {row.max_items_requested}/"
            f"{row.max_items_reported_by_api} | {dedup_display} | "
            f"{row.estimated_nr_results if row.estimated_nr_results is not None else 'n/a'} | "
            f"{row.results_received} | {'sim' if row.page_full else 'não'} | "
            f"{row.distinct_original_urls} | {'sim' if row.next_page else 'não'} |"
        )

    lines.extend(
        [
            "\n## Resumo por query\n",
            "| Query | Tentativas | recebidos min/max | alguma página cheia | "
            "estimated min/max |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for summary in summaries:
        lines.append(
            f"| {summary['query']} | {summary['trials']} | "
            f"{summary['received_min']}/{summary['received_max']} | "
            f"{'sim' if summary['any_full_page'] else 'não'} | "
            f"{summary['estimated_min']}/{summary['estimated_max']} |"
        )

    lines.append(
        "\nOs valores acima são observações desta execução. A variação entre "
        "tentativas idênticas da mesma query indica que a API TextSearch não é "
        "determinística por pedido nesta janela de observação; uma única "
        "amostra por query não é suficiente para concluir se uma query "
        "'consegue encher uma página'."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_diagnostics(project_root: Path | None = None) -> tuple[
    list[DiagnosticRow], list[dict[str, Any]]
]:
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / "data" / "raw" / "api_diagnostics_site_volume"
    client = ArquivoClient(data_dir=root / "data" / "raw", timeout=(15.0, 120.0))
    rows: list[DiagnosticRow] = []

    for query in QUERIES:
        for trial in range(1, TRIALS + 1):
            raw_path = raw_dir / f"{query}_trial-{trial}_max-{MAX_ITEMS}.json"
            response = client.search(
                query=query,
                site_search=SITE_SEARCH,
                from_date=FROM_DATE,
                to_date=TO_DATE,
                max_items=MAX_ITEMS,
                raw_path=raw_path,
            )
            rows.append(diagnose_payload(query, trial, response.raw_response))

    summaries = [
        summarize_query([row for row in rows if row.query == query])
        for query in QUERIES
    ]
    write_csv(rows, root / "output" / "api_diagnostics_site_volume.csv")
    write_markdown(rows, summaries, root / "output" / "api_diagnostics_site_volume.md")
    return rows, summaries


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        rows, _ = run_diagnostics()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("O diagnóstico falhou: %s", exc)
        return 1

    print(f"Pedidos concluídos: {len(rows)}")
    print("CSV: output/api_diagnostics_site_volume.csv")
    print("Markdown: output/api_diagnostics_site_volume.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
