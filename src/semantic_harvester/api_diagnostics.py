"""Experiência controlada sobre paginação e dedup da API TextSearch."""

from __future__ import annotations

import csv
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from .arquivo_client import ArquivoClient

LOGGER = logging.getLogger(__name__)
QUERY = "Sporting"
SITE_SEARCH = "record.pt"
FROM_DATE = "2015"
TO_DATE = "2020"


@dataclass(frozen=True)
class Variant:
    name: str
    max_items: int
    offset: int
    dedup: bool


VARIANTS = (
    Variant("A", 100, 0, True),
    Variant("B", 100, 100, True),
    Variant("C", 100, 200, True),
    Variant("D", 2000, 0, True),
    Variant("E", 100, 0, False),
    Variant("F", 200, 0, True),
)


@dataclass(frozen=True)
class DiagnosticRow:
    test: str
    max_items_requested: int
    max_items_reported_by_api: int | None
    offset: int
    dedup_parameters_sent: bool
    dedup_field_reported_by_api: str | None
    dedup_value_reported_by_api: int | None
    estimated_nr_results: int | None
    results_received: int
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
        max_items_requested=variant.max_items,
        max_items_reported_by_api=(
            int(reported_max_items) if reported_max_items is not None else None
        ),
        offset=variant.offset,
        dedup_parameters_sent=variant.dedup,
        dedup_field_reported_by_api=parameters.get("dedupField"),
        dedup_value_reported_by_api=(
            int(reported_dedup_value)
            if reported_dedup_value is not None
            else None
        ),
        estimated_nr_results=int(estimated) if estimated is not None else None,
        results_received=len(results),
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
    urls_a = url_set(payloads["A"])
    urls_b = url_set(payloads["B"])
    urls_c = url_set(payloads["C"])
    urls_e = url_set(payloads["E"])

    return {
        "b_overlap_a": len(urls_b & urls_a),
        "b_new": len(urls_b - urls_a),
        "c_overlap_a_b": len(urls_c & (urls_a | urls_b)),
        "c_new": len(urls_c - (urls_a | urls_b)),
        "dedup_on_received": rows["A"].results_received,
        "dedup_default_received": rows["E"].results_received,
        "dedup_default_unique_urls": len(urls_e),
        "dedup_default_repeated_occurrences": rows["E"].results_received
        - len(urls_e),
        "max_100_received": rows["A"].results_received,
        "max_200_received": rows["F"].results_received,
        "max_2000_received": rows["D"].results_received,
        "a_f_overlap": len(urls_a & url_set(payloads["F"])),
        "f_new_vs_a": len(url_set(payloads["F"]) - urls_a),
        "a_missing_from_f": len(urls_a - url_set(payloads["F"])),
        "f_d_overlap": len(url_set(payloads["F"]) & url_set(payloads["D"])),
        "d_new_vs_f": len(url_set(payloads["D"]) - url_set(payloads["F"])),
        "f_missing_from_d": len(url_set(payloads["F"]) - url_set(payloads["D"])),
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
    a_missing_word = (
        "ausente" if comparisons["a_missing_from_f"] == 1 else "ausentes"
    )
    f_missing_word = (
        "ausente" if comparisons["f_missing_from_d"] == 1 else "ausentes"
    )
    lines = [
        "# Diagnóstico controlado da API TextSearch\n",
        "Pesquisa comum: `Sporting`, `siteSearch=record.pt`, "
        "`from=2015`, `to=2020`. O cliente inclui também `www.record.pt`.\n",
        "| Teste | maxItems pedido/API | offset | dedup pedido/API | estimated | recebidos | "
        "URLs únicas | tstamps únicos | next_page |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        if (
            row.dedup_parameters_sent
            and row.dedup_field_reported_by_api == "url"
            and row.dedup_value_reported_by_api == 1
        ):
            dedup_display = "url/1 explícito"
        elif row.dedup_parameters_sent:
            dedup_display = (
                "url/1 pedido → "
                f"{row.dedup_field_reported_by_api}/"
                f"{row.dedup_value_reported_by_api}"
            )
        else:
            dedup_display = (
                "omitido → "
                f"{row.dedup_field_reported_by_api}/"
                f"{row.dedup_value_reported_by_api}"
            )
        lines.append(
            f"| {row.test} | {row.max_items_requested}/"
            f"{row.max_items_reported_by_api} | {row.offset} | "
            f"{dedup_display} | "
            f"{row.estimated_nr_results if row.estimated_nr_results is not None else 'n/a'} | "
            f"{row.results_received} | {row.distinct_original_urls} | "
            f"{row.distinct_tstamps} | {'sim' if row.next_page else 'não'} |"
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
            f"- URLs de B já presentes em A: {comparisons['b_overlap_a']}.",
            f"- URLs novas em B: {comparisons['b_new']}.",
            "- URLs de C já presentes na união A/B: "
            f"{comparisons['c_overlap_a_b']}.",
            f"- URLs novas em C: {comparisons['c_new']}.",
            "\n## Dedup analysis\n",
            f"- Resultados com dedup ON (A): {comparisons['dedup_on_received']}.",
            "- Resultados sem parâmetros explícitos, com defaults `url/2` (E): "
            f"{comparisons['dedup_default_received']}.",
            "- URLs distintas com os defaults `url/2`: "
            f"{comparisons['dedup_default_unique_urls']}.",
            "- Ocorrências repetidas de URL com os defaults `url/2`: "
            f"{comparisons['dedup_default_repeated_occurrences']}.",
            "- E não representa dedup desativado: a API aplicou "
            "`dedupField=url` e `dedupValue=2` por omissão.",
            "\n## maxItems analysis\n",
            f"- maxItems=100: {comparisons['max_100_received']} resultados.",
            f"- maxItems=200: {comparisons['max_200_received']} resultados.",
            f"- maxItems=2000: {comparisons['max_2000_received']} resultados.",
            "- A/F: "
            f"{comparisons['a_f_overlap']} URLs em comum, "
            f"{comparisons['f_new_vs_a']} novas em F e "
            f"{comparisons['a_missing_from_f']} de A {a_missing_word} em F.",
            "- F/D: "
            f"{comparisons['f_d_overlap']} URLs em comum, "
            f"{comparisons['d_new_vs_f']} novas em D e "
            f"{comparisons['f_missing_from_d']} de F {f_missing_word} em D.",
            "- No teste D, a API reportou `maxItems=500` apesar de terem sido "
            "pedidos 2000.",
            "\nOs valores acima são observações da execução. Não demonstram, por si "
            "só, em que fase interna a API aplica paginação ou deduplicação.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_diagnostics(project_root: Path | None = None) -> tuple[
    list[DiagnosticRow], dict[str, int]
]:
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / "data" / "raw" / "api_diagnostics"
    client = ArquivoClient(data_dir=root / "data" / "raw")
    payloads: dict[str, dict[str, Any]] = {}
    rows: list[DiagnosticRow] = []

    for variant in VARIANTS:
        dedup_label = "on" if variant.dedup else "off"
        raw_path = raw_dir / (
            f"{variant.name}_max-{variant.max_items}_offset-{variant.offset:04d}_"
            f"dedup-{dedup_label}.json"
        )
        response = client.search(
            query=QUERY,
            site_search=SITE_SEARCH,
            from_date=FROM_DATE,
            to_date=TO_DATE,
            max_items=variant.max_items,
            offset=variant.offset,
            dedup_field="url" if variant.dedup else None,
            dedup_value=1 if variant.dedup else None,
            raw_path=raw_path,
        )
        payloads[variant.name] = response.raw_response
        rows.append(diagnose_payload(variant, response.raw_response))

    rows_by_name = {row.test: row for row in rows}
    comparisons = calculate_comparisons(payloads, rows_by_name)
    write_csv(rows, root / "output" / "api_diagnostics.csv")
    write_markdown(rows, comparisons, root / "output" / "api_diagnostics.md")
    return rows, comparisons


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        rows, _ = run_diagnostics()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("O diagnóstico falhou: %s", exc)
        return 1

    print(f"Variantes concluídas: {len(rows)}")
    print("CSV: output/api_diagnostics.csv")
    print("Markdown: output/api_diagnostics.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
