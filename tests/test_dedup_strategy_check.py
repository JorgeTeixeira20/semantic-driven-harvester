from __future__ import annotations

import csv
import json
from pathlib import Path

from semantic_harvester.corpus_rdf import url_hash16
from semantic_harvester.dedup_strategy_check import run

from tests.support import OfflineTestCase

URL_A = "http://a.test/art"
URL_B = "http://b.test/art"
URL_C = "http://c.test/art"


def write_version_history_raw(
    directory: Path, original_url: str, captures: list[dict[str, str]]
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    url_hash = url_hash16(original_url)
    path = directory / f"version_history_{url_hash}_all-all_offset-000000_max-50.json"
    response_items = [
        {"originalURL": original_url, "tstamp": c["tstamp"], "title": c["title"],
         "digest": c["digest"]}
        for c in captures
    ]
    payload = {"estimated_nr_results": len(response_items), "response_items": response_items}
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_classification_csv(path: Path, urls: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["original_url", "is_artigo"])
        writer.writeheader()
        for url in urls:
            writer.writerow({"original_url": url, "is_artigo": "True"})


def write_redundancy_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["artigo", "tstamp", "camada", "representante", "rotulo"]
        )
        writer.writeheader()
        writer.writerows(rows)


class DedupStrategyCheckTest(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.output_dir = self.root / "output"
        self.output_dir.mkdir()
        self.version_history_dir = self.root / "data" / "raw" / "version_history"

        # Artigo A: título igual -> duplicado real (TP para título); digest
        # diferente num duplicado real (FN para digest); digest igual em
        # capturas realmente distintas (FP para digest).
        write_version_history_raw(self.version_history_dir, URL_A, [
            {"tstamp": "1", "title": "T1", "digest": "D1"},
            {"tstamp": "2", "title": "T1", "digest": "D1"},
            {"tstamp": "3", "title": "T2", "digest": "D2"},
            {"tstamp": "4", "title": "T2", "digest": "D3"},
            {"tstamp": "5", "title": "T3", "digest": "D2"},
        ])
        # Artigo B: título igual em capturas distintas (FP para título);
        # título diferente num duplicado real (FN para título).
        write_version_history_raw(self.version_history_dir, URL_B, [
            {"tstamp": "1", "title": "X", "digest": "Dx"},
            {"tstamp": "2", "title": "X", "digest": "Dz"},
            {"tstamp": "3", "title": "Z", "digest": "Dz"},
        ])
        # Artigo C: título em falta num duplicado real (sem_dado para título).
        write_version_history_raw(self.version_history_dir, URL_C, [
            {"tstamp": "1", "title": "", "digest": "Dc1"},
            {"tstamp": "2", "title": "Something", "digest": "Dc1"},
        ])

        write_classification_csv(
            self.output_dir / "corpus_classification.csv", [URL_A, URL_B, URL_C]
        )
        write_redundancy_csv(self.output_dir / "corpus_redundancy.csv", [
            {"artigo": URL_A, "tstamp": "1", "camada": "1_texto", "representante": "1", "rotulo": "representante"},
            {"artigo": URL_A, "tstamp": "2", "camada": "1_texto", "representante": "1", "rotulo": "redundante"},
            {"artigo": URL_A, "tstamp": "3", "camada": "1_texto", "representante": "3", "rotulo": "representante"},
            {"artigo": URL_A, "tstamp": "4", "camada": "1_texto", "representante": "3", "rotulo": "redundante"},
            {"artigo": URL_A, "tstamp": "5", "camada": "1_texto", "representante": "5", "rotulo": "representante"},
            {"artigo": URL_B, "tstamp": "1", "camada": "1_texto", "representante": "1", "rotulo": "representante"},
            {"artigo": URL_B, "tstamp": "2", "camada": "1_texto", "representante": "2", "rotulo": "representante"},
            {"artigo": URL_B, "tstamp": "3", "camada": "1_texto", "representante": "2", "rotulo": "redundante"},
            {"artigo": URL_C, "tstamp": "1", "camada": "1_texto", "representante": "1", "rotulo": "representante"},
            {"artigo": URL_C, "tstamp": "2", "camada": "1_texto", "representante": "1", "rotulo": "redundante"},
        ])

    def test_title_and_digest_tallies_against_real_jaccard_labels(self) -> None:
        title_tally, digest_tally, duplicate_pairs, distinct_pairs = run(self.root)

        self.assertEqual(duplicate_pairs, 4)
        self.assertEqual(distinct_pairs, 3)

        self.assertEqual((title_tally.true_positive, title_tally.false_negative), (2, 1))
        self.assertEqual((title_tally.true_negative, title_tally.false_positive), (2, 1))
        self.assertEqual(title_tally.sem_dado, 1)
        self.assertAlmostEqual(title_tally.recall(), 2 / 3)
        self.assertAlmostEqual(title_tally.false_positive_rate(), 1 / 3)

        self.assertEqual((digest_tally.true_positive, digest_tally.false_negative), (3, 1))
        self.assertEqual((digest_tally.true_negative, digest_tally.false_positive), (2, 1))
        self.assertEqual(digest_tally.sem_dado, 0)
        self.assertAlmostEqual(digest_tally.recall(), 3 / 4)
        self.assertAlmostEqual(digest_tally.false_positive_rate(), 1 / 3)

        summary = (self.output_dir / "corpus_dedup_strategy_check.md").read_text(encoding="utf-8")
        self.assertIn("Título exato", summary)
        self.assertIn("66.7%", summary)
