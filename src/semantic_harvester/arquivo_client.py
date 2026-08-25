"""Cliente HTTP simples para a API TextSearch do Arquivo.pt."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

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


class ArquivoClient:
    """Pesquisa capturas e descarrega o respetivo texto extraído."""

    SEARCH_URL = "https://arquivo.pt/textsearch"

    def __init__(
        self,
        data_dir: Path | str = Path("data/raw"),
        timeout: tuple[float, float] = (10.0, 30.0),
        session: requests.Session | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.searches_dir = self.data_dir / "searches"
        self.texts_dir = self.data_dir / "texts"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent", "semantic-driven-harvester/0.1 (academic prototype)"
        )

        self.searches_dir.mkdir(parents=True, exist_ok=True)
        self.texts_dir.mkdir(parents=True, exist_ok=True)

    def search(
        self,
        *,
        query: str,
        site_search: str | None = None,
        from_date: str | int | None = None,
        to_date: str | int | None = None,
        max_items: int = 20,
    ) -> SearchResponse:
        """Executa uma pesquisa e guarda a resposta JSON exatamente como recebida."""

        if not query.strip():
            raise ValueError("query não pode ser vazia")
        if max_items <= 0:
            raise ValueError("max_items deve ser superior a zero")

        params: list[tuple[str, str | int]] = [("q", query), ("maxItems", max_items)]
        if site_search:
            for host in self._site_search_hosts(site_search):
                params.append(("siteSearch", host))
        if from_date is not None:
            params.append(("from", str(from_date)))
        if to_date is not None:
            params.append(("to", str(to_date)))

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

        raw_path = self._search_path(query, site_search, from_date, to_date)
        raw_path.write_bytes(response.content)
        LOGGER.info("Resposta original guardada em %s", raw_path)

        return SearchResponse(
            results=results,
            raw_response=payload,
            raw_path=raw_path,
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

    @staticmethod
    def _text_filename(result: dict[str, Any]) -> str:
        raw_tstamp = str(result.get("tstamp") or "unknown")
        tstamp = "".join(character for character in raw_tstamp if character.isdigit())
        tstamp = tstamp or "unknown"
        url = str(result.get("originalURL") or result.get("linkToArchive") or "")
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return f"{tstamp}_{url_hash}.txt"
