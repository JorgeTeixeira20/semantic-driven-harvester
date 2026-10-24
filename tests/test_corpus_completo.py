"""Junção `por_ano` + `xl` em `completo` (`corpus_completo.py`), offline."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from semantic_harvester.corpus_completo import build, concat_csv, copy_triples, oldest_tstamps
from semantic_harvester.rdf_mapper import stable_hash
from tests.support import OfflineTestCase

P = "urn:semantic-driven-harvester:prototype:"
FIELDS = ("original_url", "title", "captures", "is_artigo", "reason", "variantes")
CAPTURE_FIELDS = ("original_url", "tstamp", "title", "facets", "queries",
                  "num_queries_matched", "divergent", "url_variants")

BOTH_PT = "https://record.pt/futebol/nacional/1a_liga/benfica/interior.aspx?content_id=100"
BOTH_XL = "https://record.xl.pt/futebol/nacional/1a_liga/benfica/interior.aspx?content_id=100"
BOTH2_PT = "https://record.pt/modalidades/judo/interior.aspx?content_id=200"
BOTH2_XL = "https://www.record.xl.pt/modalidades/judo/interior.aspx?content_id=200"
ONLY_PT = "https://record.pt/futebol/futebol-nacional/liga-nos/detalhe/a.html"
ONLY_XL = "https://record.xl.pt/futebol/nacional/1a_liga/porto/interior.aspx?content_id=300"


def triples(url: str, tstamp: str) -> str:
    h = stable_hash(url)
    return (
        f"<{P}article/{h}> <{P}temRecursoWeb> <{P}resource-web/{h}> .\n"
        f"<{P}resource-web/{h}> <{P}temCaptura> <{P}capture/{h}/{tstamp}> .\n"
        f"<{P}capture/{h}/{tstamp}> <{P}tstamp> \"{tstamp}\" .\n"
        f"<{P}capture/{h}/{tstamp}> <{P}temTextoExtraido> <{P}extracted-text/{h}/{tstamp}> .\n"
    )


def write_rows(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def cls(url: str, artigo: bool = True) -> dict:
    return {"original_url": url, "title": "t", "captures": "1", "is_artigo": str(artigo),
            "reason": "artigo" if artigo else "url_nao_artigo", "variantes": ""}


def cap(url: str, tstamp: str) -> dict:
    return {"original_url": url, "tstamp": tstamp, "title": "t", "facets": "modalidade",
            "queries": "futebol", "num_queries_matched": "1", "divergent": "False",
            "url_variants": ""}


class CompletoTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        out, data = self.root / "output", self.root / "data" / "processed"
        out.mkdir(parents=True)
        data.mkdir(parents=True)
        # BOTH: o `xl` tem a captura mais antiga; BOTH2: o `por_ano`.
        write_rows(out / "corpus_classification_por_ano.csv", FIELDS,
                   [cls(BOTH_PT), cls(BOTH2_PT), cls(ONLY_PT), cls("https://record.pt/x", False)])
        write_rows(out / "corpus_classification_xl.csv", FIELDS,
                   [cls(BOTH_XL), cls(BOTH2_XL), cls(ONLY_XL), cls("https://record.xl.pt/y", False)])
        (data / "corpus_articles_por_ano_triples.nt").write_text(
            triples(BOTH_PT, "20170101000000") + triples(BOTH2_PT, "20090101000000")
            + triples(ONLY_PT, "20180101000000"), encoding="utf-8")
        (data / "corpus_articles_xl_triples.nt").write_text(
            triples(BOTH_XL, "20150101000000") + triples(BOTH2_XL, "20100101000000")
            + triples(ONLY_XL, "20120101000000"), encoding="utf-8")
        write_rows(out / "corpus_phase1_por_ano_captures.csv", CAPTURE_FIELDS,
                   [cap(BOTH_PT, "20170101000000")])
        write_rows(out / "corpus_phase1_xl_captures.csv", CAPTURE_FIELDS,
                   [cap(BOTH_XL, "20150101000000"), cap(ONLY_XL, "20120101000000")])

    def test_each_article_once_with_the_oldest_capture(self) -> None:
        stats = build(self.root)

        text = (self.root / "data/processed/corpus_articles_completo_triples.nt").read_text("utf-8")
        for kept in (BOTH_XL, BOTH2_PT, ONLY_PT, ONLY_XL):
            self.assertIn(stable_hash(kept), text, kept)
        for dropped in (BOTH_PT, BOTH2_XL):
            self.assertNotIn(stable_hash(dropped), text, dropped)
        self.assertEqual((stats["sobreposicao"], stats["fica_xl"], stats["fica_por_ano"]), (2, 1, 1))
        self.assertEqual((stats["triplos_retirados_por_ano"], stats["triplos_retirados_xl"]), (4, 4))
        self.assertEqual(len(text.splitlines()), 4 * 4)

    def test_classification_has_one_row_per_article_and_keeps_the_others(self) -> None:
        stats = build(self.root)

        with (self.root / "output/corpus_classification_completo.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        artigos = {r["original_url"] for r in rows if r["is_artigo"] == "True"}
        self.assertEqual(artigos, {BOTH_XL, BOTH2_PT, ONLY_PT, ONLY_XL})
        self.assertEqual(stats["artigos"], 4)
        self.assertEqual(sum(1 for r in rows if r["is_artigo"] != "True"), 2)

    def test_captures_csv_is_the_concatenation(self) -> None:
        stats = build(self.root)

        self.assertEqual(stats["linhas_captures"], 3)
        with (self.root / "output/corpus_phase1_completo_captures.csv").open(encoding="utf-8") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 3)

    def test_source_corpora_are_not_modified(self) -> None:
        paths = [self.root / "data/processed/corpus_articles_por_ano_triples.nt",
                 self.root / "data/processed/corpus_articles_xl_triples.nt",
                 self.root / "output/corpus_classification_por_ano.csv"]
        before = [p.read_bytes() for p in paths]
        build(self.root)
        self.assertEqual([p.read_bytes() for p in paths], before)

    def test_xl_articles_no_longer_retained_by_the_classification_are_dropped(self) -> None:
        cover = "https://record.xl.pt/capas/detalhe/4-de-dezembro-de-2015.html"
        nt = self.root / "data/processed/corpus_articles_xl_triples.nt"
        nt.write_text(nt.read_text("utf-8") + triples(cover, "20151204181109"), encoding="utf-8")

        stats = build(self.root)

        text = (self.root / "data/processed/corpus_articles_completo_triples.nt").read_text("utf-8")
        self.assertNotIn(stable_hash(cover), text)
        self.assertEqual(stats["triplos_retirados_xl"], 4 + 4)

    def test_oldest_tstamps_and_copy_helpers(self) -> None:
        nt = self.root / "a.nt"
        nt.write_text(triples(ONLY_PT, "20180101000000") + triples(ONLY_PT, "20160101000000"), encoding="utf-8")
        h = stable_hash(ONLY_PT)
        self.assertEqual(oldest_tstamps(nt, {h}), {h: "20160101000000"})
        self.assertEqual(oldest_tstamps(nt, set()), {})
        target = self.root / "b.nt"
        with target.open("w", encoding="utf-8") as handle:
            self.assertEqual(copy_triples(nt, handle, {h}), (0, 8))

    def test_concat_csv_rejects_different_headers(self) -> None:
        a, b = self.root / "a.csv", self.root / "b.csv"
        write_rows(a, ("x",), [{"x": "1"}])
        write_rows(b, ("y",), [{"y": "1"}])
        with self.assertRaises(ValueError):
            concat_csv([a, b], self.root / "c.csv")


if __name__ == "__main__":
    unittest.main()
