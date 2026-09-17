"""Experiência 2 — testa se `offset` pagina quando a primeira página vem cheia.

Complementa a Experiência 1 (`api_diagnostics.py`, ver `docs/experiments.md`):
naquela execução, nenhuma variante devolveu tantos resultados quanto o
`maxItems` pedido, pelo que `offset=100`/`offset=200` devolverem 0 podia
refletir apenas a ausência de mais resultados materializados para aquela
pesquisa específica, não uma limitação geral da API.

Uma tentativa preliminar (não incluída aqui como variante formal, apenas
narrada em `docs/experiments.md`) usou a mesma query `Sporting`/2015-2020 sem
`siteSearch`, mas com `dedupField=url`/`dedupValue=1` explícitos, e continuou
a não preencher `maxItems=20` (13, 12 e 5 resultados). Os raw dessa tentativa
ficaram preservados com o prefixo `pilot_sporting_` em
`data/raw/api_diagnostics_offset/` e os relatórios com o sufixo `_pilot`.

A configuração usada abaixo (`futebol`, sem `siteSearch`, sem enviar
`dedupField`/`dedupValue`, deixando os defaults da API) foi escolhida por
observação direta (fora deste módulo) de que preenchia genuinamente
`maxItems=20`. Os offsets replicam os valores 0/100/200 da Experiência 1 e
acrescentam 20/40 para verificar continuidade de página em página.
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
QUERY = "futebol"
FROM_DATE = "2015"
TO_DATE = "2020"
MAX_ITEMS = 20


@dataclass(frozen=True)
class Variant:
    name: str
    offset: int


VARIANTS = (
    Variant("G", 0),
    Variant("H", 20),
    Variant("I", 40),
    Variant("J", 100),
    Variant("K", 200),
)


@dataclass(frozen=True)
class DiagnosticRow:
    test: str
    max_items_requested: int
    max_items_reported_by_api: int | None
    offset: int
    dedup_field_reported_by_api: str | None
    dedup_value_reported_by_api: int | None
    estimated_nr_results: int | None
    results_received: int
    page_full: bool
    distinct_original_urls: int
    distinct_tstamps: int
    next_page: bool
    first_url: str | None
    first_tstamp: str | None
    last_url: str | None
    last_tstamp: str | None


def diagnose_payload(variant: Variant, payload: dict[str, Any]) -> DiagnosticRow:
    results = payload.get("response_items", [])
    urls = [str(item["originalURL"]) for item in results if item.get("originalURL")]
    tstamps = [str(item["tstamp"]) for item in results if item.get("tstamp")]
    first = results[0] if results else {}
    last = results[-1] if results else {}
    estimated = payload.get("estimated_nr_results")
    parameters = payload.get("request_parameters", {})
    reported_max_items = parameters.get("maxItems")
    reported_dedup_value = parameters.get("dedupValue")

    return DiagnosticRow(
        test=variant.name,
        max_items_requested=MAX_ITEMS,
        max_items_reported_by_api=(
            int(reported_max_items) if reported_max_items is not None else None
        ),
        offset=variant.offset,
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
        distinct_tstamps=len(set(tstamps)),
        next_page=bool(payload.get("next_page")),
        first_url=str(first["originalURL"]) if first.get("originalURL") else None,
        first_tstamp=str(first["tstamp"]) if first.get("tstamp") else None,
        last_url=str(last["originalURL"]) if last.get("originalURL") else None,
        last_tstamp=str(last["tstamp"]) if last.get("tstamp") else None,
    )


def url_set(payload: dict[str, Any]) -> set[str]:
    return {
        str(item["originalURL"])
        for item in payload.get("response_items", [])
        if item.get("originalURL")
    }


def calculate_comparisons(
    payloads: dict[str, dict[str, Any]], rows: dict[str, DiagnosticRow]
) -> dict[str, int]:
    urls_g = url_set(payloads["G"])
    urls_h = url_set(payloads["H"])
    urls_i = url_set(payloads["I"])
    urls_j = url_set(payloads["J"])
    urls_k = url_set(payloads["K"])

    return {
        "h_overlap_g": len(urls_h & urls_g),
        "h_new": len(urls_h - urls_g),
        "i_overlap_g_h": len(urls_i & (urls_g | urls_h)),
        "i_new": len(urls_i - (urls_g | urls_h)),
        "j_overlap_g_h_i": len(urls_j & (urls_g | urls_h | urls_i)),
        "j_new": len(urls_j - (urls_g | urls_h | urls_i)),
        "k_overlap_others": len(urls_k & (urls_g | urls_h | urls_i | urls_j)),
        "k_new": len(urls_k - (urls_g | urls_h | urls_i | urls_j)),
    }


def write_csv(rows: list[DiagnosticRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_markdown(
    rows: list[DiagnosticRow], comparisons: dict[str, int], path: Path
) -> None:
    lines = [
        "# Diagnóstico controlado do offset (Experiência 2)\n",
        f"Pesquisa comum: `{QUERY}`, sem `siteSearch`, `from={FROM_DATE}`, "
        f"`to={TO_DATE}`, `maxItems={MAX_ITEMS}`, sem `dedupField`/`dedupValue` "
        "explícitos (defaults da API). Objetivo: verificar se `offset` pagina "
        "quando a primeira página vem efetivamente cheia (complementa a "
        "Experiência 1 em `experiments.md`, onde nenhuma variante preencheu o "
        "`maxItems` pedido). Uma tentativa preliminar com `Sporting`, sem "
        "`siteSearch` e com `dedupField=url`/`dedupValue=1` explícitos não "
        "preencheu a página (ver `output/api_diagnostics_offset_pilot.md`); "
        "esta configuração foi escolhida por preencher genuinamente `maxItems`.\n",
        "| Teste | maxItems pedido/API | offset | dedup reportado pela API | estimated | "
        "recebidos | página cheia | URLs únicas | tstamps únicos | next_page |",
        "| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        dedup_display = (
            f"{row.dedup_field_reported_by_api}/{row.dedup_value_reported_by_api}"
        )
        lines.append(
            f"| {row.test} | {row.max_items_requested}/"
            f"{row.max_items_reported_by_api} | {row.offset} | "
            f"{dedup_display} | "
            f"{row.estimated_nr_results if row.estimated_nr_results is not None else 'n/a'} | "
            f"{row.results_received} | {'sim' if row.page_full else 'não'} | "
            f"{row.distinct_original_urls} | {row.distinct_tstamps} | "
            f"{'sim' if row.next_page else 'não'} |"
        )

    lines.extend(
        [
            "\n## Primeiro e último resultado\n",
            "| Teste | Primeiro tstamp | Primeiro URL | Último tstamp | Último URL |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.test} | {row.first_tstamp or 'n/a'} | "
            f"{row.first_url or 'n/a'} | {row.last_tstamp or 'n/a'} | "
            f"{row.last_url or 'n/a'} |"
        )

    lines.extend(
        [
            "\n## Offset analysis\n",
            f"- URLs de H já presentes em G: {comparisons['h_overlap_g']}.",
            f"- URLs novas em H: {comparisons['h_new']}.",
            "- URLs de I já presentes na união G/H: "
            f"{comparisons['i_overlap_g_h']}.",
            f"- URLs novas em I: {comparisons['i_new']}.",
            "- URLs de J (offset=100) já presentes na união G/H/I: "
            f"{comparisons['j_overlap_g_h_i']}.",
            f"- URLs novas em J: {comparisons['j_new']}.",
            "- URLs de K (offset=200) já presentes na união G/H/I/J: "
            f"{comparisons['k_overlap_others']}.",
            f"- URLs novas em K: {comparisons['k_new']}.",
            "\nOs valores acima são observações desta execução. Não demonstram, "
            "por si só, em que fase interna a API aplica o offset nem generalizam "
            "para outras queries ou combinações de parâmetros.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_diagnostics(project_root: Path | None = None) -> tuple[
    list[DiagnosticRow], dict[str, int]
]:
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / "data" / "raw" / "api_diagnostics_offset"
    client = ArquivoClient(data_dir=root / "data" / "raw", timeout=(10.0, 120.0))
    payloads: dict[str, dict[str, Any]] = {}
    rows: list[DiagnosticRow] = []

    for variant in VARIANTS:
        raw_path = raw_dir / (
            f"{variant.name}_{QUERY}_max-{MAX_ITEMS}_offset-{variant.offset:04d}_"
            "dedup-default.json"
        )
        response = client.search(
            query=QUERY,
            site_search=None,
            from_date=FROM_DATE,
            to_date=TO_DATE,
            max_items=MAX_ITEMS,
            offset=variant.offset,
            raw_path=raw_path,
        )
        payloads[variant.name] = response.raw_response
        rows.append(diagnose_payload(variant, response.raw_response))

    rows_by_name = {row.test: row for row in rows}
    comparisons = calculate_comparisons(payloads, rows_by_name)
    write_csv(rows, root / "output" / "api_diagnostics_offset.csv")
    write_markdown(rows, comparisons, root / "output" / "api_diagnostics_offset.md")
    return rows, comparisons


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        rows, _ = run_diagnostics()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("O diagnóstico falhou: %s", exc)
        return 1

    print(f"Variantes concluídas: {len(rows)}")
    print("CSV: output/api_diagnostics_offset.csv")
    print("Markdown: output/api_diagnostics_offset.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
