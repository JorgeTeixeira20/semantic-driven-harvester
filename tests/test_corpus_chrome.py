from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from semantic_harvester.corpus_chrome import (
    LABEL_CHANGED, LABEL_SAME, article_frequency, chrome_ngrams,
    errors_by_threshold, frequency_buckets, min_articles, ngrams, run,
    separation, strip_chrome, tokens,
)
from semantic_harvester.rdf_mapper import (
    SDH, capture_uri, extracted_text_uri, resource_uri,
)
from tests.support import OfflineTestCase

MENU = "menu record login assinar epaper notícias opinião futebol modalidades"


def words(prefix: str, count: int) -> str:
    """Texto sintético específico de um artigo: <prefix>0 … <prefix>(count-1)."""

    return " ".join(f"{prefix}{i}" for i in range(count))


class NgramTests(unittest.TestCase):
    def test_tokens_use_the_same_normalization(self) -> None:
        self.assertEqual(tokens("Futébol,  É bom!"), ["futébol", "é", "bom"])

    def test_ngrams(self) -> None:
        self.assertEqual(ngrams(["a", "b", "c", "d"], 3), {("a", "b", "c"), ("b", "c", "d")})
        self.assertEqual(ngrams(["a", "b"], 3), set())


class ArticleFrequencyTests(unittest.TestCase):
    def test_counts_distinct_articles_not_captures(self) -> None:
        corpus = {
            # Um artigo muito capturado: o seu texto aparece em 5 capturas.
            "a": [tokens(words("x", 6))] * 5,
            "b": [tokens(words("y", 6))],
        }
        frequency = article_frequency(corpus, 3)
        self.assertEqual(frequency[("x0", "x1", "x2")], 1)

    def test_shared_ngram_counts_once_per_article(self) -> None:
        corpus = {
            "a": [tokens(MENU + " " + words("x", 5)), tokens(MENU)],
            "b": [tokens(MENU + " " + words("y", 5))],
            "c": [tokens(words("z", 5))],
        }
        frequency = article_frequency(corpus, 3)
        self.assertEqual(frequency[("menu", "record", "login")], 2)


class ChromeSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        # MENU em 8 de 10 artigos; cada artigo tem também texto próprio.
        self.corpus = {
            f"art{i}": [tokens((MENU + " " if i < 8 else "") + words(f"p{i}_", 20))]
            for i in range(10)
        }
        self.frequency = article_frequency(self.corpus, 3)

    def test_ngram_in_many_articles_is_chrome(self) -> None:
        chrome = chrome_ngrams(self.frequency, 10, 0.5)
        self.assertIn(("menu", "record", "login"), chrome)

    def test_article_specific_ngram_is_not_chrome(self) -> None:
        chrome = chrome_ngrams(self.frequency, 10, 0.5)
        self.assertNotIn(("p3_0", "p3_1", "p3_2"), chrome)

    def test_fraction_above_frequency_keeps_the_menu(self) -> None:
        chrome = chrome_ngrams(self.frequency, 10, 0.9)
        self.assertNotIn(("menu", "record", "login"), chrome)

    def test_minimum_of_two_articles_even_with_tiny_fraction(self) -> None:
        self.assertEqual(min_articles(0.001, 125), 2)
        chrome = chrome_ngrams(self.frequency, 10, 0.001)
        self.assertNotIn(("p3_0", "p3_1", "p3_2"), chrome)

    def test_min_articles_rounds_up(self) -> None:
        self.assertEqual(min_articles(0.05, 125), 7)

    def test_buckets_cover_every_ngram(self) -> None:
        buckets = frequency_buckets(self.frequency, 10)
        self.assertEqual(sum(count for _, count in buckets), len(self.frequency))
        self.assertIn(("6–10", len(ngrams(tokens(MENU), 3))), buckets)
        self.assertEqual(buckets[-1][0], "6–10")


class StripChromeTests(unittest.TestCase):
    def test_removes_covered_words_only(self) -> None:
        text = tokens(MENU + " o jogador marcou dois golos")
        chrome = ngrams(tokens(MENU), 3)
        self.assertEqual(strip_chrome(text, chrome, 3), ["o", "jogador", "marcou", "dois", "golos"])

    def test_article_text_untouched_when_no_chrome(self) -> None:
        text = tokens(words("x", 10))
        self.assertEqual(strip_chrome(text, set(), 3), text)

    def test_isolated_shared_word_is_kept(self) -> None:
        # "record" está no chrome dentro do menu, mas aqui aparece isolada.
        chrome = ngrams(tokens(MENU), 3)
        self.assertEqual(strip_chrome(tokens("o record noticiou"), chrome, 3),
                         ["o", "record", "noticiou"])

    def test_text_shorter_than_n(self) -> None:
        self.assertEqual(strip_chrome(["a", "b"], {("a", "b", "c")}, 3), ["a", "b"])


class SeparationTests(unittest.TestCase):
    def test_clean_separation(self) -> None:
        labelled = [("1", LABEL_SAME, 0.95), ("2", LABEL_SAME, 1.0), ("3", LABEL_CHANGED, 0.6)]
        result = separation(labelled)
        self.assertTrue(result.clean)
        self.assertEqual(result.ambiguous, [])

    def test_overlap_lists_ambiguous_pairs(self) -> None:
        labelled = [("1", LABEL_SAME, 0.5), ("2", LABEL_SAME, 0.9),
                    ("3", LABEL_CHANGED, 0.7), ("4", LABEL_CHANGED, 0.3)]
        result = separation(labelled)
        self.assertFalse(result.clean)
        self.assertEqual(result.ambiguous, [("1", LABEL_SAME, 0.5), ("3", LABEL_CHANGED, 0.7)])

    def test_errors_by_threshold(self) -> None:
        labelled = [("1", LABEL_SAME, 0.5), ("2", LABEL_SAME, 0.9), ("3", LABEL_CHANGED, 0.7)]
        self.assertEqual(errors_by_threshold(labelled, (0.6, 0.8)), [(0.6, 1, 1), (0.8, 1, 0)])


class RunOnSyntheticCorpusTests(OfflineTestCase):
    """Artigo com duas capturas que só diferem nas manchetes do dia (chrome)."""

    def _write(self) -> None:
        graph = Graph()
        texts_dir = self.root / "data" / "raw" / "texts"
        texts_dir.mkdir(parents=True)
        headlines_1 = "manchete um sobre benfica e sporting hoje"
        headlines_2 = "manchete dois sobre porto e braga amanhã"
        spec = {
            # Artigo avaliado: mesmo corpo, manchetes diferentes.
            "https://news.example.test/a": [
                ("20200101000000", f"{MENU} {headlines_1} {words('a', 30)}"),
                ("20200102000000", f"{MENU} {headlines_2} {words('a', 30)}"),
            ],
            # Artigo com texto alterado.
            "https://news.example.test/b": [
                ("20200101000000", f"{MENU} {headlines_1} {words('b', 30)}"),
                ("20200102000000", f"{MENU} {headlines_2} {words('c', 30)}"),
            ],
        }
        # Outros artigos que partilham o menu e as manchetes (para serem chrome).
        for i in range(6):
            spec[f"https://news.example.test/o{i}"] = [
                ("20200101000000", f"{MENU} {headlines_1 if i % 2 else headlines_2} "
                                   f"{words(f'o{i}_', 30)}"),
            ]
        for url, captures in spec.items():
            resource = resource_uri(url)
            graph.add((resource, RDF.type, SDH.RecursoWeb))
            graph.add((resource, SDH.originalURL, Literal(url, datatype=XSD.anyURI)))
            for tstamp, text in captures:
                node = capture_uri(url, tstamp)
                graph.add((resource, SDH.temCaptura, node))
                graph.add((node, SDH.tstamp, Literal(tstamp)))
                graph.add((node, SDH.digest, Literal("D" + tstamp)))
                graph.add((node, SDH.contentLength, Literal(10, datatype=XSD.nonNegativeInteger)))
                graph.add((node, SDH.statusCode, Literal(200, datatype=XSD.integer)))
                path = texts_dir / f"{tstamp}_{url.rsplit('/', 1)[-1]}.txt"
                path.write_text(text, encoding="utf-8")
                text_node = extracted_text_uri(url, tstamp)
                graph.add((node, SDH.temTextoExtraido, text_node))
                graph.add((text_node, SDH.filePath, Literal(str(path.relative_to(self.root)))))
        (self.root / "output").mkdir()
        graph.serialize(destination=self.root / "output" / "corpus_articles.ttl", format="turtle")
        fields = ["par_id", "faixa", "artigo", "tstamp_a", "tstamp_b", "similaridade",
                  "n_palavras_so_a", "n_palavras_so_b", "palavras_so_a", "palavras_so_b",
                  "rotulo_manual", "notas"]
        with (self.root / "output" / "corpus_redundancy_label_sample.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for pid, url, label in (("1", "https://news.example.test/a", LABEL_SAME),
                                    ("2", "https://news.example.test/b", LABEL_CHANGED)):
                writer.writerow({"par_id": pid, "faixa": "baixa", "artigo": url,
                                 "tstamp_a": "20200101000000", "tstamp_b": "20200102000000",
                                 "similaridade": "0.5", "rotulo_manual": label})

    def test_distribution_only_does_not_evaluate(self) -> None:
        self._write()
        self.assertIsNone(run(self.root, n=3, fraction=None))
        summary = (self.root / "output" / "corpus_chrome_summary.md").read_text("utf-8")
        self.assertIn("Fração de corte ainda não escolhida", summary)
        self.assertFalse((self.root / "output" / "corpus_chrome_label_eval.csv").exists())

    def test_chrome_removal_separates_labels_and_is_non_destructive(self) -> None:
        self._write()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

        result = run(self.root, n=3, fraction=0.4)

        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        sims = {pid: s for pid, _, s in result["labelled"]}
        self.assertEqual(sims["1"], 1.0)
        self.assertEqual(sims["2"], 0.0)
        self.assertTrue(result["separation"].clean)
        with (self.root / "output" / "corpus_chrome_label_eval.csv").open(encoding="utf-8") as h:
            self.assertEqual(len(list(csv.DictReader(h))), 2)


if __name__ == "__main__":
    unittest.main()
