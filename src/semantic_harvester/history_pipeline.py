"""Recolha e descrição do histórico temporal do artigo usado no M2."""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

import requests

from .arquivo_client import ArquivoClient, TextDownloadResult
from .rdf_mapper import SAMPLE_ORIGINAL_URL, generate_article_history, stable_hash

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoryMetrics:
    captures: int
    estimated_total: int | None
    oldest: str | None
    newest: str | None
    texts_obtained: int
    text_failures: int
    distinct_digests: int
    repeated_digests: int
    text_size_min: int | None
    text_size_mean: float | None
    text_size_max: int | None
    texts_not_requested: int = 0


@dataclass(frozen=True)
class HistoryRun:
    captures: list[dict[str, Any]]
    manifest_records: list[dict[str, Any]]
    raw_paths: list[Path]
    manifest_path: Path
    metrics: HistoryMetrics


def captured_at(tstamp: str) -> str:
    parsed = datetime.strptime(tstamp, "%Y%m%d%H%M%S")
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_all_captures(
    client: ArquivoClient,
    *,
    original_url: str,
    from_date: str | int | None = None,
    to_date: str | int | None = None,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], list[Path], int | None]:
    """Percorre páginas enquanto houver resultados, sem confiar só em maxItems.

    Não usa `estimated_nr_results` como critério de paragem: a Experiência 1
    (`docs/experiments.md`) mostrou que a estimativa da API não é uma
    contagem fiável de resultados acessíveis. `estimated_total` continua a
    ser recolhido e devolvido para fins de relatório, mas só as duas
    condições validadas nas Experiências 2 e 3 decidem parar a paginação:
    página incompleta (`len(page.results) < page_size`) ou ausência de
    `next_page`.
    """

    captures: list[dict[str, Any]] = []
    raw_paths: list[Path] = []
    estimated_total: int | None = None
    offset = 0

    while True:
        page = client.version_history(
            original_url=original_url,
            from_date=from_date,
            to_date=to_date,
            max_items=page_size,
            offset=offset,
        )
        raw_paths.append(page.raw_path)
        if estimated_total is None:
            estimated_total = page.estimated_nr_results
        captures.extend(page.results)

        if not page.results:
            break
        if len(page.results) < page_size:
            break
        if not page.next_page:
            break

        offset += len(page.results)

    return captures, raw_paths, estimated_total


TEXT_POLICY_FIRST = "primeira"
TEXT_POLICY_ALL = "todas"


def oldest_capture_keys(captures: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """(originalURL, tstamp) da captura mais antiga de cada artigo (por `tstamp`)."""

    oldest: dict[str, str] = {}
    for capture in captures:
        url, tstamp = str(capture["originalURL"]), str(capture["tstamp"])
        if url not in oldest or tstamp < oldest[url]:
            oldest[url] = tstamp
    return set(oldest.items())


def build_manifest_records(
    client: ArquivoClient,
    captures: list[dict[str, Any]],
    project_root: Path,
    *,
    text_policy: str,
) -> list[dict[str, Any]]:
    """Cria um registo por captura, sem deduplicar; o texto depende de `text_policy`.

    - `TEXT_POLICY_FIRST` ("primeira", política para artigos novos desde
      2026-10-15, `docs/experiments.md`): só se pede o texto da captura mais
      antiga de cada artigo; as restantes ficam no manifesto como "não pedido"
      (`text_requested=False`), nunca como falha.
    - `TEXT_POLICY_ALL` ("todas"): pede/reutiliza o texto de todas as capturas
      (corpus histórico de 125 artigos e M3).
    """

    if text_policy not in (TEXT_POLICY_FIRST, TEXT_POLICY_ALL):
        raise ValueError(f"Política de texto desconhecida: {text_policy!r}")
    requested = (
        oldest_capture_keys(captures) if text_policy == TEXT_POLICY_FIRST else None
    )

    records: list[dict[str, Any]] = []
    for capture in captures:
        original_url = str(capture["originalURL"])
        tstamp = str(capture["tstamp"])
        text_requested = requested is None or (original_url, tstamp) in requested
        if text_requested:
            download = client.download_extracted_text(
                capture,
                skip_existing=True,
                derive_url_when_missing=True,
            )
        else:
            download = TextDownloadResult(
                success=False, path=None, size_bytes=0, downloaded=False, text_url=None,
            )

        relative_path = None
        if download.path is not None:
            relative_path = download.path.relative_to(project_root).as_posix()

        records.append(
            {
                "article_id": stable_hash(original_url),
                "original_url": original_url,
                "tstamp": tstamp,
                "captured_at": captured_at(tstamp),
                "archive_url": capture.get("linkToArchive"),
                "title": capture.get("title"),
                "digest": capture.get("digest"),
                "content_length": capture.get("contentLength"),
                "mime_type": capture.get("mimeType"),
                "encoding": capture.get("encoding"),
                "collection": capture.get("collection"),
                "status_code": capture.get("statusCode", capture.get("status")),
                "extracted_text_path": relative_path,
                "text_download_success": download.success,
                "text_downloaded_now": download.downloaded,
                "text_size_bytes": download.size_bytes,
                "text_error": download.error,
                "text_requested": text_requested,
            }
        )
    return records


def write_manifest(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    path.write_text(content, encoding="utf-8")


def calculate_metrics(
    records: list[dict[str, Any]], estimated_total: int | None
) -> HistoryMetrics:
    tstamps = sorted(str(record["tstamp"]) for record in records)
    successful_sizes = [
        int(record["text_size_bytes"])
        for record in records
        if record["text_download_success"]
    ]
    digest_counts = Counter(
        str(record["digest"]) for record in records if record.get("digest")
    )

    return HistoryMetrics(
        captures=len(records),
        estimated_total=estimated_total,
        oldest=tstamps[0] if tstamps else None,
        newest=tstamps[-1] if tstamps else None,
        texts_obtained=len(successful_sizes),
        text_failures=sum(
            record.get("text_requested", True) and not bool(record["text_download_success"])
            for record in records
        ),
        distinct_digests=len(digest_counts),
        repeated_digests=sum(count - 1 for count in digest_counts.values()),
        text_size_min=min(successful_sizes) if successful_sizes else None,
        text_size_mean=mean(successful_sizes) if successful_sizes else None,
        text_size_max=max(successful_sizes) if successful_sizes else None,
        texts_not_requested=sum(not record.get("text_requested", True) for record in records),
    )


def run_history_pipeline(
    project_root: Path | None = None,
    *,
    original_url: str = SAMPLE_ORIGINAL_URL,
    page_size: int = 50,
) -> HistoryRun:
    root = project_root or Path(__file__).resolve().parents[2]
    client = ArquivoClient(data_dir=root / "data" / "raw")
    captures, raw_paths, estimated_total = collect_all_captures(
        client,
        original_url=original_url,
        page_size=page_size,
    )
    # M3 (artigo único histórico): mantém o texto de todas as capturas.
    records = build_manifest_records(client, captures, root, text_policy=TEXT_POLICY_ALL)
    manifest_path = root / "data" / "processed" / "captures_manifest.jsonl"
    write_manifest(records, manifest_path)
    metrics = calculate_metrics(records, estimated_total)
    return HistoryRun(captures, records, raw_paths, manifest_path, metrics)


def print_metrics(metrics: HistoryMetrics) -> None:
    print("\nHistórico temporal")
    print(f"Total estimado pela API: {metrics.estimated_total}")
    print(f"Capturas devolvidas: {metrics.captures}")
    print(f"Captura mais antiga: {metrics.oldest}")
    print(f"Captura mais recente: {metrics.newest}")
    print(f"Textos obtidos: {metrics.texts_obtained}")
    print(f"Falhas de texto: {metrics.text_failures}")
    print(f"Textos não pedidos (só a 1.ª captura): {metrics.texts_not_requested}")
    print(f"Digests distintos: {metrics.distinct_digests}")
    print(f"Digests repetidos: {metrics.repeated_digests}")
    if metrics.text_size_mean is None:
        print("Tamanho dos textos: indisponível")
    else:
        print(
            "Tamanho dos textos (mín./média/máx.): "
            f"{metrics.text_size_min} / {metrics.text_size_mean:.2f} / "
            f"{metrics.text_size_max} bytes"
        )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run = run_history_pipeline()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("A recolha do histórico falhou: %s", exc)
        return 1

    print_metrics(run.metrics)
    print(f"Manifesto: {run.manifest_path}")
    rdf_path = generate_article_history()
    print(f"RDF temporal: {rdf_path}")
    print("JSON raw:")
    for path in run.raw_paths:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
