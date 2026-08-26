"""Experiência isolada de profiling da API TextSearch do Arquivo.pt."""

from __future__ import annotations

import csv
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from .arquivo_client import ArquivoClient

LOGGER = logging.getLogger(__name__)
MAX_ITEMS = 100

SEARCHES = (
    ("Benfica", "2010", "2020"),
    ("Benfica", "2015", "2020"),
    ("Benfica", "2018", "2020"),
    ("Benfica", "2018", "2022"),
    ("Sporting", "2015", "2020"),
    ("FC Porto", "2015", "2020"),
)


@dataclass(frozen=True)
class ProfileRow:
    query: str
    from_date: str
    to_date: str
    estimated_nr_results: int | None
    results_received: int
    distinct_original_urls: int
    detail_urls: int
    non_detail_results: int
    oldest_tstamp: str | None
    newest_tstamp: str | None


def profile_payload(
    query: str, from_date: str, to_date: str, payload: dict[str, Any]
) -> ProfileRow:
    results = payload.get("response_items", [])
    urls = [str(result["originalURL"]) for result in results if result.get("originalURL")]
    distinct_urls = set(urls)
    detail_urls = {url for url in distinct_urls if "/detalhe/" in url.lower()}
    tstamps = sorted(
        str(result["tstamp"]) for result in results if result.get("tstamp")
    )
    estimated = payload.get("estimated_nr_results")

    return ProfileRow(
        query=query,
        from_date=from_date,
        to_date=to_date,
        estimated_nr_results=int(estimated) if estimated is not None else None,
        results_received=len(results),
        distinct_original_urls=len(distinct_urls),
        detail_urls=len(detail_urls),
        non_detail_results=sum(
            "/detalhe/" not in str(result.get("originalURL", "")).lower()
            for result in results
        ),
        oldest_tstamp=tstamps[0] if tstamps else None,
        newest_tstamp=tstamps[-1] if tstamps else None,
    )


def profiling_anomalies(
    rows_and_payloads: list[tuple[ProfileRow, dict[str, Any]]],
) -> list[str]:
    anomalies: list[str] = []
    for row, payload in rows_and_payloads:
        label = f'{row.query} ({row.from_date}–{row.to_date})'
        parameters = payload.get("request_parameters", {})
        dedup_field = parameters.get("dedupField")
        dedup_value = parameters.get("dedupValue")

        if dedup_field != "url" or str(dedup_value) != "1":
            anomalies.append(
                f"{label}: a API reportou dedupField={dedup_field!r} e "
                f"dedupValue={dedup_value!r}."
            )
        if row.distinct_original_urls < row.results_received:
            anomalies.append(
                f"{label}: {row.results_received - row.distinct_original_urls} "
                "resultados repetem um originalURL apesar dos parâmetros de dedup."
            )
        if row.oldest_tstamp and row.oldest_tstamp[:4] < row.from_date:
            anomalies.append(
                f"{label}: a captura mais antiga ({row.oldest_tstamp}) é anterior "
                "ao ano inicial pedido."
            )
        if row.newest_tstamp and row.newest_tstamp[:4] > row.to_date:
            anomalies.append(
                f"{label}: a captura mais recente ({row.newest_tstamp}) é posterior "
                "ao ano final pedido."
            )
        if payload.get("next_page") and row.results_received < MAX_ITEMS:
            anomalies.append(
                f"{label}: a API forneceu next_page apesar de devolver apenas "
                f"{row.results_received} de {MAX_ITEMS} itens pedidos."
            )
        if (
            row.estimated_nr_results is not None
            and row.estimated_nr_results > row.results_received
            and row.results_received < MAX_ITEMS
            and not payload.get("next_page")
        ):
            anomalies.append(
                f"{label}: estimated_nr_results={row.estimated_nr_results}, mas "
                f"foram devolvidos {row.results_received} itens e não existe "
                "next_page."
            )

    return anomalies


def write_csv(rows: list[ProfileRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_markdown(
    rows: list[ProfileRow], anomalies: list[str], path: Path
) -> None:
    best_distinct = max(rows, key=lambda row: row.distinct_original_urls)
    best_detail = max(rows, key=lambda row: row.detail_urls)
    lines = [
        "# Profiling da API TextSearch\n",
        "Parâmetros comuns: `siteSearch=record.pt`, `maxItems=100`, "
        "`dedupField=url`, `dedupValue=1`. O cliente existente inclui também "
        "o host `www.record.pt`.\n",
        "| Query | Período | Estimated | Recebidos | URLs distintas | "
        "/detalhe/ | Não /detalhe/ | Mais antiga | Mais recente |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.query} | {row.from_date}–{row.to_date} | "
            f"{row.estimated_nr_results if row.estimated_nr_results is not None else 'n/a'} | "
            f"{row.results_received} | {row.distinct_original_urls} | "
            f"{row.detail_urls} | {row.non_detail_results} | "
            f"{row.oldest_tstamp or 'n/a'} | {row.newest_tstamp or 'n/a'} |"
        )

    lines.extend(
        [
            "\n## Destaques\n",
            f"- Mais URLs distintas: **{best_distinct.query} "
            f"({best_distinct.from_date}–{best_distinct.to_date})**, "
            f"com **{best_distinct.distinct_original_urls}**.",
            f"- Mais URLs com `/detalhe/`: **{best_detail.query} "
            f"({best_detail.from_date}–{best_detail.to_date})**, "
            f"com **{best_detail.detail_urls}**.",
            "\n`/detalhe/` é apenas um indicador exploratório, não uma "
            "classificação definitiva de Artigo.",
            "\n## Anomalias observadas\n",
        ]
    )
    if anomalies:
        lines.extend(f"- {anomaly}" for anomaly in anomalies)
    else:
        lines.append("- Não foram detetadas anomalias pelos critérios deste profiling.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_profiling(project_root: Path | None = None) -> list[ProfileRow]:
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / "data" / "raw" / "profiling"
    client = ArquivoClient(data_dir=root / "data" / "raw")
    rows_and_payloads: list[tuple[ProfileRow, dict[str, Any]]] = []

    for index, (query, from_date, to_date) in enumerate(SEARCHES, start=1):
        slug = query.lower().replace(" ", "_")
        raw_path = raw_dir / f"{index:02d}_{slug}_{from_date}_{to_date}.json"
        response = client.search(
            query=query,
            site_search="record.pt",
            from_date=from_date,
            to_date=to_date,
            max_items=MAX_ITEMS,
            dedup_field="url",
            dedup_value=1,
            raw_path=raw_path,
        )
        row = profile_payload(query, from_date, to_date, response.raw_response)
        rows_and_payloads.append((row, response.raw_response))

    rows = [row for row, _ in rows_and_payloads]
    anomalies = profiling_anomalies(rows_and_payloads)
    write_csv(rows, root / "output" / "api_profiling.csv")
    write_markdown(rows, anomalies, root / "output" / "api_profiling.md")
    return rows


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        rows = run_profiling()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("O profiling falhou: %s", exc)
        return 1

    print(f"Pesquisas concluídas: {len(rows)}")
    print("CSV: output/api_profiling.csv")
    print("Markdown: output/api_profiling.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
