"""Obtenção de metadados e texto preservado pelo Arquivo.pt."""

from .arquivo_client import (
    ArquivoClient,
    DownloadSummary,
    SearchResponse,
    TextDownloadResult,
    VersionHistoryResponse,
)

__all__ = [
    "ArquivoClient",
    "DownloadSummary",
    "SearchResponse",
    "TextDownloadResult",
    "VersionHistoryResponse",
]
