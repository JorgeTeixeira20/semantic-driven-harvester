"""Testes offline para `ArquivoClient.download_original_html`.

Espelho de `download_extracted_text` (`docs/experiments.md`, "Download do
HTML em bruto da captura mais antiga"): lê `linkToOriginalFile` em vez de
`linkToExtractedText` e grava em `data/raw/original_html/`.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from semantic_harvester.arquivo_client import (
    CONNECTION_ERROR_MAX_WAITS, CONNECTION_ERROR_WAIT_SECONDS, RATE_LIMIT_DEFAULT_WAIT_SECONDS,
    RATE_LIMIT_MAX_WAITS, ArquivoClient,
)
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


TEXT_URL = "https://archive.example.test/text/20200101000000"


class StatusResponse:
    def __init__(self, status: int, body: bytes = b"", retry_after: str | None = None) -> None:
        self.status_code = status
        self.content = body
        self.headers = {"Retry-After": retry_after} if retry_after else {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)


class ScriptedSession:
    def __init__(self, *responses: StatusResponse) -> None:
        self.responses = list(responses)
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []

    def get(self, url: str, **kwargs) -> StatusResponse:
        self.calls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class RateLimitedDownloadTests(OfflineTestCase):
    """429 nos downloads de texto e HTML (2026-10-20): esperar o `Retry-After`
    e repetir; só conta como falha se continuar 429 depois das esperas."""

    def client(self, *responses: StatusResponse) -> tuple[ArquivoClient, ScriptedSession]:
        session = ScriptedSession(*responses)
        client = ArquivoClient(data_dir=self.root / "raw", session=session,
                               connection_error_max_waits=CONNECTION_ERROR_MAX_WAITS)
        return client, session

    def test_text_waits_retry_after_then_succeeds(self) -> None:
        client, session = self.client(StatusResponse(429, retry_after="5"),
                                      StatusResponse(200, b"texto"))
        with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
            result = client.download_extracted_text({**CAPTURE, "linkToExtractedText": TEXT_URL})
        self.assertTrue(result.success)
        self.assertEqual(result.path.read_bytes(), b"texto")
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [5.0])
        self.assertEqual(session.calls, [TEXT_URL, TEXT_URL])

    def test_html_without_retry_after_waits_the_default(self) -> None:
        client, _ = self.client(StatusResponse(429), StatusResponse(200, b"<html/>"))
        with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
            result = client.download_original_html(CAPTURE)
        self.assertTrue(result.success)
        self.assertEqual([call.args[0] for call in sleep.call_args_list],
                         [RATE_LIMIT_DEFAULT_WAIT_SECONDS])

    def test_persistent_429_is_a_failure_after_the_waits(self) -> None:
        client, session = self.client(*(StatusResponse(429) for _ in range(RATE_LIMIT_MAX_WAITS + 1)))
        with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
            result = client.download_original_html(CAPTURE)
        self.assertFalse(result.success)
        self.assertIn("429", result.error)
        self.assertEqual(sleep.call_count, RATE_LIMIT_MAX_WAITS)
        self.assertEqual(session.responses, [])

    def test_other_errors_are_not_retried(self) -> None:
        for status in (404, 500):
            client, session = self.client(StatusResponse(status))
            with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
                result = client.download_extracted_text({**CAPTURE, "linkToExtractedText": TEXT_URL})
            self.assertFalse(result.success)
            self.assertEqual((sleep.call_count, len(session.calls)), (0, 1))


    def test_connection_reset_waits_and_then_succeeds(self) -> None:
        reset = requests.ConnectionError("Connection aborted: reset by peer")
        client, session = self.client(reset, reset, StatusResponse(200, b"texto"))
        with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
            result = client.download_extracted_text({**CAPTURE, "linkToExtractedText": TEXT_URL})
        self.assertTrue(result.success)
        self.assertEqual([call.args[0] for call in sleep.call_args_list],
                         [CONNECTION_ERROR_WAIT_SECONDS] * 2)

    def test_connection_errors_are_not_retried_by_default(self) -> None:
        session = ScriptedSession(requests.ConnectionError("reset"))
        client = ArquivoClient(data_dir=self.root / "raw", session=session)
        with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
            result = client.download_original_html(CAPTURE)
        self.assertFalse(result.success)
        self.assertEqual(sleep.call_count, 0)

    def test_persistent_connection_error_is_a_failure_after_the_waits(self) -> None:
        client, _ = self.client(*(requests.ConnectionError("reset")
                                  for _ in range(CONNECTION_ERROR_MAX_WAITS + 1)))
        with patch("semantic_harvester.arquivo_client.time.sleep") as sleep:
            result = client.download_original_html(CAPTURE)
        self.assertFalse(result.success)
        self.assertEqual(sleep.call_count, CONNECTION_ERROR_MAX_WAITS)


if __name__ == "__main__":
    unittest.main()
