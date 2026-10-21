"""Cliente HTTP simples para a API TextSearch do Arquivo.pt."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode, urlsplit

import requests

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResponse:
    """Resposta de uma pesquisa e caminho da cópia JSON original."""

    results: list[dict[str, Any]]
    raw_response: dict[str, Any]
    raw_path: Path


@dataclass(frozen=True)
class DownloadSummary:
    """Contadores e ficheiros produzidos ao descarregar textos."""

    downloaded: int
    failed: int
    without_link: int
    files: list[Path]


@dataclass(frozen=True)
class VersionHistoryResponse:
    """Uma página do histórico de versões e a sua resposta raw preservada."""

    results: list[dict[str, Any]]
    raw_response: dict[str, Any]
    raw_path: Path
    estimated_nr_results: int | None
    next_page: str | None


@dataclass(frozen=True)
class TextDownloadResult:
    """Resultado do acesso ao texto de uma captura individual."""

    success: bool
    path: Path | None
    size_bytes: int
    downloaded: bool
    text_url: str | None
    error: str | None = None


@dataclass(frozen=True)
class HtmlDownloadResult:
    """Resultado do acesso ao HTML em bruto (`linkToOriginalFile`) de uma captura."""

    success: bool
    path: Path | None
    size_bytes: int
    downloaded: bool
    html_url: str | None
    error: str | None = None


# 429 Too Many Requests nos downloads de texto e HTML (2026-10-20,
# docs/experiments.md): esperar o `Retry-After` (ou 60 s) e repetir, até este
# número de esperas por pedido; só depois conta como falha.
RATE_LIMIT_DEFAULT_WAIT_SECONDS = 60.0
RATE_LIMIT_MAX_WAITS = 20
# Erro de ligação (inclui "connection reset by peer") nos mesmos downloads:
# na execução de 2026-10-20 o serviço passou a recusar ligações ao fim de
# ~13 h e cada pedido falhava de imediato. Com `connection_error_max_waits`
# (desligado por omissão, para não mudar `corpus_text_retry`, que tem a sua
# própria retentativa), espera-se e repete-se até esse número de vezes por
# pedido, para a recolha pausar em vez de gerar falhas.
CONNECTION_ERROR_WAIT_SECONDS = 60.0
CONNECTION_ERROR_MAX_WAITS = 10


def retry_after_seconds(response: Any) -> float:
    """Espera indicada por uma resposta 429 (`Retry-After` em segundos, ou 60 s)."""

    try:
        return max(float(response.headers.get("Retry-After", "")), 1.0)
    except (AttributeError, TypeError, ValueError):
        return RATE_LIMIT_DEFAULT_WAIT_SECONDS


class ArquivoClient:
    """Pesquisa capturas e descarrega o respetivo texto extraído."""

    SEARCH_URL = "https://arquivo.pt/textsearch"

    def __init__(
        self,
        data_dir: Path | str = Path("data/raw"),
        timeout: tuple[float, float] = (10.0, 30.0),
        session: requests.Session | None = None,
        connection_error_max_waits: int = 0,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.connection_error_max_waits = connection_error_max_waits
        self.searches_dir = self.data_dir / "searches"
        self.texts_dir = self.data_dir / "texts"
        self.html_dir = self.data_dir / "original_html"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent", "semantic-driven-harvester/0.1 (academic prototype)"
        )

        self.searches_dir.mkdir(parents=True, exist_ok=True)
        self.texts_dir.mkdir(parents=True, exist_ok=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)

    def search(
        self,
        *,
        query: str,
        site_search: str | None = None,
        from_date: str | int | None = None,
        to_date: str | int | None = None,
        max_items: int = 20,
        offset: int | None = None,
        dedup_field: str | None = None,
        dedup_value: int | None = None,
        raw_path: Path | str | None = None,
    ) -> SearchResponse:
        """Executa uma pesquisa e guarda a resposta JSON exatamente como recebida."""

        if not query.strip():
            raise ValueError("query não pode ser vazia")
        if max_items <= 0:
            raise ValueError("max_items deve ser superior a zero")
        if offset is not None and offset < 0:
            raise ValueError("offset não pode ser negativo")

        params: list[tuple[str, str | int]] = [("q", query), ("maxItems", max_items)]
        if site_search:
            for host in self._site_search_hosts(site_search):
                params.append(("siteSearch", host))
        if from_date is not None:
            params.append(("from", str(from_date)))
        if to_date is not None:
            params.append(("to", str(to_date)))
        if offset is not None:
            params.append(("offset", offset))
        if dedup_field is not None:
            params.append(("dedupField", dedup_field))
        if dedup_value is not None:
            params.append(("dedupValue", dedup_value))

        LOGGER.info("A pesquisar o Arquivo.pt: query=%r", query)
        response = self.session.get(self.SEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        try:
            payload: dict[str, Any] = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise RuntimeError("O Arquivo.pt devolveu uma resposta JSON inválida") from exc

        results = payload.get("response_items", [])
        if not isinstance(results, list):
            raise RuntimeError("Resposta inesperada: 'response_items' não é uma lista")

        destination = (
            Path(raw_path)
            if raw_path is not None
            else self._search_path(query, site_search, from_date, to_date)
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        LOGGER.info("Resposta original guardada em %s", destination)

        return SearchResponse(
            results=results,
            raw_response=payload,
            raw_path=destination,
        )

    def version_history(
        self,
        *,
        original_url: str,
        from_date: str | int | None = None,
        to_date: str | int | None = None,
        max_items: int = 50,
        offset: int = 0,
    ) -> VersionHistoryResponse:
        """Obtém uma página do histórico de um URL e preserva o JSON raw."""

        if not original_url.strip():
            raise ValueError("original_url não pode ser vazio")
        if max_items <= 0:
            raise ValueError("max_items deve ser superior a zero")
        if offset < 0:
            raise ValueError("offset não pode ser negativo")

        params: list[tuple[str, str | int]] = [
            ("versionHistory", original_url),
            ("maxItems", max_items),
            ("offset", offset),
        ]
        if from_date is not None:
            params.append(("from", str(from_date)))
        if to_date is not None:
            params.append(("to", str(to_date)))

        LOGGER.info(
            "A consultar histórico no Arquivo.pt: url=%r offset=%d",
            original_url,
            offset,
        )
        response = self.session.get(self.SEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        try:
            payload: dict[str, Any] = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise RuntimeError("O Arquivo.pt devolveu uma resposta JSON inválida") from exc

        results = payload.get("response_items", [])
        if not isinstance(results, list):
            raise RuntimeError("Resposta inesperada: 'response_items' não é uma lista")

        raw_path = self._version_history_path(
            original_url, from_date, to_date, max_items, offset
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
        LOGGER.info("Histórico raw guardado em %s", raw_path)

        estimated = payload.get("estimated_nr_results")
        return VersionHistoryResponse(
            results=results,
            raw_response=payload,
            raw_path=raw_path,
            estimated_nr_results=int(estimated) if estimated is not None else None,
            next_page=payload.get("next_page"),
        )

    def download_extracted_text(
        self,
        result: dict[str, Any],
        *,
        skip_existing: bool = True,
        derive_url_when_missing: bool = False,
    ) -> TextDownloadResult:
        """Obtém um texto sem alterar o raw e pode reutilizar um ficheiro existente."""

        destination = self.texts_dir / self._text_filename(result)
        text_url = result.get("linkToExtractedText")

        if skip_existing and destination.is_file():
            return TextDownloadResult(
                success=True,
                path=destination,
                size_bytes=destination.stat().st_size,
                downloaded=False,
                text_url=str(text_url) if text_url else None,
            )

        if not text_url and derive_url_when_missing:
            text_url = self._derived_extracted_text_url(result)
        if not text_url:
            return TextDownloadResult(
                success=False,
                path=None,
                size_bytes=0,
                downloaded=False,
                text_url=None,
                error="linkToExtractedText ausente",
            )

        try:
            response = self._get_respecting_rate_limit(str(text_url))
            response.raise_for_status()
            destination.write_bytes(response.content)
        except (requests.RequestException, OSError) as exc:
            LOGGER.warning("Falha ao obter %s: %s", text_url, exc)
            return TextDownloadResult(
                success=False,
                path=None,
                size_bytes=0,
                downloaded=False,
                text_url=str(text_url),
                error=str(exc),
            )

        return TextDownloadResult(
            success=True,
            path=destination,
            size_bytes=destination.stat().st_size,
            downloaded=True,
            text_url=str(text_url),
        )

    def _get_respecting_rate_limit(self, url: str) -> Any:
        """GET que, num 429, espera o `Retry-After` e repete (até `RATE_LIMIT_MAX_WAITS`);
        num erro de ligação, espera `CONNECTION_ERROR_WAIT_SECONDS` e repete (até
        `self.connection_error_max_waits`, 0 por omissão), depois deixa o erro seguir.

        Devolve a última resposta; se continuar a ser 429 depois das esperas,
        o `raise_for_status()` do chamador regista-a como falha.
        """

        waits = 0
        connection_waits = 0
        while True:
            try:
                response = self.session.get(url, timeout=self.timeout)
            except requests.ConnectionError as exc:
                if connection_waits >= self.connection_error_max_waits:
                    raise
                connection_waits += 1
                LOGGER.warning("Erro de ligação em %s (%s): a esperar %.0fs (espera %d/%d).",
                               url, exc, CONNECTION_ERROR_WAIT_SECONDS, connection_waits,
                               self.connection_error_max_waits)
                time.sleep(CONNECTION_ERROR_WAIT_SECONDS)
                continue
            if getattr(response, "status_code", 200) != 429 or waits >= RATE_LIMIT_MAX_WAITS:
                return response
            waits += 1
            wait = retry_after_seconds(response)
            LOGGER.warning("429 em %s: a esperar %.0fs antes de repetir (espera %d/%d).",
                           url, wait, waits, RATE_LIMIT_MAX_WAITS)
            time.sleep(wait)

    def download_original_html(
        self,
        result: dict[str, Any],
        *,
        skip_existing: bool = True,
    ) -> HtmlDownloadResult:
        """Espelho de `download_extracted_text`, para `linkToOriginalFile`.

        Sem derivação de URL quando o campo falta: ao contrário de
        `linkToExtractedText`, não há (ainda) fórmula confirmada equivalente
        à de `_derived_extracted_text_url` para o HTML em bruto.
        """

        destination = self.html_dir / self._capture_filename(result, "html")
        html_url = result.get("linkToOriginalFile")

        if skip_existing and destination.is_file():
            return HtmlDownloadResult(
                success=True,
                path=destination,
                size_bytes=destination.stat().st_size,
                downloaded=False,
                html_url=str(html_url) if html_url else None,
            )

        if not html_url:
            return HtmlDownloadResult(
                success=False,
                path=None,
                size_bytes=0,
                downloaded=False,
                html_url=None,
                error="linkToOriginalFile ausente",
            )

        try:
            response = self._get_respecting_rate_limit(str(html_url))
            response.raise_for_status()
            destination.write_bytes(response.content)
        except (requests.RequestException, OSError) as exc:
            LOGGER.warning("Falha ao obter %s: %s", html_url, exc)
            return HtmlDownloadResult(
                success=False,
                path=None,
                size_bytes=0,
                downloaded=False,
                html_url=str(html_url),
                error=str(exc),
            )

        return HtmlDownloadResult(
            success=True,
            path=destination,
            size_bytes=destination.stat().st_size,
            downloaded=True,
            html_url=str(html_url),
        )

    def download_extracted_texts(
        self, results: Iterable[dict[str, Any]]
    ) -> DownloadSummary:
        """Descarrega os textos disponíveis sem parar perante falhas individuais."""

        downloaded = 0
        failed = 0
        without_link = 0
        files: list[Path] = []

        for result in results:
            text_url = result.get("linkToExtractedText")
            if not text_url:
                without_link += 1
                LOGGER.warning(
                    "Captura %s sem linkToExtractedText; ignorada",
                    result.get("tstamp", "desconhecida"),
                )
                continue

            destination = self.texts_dir / self._text_filename(result)
            try:
                response = self.session.get(text_url, timeout=self.timeout)
                response.raise_for_status()
                destination.write_bytes(response.content)
            except (requests.RequestException, OSError) as exc:
                failed += 1
                LOGGER.warning("Falha ao obter %s: %s", text_url, exc)
                continue

            downloaded += 1
            files.append(destination)
            LOGGER.info("Texto guardado em %s", destination)

        return DownloadSummary(
            downloaded=downloaded,
            failed=failed,
            without_link=without_link,
            files=files,
        )

    @staticmethod
    def _site_search_hosts(site_search: str) -> list[str]:
        """Inclui o host www para um domínio simples, evitando duplicados."""

        value = site_search.strip()
        parsed = urlsplit(value if "://" in value else f"//{value}")
        host = (parsed.hostname or value).lower().rstrip(".")

        hosts = [host]
        if host.count(".") == 1 and not host.startswith("www."):
            hosts.append(f"www.{host}")
        return hosts

    def _search_path(
        self,
        query: str,
        site_search: str | None,
        from_date: str | int | None,
        to_date: str | int | None,
    ) -> Path:
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        identity = "|".join(
            [query, site_search or "", str(from_date or ""), str(to_date or "")]
        )
        short_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        return self.searches_dir / f"search_{now}_{short_hash}.json"

    def _version_history_path(
        self,
        original_url: str,
        from_date: str | int | None,
        to_date: str | int | None,
        max_items: int,
        offset: int,
    ) -> Path:
        url_hash = hashlib.sha256(original_url.encode("utf-8")).hexdigest()[:16]
        date_range = f"{from_date or 'all'}-{to_date or 'all'}"
        safe_range = "".join(
            character if character.isalnum() or character == "-" else "_"
            for character in date_range
        )
        filename = (
            f"version_history_{url_hash}_{safe_range}_"
            f"offset-{offset:06d}_max-{max_items}.json"
        )
        return self.data_dir / "version_history" / filename

    @staticmethod
    def _derived_extracted_text_url(result: dict[str, Any]) -> str | None:
        original_url = result.get("originalURL")
        tstamp = result.get("tstamp")
        if not original_url or not tstamp:
            return None
        query = urlencode({"m": f"{original_url}/{tstamp}"})
        return f"https://arquivo.pt/textextracted?{query}"

    @staticmethod
    def _capture_filename(result: dict[str, Any], suffix: str) -> str:
        raw_tstamp = str(result.get("tstamp") or "unknown")
        tstamp = "".join(character for character in raw_tstamp if character.isdigit())
        tstamp = tstamp or "unknown"
        url = str(result.get("originalURL") or result.get("linkToArchive") or "")
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return f"{tstamp}_{url_hash}.{suffix}"

    @classmethod
    def _text_filename(cls, result: dict[str, Any]) -> str:
        return cls._capture_filename(result, "txt")
