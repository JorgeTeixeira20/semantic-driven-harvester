"""Testes offline para a Fase 2 do Caminho A (`corpus_phase2.py`)."""

from __future__ import annotations

import json
from unittest.mock import patch

import requests

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_phase2 import (
    RATE_LIMIT_DEFAULT_WAIT_SECONDS, phase2_paths, run_phase2,
)
from tests.support import OfflineTestCase

URL = "https://www.record.pt/futebol/detalhe/jonas-renova"


def history_page(*tstamps: str) -> bytes:
    items = [{"originalURL": URL, "tstamp": tstamp} for tstamp in tstamps]
    return json.dumps({"next_page": None, "response_items": items}).encode("utf-8")


class LabelledRunTests(OfflineTestCase):
    """Com `label`, a execução não toca na Fase 2 original nem no raw de
    `data/raw/version_history/` do corpus de 125 artigos (2026-10-20)."""

    def test_labelled_run_writes_only_to_its_own_paths(self) -> None:
        output = self.root / "output"
        output.mkdir()
        captures_csv = output / "corpus_phase1_por_ano_captures.csv"
        captures_csv.write_text(f"original_url,tstamp\n{URL},1\n{URL},2\n", encoding="utf-8")
        original_history = output / "corpus_phase2_history.csv"
        original_history.write_text("original_url,captures,estimated_total,requests_made,error\n",
                                    encoding="utf-8")
        paths = phase2_paths(self.root, "por_ano")
        session = self.fixture_session((ArquivoClient.SEARCH_URL, history_page("1", "2", "3")))
        client = ArquivoClient(data_dir=paths["data_dir"], session=session)

        results = run_phase2(self.root, captures_csv, "por_ano", client=client)

        self.assertEqual([(r.original_url, r.captures, r.error) for r in results], [(URL, 3, None)])
        self.assertEqual(
            original_history.read_text("utf-8"),
            "original_url,captures,estimated_total,requests_made,error\n",
        )
        self.assertIn(URL, paths["history"].read_text("utf-8"))
        self.assertTrue(paths["summary"].is_file())
        raw = list((self.root / "data" / "raw" / "phase2_por_ano" / "version_history").iterdir())
        self.assertEqual(len(raw), 1)
        self.assertFalse((self.root / "data" / "raw" / "version_history").exists())

    def test_rerun_skips_articles_already_in_its_own_history(self) -> None:
        output = self.root / "output"
        output.mkdir()
        captures_csv = output / "captures.csv"
        captures_csv.write_text(f"original_url,tstamp\n{URL},1\n", encoding="utf-8")
        paths = phase2_paths(self.root, "por_ano")
        first = ArquivoClient(data_dir=paths["data_dir"],
                              session=self.fixture_session((ArquivoClient.SEARCH_URL, history_page("1"))))
        run_phase2(self.root, captures_csv, "por_ano", client=first)

        # Sessão sem respostas: qualquer pedido falharia a fixture.
        second = ArquivoClient(data_dir=paths["data_dir"], session=self.fixture_session())
        results = run_phase2(self.root, captures_csv, "por_ano", client=second)
        self.assertEqual(len(results), 1)


class RateLimitedResponse:
    def __init__(self, status: int, body: bytes, retry_after: str | None = None) -> None:
        self.status_code = status
        self.content = body
        self.headers = {"Retry-After": retry_after} if retry_after else {}

    def json(self) -> dict:
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)


class ScriptedSession:
    def __init__(self, *responses: RateLimitedResponse) -> None:
        self.responses = list(responses)
        self.headers: dict[str, str] = {}

    def get(self, url: str, **kwargs) -> RateLimitedResponse:
        return self.responses.pop(0)


class RateLimitTests(OfflineTestCase):
    """429 Too Many Requests (observado na Fase 2 de 2026-10-20): esperar e
    repetir sem gastar tentativas nem marcar o artigo como falhado."""

    def run_with(self, *responses: RateLimitedResponse):
        output = self.root / "output"
        output.mkdir()
        captures_csv = output / "captures.csv"
        captures_csv.write_text(f"original_url,tstamp\n{URL},1\n", encoding="utf-8")
        session = ScriptedSession(*responses)
        client = ArquivoClient(data_dir=self.root / "raw", session=session)
        with patch("semantic_harvester.corpus_phase2.time.sleep") as sleep:
            results = run_phase2(self.root, captures_csv, "por_ano", client=client)
        return results, sleep, session

    def test_429_waits_retry_after_and_then_succeeds(self) -> None:
        results, sleep, session = self.run_with(
            RateLimitedResponse(429, b"", retry_after="7"),
            RateLimitedResponse(429, b""),
            RateLimitedResponse(200, history_page("1", "2")),
        )
        self.assertEqual([(r.captures, r.error) for r in results], [(2, None)])
        self.assertEqual([call.args[0] for call in sleep.call_args_list],
                         [7.0, RATE_LIMIT_DEFAULT_WAIT_SECONDS])
        self.assertEqual(session.responses, [])

    def test_other_http_errors_still_use_the_normal_attempts(self) -> None:
        results, sleep, _ = self.run_with(*(RateLimitedResponse(500, b"") for _ in range(3)))
        self.assertIsNotNone(results[0].error)
        self.assertEqual(sleep.call_count, 2)
