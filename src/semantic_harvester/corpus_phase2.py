"""Fase 2 do protocolo de queries do Caminho A — profundidade temporal.

Generaliza `collect_all_captures()` (`history_pipeline.py`, já corrigida
para não depender de `estimated_nr_results` como condição de paragem) de um
único `originalURL` hardcoded para a lista de artigos únicos descoberta na
Fase 1 (`output/corpus_phase1_captures.csv`, 159 `originalURL` distintos).

Por artigo, corre `version_history()` sem restrição de datas (como o M3),
com paginação por offset só quando a página anterior vier cheia. Preserva o
raw de cada pedido usando a convenção já existente do cliente
(`data/raw/version_history/`). Não descarrega textos nem gera RDF — isso
fica para depois da classificação Artigo/redirecionamento (passo 6 do
protocolo), fora do âmbito desta fase.

Escreve o resultado por artigo incrementalmente em
`output/corpus_phase2_history.csv` (uma linha por pedido concluído, com
flush imediato) para não perder progresso se a execução for interrompida;
uma nova execução salta automaticamente os artigos já presentes nesse CSV.

Com `--label` (ex.: `por_ano`, sobre `output/corpus_phase1_por_ano_captures.csv`,
2026-10-20), a execução fica separada da original: resultados em
`output/corpus_phase2_<label>_{history.csv,summary.md,progress.log}` e raw de
`version_history` em `data/raw/phase2_<label>/version_history/`. Assim não
reescreve o raw de `data/raw/version_history/`, de que depende a
reconstrução offline do corpus de 125 artigos (`corpus_rdf.py`).
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from .arquivo_client import ArquivoClient
from .history_pipeline import collect_all_captures

LOGGER = logging.getLogger(__name__)

RETRY_ATTEMPTS = 3
RETRY_SLEEP_SECONDS = 10.0
PROGRESS_EVERY = 10

RESULTS_CSV_FIELDS = (
    "original_url",
    "captures",
    "estimated_total",
    "requests_made",
    "error",
)


@dataclass(frozen=True)
class ArticleHistoryResult:
    original_url: str
    captures: int
    estimated_total: int | None
    requests_made: int
    error: str | None


def load_unique_urls(captures_csv: Path) -> list[str]:
    """Lê os originalURL distintos da Fase 1, preservando a primeira ordem de aparição."""

    seen: set[str] = set()
    urls: list[str] = []
    with captures_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            url = row["original_url"]
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def load_already_processed(results_csv: Path) -> dict[str, ArticleHistoryResult]:
    """Permite retomar uma execução interrompida sem repetir artigos já concluídos."""

    if not results_csv.is_file():
        return {}

    processed: dict[str, ArticleHistoryResult] = {}
    with results_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            processed[row["original_url"]] = ArticleHistoryResult(
                original_url=row["original_url"],
                captures=int(row["captures"]),
                estimated_total=(
                    int(row["estimated_total"]) if row["estimated_total"] else None
                ),
                requests_made=int(row["requests_made"]),
                error=row["error"] or None,
            )
    return processed


def _collect_with_retries(
    client: ArquivoClient, original_url: str
) -> tuple[list[dict[str, Any]], list[Path], int | None]:
    last_exc: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return collect_all_captures(client, original_url=original_url)
        except (requests.RequestException, RuntimeError) as exc:
            last_exc = exc
            LOGGER.warning(
                "Falha em %s (tentativa %d/%d): %s",
                original_url,
                attempt,
                RETRY_ATTEMPTS,
                exc,
            )
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_SLEEP_SECONDS)
    assert last_exc is not None
    raise last_exc


def write_summary_markdown(
    results: list[ArticleHistoryResult],
    path: Path,
    captures_name: str = "corpus_phase1_captures.csv",
    history_name: str = "corpus_phase2_history.csv",
) -> None:
    successes = [r for r in results if r.error is None]
    failures = [r for r in results if r.error is not None]
    distribution: dict[int, int] = {}
    for result in successes:
        distribution[result.captures] = distribution.get(result.captures, 0) + 1
    multi_capture = sum(1 for r in successes if r.captures > 1)
    total_captures = sum(r.captures for r in successes)
    total_requests = sum(r.requests_made for r in results)

    lines = [
        "# Fase 2 — profundidade temporal via version_history\n",
        f"Execução real sobre os {len(results)} artigos únicos descobertos na "
        f"Fase 1 (`output/{captures_name}`). Sem restrição de "
        "datas por artigo (como o M3); paginação por offset só quando a "
        "página anterior veio cheia; `estimated_nr_results` não é usado "
        "como condição de paragem (correção de 2026-09-18).\n",
        "## Resumo\n",
        f"- Artigos processados: {len(results)}",
        f"- Sucessos: {len(successes)}",
        f"- Falhas (após {RETRY_ATTEMPTS} tentativas cada): {len(failures)}",
        f"- Pedidos reais efetuados (todos os artigos, incluindo paginação): "
        f"{total_requests}",
        f"- Total de capturas encontradas (artigos com sucesso): {total_captures}",
        f"- Artigos com mais do que uma captura: {multi_capture} "
        f"de {len(successes)} bem-sucedidos",
        "\n## Distribuição de capturas por artigo\n",
        "| Nº de capturas | Nº de artigos |",
        "| ---: | ---: |",
    ]
    for n_captures in sorted(distribution):
        lines.append(f"| {n_captures} | {distribution[n_captures]} |")

    if failures:
        lines.extend(
            [
                "\n## Falhas\n",
                "| originalURL | erro |",
                "| --- | --- |",
            ]
        )
        for result in failures:
            lines.append(f"| {result.original_url} | {result.error} |")

    lines.append(
        "\nEstes valores são o resultado real desta execução, não uma "
        f"estimativa. Detalhe por artigo em `output/{history_name}`."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def phase2_paths(root: Path, label: str | None) -> dict[str, Path]:
    """Caminhos de uma execução; sem `label`, os da Fase 2 original."""

    stem = f"corpus_phase2_{label}" if label else "corpus_phase2"
    return {
        "history": root / "output" / f"{stem}_history.csv",
        "summary": root / "output" / f"{stem}_summary.md",
        "progress": root / "output" / f"{stem}_progress.log",
        "data_dir": root / "data" / "raw" / (f"phase2_{label}" if label else ""),
    }


def run_phase2(
    project_root: Path | None = None,
    captures_csv: Path | None = None,
    label: str | None = None,
    client: ArquivoClient | None = None,
) -> list[ArticleHistoryResult]:
    root = project_root or Path(__file__).resolve().parents[2]
    captures_csv = captures_csv or root / "output" / "corpus_phase1_captures.csv"
    paths = phase2_paths(root, label)
    results_csv = paths["history"]

    urls = load_unique_urls(captures_csv)
    already = load_already_processed(results_csv)
    pending = [url for url in urls if url not in already]

    LOGGER.info(
        "Fase 2: %d artigos no total, %d já concluídos numa execução anterior, "
        "%d por processar.",
        len(urls),
        len(already),
        len(pending),
    )

    client = client or ArquivoClient(data_dir=paths["data_dir"], timeout=(15.0, 120.0))
    results: list[ArticleHistoryResult] = list(already.values())

    write_header = not results_csv.is_file()
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    with results_csv.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RESULTS_CSV_FIELDS), lineterminator="\n")
        if write_header:
            writer.writeheader()

        start = time.monotonic()
        for index, url in enumerate(pending, start=1):
            try:
                captures, raw_paths, estimated = _collect_with_retries(client, url)
                result = ArticleHistoryResult(
                    original_url=url,
                    captures=len(captures),
                    estimated_total=estimated,
                    requests_made=len(raw_paths),
                    error=None,
                )
            except (requests.RequestException, RuntimeError) as exc:
                LOGGER.error("Artigo falhou definitivamente: %s (%s)", url, exc)
                result = ArticleHistoryResult(
                    original_url=url,
                    captures=0,
                    estimated_total=None,
                    requests_made=0,
                    error=str(exc),
                )

            results.append(result)
            writer.writerow(asdict(result))
            handle.flush()

            if index % PROGRESS_EVERY == 0 or index == len(pending):
                elapsed = time.monotonic() - start
                rate = elapsed / index
                remaining = (len(pending) - index) * rate
                failures_so_far = sum(1 for r in results if r.error)
                LOGGER.info(
                    "Progresso: %d/%d pendentes (%d/%d no total), "
                    "%.0fs decorridos, ~%.0fs restantes, %d falhas até agora.",
                    index,
                    len(pending),
                    len(already) + index,
                    len(urls),
                    elapsed,
                    remaining,
                    failures_so_far,
                )

    write_summary_markdown(results, paths["summary"], captures_csv.name, paths["history"].name)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_phase2")
    parser.add_argument("--captures-csv", type=Path,
                        help="CSV de capturas da Fase 1 (por omissão, o da Fase 1 original)")
    parser.add_argument("--label",
                        help="separa a execução: output/corpus_phase2_<label>_* e "
                             "data/raw/phase2_<label>/")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    paths = phase2_paths(root, args.label)
    paths["progress"].parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(paths["progress"], mode="a", encoding="utf-8"),
        ],
    )
    try:
        results = run_phase2(root, args.captures_csv, args.label)
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("A Fase 2 falhou: %s", exc)
        return 1

    successes = [r for r in results if r.error is None]
    failures = [r for r in results if r.error is not None]
    print(f"Artigos processados: {len(results)}")
    print(f"Sucessos: {len(successes)}, falhas: {len(failures)}")
    print(f"Total de capturas: {sum(r.captures for r in successes)}")
    print(f"Relatórios: {paths['history']}, {paths['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
