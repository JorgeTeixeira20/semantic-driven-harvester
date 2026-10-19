"""Testes offline para a Fase 1 do Caminho A (`corpus_phase1.py`)."""

from __future__ import annotations

import json
import unittest

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_phase1 import (
    ATLETAS, CLUBES, COMPETICOES, MODALIDADES, RUN_LABEL, TERMS, collect_term_repetition,
    slugify,
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
    """Regressão (`docs/experiments.md`, 2026-10-19): `next_page` não é um
    sinal fiável de fim mesmo a grande escala; só página incompleta/vazia
    deve parar a recolha da Fase 1."""

    def test_full_page_without_next_page_still_continues(self) -> None:
        full_page_without_next = page([fake_item(i) for i in range(50)], next_page=None)
        incomplete_page = page([fake_item(50)], next_page="https://arquivo.pt/textsearch?offset=100")
        session = self.fixture_session(
            (ArquivoClient.SEARCH_URL, full_page_without_next),
            (ArquivoClient.SEARCH_URL, incomplete_page),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        items, raw_paths = collect_term_repetition(
            client, "modalidade", "futebol", 1, self.root / "raw" / "corpus_queries"
        )

        self.assertEqual(len(items), 51)
        self.assertEqual(len(raw_paths), 2)

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


class FinalTermsTests(unittest.TestCase):
    """Lista final de 2026-10-19 (`docs/experiments.md`): valores reais da
    enumeração por URL, com as decisões do autor sobre os casos ambíguos."""

    def test_totals_per_facet(self) -> None:
        self.assertEqual(
            (len(MODALIDADES), len(CLUBES), len(ATLETAS), len(COMPETICOES), len(TERMS)),
            (39, 57, 5, 7, 108),
        )

    def test_no_duplicate_terms_or_raw_file_slugs(self) -> None:
        self.assertEqual(len({query.casefold() for _, query in TERMS}), len(TERMS))
        self.assertEqual(len({(facet, slugify(query)) for facet, query in TERMS}), len(TERMS))

    def test_ambiguous_cases_follow_the_authors_decisions(self) -> None:
        for excluded in ("outras", "record-pela-patagonia", "aventura-em-mocambique"):
            self.assertNotIn(excluded, MODALIDADES)
        self.assertNotIn("campeao", {slugify(club) for club in CLUBES})
        self.assertIn("Académico de Viseu", CLUBES)
        self.assertIn("Belenenses SAD", CLUBES)
        self.assertIn("Liga NOS", COMPETICOES)

    def test_athletes_stay_as_a_small_discovery_facet(self) -> None:
        self.assertEqual(
            ATLETAS,
            ("Cristiano Ronaldo", "Bruno Fernandes", "Telma Monteiro", "João Félix",
             "Nelson Évora"),
        )

    def test_run_does_not_overwrite_the_original_phase1(self) -> None:
        # A Fase 1 original (corpus de 125 artigos) está em
        # data/raw/corpus_queries/ e output/corpus_phase1_*.{csv,md}.
        self.assertTrue(RUN_LABEL)
        self.assertNotIn(RUN_LABEL, ("per_term", "captures", "aggregation"))


if __name__ == "__main__":
    unittest.main()
