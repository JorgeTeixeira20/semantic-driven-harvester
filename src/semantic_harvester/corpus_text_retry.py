"""Retentativa dos textos que falharam por timeout ou ligação cortada.

Lê `output/corpus_text_retry_candidates.csv` (as 324 capturas cuja última
falha registada, na análise de 2026-09-19, foi timeout de leitura, timeout de
ligação ou ligação cortada — ver `docs/experiments.md`) e tenta obter o texto
extraído de cada uma com `ArquivoClient.download_extracted_text()`, com
várias tentativas e espera crescente entre elas. Um HTTP 404 é tratado como
resposta definitiva e não é retentado.

Isolado de propósito: não lê nem escreve `output/corpus_rdf_report.csv`, os
triplos em `data/processed/` nem o grafo Turtle. O único efeito nos dados do
corpus é acrescentar ficheiros a `data/raw/texts/` (com o mesmo nome que
`corpus_rdf.py` usa, porque as capturas vão com o `originalURL` canónico).
Integrar os textos recuperados no grafo é um passo separado, descrito em
`docs/experiments.md`.

Retomável por captura: o resultado de cada uma (sucesso ou falha definitiva
depois de todas as tentativas) é escrito de imediato, com flush, em
`output/corpus_text_retry_report.csv`; uma nova execução salta as capturas
já presentes nesse ficheiro. Para retentar uma falha definitiva, apagar a
sua linha do relatório.
"""

from __future__ import annotations

import csv
import logging
import re
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Callable

from .arquivo_client import ArquivoClient

LOGGER = logging.getLogger(__name__)

ATTEMPTS = 3
BASE_SLEEP_SECONDS = 10.0
PROGRESS_EVERY = 10

OUTCOME_SUCCESS = "success"
OUTCOME_SUCCESS_CACHED = "success_cached"
OUTCOME_FAILED = "failed"

CAUSE_CONNECT_TIMEOUT = "timeout_de_ligacao"
CAUSE_READ_TIMEOUT = "timeout_de_leitura"
CAUSE_404 = "http_404"
CAUSE_CONNECTION_CUT = "ligacao_cortada"
CAUSE_OTHER_HTTP = "outro_http"
CAUSE_OTHER = "outros"


def classify_error(message: str | None) -> str:
    """Mesmas categorias usadas na análise dos 401 textos indisponíveis."""

    text = message or ""
    if "ConnectTimeoutError" in text or "Connection to arquivo.pt timed out" in text:
        return CAUSE_CONNECT_TIMEOUT
    if "Read timed out" in text:
        return CAUSE_READ_TIMEOUT
    if "404 Client Error" in text:
        return CAUSE_404
    if "RemoteDisconnected" in text or "Connection aborted" in text:
        return CAUSE_CONNECTION_CUT
    if re.search(r"\b\d{3} (Client|Server) Error", text):
        return CAUSE_OTHER_HTTP
    return CAUSE_OTHER


@dataclass(frozen=True)
class RetryResult:
    original_url: str
    tstamp: str
    outcome: str
    cause: str
    attempts: int
    error: str
    text_path: str
    size_bytes: int


RESULT_FIELDS = tuple(f.name for f in fields(RetryResult))


def retry_one(
    client: ArquivoClient,
    original_url: str,
    tstamp: str,
    project_root: Path,
    *,
    attempts: int = ATTEMPTS,
    base_sleep: float = BASE_SLEEP_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Até `attempts` tentativas, com espera `base_sleep * 2**(n-1)` entre elas."""

    if attempts < 1:
        raise ValueError("attempts deve ser pelo menos 1")

    capture = {"originalURL": original_url, "tstamp": tstamp}
    last_error = ""
    made = 0
    for made in range(1, attempts + 1):
        download = client.download_extracted_text(
            capture, skip_existing=True, derive_url_when_missing=True
        )
        if download.success:
            try:
                relative = download.path.relative_to(project_root).as_posix()
            except ValueError:
                relative = str(download.path)
            return RetryResult(
                original_url=original_url,
                tstamp=tstamp,
                outcome=OUTCOME_SUCCESS if download.downloaded else OUTCOME_SUCCESS_CACHED,
                cause="",
                attempts=made,
                error="",
                text_path=relative,
                size_bytes=download.size_bytes,
            )

        last_error = download.error or ""
        if classify_error(last_error) == CAUSE_404 or made == attempts:
            break
        delay = base_sleep * 2 ** (made - 1)
        LOGGER.info(
            "Tentativa %d/%d falhou para %s/%s; nova tentativa em %.0fs.",
            made, attempts, original_url, tstamp, delay,
        )
        sleep(delay)

    return RetryResult(
        original_url=original_url,
        tstamp=tstamp,
        outcome=OUTCOME_FAILED,
        cause=classify_error(last_error),
        attempts=made,
        error=last_error,
        text_path="",
        size_bytes=0,
    )


def load_candidates(candidates_csv: Path) -> list[dict[str, str]]:
    if not candidates_csv.is_file():
        raise FileNotFoundError(f"Lista de candidatas não encontrada: {candidates_csv}")
    with candidates_csv.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_already_attempted(report_csv: Path) -> dict[tuple[str, str], RetryResult]:
    if not report_csv.is_file():
        return {}
    done: dict[tuple[str, str], RetryResult] = {}
    with report_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            done[(row["original_url"], row["tstamp"])] = RetryResult(
                original_url=row["original_url"],
                tstamp=row["tstamp"],
                outcome=row["outcome"],
                cause=row["cause"],
                attempts=int(row["attempts"]),
                error=row["error"],
                text_path=row["text_path"],
                size_bytes=int(row["size_bytes"]),
            )
    return done


def write_summary_markdown(
    results: list[RetryResult], total_candidates: int, path: Path
) -> None:
    recovered = [r for r in results if r.outcome != OUTCOME_FAILED]
    failed = [r for r in results if r.outcome == OUTCOME_FAILED]
    by_cause: dict[str, int] = {}
    for result in failed:
        by_cause[result.cause] = by_cause.get(result.cause, 0) + 1

    lines = [
        "# Retentativa dos textos que falharam por timeout ou ligação cortada\n",
        "Candidatas em `output/corpus_text_retry_candidates.csv`; resultado por "
        "captura em `output/corpus_text_retry_report.csv`. Não altera "
        "`output/corpus_rdf_report.csv` nem o grafo: os textos recuperados só "
        "ficam em `data/raw/texts/` até o grafo ser reconstruído.\n",
        "## Resumo\n",
        f"- Candidatas: {total_candidates}",
        f"- Já tentadas (com resultado definitivo): {len(results)}",
        f"- Por tentar: {total_candidates - len(results)}",
        f"- Recuperadas: {len(recovered)} "
        f"({sum(1 for r in recovered if r.outcome == OUTCOME_SUCCESS)} "
        f"descarregadas, {sum(1 for r in recovered if r.outcome == OUTCOME_SUCCESS_CACHED)} "
        "já existiam em cache)",
        f"- Falhas definitivas: {len(failed)}",
    ]
    for cause in sorted(by_cause):
        lines.append(f"  - {cause}: {by_cause[cause]}")
    lines.append(
        "\nEstes valores são o resultado real desta execução, não uma estimativa."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_retry(
    project_root: Path | None = None,
    client: ArquivoClient | None = None,
    *,
    attempts: int = ATTEMPTS,
    base_sleep: float = BASE_SLEEP_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> list[RetryResult]:
    root = project_root or Path(__file__).resolve().parents[2]
    candidates_csv = root / "output" / "corpus_text_retry_candidates.csv"
    report_csv = root / "output" / "corpus_text_retry_report.csv"

    candidates = load_candidates(candidates_csv)
    already = load_already_attempted(report_csv)
    pending = [
        row for row in candidates
        if (row["original_url"], row["tstamp"]) not in already
    ]
    LOGGER.info(
        "Retentativa: %d candidatas, %d já tentadas numa execução anterior, "
        "%d por tentar nesta sessão.",
        len(candidates), len(already), len(pending),
    )

    if client is None:
        client = ArquivoClient(data_dir=root / "data" / "raw")

    results: list[RetryResult] = list(already.values())
    if pending:
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        write_header = not report_csv.is_file()
        with report_csv.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(RESULT_FIELDS))
            if write_header:
                writer.writeheader()

            start = time.monotonic()
            for index, row in enumerate(pending, start=1):
                result = retry_one(
                    client,
                    row["original_url"],
                    row["tstamp"],
                    root,
                    attempts=attempts,
                    base_sleep=base_sleep,
                    sleep=sleep,
                )
                results.append(result)
                writer.writerow(asdict(result))
                handle.flush()

                if index % PROGRESS_EVERY == 0 or index == len(pending):
                    elapsed = time.monotonic() - start
                    remaining = (len(pending) - index) * (elapsed / index)
                    recovered = sum(1 for r in results if r.outcome != OUTCOME_FAILED)
                    LOGGER.info(
                        "Progresso: %d/%d pendentes nesta sessão (%d/%d no total), "
                        "%d recuperadas até agora, %.0fs decorridos, ~%.0fs restantes.",
                        index, len(pending), len(already) + index, len(candidates),
                        recovered, elapsed, remaining,
                    )
    else:
        LOGGER.info("Todas as candidatas já foram tentadas; nada a fazer.")

    write_summary_markdown(results, len(candidates), root / "output" / "corpus_text_retry_summary.md")
    return results


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).resolve().parents[2] / "output" / "corpus_text_retry_progress.log",
                mode="a",
                encoding="utf-8",
            ),
        ],
    )
    try:
        results = run_retry()
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1

    recovered = sum(1 for r in results if r.outcome != OUTCOME_FAILED)
    print(f"Candidatas tentadas: {len(results)}")
    print(f"Recuperadas: {recovered}; falhas definitivas: {len(results) - recovered}")
    print("Relatório: output/corpus_text_retry_report.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
