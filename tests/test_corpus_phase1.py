"""Testes offline para a Fase 1 do Caminho A (`corpus_phase1.py`)."""

from __future__ import annotations

import json
import unittest

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_phase1 import (
    COMPETICOES, MODALIDADES, TERMS, collect_term_repetition,
)
from tests.support import OfflineTestCase


def page(items: list[dict], next_page: str | None) -> bytes:
    payload = {
        "estimated_nr_results": 999999,
        "next_page": next_page,
        "response_items": items,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def fake_item(n: int) -> dict:
    return {"originalURL": f"https://www.record.pt/artigo-{n}", "tstamp": f"2020010100{n:04d}"}


class PaginationIgnoresNextPageTests(OfflineTestCase):
    """Regressão (`docs/experiments.md`, 2026-10-19): nem `next_page` nem uma
    página incompleta são sinal fiável de fim; só uma página vazia confirma
    o fim real da recolha da Fase 1 (achado da enumeração de clubes e
    modalidades: página com 490-499 de 500 seguida de página cheia)."""

    def test_full_page_without_next_page_still_continues(self) -> None:
        full_page_without_next = page([fake_item(i) for i in range(50)], next_page=None)
        empty_page = page([], next_page="https://arquivo.pt/textsearch?offset=100")
        session = self.fixture_session(
            (ArquivoClient.SEARCH_URL, full_page_without_next),
            (ArquivoClient.SEARCH_URL, empty_page),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        items, raw_paths = collect_term_repetition(
            client, "modalidade", "futebol", 1, self.root / "raw" / "corpus_queries"
        )

        self.assertEqual(len(items), 50)
        self.assertEqual(len(raw_paths), 2)

    def test_incomplete_nonempty_page_does_not_stop_the_pagination(self) -> None:
        full_page = page([fake_item(i) for i in range(50)], next_page=None)
        incomplete_but_nonempty_page = page(
            [fake_item(50)], next_page="https://arquivo.pt/textsearch?offset=100",
        )
        empty_page = page([], next_page=None)
        session = self.fixture_session(
            (ArquivoClient.SEARCH_URL, full_page),
            (ArquivoClient.SEARCH_URL, incomplete_but_nonempty_page),
            (ArquivoClient.SEARCH_URL, empty_page),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        items, raw_paths = collect_term_repetition(
            client, "modalidade", "futebol", 1, self.root / "raw" / "corpus_queries"
        )

        self.assertEqual(len(items), 51)
        self.assertEqual(len(raw_paths), 3)

    def test_empty_page_stops_even_with_next_page_present(self) -> None:
        full_page = page(
            [fake_item(i) for i in range(50)], next_page="https://arquivo.pt/textsearch?offset=50",
        )
        empty_page_with_next = page([], next_page="https://arquivo.pt/textsearch?offset=100")
        session = self.fixture_session(
            (ArquivoClient.SEARCH_URL, full_page),
            (ArquivoClient.SEARCH_URL, empty_page_with_next),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        items, raw_paths = collect_term_repetition(
            client, "modalidade", "futebol", 1, self.root / "raw" / "corpus_queries"
        )

        self.assertEqual(len(items), 50)
        self.assertEqual(len(raw_paths), 2)


class ExpandedTermsTests(unittest.TestCase):
    """Alargamento de 2026-10-19 (`docs/experiments.md`): 11 termos novos,
    a partir de valores reais do vocabulário do Caminho B."""

    def test_includes_the_2026_10_19_additions(self) -> None:
        for termo in ("atletismo", "ciclismo", "judo", "motores", "natação"):
            self.assertIn(termo, MODALIDADES)
        self.assertEqual(
            COMPETICOES,
            ("2.ª Liga", "CAN", "Europeu", "Liga Jovem da UEFA",
             "Taça das Confederações", "Taça de Portugal"),
        )
        self.assertEqual(len(TERMS), 24)


if __name__ == "__main__":
    unittest.main()
