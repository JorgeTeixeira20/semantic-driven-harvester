"""Testes offline para `ArquivoClient.download_original_html`.

Espelho de `download_extracted_text` (`docs/experiments.md`, "Download do
HTML em bruto da captura mais antiga"): lê `linkToOriginalFile` em vez de
`linkToExtractedText` e grava em `data/raw/original_html/`.
"""

from __future__ import annotations

import unittest

import requests

from semantic_harvester.arquivo_client import ArquivoClient
from tests.support import ORIGINAL_URL, FixtureSession, OfflineTestCase

HTML_URL = "https://archive.example.test/original/20200101000000"
CAPTURE = {
    "originalURL": ORIGINAL_URL,
    "tstamp": "20200101000000",
    "linkToOriginalFile": HTML_URL,
}


class FailingSession(FixtureSession):
    """Como a FixtureSession, mas qualquer pedido falha por erro de rede."""

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        raise requests.ConnectionError("falhou")


class DownloadOriginalHtmlTests(OfflineTestCase):
    def test_downloads_and_preserves_bytes(self) -> None:
        content = b"<html><body>Artigo</body></html>"
        session = self.fixture_session((HTML_URL, content))
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        result = client.download_original_html(CAPTURE)

        self.assertEqual(
            (result.success, result.downloaded, result.html_url, result.error),
            (True, True, HTML_URL, None),
        )
        self.assertEqual(result.path.read_bytes(), content)
        self.assertTrue(result.path.name.endswith(".html"))
        self.assertEqual(result.path.parent, client.html_dir)

    def test_existing_file_is_reused_without_any_request(self) -> None:
        session = self.fixture_session()
        client = ArquivoClient(data_dir=self.root / "raw", session=session)
        destination = client.html_dir / client._capture_filename(CAPTURE, "html")
        destination.write_bytes(b"cache")

        result = client.download_original_html(CAPTURE)

        self.assertEqual((result.success, result.downloaded), (True, False))
        self.assertEqual(result.path.read_bytes(), b"cache")

    def test_missing_field_fails_without_any_request(self) -> None:
        session = self.fixture_session()
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        result = client.download_original_html({**CAPTURE, "linkToOriginalFile": None})

        self.assertEqual(
            (result.success, result.path, result.html_url, result.error),
            (False, None, None, "linkToOriginalFile ausente"),
        )

    def test_network_failure_is_reported_without_raising(self) -> None:
        session = FailingSession()
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        result = client.download_original_html(CAPTURE)

        self.assertEqual((result.success, result.path, result.html_url), (False, None, HTML_URL))
        self.assertIn("falhou", result.error)

    def test_filename_mirrors_text_filename_with_html_suffix(self) -> None:
        session = self.fixture_session()
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        self.assertEqual(
            client._capture_filename(CAPTURE, "html"),
            client._text_filename(CAPTURE).replace(".txt", ".html"),
        )


if __name__ == "__main__":
    unittest.main()
