"""Testes offline para o teste exploratório de candidatos a entidade
(`corpus_candidate_entities.py`) — heurística sem NER, fora do vocabulário
fechado do Caminho B."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from semantic_harvester.corpus_candidate_entities import (
    capitalized_candidates, is_known, run, unseen_candidates,
)
from semantic_harvester.corpus_entities import match_tokens
from semantic_harvester.corpus_redundancy import Capture
from semantic_harvester.rdf_mapper import (
    SDH, capture_uri, extracted_text_uri, resource_uri,
)
from tests.support import OfflineTestCase

ARTICLE = "https://www.record.pt/futebol/futebol-nacional/liga-nos/sporting/detalhe/exemplo.html"


def key(text: str) -> tuple[str, ...]:
    return tuple(match_tokens(text))


class CapitalizedCandidatesTests(unittest.TestCase):
    def test_sentence_initial_sequence_is_not_a_candidate(self) -> None:
        text = "Estádio da Luz recebe hoje o jogo decisivo."
        self.assertEqual(capitalized_candidates(text), [])

    def test_same_sequence_mid_sentence_is_a_candidate(self) -> None:
        text = "O jogo aconteceu no Estádio da Luz."
        self.assertEqual(capitalized_candidates(text), ["Estádio da Luz"])

    def test_connector_joins_two_capitalized_words(self) -> None:
        text = "Hoje à noite o jogo é no Estádio da Pedreira."
        self.assertEqual(capitalized_candidates(text), ["Estádio da Pedreira"])

    def test_connector_e_between_two_names(self) -> None:
        text = "Visitou Lisboa e Porto no fim de semana."
        self.assertEqual(capitalized_candidates(text), ["Lisboa e Porto"])

    def test_single_capitalized_word_is_not_a_candidate(self) -> None:
        text = "Chegou tarde. Visitou Lisboa no fim de semana."
        self.assertEqual(capitalized_candidates(text), [])

    def test_connector_without_following_capital_does_not_extend_run(self) -> None:
        text = "Chegou tarde. Visitou Lisboa e depois descansou."
        self.assertEqual(capitalized_candidates(text), [])

    def test_two_sentences_each_contribute_their_own_candidates(self) -> None:
        text = "O jogo foi no Estádio da Luz. No intervalo falou José Mourinho."
        self.assertEqual(
            capitalized_candidates(text), ["Estádio da Luz", "José Mourinho"],
        )


class IsKnownTests(unittest.TestCase):
    def test_exact_match(self) -> None:
        variants = frozenset({key("Bruno Fernandes")})
        self.assertTrue(is_known(key("Bruno Fernandes"), variants))

    def test_candidate_containing_a_known_variant(self) -> None:
        variants = frozenset({key("FC Porto")})
        self.assertTrue(is_known(key("Visita do FC Porto hoje"), variants))

    def test_unknown_sequence_is_not_known(self) -> None:
        variants = frozenset({key("Bruno Fernandes")})
        self.assertFalse(is_known(key("Estádio da Luz"), variants))


def capture(tstamp: str, text: str | None, status: int = 200) -> Capture:
    return Capture(ARTICLE, tstamp, "D" + tstamp, 10, status, text)


class UnseenCandidatesTests(unittest.TestCase):
    def test_known_entity_is_filtered_out(self) -> None:
        corpus = {ARTICLE: [capture("1", "Bruno Fernandes marcou de livre.")]}
        variants = frozenset({key("Bruno Fernandes")})
        self.assertEqual(unseen_candidates(corpus, variants), [])

    def test_new_candidate_is_reported_with_article_and_occurrence_counts(self) -> None:
        corpus = {
            ARTICLE: [
                capture("1", "O jogo foi no Estádio da Luz."),
                capture("2", "No Estádio da Luz repetiu-se o resultado."),
            ],
        }
        rows = unseen_candidates(corpus, frozenset())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidato"], "Estádio da Luz")
        self.assertEqual(rows[0]["artigos"], "1")
        self.assertEqual(rows[0]["ocorrencias"], "2")
        self.assertEqual(rows[0]["exemplo_artigo"], ARTICLE)

    def test_capture_without_text_or_not_200_is_ignored(self) -> None:
        corpus = {
            ARTICLE: [
                capture("1", "No Estádio da Luz."),
                capture("2", None),
                capture("3", "No Estádio da Luz outra vez.", status=404),
            ],
        }
        rows = unseen_candidates(corpus, frozenset())
        self.assertEqual(rows[0]["ocorrencias"], "1")

    def test_results_sorted_by_article_count_then_occurrences(self) -> None:
        other_article = ARTICLE.replace("exemplo", "outro")
        corpus = {
            ARTICLE: [capture("1", "No Estádio da Luz.")],
            other_article: [
                Capture(other_article, "1", "Dx", 10, 200, "No Estádio da Luz outra vez."),
                Capture(other_article, "2", "Dy", 10, 200, "Na antevisão, José Mourinho falou depois."),
            ],
        }
        rows = unseen_candidates(corpus, frozenset())
        self.assertEqual(rows[0]["candidato"], "Estádio da Luz")
        self.assertEqual(rows[0]["artigos"], "2")
        self.assertEqual(rows[1]["candidato"], "José Mourinho")
        self.assertEqual(rows[1]["artigos"], "1")


class RunOnSyntheticCorpusTests(OfflineTestCase):
    def _write(self) -> Path:
        graph = Graph()
        texts_dir = self.root / "data" / "raw" / "texts"
        texts_dir.mkdir(parents=True)
        spec = {
            ARTICLE: [
                ("20200101000000",
                 "Exemplo - Record - Jornal Record Menu Benfica Sporting FC Porto "
                 "Exemplo. No Estádio da Luz, Bruno Fernandes marcou de livre."),
            ],
        }
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
        vocab = self.root / "vocab.csv"
        vocab.write_text(
            "tipo,categoria,rotulo,variantes\nentidade,atleta,Bruno Fernandes,\n",
            encoding="utf-8",
        )
        return vocab

    def test_run_filters_known_entity_and_reports_new_candidate(self) -> None:
        vocab = self._write()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

        rows = run(self.root, vocab)

        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual([r["candidato"] for r in rows], ["Estádio da Luz"])
        with (self.root / "output" / "corpus_candidate_entities.csv").open(encoding="utf-8") as h:
            self.assertEqual(len(list(csv.DictReader(h))), 1)
        summary = (self.root / "output" / "corpus_candidate_entities_summary.md").read_text("utf-8")
        self.assertIn("Estádio da Luz", summary)
        self.assertIn("Candidatos distintos fora do vocabulário: 1", summary)

    def test_run_requires_vocabulary_path(self) -> None:
        self._write()
        with self.assertRaises(ValueError):
            run(self.root, None)


if __name__ == "__main__":
    unittest.main()
