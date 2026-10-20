"""Testes offline para a Fase 2 do Caminho A (`corpus_phase2.py`)."""

from __future__ import annotations

import json

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_phase2 import phase2_paths, run_phase2
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
