from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from semantic_harvester.corpus_redundancy import (
    LABEL_DIGEST_CANDIDATE, LABEL_DIGEST_CANDIDATE_MIXED, LABEL_KEPT_NO_TEXT,
    LABEL_PENDING, LABEL_REDUNDANT, LABEL_REPRESENTATIVE, LAYER_NO_TEXT,
    LAYER_NOT_EVALUABLE, LAYER_TEXT, Capture, Pair, annotate_article,
    assign_consecutive, assign_last_representative, jaccard, label_sample,
    load_corpus, normalize_text, run, sensitivity_table, word_set,
)
from semantic_harvester.rdf_mapper import (
    SDH, capture_uri, extracted_text_uri, resource_uri,
)
from tests.support import OfflineTestCase

ARTICLE = "https://news.example.test/articles/synthetic"


def words(start: int, stop: int) -> str:
    """Texto sintético com as palavras w<start> … w<stop-1>."""

    return " ".join(f"w{i}" for i in range(start, stop))


def capture(
    tstamp: str, text: str | None, digest: str = "D", length: int = 100,
    status: int = 200, article: str = ARTICLE,
) -> Capture:
    return Capture(article, tstamp, digest + tstamp if digest == "D" else digest,
                   length, status, text)


class SimilarityTests(unittest.TestCase):
    def test_normalization_unicode_case_and_spaces(self) -> None:
        decomposed = "Futébol  É\n\tbom"
        self.assertEqual(normalize_text(decomposed), "futébol é bom")
        self.assertEqual(word_set("Futébol é BOM"), word_set(decomposed))

    def test_identical_texts(self) -> None:
        self.assertEqual(jaccard(word_set(words(0, 50)), word_set(words(0, 50))), 1.0)

    def test_near_identical_texts(self) -> None:
        a = word_set(words(0, 100))
        b = word_set(words(0, 99) + " alterada")
        self.assertAlmostEqual(jaccard(a, b), 99 / 101)

    def test_different_texts(self) -> None:
        self.assertEqual(jaccard(word_set(words(0, 50)), word_set(words(50, 100))), 0.0)

    def test_empty_texts(self) -> None:
        self.assertEqual(jaccard(frozenset(), frozenset()), 1.0)


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        # A≈B e B≈C (95/105 ≈ 0,905), mas A≉C (90/110 ≈ 0,818) com limiar 0,9.
        self.chain = [word_set(words(0, 100)), word_set(words(5, 105)),
                      word_set(words(10, 110))]

    def test_chain_last_representative_does_not_merge_a_and_c(self) -> None:
        result = assign_last_representative(self.chain, 0.9)
        self.assertEqual([a.redundant for a in result], [False, True, False])
        self.assertEqual([a.representative for a in result], [0, 0, 2])
        self.assertAlmostEqual(result[2].similarity, 90 / 110)

    def test_chain_consecutive_merges_a_and_c(self) -> None:
        result = assign_consecutive(self.chain, 0.9)
        self.assertEqual([a.redundant for a in result], [False, True, True])
        self.assertEqual([a.representative for a in result], [0, 0, 0])

    def test_sensitivity_counts_both_strategies(self) -> None:
        (row,) = sensitivity_table({ARTICLE: self.chain}, thresholds=(0.9,))
        self.assertEqual(row.redundant_last_rep, 1)
        self.assertEqual(row.redundant_consecutive, 2)
        self.assertEqual(row.versions_last_rep, 2)
        self.assertEqual(row.versions_consecutive, 1)
        self.assertEqual(row.disagreements, 1)
        self.assertEqual(row.articles_with_redundant, 1)


class AnnotateArticleTests(unittest.TestCase):
    def test_identical_near_and_different(self) -> None:
        captures = [
            capture("1", words(0, 100)),
            capture("2", words(0, 100)),
            capture("3", words(0, 99) + " alterada"),
            capture("4", words(200, 300)),
        ]
        rows = annotate_article(captures, threshold=0.9)
        self.assertEqual([r["camada"] for r in rows], [LAYER_TEXT] * 4)
        self.assertEqual(
            [r["rotulo"] for r in rows],
            [LABEL_REPRESENTATIVE, LABEL_REDUNDANT, LABEL_REDUNDANT, LABEL_REPRESENTATIVE],
        )
        self.assertEqual([r["representante"] for r in rows], ["1", "1", "1", "4"])
        self.assertEqual(rows[1]["similaridade"], "1.000000")
        self.assertEqual(rows[0]["similaridade"], "")

    def test_single_capture_article(self) -> None:
        (row,) = annotate_article([capture("1", words(0, 10))], threshold=0.9)
        self.assertEqual(row["camada"], LAYER_TEXT)
        self.assertEqual(row["rotulo"], LABEL_REPRESENTATIVE)
        self.assertEqual(row["representante"], "1")
        self.assertEqual(row["sim_consecutiva"], "")

    def test_article_without_any_text_is_not_evaluable(self) -> None:
        rows = annotate_article(
            [capture("1", None), capture("2", None)], threshold=0.9
        )
        self.assertEqual([r["camada"] for r in rows], [LAYER_NOT_EVALUABLE] * 2)
        self.assertEqual([r["rotulo"] for r in rows], [LABEL_KEPT_NO_TEXT] * 2)
        self.assertEqual([r["tem_texto"] for r in rows], ["False", "False"])

    def test_capture_without_text_between_two_with_text(self) -> None:
        rows = annotate_article(
            [capture("1", words(0, 100)), capture("2", None), capture("3", words(0, 100))],
            threshold=0.9,
        )
        self.assertEqual([r["camada"] for r in rows], [LAYER_TEXT, LAYER_NO_TEXT, LAYER_TEXT])
        self.assertEqual(rows[1]["rotulo"], LABEL_KEPT_NO_TEXT)
        self.assertEqual(rows[1]["representante"], "")
        # As duas com texto são comparadas diretamente, saltando a do meio.
        self.assertEqual(rows[2]["sim_consecutiva"], "1.000000")
        self.assertEqual(rows[2]["representante"], "1")
        self.assertEqual(rows[2]["rotulo"], LABEL_REDUNDANT)

    def test_status_not_200_with_text_stays_in_layer2(self) -> None:
        rows = annotate_article(
            [capture("1", words(0, 10)), capture("2", words(0, 10), status=404)],
            threshold=0.9,
        )
        self.assertEqual([r["camada"] for r in rows], [LAYER_TEXT, LAYER_NO_TEXT])
        self.assertEqual(rows[1]["tem_texto"], "True")

    def test_digest_group_without_text_is_annotated_not_removed(self) -> None:
        captures = [
            capture("1", words(0, 10)),
            capture("2", None, digest="X", length=50),
            capture("3", None, digest="X", length=50),
            capture("4", None, digest="X", length=50),
            capture("5", None, digest="X", length=51),  # contentLength diferente
        ]
        rows = annotate_article(captures, threshold=0.9)
        self.assertEqual(len(rows), 5)
        self.assertEqual(
            [r["rotulo"] for r in rows[1:]],
            [LABEL_KEPT_NO_TEXT, LABEL_DIGEST_CANDIDATE, LABEL_DIGEST_CANDIDATE,
             LABEL_KEPT_NO_TEXT],
        )
        self.assertEqual([r["grupo_digest"] for r in rows[1:4]], ["X|50"] * 3)
        self.assertEqual(rows[4]["grupo_digest"], "")
        self.assertEqual({r["camada"] for r in rows[1:]}, {LAYER_NO_TEXT})

    def test_mixed_digest_group(self) -> None:
        rows = annotate_article(
            [capture("1", words(0, 10), digest="Y", length=7),
             capture("2", None, digest="Y", length=7)],
            threshold=0.9,
        )
        self.assertEqual(rows[0]["rotulo"], LABEL_REPRESENTATIVE)
        self.assertEqual(rows[0]["grupo_digest"], "")
        self.assertEqual(rows[1]["rotulo"], LABEL_DIGEST_CANDIDATE_MIXED)

    def test_without_threshold_layer1_is_pending(self) -> None:
        rows = annotate_article(
            [capture("1", words(0, 100)), capture("2", words(0, 100))], threshold=None
        )
        self.assertEqual([r["rotulo"] for r in rows], [LABEL_REPRESENTATIVE, LABEL_PENDING])
        self.assertEqual(rows[1]["representante"], "")
        self.assertEqual(rows[1]["similaridade"], "")
        self.assertEqual(rows[1]["sim_consecutiva"], "1.000000")
        self.assertEqual(rows[1]["limiar"], "")


class LabelSampleTests(unittest.TestCase):
    def test_sample_spreads_over_bands_and_is_deterministic(self) -> None:
        values = [0.3, 0.4, 0.5, 0.72, 0.8, 0.88, 0.91, 0.97, 1.0, 1.0, 1.0, 1.0]
        pairs = [Pair(ARTICLE, str(i), str(i + 1), v, [], []) for i, v in enumerate(values)]
        sample = label_sample(pairs, per_band=3, seed=0)
        self.assertEqual(sample, label_sample(pairs, per_band=3, seed=0))
        by_band: dict[str, list[float]] = {}
        for band, pair in sample:
            by_band.setdefault(band, []).append(pair.similarity)
        self.assertEqual(sorted(by_band), ["alta", "baixa", "media"])
        self.assertEqual({k: len(v) for k, v in by_band.items()},
                         {"baixa": 3, "media": 3, "alta": 3})
        # A faixa alta não fica só com 1,0: inclui as sub-faixas 0,90 e 0,95.
        self.assertIn(0.91, by_band["alta"])
        self.assertIn(0.97, by_band["alta"])


class RunOnSyntheticCorpusTests(OfflineTestCase):
    def _write_corpus(self) -> Path:
        graph = Graph()
        texts_dir = self.root / "data" / "raw" / "texts"
        texts_dir.mkdir(parents=True)
        spec = {
            ARTICLE: [("20200101000000", words(0, 100), "A"),
                      ("20200102000000", None, "B"),
                      ("20200103000000", words(0, 100), "C")],
            ARTICLE + "-sem-texto": [("20200101000000", None, "Z")],
        }
        for url, captures in spec.items():
            resource = resource_uri(url)
            graph.add((resource, RDF.type, SDH.RecursoWeb))
            graph.add((resource, SDH.originalURL, Literal(url, datatype=XSD.anyURI)))
            for tstamp, text, digest in captures:
                node = capture_uri(url, tstamp)
                graph.add((resource, SDH.temCaptura, node))
                graph.add((node, RDF.type, SDH.CapturaArquivada))
                graph.add((node, SDH.tstamp, Literal(tstamp, datatype=XSD.string)))
                graph.add((node, SDH.digest, Literal(digest, datatype=XSD.string)))
                graph.add((node, SDH.contentLength,
                           Literal(10, datatype=XSD.nonNegativeInteger)))
                graph.add((node, SDH.statusCode, Literal(200, datatype=XSD.integer)))
                if text is not None:
                    path = texts_dir / f"{tstamp}_{len(url)}.txt"
                    path.write_text(text, encoding="utf-8")
                    text_node = extracted_text_uri(url, tstamp)
                    graph.add((node, SDH.temTextoExtraido, text_node))
                    graph.add((text_node, RDF.type, SDH.TextoExtraido))
                    graph.add((text_node, SDH.filePath, Literal(
                        str(path.relative_to(self.root)), datatype=XSD.string)))
        ttl = self.root / "output" / "corpus_articles.ttl"
        ttl.parent.mkdir(parents=True)
        graph.serialize(destination=ttl, format="turtle")
        return ttl

    def test_load_corpus_orders_by_tstamp(self) -> None:
        ttl = self._write_corpus()
        corpus = load_corpus(ttl, self.root)
        self.assertEqual([c.tstamp for c in corpus[ARTICLE]],
                         ["20200101000000", "20200102000000", "20200103000000"])
        self.assertEqual([c.has_text for c in corpus[ARTICLE]], [True, False, True])

    def test_run_is_non_destructive_and_writes_outputs(self) -> None:
        ttl = self._write_corpus()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

        rows, sensitivity, sample = run(self.root, threshold=None)

        after = {p: p.read_bytes() for p in before}
        self.assertEqual(before, after)
        self.assertEqual(len(rows), 4)
        with (self.root / "output" / "corpus_redundancy.csv").open(encoding="utf-8") as h:
            csv_rows = list(csv.DictReader(h))
        self.assertEqual(len(csv_rows), 4)
        self.assertEqual(
            sorted(r["camada"] for r in csv_rows),
            sorted([LAYER_TEXT, LAYER_NO_TEXT, LAYER_TEXT, LAYER_NOT_EVALUABLE]),
        )
        self.assertEqual(len(sample), 1)
        self.assertEqual(sample[0][0], "alta")
        summary = (self.root / "output" / "corpus_redundancy_summary.md").read_text("utf-8")
        self.assertIn("pendente de rotulagem manual", summary)
        self.assertTrue((self.root / "output" / "corpus_redundancy_label_sample.csv").is_file())
        self.assertTrue(ttl.is_file())
        self.assertEqual(sensitivity[-1].redundant_last_rep, 1)


if __name__ == "__main__":
    unittest.main()
