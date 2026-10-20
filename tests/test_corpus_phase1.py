"""Testes offline para a Fase 1 do Caminho A (`corpus_phase1.py`)."""

from __future__ import annotations

import json
import unittest

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_phase1 import (
    ATLETAS, CLUBES, COMPETICOES, MAX_PAGES_PER_TERM, MODALIDADES, REPETITIONS, RUN_LABEL,
    RUN_LABEL as LABEL, TERMS, YEARS, aggregate, collect_term_year, rebuild_offline,
    records_from_raw, representative_urls, slugify, year_bounds,
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


BASE = "https://www.record.pt/futebol/detalhe/jonas-renova"


def hit(url: str, tstamp: str, **extra) -> dict:
    return {"originalURL": url, "tstamp": tstamp, "title": "Jonas", **extra}


class NormalizedAggregationTests(unittest.TestCase):
    """Variantes do mesmo `originalURL` (`url_identity.normalize_for_grouping`)
    contam como um só artigo; ver `docs/experiments.md`, 2026-10-20."""

    def test_variants_merge_into_one_representative(self) -> None:
        records = [
            ("clube", "Benfica", hit("http://www.record.pt/futebol/detalhe/jonas-renova", "1")),
            ("clube", "Benfica", hit(BASE + "?ref=HP_A", "2")),
            ("clube", "Benfica", hit("https://www.record.pt//futebol/detalhe/jonas-renova/", "3")),
            ("atleta", "Jonas", hit(BASE, "4")),
            ("atleta", "Jonas", hit(BASE + "?utm_source=x", "4")),
        ]
        url_map = representative_urls(records)
        self.assertEqual(set(url_map.values()), {BASE})

        captures, divergent = aggregate(records, url_map)
        self.assertEqual({url for url, _ in captures}, {BASE})
        self.assertEqual(len(captures), 4)  # tstamps 1, 2, 3, 4
        self.assertEqual(captures[(BASE, "4")].facets, {"atleta"})
        self.assertEqual(captures[(BASE, "4")].variants, {BASE, BASE + "?utm_source=x"})
        # Itens de variantes diferem no URL por construção: não é divergência.
        self.assertEqual(divergent, [])

    def test_old_site_content_ids_are_not_merged(self) -> None:
        old = "http://www.record.pt/Futebol/interior.aspx?content_id/x3d"
        records = [("clube", "Benfica", hit(old + "1", "1")),
                   ("clube", "Benfica", hit(old + "2", "1"))]
        self.assertEqual(len(set(representative_urls(records).values())), 2)

    def test_representative_prefers_clean_https_then_most_captures(self) -> None:
        http = "http://www.record.pt/futebol/detalhe/x"
        records = [("clube", "Benfica", hit(http, t)) for t in "123"]
        records.append(("clube", "Benfica", hit("https://www.record.pt/futebol/detalhe/x", "4")))
        self.assertEqual(set(representative_urls(records).values()),
                         {"https://www.record.pt/futebol/detalhe/x"})


class RebuildOfflineTests(OfflineTestCase):
    def write_raw(self, name: str, items: list[dict]) -> None:
        raw_dir = self.root / "data" / "raw" / "corpus_queries" / LABEL
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / name).write_bytes(page(items, next_page=None))

    def test_rebuild_reads_raw_without_network_and_keeps_the_old_csv_once(self) -> None:
        self.write_raw("clube_benfica_2017_rep1_offset-0000.json",
                       [hit(BASE, "1"), hit(BASE + "?ref=x", "2")])
        self.write_raw("clube_benfica_2017_rep1_offset-0050.json", [])
        self.write_raw("atleta_joao-felix_2018_rep1_offset-0000.json", [hit(BASE + "/", "3")])
        output = self.root / "output"
        output.mkdir()
        old_csv = output / f"corpus_phase1_{LABEL}_captures.csv"
        old_csv.write_text("antigo\n", encoding="utf-8")

        stats, captures, _ = rebuild_offline(self.root)

        self.assertEqual({url for url, _ in captures}, {BASE})
        self.assertEqual(
            [(r.facet, r.query, r.year, r.requests_made, r.results_received) for r in stats],
            [("clube", "Benfica", 2017, 2, 2), ("atleta", "João Félix", 2018, 1, 1)],
        )
        backup = output / f"corpus_phase1_{LABEL}_captures.pre-normalizacao.csv"
        self.assertEqual(backup.read_text("utf-8"), "antigo\n")
        rebuild_offline(self.root)  # segunda vez: não reescreve a cópia
        self.assertEqual(backup.read_text("utf-8"), "antigo\n")
        summary = (output / f"corpus_phase1_{LABEL}_aggregation.md").read_text("utf-8")
        self.assertIn("`originalURL` distintos tal como vieram da API: 3", summary)
        self.assertIn("(2 variantes juntadas)", summary)

    def test_unknown_term_in_raw_fails(self) -> None:
        self.write_raw("clube_desconhecido_2017_rep1_offset-0000.json", [])
        with self.assertRaises(ValueError):
            records_from_raw(self.root / "data" / "raw" / "corpus_queries" / LABEL)


if __name__ == "__main__":
    unittest.main()
