"""Testes offline para a Fase 1 do Caminho A (`corpus_phase1.py`)."""

from __future__ import annotations

import json
import unittest

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_phase1 import (
    ATLETAS, CLUBES, COMPETICOES, MAX_PAGES_PER_TERM, MODALIDADES, REPETITIONS, RUN_LABEL,
    TERMS, YEARS, collect_term_year, slugify, year_bounds,
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


def sent_params(call: tuple[str, dict]) -> dict[str, list]:
    params: dict[str, list] = {}
    for key, value in call[1]["params"]:
        params.setdefault(key, []).append(value)
    return params


class CollectTermYearTests(OfflineTestCase):
    """Recolha ano a ano (`docs/experiments.md`, 2026-10-19): datas de 14
    dígitos, paragem só na primeira página vazia, ano no nome do raw."""

    def collect(self, *pages: bytes, year: int = 2020):
        session = self.fixture_session(*((ArquivoClient.SEARCH_URL, body) for body in pages))
        client = ArquivoClient(data_dir=self.root / "raw", session=session)
        items, raw_paths = collect_term_year(
            client, "modalidade", "futebol", year, self.root / "raw" / "corpus_queries"
        )
        return items, raw_paths, session

    def test_year_bounds_use_full_14_digit_timestamps(self) -> None:
        self.assertEqual(year_bounds(2020), ("20200101000000", "20201231235959"))

    def test_sends_the_whole_year_and_not_the_bare_year(self) -> None:
        _, _, session = self.collect(page([], next_page=None))
        params = sent_params(session.calls[0])
        self.assertEqual(params["from"], ["20200101000000"])
        self.assertEqual(params["to"], ["20201231235959"])

    def test_incomplete_page_does_not_stop_only_an_empty_page_does(self) -> None:
        items, raw_paths, session = self.collect(
            page([fake_item(i) for i in range(50)], next_page=None),
            page([fake_item(i) for i in range(50, 98)], next_page=None),
            page([fake_item(i) for i in range(98, 148)], next_page=None),
            page([], next_page="https://arquivo.pt/textsearch?offset=150"),
        )
        self.assertEqual(len(items), 148)
        self.assertEqual(len(raw_paths), 4)
        self.assertEqual([sent_params(call)["offset"] for call in session.calls],
                         [[0], [50], [100], [150]])

    def test_stops_at_the_page_cap(self) -> None:
        pages = [page([fake_item(50 * n + i) for i in range(50)], next_page=None)
                 for n in range(MAX_PAGES_PER_TERM)]
        items, raw_paths, _ = self.collect(*pages)
        self.assertEqual(len(items), 50 * MAX_PAGES_PER_TERM)
        self.assertEqual(len(raw_paths), MAX_PAGES_PER_TERM)

    def test_raw_file_names_include_the_year(self) -> None:
        _, paths_2007, _ = self.collect(page([], next_page=None), year=2007)
        _, paths_2008, _ = self.collect(page([], next_page=None), year=2008)
        self.assertEqual(paths_2007[0].name, "modalidade_futebol_2007_rep1_offset-0000.json")
        self.assertNotEqual(paths_2007[0], paths_2008[0])

    def test_existing_raw_is_reused_without_a_request(self) -> None:
        raw_dir = self.root / "raw" / "corpus_queries"
        raw_dir.mkdir(parents=True)
        (raw_dir / "modalidade_futebol_2020_rep1_offset-0000.json").write_bytes(
            page([fake_item(1)], next_page=None)
        )
        items, raw_paths, session = self.collect(page([], next_page=None))
        self.assertEqual(len(items), 1)
        self.assertEqual(len(raw_paths), 2)
        self.assertEqual([sent_params(call)["offset"] for call in session.calls], [[50]])


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

    def test_run_does_not_overwrite_previous_phase1_runs(self) -> None:
        # Original (corpus de 125 artigos): data/raw/corpus_queries/ e
        # output/corpus_phase1_*; alargada: .../alargada/ e *_alargada_*.
        self.assertNotIn(RUN_LABEL, ("", "alargada", "per_term", "captures", "aggregation"))

    def test_one_repetition_per_year_from_1999_to_2026(self) -> None:
        self.assertEqual(REPETITIONS, 1)
        self.assertEqual((YEARS[0], YEARS[-1], len(YEARS)), (1999, 2026, 28))


if __name__ == "__main__":
    unittest.main()
