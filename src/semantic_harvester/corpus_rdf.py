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

Segundo achado, também documentado em `docs/experiments.md`: a execução
real revelou uma taxa de falha alta nos downloads de texto (muitos 404 e
ligações cortadas para capturas de ~2017), tornando cada sessão lenta. Sem
retomar por artigo, cada nova tentativa reprocessava todos os artigos desde
o início — incluindo novas tentativas para downloads já falhados — e nunca
ultrapassava os primeiros ~20 artigos antes do corte seguinte. A execução é
por isso retomável por artigo: `build_corpus_graph()` salta os artigos já
presentes em `output/corpus_rdf_report.csv` e os seus triplos já
preservados em `data/processed/corpus_articles_triples.nt`.

Quarto ponto (2026-10-04, `docs/experiments.md`): duas variantes do mesmo
artigo que só diferem em parâmetros de rastreio (`?ref=…`, `?utm_…`) eram
contadas como dois artigos. A classificação passa a agrupá-las
(`url_identity.py`) e a listar as outras formas na coluna `variantes`; aqui
junta-se o raw de todas as variantes antes de mapear, sem pedidos novos.

Terceiro ponto: textos obtidos depois de um artigo ter sido dado como concluído
(por exemplo, pela retentativa em `corpus_text_retry.py`) não entram no grafo
por esta retoma. `--rebuild-offline` reconstrói o grafo de todos os artigos a
partir do raw, da classificação e da cache de textos, sem qualquer pedido à
API (`CacheOnlyClient`), com o mesmo código de produção, e só substitui os
outputs se todas as verificações de `verify_rebuild()` passarem.

Modo `--fase1 <label>` (2026-10-20, `docs/experiments.md`), para o corpus
alargado sem Fase 2: os artigos vêm de `output/corpus_classification_<label>.csv`
e cada um é registado com **uma só captura, a mais antiga que a descoberta
(Fase 1) encontrou**, lida do raw da TextSearch
(`data/raw/corpus_queries/<label>/`), sem reconstruir de `version_history`.
Ressalva: é a captura mais antiga *conhecida*, não necessariamente a mais
antiga que existe no Arquivo.pt. Texto e HTML seguem `TEXT_POLICY_FIRST`.
Os itens da TextSearch não trazem `statusCode` nem `contentLength`, que
ficam por isso ausentes do grafo. Outputs separados:
`output/corpus_articles_<label>.ttl`, `output/corpus_rdf_<label>_{report.csv,summary.md}`
e `data/processed/corpus_articles_<label>_triples.nt`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from rdflib import RDF, RDFS, Graph, XSD

from .arquivo_client import BAD_REQUEST_MAX_PAUSES, CONNECTION_ERROR_MAX_WAITS, ArquivoClient, TextDownloadResult
from .history_pipeline import TEXT_POLICY_ALL, TEXT_POLICY_FIRST, build_manifest_records
from .rdf_mapper import SDH, build_article_history_graph, stable_hash
from .url_identity import normalize_for_grouping

LOGGER = logging.getLogger(__name__)

PROGRESS_EVERY = 10
PHASE1_MIN_REQUEST_INTERVAL = 1.0


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


def load_article_captures(
    original_url: str, variants: list[str], version_history_dir: Path
) -> tuple[list[dict[str, Any]], int]:
    """Capturas do URL canónico e de todas as variantes, sem `tstamp` repetidos.

    Devolve `(capturas, repetidas_descartadas)`. O raw de cada variante já está
    preservado da Fase 2; não há pedidos novos.
    """

    captures: list[dict[str, Any]] = []
    seen: set[str] = set()
    repeated = 0
    for url in [original_url, *variants]:
        for capture in load_captures_from_raw(url, version_history_dir):
            tstamp = str(capture.get("tstamp"))
            if tstamp in seen:
                repeated += 1
                continue
            seen.add(tstamp)
            captures.append(capture)
    return captures, repeated


def variants_of(row: dict[str, str]) -> list[str]:
    return [url for url in (row.get("variantes") or "").split("|") if url]


def normalize_captures_to_canonical_url(
    captures: list[dict[str, Any]], canonical_url: str
) -> tuple[list[dict[str, Any]], int, int]:
    """Reatribui `originalURL` ao valor canónico quando só varia em esquema, barras
    ou parâmetros de rastreio.

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
            # O URL real da captura fica registado: os textos já em cache foram
            # guardados com o hash dele (CacheOnlyClient procura também assim).
            capture = {**capture, "originalURL": canonical_url, "sourceOriginalURL": capture_url}
            rewritten += 1
        normalized.append(capture)
    return normalized, dropped, rewritten


def load_phase1_oldest_captures(
    raw_dir: Path, canonical_urls: list[str]
) -> dict[str, dict[str, Any]]:
    """URL canónico → item da captura mais antiga que a Fase 1 encontrou.

    Lê todos os `response_items` do raw da TextSearch em `raw_dir`; um item
    pertence ao artigo se `normalize_for_grouping()` coincidir (a mesma regra
    da agregação da Fase 1). O `originalURL` do item devolvido é o canónico.
    """

    by_key = {normalize_for_grouping(url): url for url in canonical_urls}
    oldest: dict[str, dict[str, Any]] = {}
    for path in sorted(raw_dir.glob("*.json")):
        for item in json.loads(path.read_bytes()).get("response_items") or []:
            canonical = by_key.get(normalize_for_grouping(str(item.get("originalURL"))))
            if canonical is None:
                continue
            current = oldest.get(canonical)
            if current is None or str(item.get("tstamp")) < str(current.get("tstamp")):
                oldest[canonical] = {**item, "originalURL": canonical}
    return oldest


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

    @property
    def texts_not_requested(self) -> int:
        """Capturas sem pedido de texto (política "primeira"); não são falhas.

        Derivado, para não mudar o esquema de `corpus_rdf_report.csv`, que é
        retomável e acrescentado em modo append.
        """

        if self.error is not None:
            return 0
        return self.captures_used - self.texts_downloaded_now - self.texts_reused - self.texts_failed


RESULT_FIELDS = tuple(f.name for f in fields(ArticleGraphResult))


def article_result_from_row(row: dict[str, str]) -> ArticleGraphResult:
    return ArticleGraphResult(
        original_url=row["original_url"],
        captures_used=int(row["captures_used"]),
        captures_url_variants_normalized=int(row["captures_url_variants_normalized"]),
        captures_dropped_mismatched_url=int(row["captures_dropped_mismatched_url"]),
        texts_downloaded_now=int(row["texts_downloaded_now"]),
        texts_reused=int(row["texts_reused"]),
        texts_failed=int(row["texts_failed"]),
        error=row["error"] or None,
    )


def load_already_processed(report_csv: Path) -> dict[str, ArticleGraphResult]:
    """Permite retomar sem repetir artigos já processados (sucesso ou falha).

    Sem isto, cada retoma reprocessava todos os artigos desde o início,
    incluindo novas tentativas para todos os downloads de texto já falhados
    nas execuções anteriores — na prática, ficava sempre preso nos primeiros
    ~20 artigos antes do próximo corte por memória (ver docs/experiments.md).
    """

    if not report_csv.is_file():
        return {}
    processed: dict[str, ArticleGraphResult] = {}
    with report_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            processed[row["original_url"]] = article_result_from_row(row)
    return processed


def build_one_article_graph(
    client: ArquivoClient,
    original_url: str,
    title: str,
    version_history_dir: Path,
    project_root: Path,
    variants: list[str] | None = None,
    text_policy: str = TEXT_POLICY_ALL,
) -> tuple[Graph | None, ArticleGraphResult]:
    try:
        raw_captures, repeated = load_article_captures(
            original_url, variants or [], version_history_dir
        )
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return None, ArticleGraphResult(original_url, 0, 0, 0, 0, 0, 0, str(exc))

    if repeated:
        LOGGER.info("%s: %d captura(s) repetida(s) entre variantes de URL ignorada(s).",
                    original_url, repeated)
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

    records = build_manifest_records(client, captures, project_root, text_policy=text_policy)
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
    failed = sum(
        1 for r in records if r["text_requested"] and not r["text_download_success"]
    )

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


def build_article_graph_from_capture(
    client: ArquivoClient,
    capture: dict[str, Any],
    title: str,
    project_root: Path,
) -> tuple[Graph | None, ArticleGraphResult]:
    """Grafo de um artigo com uma só captura (modo `--fase1`); texto e HTML pela política "primeira"."""

    original_url = str(capture["originalURL"])
    records = build_manifest_records(client, [capture], project_root, text_policy=TEXT_POLICY_FIRST)
    try:
        graph = build_article_history_graph(records, title, project_root)
    except ValueError as exc:
        LOGGER.error("Falha ao mapear %s: %s", original_url, exc)
        return None, ArticleGraphResult(original_url, len(records), 0, 0, 0, 0, 0, str(exc))
    (record,) = records
    return graph, ArticleGraphResult(
        original_url=original_url,
        captures_used=1,
        captures_url_variants_normalized=0,
        captures_dropped_mismatched_url=0,
        texts_downloaded_now=int(record["text_downloaded_now"]),
        texts_reused=int(record["text_download_success"] and not record["text_downloaded_now"]),
        texts_failed=int(record["text_requested"] and not record["text_download_success"]),
        error=None,
    )


def rdf_paths(root: Path, phase1_label: str | None) -> dict[str, Path]:
    """Caminhos de uma execução; sem `phase1_label`, os do corpus de 125 artigos."""

    tag = f"_{phase1_label}" if phase1_label else ""
    return {
        "classification": root / "output" / f"corpus_classification{tag}.csv",
        "report": root / "output" / f"corpus_rdf{tag}_report.csv",
        "triples": root / "data" / "processed" / f"corpus_articles{tag}_triples.nt",
        "turtle": root / "output" / f"corpus_articles{tag}.ttl",
        "summary": root / "output" / f"corpus_rdf{tag}_summary.md",
        "progress": root / "output" / f"corpus_rdf{tag}_progress.log",
        "phase1_raw": root / "data" / "raw" / "corpus_queries" / (phase1_label or ""),
    }


def _summary_intro(
    n_articles: int, rebuilt_offline: bool, phase1_label: str | None = None
) -> list[str]:
    if phase1_label:
        return [
            f"Execução real sobre os {n_articles} artigos classificados como "
            f"`Artigo` em `output/corpus_classification_{phase1_label}.csv`. Cada "
            "artigo tem **uma só captura: a mais antiga que a descoberta (Fase 1) "
            "encontrou**, lida do raw da TextSearch "
            f"(`data/raw/corpus_queries/{phase1_label}/`), sem `version_history`. "
            "Ressalva: é a mais antiga conhecida, não necessariamente a mais antiga "
            "que existe no Arquivo.pt. Texto e HTML só dessa captura. A execução é "
            f"retomável por artigo (`output/corpus_rdf_{phase1_label}_report.csv`).\n"
        ]
    if rebuilt_offline:
        return [
            f"Reconstrução **offline** sobre os {n_articles} artigos "
            "classificados como `Artigo` em `output/corpus_classification.csv`, "
            "a partir do raw de `version_history` (`data/raw/version_history/`) "
            "e da cache de textos (`data/raw/texts/`), **sem qualquer pedido à "
            "API**. Um texto conta como disponível se o ficheiro existir na "
            "cache. Inclui os textos recuperados pela retentativa "
            "(`output/corpus_text_retry_report.csv`).\n"
        ]
    return [
        f"Execução real sobre os {n_articles} artigos classificados como "
        "`Artigo` em `output/corpus_classification.csv`. As capturas foram "
        "reconstruídas a partir do raw de `version_history` já preservado "
        "pela Fase 2 (`data/raw/version_history/`), sem pedidos novos; só o "
        "download dos textos extraídos fez pedidos reais à API. A execução é "
        "retomável por artigo (`output/corpus_rdf_report.csv`); estes números "
        "agregam todas as sessões até à conclusão, não só a última.\n"
    ]


def _summary_text_lines(
    downloaded: int, reused: int, failed: int, not_requested: int, rebuilt_offline: bool
) -> list[str]:
    if rebuilt_offline:
        return [
            f"- Textos disponíveis (ficheiro na cache): {downloaded + reused}",
            f"- Textos indisponíveis (sem ficheiro na cache): {failed}",
            "- A divisão histórica descarregados/reutilizados não é preservada "
            "numa reconstrução offline (todos contam como reutilizados); só o "
            "total disponível é informativo.",
        ]
    return [
        f"- Textos descarregados (soma de todas as sessões): {downloaded}",
        f"- Textos reutilizados (já existentes em `data/raw/texts/`): {reused}",
        f"- Textos indisponíveis (falha ou 404): {failed}",
        f"- Textos não pedidos (só a captura mais antiga de cada artigo novo; "
        f"não são falhas): {not_requested}",
    ]


def write_summary_markdown(
    results: list[ArticleGraphResult],
    graph_size: int,
    path: Path,
    rebuilt_offline: bool = False,
    phase1_label: str | None = None,
) -> None:
    successes = [r for r in results if r.error is None]
    failures = [r for r in results if r.error is not None]
    total_captures = sum(r.captures_used for r in successes)
    total_downloaded = sum(r.texts_downloaded_now for r in successes)
    total_reused = sum(r.texts_reused for r in successes)
    total_failed = sum(r.texts_failed for r in successes)
    total_not_requested = sum(r.texts_not_requested for r in successes)
    total_variants = sum(r.captures_url_variants_normalized for r in successes)
    total_dropped = sum(r.captures_dropped_mismatched_url for r in results)
    articles_with_variants = sum(
        1 for r in successes if r.captures_url_variants_normalized > 0
    )

    lines = [
        "# Grafo RDF do corpus do Caminho A (passo final)\n",
        *_summary_intro(len(results), rebuilt_offline, phase1_label),
        "## Resumo\n",
        f"- Artigos mapeados com sucesso: {len(successes)} de {len(results)}",
        f"- Artigos com falha (raw em falta ou manifesto inválido): {len(failures)}",
        f"- Total de capturas incluídas no grafo: {total_captures}",
        *_summary_text_lines(
            total_downloaded, total_reused, total_failed, total_not_requested,
            rebuilt_offline,
        ),
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
    phase1_label: str | None = None,
    store_cookies: bool = False,
) -> tuple[Graph, list[ArticleGraphResult]]:
    """Retomável por artigo: uma execução interrompida pode ser repetida sem
    repetir pedidos de rede para artigos já processados (sucesso ou falha).

    Cada artigo concluído é escrito de imediato em `report_csv` (uma linha,
    com flush) e os triplos do seu grafo são acrescentados a `triples_path`
    em N-Triples (uma linha por triplo, também com flush) — formato
    apendável sem reescrever o ficheiro inteiro, ao contrário de Turtle. O
    grafo Turtle final e o relatório em Markdown são sempre regenerados a
    partir destes dois ficheiros acumulados, nunca só da sessão atual.
    """

    root = project_root or Path(__file__).resolve().parents[2]
    paths = rdf_paths(root, phase1_label)
    classification_csv = paths["classification"]
    version_history_dir = root / "data" / "raw" / "version_history"
    report_csv = paths["report"]
    triples_path = paths["triples"]

    articles = load_retained_articles(classification_csv)
    already = load_already_processed(report_csv)
    pending = [row for row in articles if row["original_url"] not in already]
    oldest = (
        load_phase1_oldest_captures(paths["phase1_raw"], [row["original_url"] for row in pending])
        if phase1_label else {}
    )

    LOGGER.info(
        "Grafo RDF: %d artigos no total, %d já concluídos numa execução "
        "anterior, %d por processar nesta sessão.",
        len(articles), len(already), len(pending),
    )

    if client is None:
        # Timeout por omissão do ArquivoClient (10s/30s), não o (15s/120s)
        # copiado sem justificação das Fases 1-2: download de texto por
        # tstamp é um pedido direto, não pesquisa de texto livre, e um
        # read_timeout de 120s revelou-se demasiado tolerante a ligações
        # penduradas/cortadas (ver docs/experiments.md).
        client = ArquivoClient(
            data_dir=root / "data" / "raw",
            # Modo --fase1: uma quebra de ligação pausa a recolha em vez de
            # gerar falhas em série (2026-10-21, docs/experiments.md).
            connection_error_max_waits=CONNECTION_ERROR_MAX_WAITS if phase1_label else 0,
            # ~1 pedido/s no modo --fase1 (2026-10-21, docs/experiments.md).
            min_request_interval=PHASE1_MIN_REQUEST_INTERVAL if phase1_label else 0.0,
            # 400: renova a sessão e repete; se persistir, pausa ~10 min, até 3
            # vezes por URL. Sem cookies, salvo --guardar-cookies (diagnóstico).
            bad_request_max_pauses=BAD_REQUEST_MAX_PAUSES if phase1_label else 0,
            renew_session_on_bad_request=bool(phase1_label),
            store_cookies=store_cookies or not phase1_label,
        )

    results: list[ArticleGraphResult] = list(already.values())

    if pending:
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        triples_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not report_csv.is_file()

        with report_csv.open("a", encoding="utf-8", newline="") as report_handle:
            with triples_path.open("a", encoding="utf-8") as triples_handle:
                writer = csv.DictWriter(report_handle, fieldnames=list(RESULT_FIELDS), lineterminator="\n")
                if write_header:
                    writer.writeheader()

                start = time.monotonic()
                for index, row in enumerate(pending, start=1):
                    url = row["original_url"]
                    title = row["title"]
                    # Artigos novos (os já no relatório são saltados): só o
                    # texto da captura mais antiga (docs/experiments.md).
                    if phase1_label and url not in oldest:
                        graph, result = None, ArticleGraphResult(
                            url, 0, 0, 0, 0, 0, 0, "sem captura no raw da Fase 1")
                    elif phase1_label:
                        graph, result = build_article_graph_from_capture(
                            client, oldest[url], title, root)
                    else:
                        graph, result = build_one_article_graph(
                            client, url, title, version_history_dir, root, variants_of(row),
                            text_policy=TEXT_POLICY_FIRST,
                        )
                    if graph is not None:
                        triples_handle.write(graph.serialize(format="nt"))
                        triples_handle.write("\n")
                        triples_handle.flush()

                    results.append(result)
                    writer.writerow(asdict(result))
                    report_handle.flush()

                    if index % PROGRESS_EVERY == 0 or index == len(pending):
                        elapsed = time.monotonic() - start
                        rate = elapsed / index
                        remaining = (len(pending) - index) * rate
                        failures_so_far = sum(1 for r in results if r.error)
                        captures_so_far = sum(r.captures_used for r in results)
                        LOGGER.info(
                            "Progresso: %d/%d pendentes nesta sessão "
                            "(%d/%d no total), %d capturas processadas (total), "
                            "%.0fs decorridos nesta sessão, ~%.0fs restantes "
                            "nesta sessão, %d falhas até agora.",
                            index,
                            len(pending),
                            len(already) + index,
                            len(articles),
                            captures_so_far,
                            elapsed,
                            remaining,
                            failures_so_far,
                        )
    else:
        LOGGER.info(
            "Todos os %d artigos já tinham sido processados numa execução "
            "anterior; nada a fazer nesta sessão.",
            len(articles),
        )

    combined = Graph()
    combined.bind("sdh", SDH)
    combined.bind("rdf", RDF)
    combined.bind("rdfs", RDFS)
    combined.bind("xsd", XSD)
    if triples_path.is_file():
        combined.parse(location=str(triples_path), format="nt")

    return combined, results


class _OfflineSession:
    """Sessão que recusa qualquer pedido: garante que a reconstrução não usa rede."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, url: str, **kwargs: Any) -> Any:
        raise RuntimeError(f"Pedido de rede em modo offline: {url}")


class CacheOnlyClient(ArquivoClient):
    """Cliente cujos downloads de texto só consultam `data/raw/texts/`.

    Um texto é "disponível" se o ficheiro existir na cache; caso contrário
    fica indisponível sem qualquer pedido. Permite reutilizar
    `build_manifest_records()` e `build_one_article_graph()` tal como estão.
    """

    def __init__(self, data_dir: Path | str = Path("data/raw")) -> None:
        super().__init__(data_dir=data_dir, session=_OfflineSession())

    def download_extracted_text(
        self,
        result: dict[str, Any],
        *,
        skip_existing: bool = True,
        derive_url_when_missing: bool = False,
    ) -> TextDownloadResult:
        candidates = [self.texts_dir / self._text_filename(result)]
        if result.get("sourceOriginalURL"):
            candidates.append(self.texts_dir / self._text_filename(
                {**result, "originalURL": result["sourceOriginalURL"]}
            ))
        destination = next((path for path in candidates if path.is_file()), candidates[0])
        if destination.is_file():
            return TextDownloadResult(
                success=True,
                path=destination,
                size_bytes=destination.stat().st_size,
                downloaded=False,
                text_url=None,
            )
        return TextDownloadResult(
            success=False,
            path=None,
            size_bytes=0,
            downloaded=False,
            text_url=None,
            error="texto não disponível na cache (modo offline)",
        )


def rebuild_graph_offline(
    project_root: Path | None = None,
) -> tuple[Graph, list[ArticleGraphResult]]:
    """Reconstrói o grafo de todos os artigos retidos sem qualquer pedido à API.

    Usa o raw de `version_history`, a classificação e a cache de textos. É a
    forma de incorporar no grafo textos obtidos depois de os artigos terem
    sido dados como concluídos (`docs/experiments.md`).
    """

    root = project_root or Path(__file__).resolve().parents[2]
    articles = load_retained_articles(root / "output" / "corpus_classification.csv")
    client = CacheOnlyClient(data_dir=root / "data" / "raw")
    version_history_dir = root / "data" / "raw" / "version_history"

    combined = Graph()
    combined.bind("sdh", SDH)
    combined.bind("rdf", RDF)
    combined.bind("rdfs", RDFS)
    combined.bind("xsd", XSD)

    results: list[ArticleGraphResult] = []
    for row in articles:
        graph, result = build_one_article_graph(
            client, row["original_url"], row["title"], version_history_dir, root,
            variants_of(row), text_policy=TEXT_POLICY_ALL,
        )
        if graph is not None:
            combined += graph
        results.append(result)
    return combined, results


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool | None
    detail: str


def _count(graph: Graph, rdf_class: Any) -> int:
    return len(set(graph.subjects(RDF.type, rdf_class)))


def _recovered_by_retry(retry_report: Path, old_graph: Graph) -> tuple[int, int]:
    """(recuperadas pela retentativa, das quais ainda sem texto no grafo antigo)."""

    # Compara pelo ficheiro, não pelo URI do texto: depois de fundir variantes de
    # URL, o texto de uma variante passa a ter o URI do artigo canónico.
    old_files = {Path(str(o)).name for o in old_graph.objects(None, SDH.filePath)}
    with retry_report.open(encoding="utf-8", newline="") as handle:
        recovered = [row for row in csv.DictReader(handle) if row["outcome"] != "failed"]
    new = sum(
        1 for row in recovered
        if ArquivoClient._text_filename(
            {"originalURL": row["original_url"], "tstamp": row["tstamp"]}
        ) not in old_files
    )
    return len(recovered), new


def _found_by_capture_url(old_graph: Graph, new_graph: Graph) -> int:
    """Textos novos cujo ficheiro tem o hash de outra forma do URL (não do canónico).

    São textos já em cache, guardados com o hash do URL real da captura (por
    exemplo com barra dupla, antes da correção das variantes cosméticas), que
    a procura só pelo hash canónico não encontrava (`docs/experiments.md`).
    """

    old_files = {str(o) for o in old_graph.objects(None, SDH.filePath)}
    count = 0
    for text, path in new_graph.subject_objects(SDH.filePath):
        if str(path) in old_files:
            continue
        canonical_hash16 = str(text).rsplit("/", 2)[-2][:16]
        file_hash16 = Path(str(path)).stem.rsplit("_", 1)[-1]
        count += file_hash16 != canonical_hash16
    return count


def _merged_variants(
    old_graph: Graph, new_graph: Graph, retained: list[dict[str, str]]
) -> tuple[set[str], set[str], set[str]]:
    """URLs que deixaram de ser recurso próprio: (fundidos, que os absorveram, perdidos).

    Um URL só pode desaparecer se estiver declarado como variante de um artigo
    retido (coluna `variantes`); caso contrário é um artigo perdido.
    """

    old_urls = {str(o) for o in old_graph.objects(None, SDH.originalURL)}
    new_urls = {str(o) for o in new_graph.objects(None, SDH.originalURL)}
    removed = old_urls - new_urls
    declared = {variant: row["original_url"] for row in retained for variant in variants_of(row)}
    merged = {url for url in removed if url in declared}
    return merged, {declared[url] for url in merged}, removed - merged


def _about(subject: Any, urls: set[str]) -> bool:
    """O sujeito é um artigo/recurso/captura/texto de um destes URLs (hash no URI)."""

    return any(f"/{stable_hash(url)}" in str(subject) for url in urls)


def verify_rebuild(
    root: Path,
    new_graph: Graph,
    results: list[ArticleGraphResult],
    old_graph: Graph | None,
) -> list[Check]:
    """Verificações de aceitação da reconstrução (`docs/experiments.md`)."""

    checks: list[Check] = []
    retained = load_retained_articles(root / "output" / "corpus_classification.csv")
    errors = [r for r in results if r.error is not None]

    n_articles = _count(new_graph, SDH.Artigo)
    checks.append(Check(
        "artigos",
        n_articles == len(retained) and not errors,
        f"{n_articles} Artigo no grafo; {len(retained)} retidos na classificação; "
        f"{len(errors)} com erro",
    ))

    expected_captures = sum(int(row["captures"]) for row in retained)
    n_captures = _count(new_graph, SDH.CapturaArquivada)
    checks.append(Check(
        "capturas",
        n_captures == expected_captures == sum(r.captures_used for r in results),
        f"{n_captures} CapturaArquivada; {expected_captures} esperadas pela "
        "classificação",
    ))

    new_texts = _count(new_graph, SDH.TextoExtraido)
    retry_report = root / "output" / "corpus_text_retry_report.csv"
    if old_graph is None or not retry_report.is_file():
        checks.append(Check(
            "textos_esperados", None,
            "saltada: falta o grafo antigo ou o relatório da retentativa",
        ))
    else:
        old_texts = _count(old_graph, SDH.TextoExtraido)
        recovered, recovered_new = _recovered_by_retry(retry_report, old_graph)
        by_capture_url = _found_by_capture_url(old_graph, new_graph)
        expected = old_texts + recovered_new + by_capture_url
        checks.append(Check(
            "textos_esperados",
            new_texts == expected,
            f"{new_texts} TextoExtraido no novo; {old_texts} no antigo + "
            f"{recovered_new} recuperadas pela retentativa ainda não incorporadas "
            f"(de {recovered}) + {by_capture_url} já em cache encontrados pelo URL "
            f"real da captura = {expected}",
        ))

    if old_graph is None:
        for name in ("variantes_fundidas", "antigo_contido_no_novo",
                     "diferenca_so_textos", "ficheiros_de_texto_preservados"):
            checks.append(Check(name, None, "saltada: sem grafo antigo"))
    else:
        merged, absorbing, lost = _merged_variants(old_graph, new_graph, retained)
        checks.append(Check(
            "variantes_fundidas",
            not lost,
            f"{len(merged)} URL(s) fundido(s) como variante noutro artigo"
            + (f": {sorted(merged)} → {sorted(absorbing)}" if merged else "")
            + f"; {len(lost)} desaparecido(s) sem ser variante declarada",
        ))
        missing = old_graph - new_graph
        unexplained = [triple for triple in missing if not _about(triple[0], merged)]
        checks.append(Check(
            "antigo_contido_no_novo",
            not unexplained,
            f"{len(old_graph)} triplos no antigo; {len(missing)} ausentes do novo, "
            f"dos quais {len(missing) - len(unexplained)} de URLs fundidos e "
            f"{len(unexplained)} sem explicação",
        ))
        text_subjects = set(new_graph.subjects(RDF.type, SDH.TextoExtraido))
        added = new_graph - old_graph
        unexpected = [
            triple for triple in added
            if triple[1] != SDH.temTextoExtraido and triple[0] not in text_subjects
            and not _about(triple[0], absorbing)
        ]
        checks.append(Check(
            "diferenca_so_textos",
            not unexpected,
            f"{len(added)} triplos acrescentados; {len(unexpected)} que não são "
            "de TextoExtraido nem de artigos que absorveram variantes",
        ))
        old_files = {str(o) for o in old_graph.objects(None, SDH.filePath)}
        new_files = {str(o) for o in new_graph.objects(None, SDH.filePath)}
        checks.append(Check(
            "ficheiros_de_texto_preservados",
            old_files <= new_files,
            f"{len(old_files - new_files)} ficheiro(s) de texto do grafo antigo "
            "deixaram de ser referenciados",
        ))

    missing_files = [
        str(path) for path in new_graph.objects(None, SDH.filePath)
        if not (root / str(path)).is_file()
    ]
    checks.append(Check(
        "filepaths_existem",
        not missing_files,
        f"{new_texts} caminhos de texto; {len(missing_files)} sem ficheiro em disco",
    ))

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "corpus_articles.ttl"
        new_graph.serialize(destination=probe, format="turtle")
        try:
            reparsed = Graph().parse(probe, format="turtle")
            roundtrip = set(reparsed) == set(new_graph)
            detail = f"relido: {len(reparsed)} triplos; iguais aos do grafo em memória: {roundtrip}"
        except Exception as exc:  # noqa: BLE001 - qualquer erro de leitura é falha da verificação
            roundtrip, detail = False, f"erro ao reler o Turtle: {exc}"
    checks.append(Check("turtle_reler", roundtrip, detail))
    return checks


def rebuild_offline(
    project_root: Path | None = None, *, apply: bool = True
) -> tuple[list[Check], list[ArticleGraphResult], Graph]:
    """Reconstrói, verifica e só depois (se tudo passar e `apply`) substitui os outputs.

    Se alguma verificação falhar, os ficheiros existentes ficam intactos.
    """

    root = project_root or Path(__file__).resolve().parents[2]
    ttl_path = root / "output" / "corpus_articles.ttl"
    report_csv = root / "output" / "corpus_rdf_report.csv"
    triples_path = root / "data" / "processed" / "corpus_articles_triples.nt"

    old_graph = Graph().parse(ttl_path, format="turtle") if ttl_path.is_file() else None
    new_graph, results = rebuild_graph_offline(root)
    checks = verify_rebuild(root, new_graph, results, old_graph)

    if apply and all(check.passed is not False for check in checks):
        if triples_path.is_file():
            shutil.copy2(triples_path, triples_path.with_name(triples_path.name + ".pre-rebuild"))
        triples_path.parent.mkdir(parents=True, exist_ok=True)
        new_graph.serialize(destination=triples_path, format="nt", encoding="utf-8")
        with report_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(RESULT_FIELDS), lineterminator="\n")
            writer.writeheader()
            writer.writerows(asdict(result) for result in results)
        new_graph.serialize(destination=ttl_path, format="turtle")
        write_summary_markdown(
            results, len(new_graph), root / "output" / "corpus_rdf_summary.md",
            rebuilt_offline=True,
        )
    return checks, results, new_graph


def run(
    project_root: Path | None = None,
    phase1_label: str | None = None,
    store_cookies: bool = False,
) -> tuple[Graph, list[ArticleGraphResult]]:
    root = project_root or Path(__file__).resolve().parents[2]
    paths = rdf_paths(root, phase1_label)
    graph, results = build_corpus_graph(root, phase1_label=phase1_label, store_cookies=store_cookies)

    output_path = paths["turtle"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format="turtle")

    write_summary_markdown(results, len(graph), paths["summary"], phase1_label=phase1_label)
    return graph, results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.corpus_rdf",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument(
        "--rebuild-offline",
        action="store_true",
        help="reconstrói o grafo dos artigos retidos a partir do raw e da cache "
        "de textos, sem pedidos à API, e só substitui os outputs se todas as "
        "verificações passarem",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="com --rebuild-offline: só reconstrói e verifica, sem escrever",
    )
    parser.add_argument(
        "--fase1",
        metavar="LABEL",
        help="corpus alargado sem Fase 2: artigos de corpus_classification_<LABEL>.csv, "
        "uma captura por artigo (a mais antiga encontrada pela Fase 1 <LABEL>); "
        "outputs etiquetados",
    )
    parser.add_argument(
        "--guardar-cookies",
        action="store_true",
        help="com --fase1: a sessão guarda cookies (só para diagnóstico do 400; "
        "por omissão o modo --fase1 recusa-os)",
    )
    args = parser.parse_args(argv)
    if args.guardar_cookies and not args.fase1:
        parser.error("--guardar-cookies só faz sentido com --fase1")
    if args.check_only and not args.rebuild_offline:
        parser.error("--check-only só faz sentido com --rebuild-offline")
    if args.fase1 and args.rebuild_offline:
        parser.error("--fase1 não se combina com --rebuild-offline")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                rdf_paths(Path(__file__).resolve().parents[2], args.fase1)["progress"],
                mode="a",
                encoding="utf-8",
            ),
        ],
    )
    if args.rebuild_offline:
        checks, results, graph = rebuild_offline(apply=not args.check_only)
        for check in checks:
            state = "SALTADA" if check.passed is None else "OK" if check.passed else "FALHOU"
            print(f"[{state}] {check.name}: {check.detail}")
        if any(check.passed is False for check in checks):
            print("Verificações falhadas: nenhum ficheiro foi alterado.")
            return 1
        if args.check_only:
            print("Verificações OK (--check-only): nenhum ficheiro foi alterado.")
        else:
            print("Verificações OK: outputs substituídos (cópia do .nt em "
                  "data/processed/corpus_articles_triples.nt.pre-rebuild).")
        return 0

    graph, results = run(phase1_label=args.fase1, store_cookies=args.guardar_cookies)
    paths = rdf_paths(Path(__file__).resolve().parents[2], args.fase1)
    successes = [r for r in results if r.error is None]
    print(f"Artigos mapeados: {len(successes)} de {len(results)}")
    print(f"Triplos no grafo: {len(graph)}")
    print(f"Turtle: {paths['turtle']}")
    print(f"Relatórios: {paths['report']}, {paths['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
