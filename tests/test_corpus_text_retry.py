from __future__ import annotations

import csv
import unittest
from collections import deque

import requests

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_text_retry import (
    OUTCOME_FAILED, OUTCOME_SUCCESS, OUTCOME_SUCCESS_CACHED, classify_error,
    load_already_attempted, retry_one, run_retry,
)
from tests.support import OfflineTestCase

URL_A = "https://news.example.test/articles/retry-a"
URL_B = "https://news.example.test/articles/retry-b"
TSTAMP_A = "20200101000000"
TSTAMP_B = "20200202000000"

CANDIDATE_FIELDS = (
    "original_url", "tstamp", "last_failure_category", "attempts_logged", "status_code",
)


def read_timeout() -> Exception:
    return requests.exceptions.ReadTimeout(
        "HTTPSConnectionPool(host='arquivo.pt', port=443): Read timed out. "
        "(read timeout=30.0)"
    )


def connection_cut() -> Exception:
    return requests.exceptions.ConnectionError(
        "('Connection aborted.', RemoteDisconnected('Remote end closed "
        "connection without response'))"
    )


def not_found() -> Exception:
    return requests.exceptions.HTTPError(
        "404 Client Error: Not Found for url: https://arquivo.pt/textextracted?m=x"
    )


class ScriptedResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class ScriptedSession:
    """Cada pedido consome um passo: bytes = resposta, Exception = é levantada.

    Ao contrário de FixtureSession, permite simular falhas de rede. Um pedido
    sem passo preparado falha o teste, provando que não houve rede."""

    def __init__(self, *script: bytes | Exception) -> None:
        self.script = deque(script)
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []

    def get(self, url: str, **kwargs) -> ScriptedResponse:
        if not self.script:
            raise AssertionError(f"Pedido inesperado: {url}")
        self.calls.append(url)
        step = self.script.popleft()
        if isinstance(step, Exception):
            raise step
        return ScriptedResponse(step)


class RetryTestCase(OfflineTestCase):
    def make_client(self, *script: bytes | Exception) -> tuple[ArquivoClient, ScriptedSession]:
        session = ScriptedSession(*script)
        self.addCleanup(lambda: self.assertEqual(list(session.script), []))
        return ArquivoClient(data_dir=self.root / "data" / "raw", session=session), session

    def write_candidates(self, *pairs: tuple[str, str]) -> None:
        output = self.root / "output"
        output.mkdir(parents=True, exist_ok=True)
        with (output / "corpus_text_retry_candidates.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(CANDIDATE_FIELDS))
            writer.writeheader()
            for url, tstamp in pairs:
                writer.writerow({
                    "original_url": url, "tstamp": tstamp,
                    "last_failure_category": "timeout_de_leitura",
                    "attempts_logged": "1", "status_code": "200",
                })

    def read_report(self) -> list[dict[str, str]]:
        path = self.root / "output" / "corpus_text_retry_report.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))


class ClassifyErrorTests(unittest.TestCase):
    def test_categories_match_the_log_analysis(self) -> None:
        self.assertEqual(classify_error(str(read_timeout())), "timeout_de_leitura")
        self.assertEqual(classify_error(str(connection_cut())), "ligacao_cortada")
        self.assertEqual(classify_error(str(not_found())), "http_404")
        self.assertEqual(
            classify_error(
                "HTTPSConnectionPool(host='arquivo.pt', port=443): Max retries "
                "exceeded (Caused by ConnectTimeoutError(..., 'Connection to "
                "arquivo.pt timed out. (connect timeout=10.0)'))"
            ),
            "timeout_de_ligacao",
        )
        self.assertEqual(
            classify_error("503 Server Error: Service Unavailable for url: x"),
            "outro_http",
        )
        self.assertEqual(classify_error("algo inesperado"), "outros")
        self.assertEqual(classify_error(None), "outros")


class RetryOneTests(RetryTestCase):
    def test_success_on_first_attempt_writes_the_text(self) -> None:
        client, session = self.make_client(b"texto sintetico")
        sleeps: list[float] = []

        result = retry_one(client, URL_A, TSTAMP_A, self.root, sleep=sleeps.append)

        self.assertEqual(result.outcome, OUTCOME_SUCCESS)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.cause, "")
        self.assertEqual(sleeps, [])
        self.assertTrue(session.calls[0].startswith("https://arquivo.pt/textextracted?m="))
        self.assertEqual((self.root / result.text_path).read_bytes(), b"texto sintetico")
        self.assertEqual(result.size_bytes, len(b"texto sintetico"))

    def test_success_after_transient_failures_uses_growing_backoff(self) -> None:
        client, session = self.make_client(read_timeout(), connection_cut(), b"texto")
        sleeps: list[float] = []

        result = retry_one(
            client, URL_A, TSTAMP_A, self.root, attempts=3, base_sleep=10.0,
            sleep=sleeps.append,
        )

        self.assertEqual(result.outcome, OUTCOME_SUCCESS)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(sleeps, [10.0, 20.0])
        self.assertTrue((self.root / result.text_path).is_file())

    def test_persistent_failure_is_recorded_with_its_cause(self) -> None:
        client, session = self.make_client(read_timeout(), read_timeout(), read_timeout())
        sleeps: list[float] = []

        result = retry_one(
            client, URL_A, TSTAMP_A, self.root, attempts=3, base_sleep=5.0,
            sleep=sleeps.append,
        )

        self.assertEqual(result.outcome, OUTCOME_FAILED)
        self.assertEqual(result.cause, "timeout_de_leitura")
        self.assertEqual(result.attempts, 3)
        self.assertIn("Read timed out", result.error)
        self.assertEqual(result.text_path, "")
        self.assertEqual(sleeps, [5.0, 10.0])
        self.assertFalse(any((self.root / "data" / "raw" / "texts").glob("*.txt")))

    def test_404_is_definitive_and_not_retried(self) -> None:
        client, session = self.make_client(not_found())
        sleeps: list[float] = []

        result = retry_one(client, URL_A, TSTAMP_A, self.root, attempts=3, sleep=sleeps.append)

        self.assertEqual(result.outcome, OUTCOME_FAILED)
        self.assertEqual(result.cause, "http_404")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(sleeps, [])

    def test_text_already_in_cache_needs_no_request(self) -> None:
        client, session = self.make_client()
        cached = client.texts_dir / ArquivoClient._text_filename(
            {"originalURL": URL_A, "tstamp": TSTAMP_A}
        )
        cached.write_bytes(b"ja existia")

        result = retry_one(client, URL_A, TSTAMP_A, self.root)

        self.assertEqual(result.outcome, OUTCOME_SUCCESS_CACHED)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(session.calls, [])
        self.assertEqual(cached.read_bytes(), b"ja existia")


class RunRetryTests(RetryTestCase):
    def test_reports_each_capture_incrementally(self) -> None:
        self.write_candidates((URL_A, TSTAMP_A), (URL_B, TSTAMP_B))
        client, _ = self.make_client(b"texto a", not_found())

        results = run_retry(self.root, client, sleep=lambda _: None)

        self.assertEqual([r.outcome for r in results], [OUTCOME_SUCCESS, OUTCOME_FAILED])
        rows = self.read_report()
        self.assertEqual([r["original_url"] for r in rows], [URL_A, URL_B])
        self.assertEqual(rows[1]["cause"], "http_404")
        summary = (self.root / "output" / "corpus_text_retry_summary.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Candidatas: 2", summary)
        self.assertIn("Recuperadas: 1", summary)

    def test_second_call_does_not_repeat_completed_captures(self) -> None:
        self.write_candidates((URL_A, TSTAMP_A), (URL_B, TSTAMP_B))
        first_client, _ = self.make_client(b"texto a", not_found())
        run_retry(self.root, first_client, sleep=lambda _: None)

        # Sem passos preparados: qualquer pedido nesta segunda chamada falha.
        second_client, second_session = self.make_client()
        results = run_retry(self.root, second_client, sleep=lambda _: None)

        self.assertEqual(second_session.calls, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(len(self.read_report()), 2)

    def test_resumes_after_an_interruption_with_only_the_missing_capture(self) -> None:
        # Primeira sessão "interrompida": só a primeira candidata ficou no relatório.
        self.write_candidates((URL_A, TSTAMP_A))
        first_client, _ = self.make_client(b"texto a")
        run_retry(self.root, first_client, sleep=lambda _: None)
        self.write_candidates((URL_A, TSTAMP_A), (URL_B, TSTAMP_B))

        second_client, second_session = self.make_client(b"texto b")
        results = run_retry(self.root, second_client, sleep=lambda _: None)

        self.assertEqual(len(second_session.calls), 1)
        self.assertEqual([r.original_url for r in results], [URL_A, URL_B])
        rows = self.read_report()
        self.assertEqual([r["original_url"] for r in rows], [URL_A, URL_B])
        self.assertEqual(
            set(load_already_attempted(self.root / "output" / "corpus_text_retry_report.csv")),
            {(URL_A, TSTAMP_A), (URL_B, TSTAMP_B)},
        )

    def test_does_not_touch_the_rdf_report_or_graph(self) -> None:
        self.write_candidates((URL_A, TSTAMP_A))
        sentinels = {
            self.root / "output" / "corpus_rdf_report.csv": b"original_url\nx\n",
            self.root / "output" / "corpus_articles.ttl": b"# grafo\n",
            self.root / "data" / "processed" / "corpus_articles_triples.nt": b"<a> <b> <c> .\n",
        }
        for path, content in sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        client, _ = self.make_client(b"texto a")

        run_retry(self.root, client, sleep=lambda _: None)

        for path, content in sentinels.items():
            self.assertEqual(path.read_bytes(), content, path.name)

    def test_missing_candidates_file_raises_a_clear_error(self) -> None:
        client, _ = self.make_client()
        with self.assertRaises(FileNotFoundError):
            run_retry(self.root, client)


if __name__ == "__main__":
    unittest.main()
