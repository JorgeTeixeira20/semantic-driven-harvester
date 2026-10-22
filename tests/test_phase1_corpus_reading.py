"""Leitura do corpus da Fase 1 (N-Triples, sem statusCode/contentLength/digest)
pelos Caminhos B e pelo teste de candidatos, sem tocar nas saídas oficiais."""

from __future__ import annotations

import csv
import hashlib
import unittest
from pathlib import Path

from rdflib import Graph

from semantic_harvester import corpus_candidate_entities, corpus_entities, corpus_entities_rdf
from semantic_harvester.corpus_entities import Term, club_coherence
from semantic_harvester.corpus_rdf import rdf_paths
from semantic_harvester.corpus_redundancy import Capture, corpus_graph_path, load_corpus
from semantic_harvester.history_pipeline import captured_at
from semantic_harvester.rdf_mapper import build_article_history_graph, stable_hash
from tests.support import OfflineTestCase

LABEL = "por_ano"
BENFICA = "https://www.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/a.html"
VISEU = "https://www.record.pt/futebol/futebol-nacional/liga-2/academico-de-viseu/detalhe/b.html"
OLD = "https://www.record.pt/noticia.asp?id=1"


def body_text(title: str, body: str) -> str:
    return f"{title} - Record - Jornal Record Menu Benfica Sporting {title}. {body}"


def term(rotulo: str, categoria: str, clubs: tuple[str, ...] = ()) -> Term:
    return Term("entidade", categoria, rotulo, (tuple(rotulo.lower().split()),), frozenset(clubs))


class Phase1Corpus(OfflineTestCase):
    """Escreve um N-Triples apendável como o `corpus_rdf --fase1`: um grafo por
    artigo, mapeado pelo mesmo `build_article_history_graph`, sem os campos que
    a TextSearch não devolve."""

    def write_article(self, url: str, tstamp: str, text: str | None, html: bool | str = False) -> None:
        stem = f"{tstamp}_{hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]}"
        relative = None
        if text is not None:
            path = self.root / "data" / "raw" / "texts" / f"{stem}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            relative = path.relative_to(self.root).as_posix()
        if html:
            html_path = self.root / "data" / "raw" / "original_html" / f"{stem}.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(html if isinstance(html, str) else "<html></html>", encoding="utf-8")
        record = {
            "article_id": stable_hash(url), "original_url": url, "tstamp": tstamp,
            "captured_at": captured_at(tstamp), "title": "t",
            "extracted_text_path": relative, "text_download_success": text is not None,
        }
        graph = build_article_history_graph([record], "t", self.root)
        nt = corpus_graph_path(self.root, LABEL)
        nt.parent.mkdir(parents=True, exist_ok=True)
        with nt.open("a", encoding="utf-8") as handle:
            handle.write(graph.serialize(format="nt") + "\n")

    def write_vocabulary(self) -> Path:
        path = self.root / "vocab.csv"
        path.write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos\n"
            "entidade,jogador,Rafa Silva,,Q1,futebol,Sport Lisboa e Benfica,1\n"
            "entidade,clube,Sport Lisboa e Benfica,Benfica,Q131499,futebol,,1\n",
            encoding="utf-8",
        )
        return path

    def write_club_map(self) -> Path:
        path = self.root / "clubes.csv"
        path.write_text("slug,wikidata,clube\nbenfica,Q131499,Sport Lisboa e Benfica\n",
                        encoding="utf-8")
        return path


class LoadPhase1CorpusTests(Phase1Corpus):
    def test_capture_without_status_length_digest_is_in_layer1(self) -> None:
        self.write_article(BENFICA, "20190101000000", body_text("A", "Texto."), html=True)
        (capture,) = load_corpus(corpus_graph_path(self.root, LABEL), self.root)[BENFICA]
        self.assertIsNone(capture.status_code)
        self.assertIsNone(capture.content_length)
        self.assertIsNone(capture.digest)
        self.assertTrue(capture.in_layer1)
        self.assertEqual(capture.html_path.parent.name, "original_html")

    def test_html_path_is_none_when_the_file_is_missing(self) -> None:
        self.write_article(BENFICA, "20190101000000", "Texto.")
        (capture,) = load_corpus(corpus_graph_path(self.root, LABEL), self.root)[BENFICA]
        self.assertIsNone(capture.html_path)

    def test_article_repeated_in_appended_ntriples_is_merged(self) -> None:
        # Primeiro sem texto (artefacto de rede), depois refeito com texto.
        self.write_article(BENFICA, "20190101000000", None)
        self.write_article(BENFICA, "20190101000000", "Texto.")
        (capture,) = load_corpus(corpus_graph_path(self.root, LABEL), self.root)[BENFICA]
        self.assertEqual(capture.text, "Texto.")

    def test_turtle_and_ntriples_give_the_same_corpus(self) -> None:
        self.write_article(BENFICA, "20190101000000", "Texto A.")
        self.write_article(OLD, "20010101000000", "Texto B.")
        nt = corpus_graph_path(self.root, LABEL)
        ttl = self.root / "corpus.ttl"
        Graph().parse(nt, format="nt").serialize(destination=ttl, format="turtle")
        self.assertEqual(load_corpus(nt, self.root), load_corpus(ttl, self.root))

    def test_status_200_still_required_when_recorded(self) -> None:
        capture = Capture("a", "1", "d", 1, 404, "Texto.")
        self.assertFalse(capture.in_layer1)

    def test_paths_match_corpus_rdf(self) -> None:
        self.assertEqual(corpus_graph_path(self.root), rdf_paths(self.root, None)["turtle"])
        self.assertEqual(corpus_graph_path(self.root, LABEL), rdf_paths(self.root, LABEL)["triples"])


class ClubCoherenceTests(unittest.TestCase):
    def test_unmapped_slug_is_sem_mapa_when_not_strict(self) -> None:
        player = term("Rafa Silva", "jogador", ("Sport Lisboa e Benfica",))
        self.assertEqual(club_coherence(player, ["academico-de-viseu"], {}, strict=False), "sem_mapa")
        with self.assertRaises(ValueError):
            club_coherence(player, ["academico-de-viseu"], {})

    def test_club_entity_compares_its_own_label(self) -> None:
        club = term("Sport Lisboa e Benfica", "clube")
        mapping = {"benfica": "Sport Lisboa e Benfica", "porto": "Futebol Clube do Porto"}
        self.assertEqual(club_coherence(club, ["benfica"], mapping), "sim")
        self.assertEqual(club_coherence(club, ["porto"], mapping), "nao")


class RunOnPhase1CorpusTests(Phase1Corpus):
    def setUp(self) -> None:
        super().setUp()
        self.write_article(BENFICA, "20190101000000",
                           body_text("A", "No jogo, Rafa Silva marcou pelo Benfica."), html=True)
        self.write_article(VISEU, "20200101000000", body_text("B", "O Benfica B perdeu."))
        self.write_article(OLD, "20010101000000", "Página sem título reconhecível.")
        self.vocab = self.write_vocabulary()
        self.club_map = self.write_club_map()

    def test_entities_run_writes_labelled_outputs_only(self) -> None:
        rows = corpus_entities.run(self.root, self.vocab, club_map_path=self.club_map,
                                   use_body=True, corpus_label=LABEL)
        output = self.root / "output"
        self.assertFalse((output / "corpus_entities.csv").exists())
        self.assertTrue((output / f"corpus_entities_{LABEL}.csv").is_file())

        text = {(r["artigo"], r["rotulo"]): r for r in rows if r["origem"] == "texto"}
        self.assertEqual(text[(BENFICA, "Rafa Silva")]["clube_coerente"], "sim")
        self.assertEqual(text[(BENFICA, "Sport Lisboa e Benfica")]["clube_coerente"], "sim")
        self.assertEqual(text[(VISEU, "Sport Lisboa e Benfica")]["clube_coerente"], "sem_mapa")
        self.assertNotIn(OLD, {r["artigo"] for r in rows})

        summary = (output / f"corpus_entities_{LABEL}_summary.md").read_text("utf-8")
        self.assertIn("| academico-de-viseu | 1 |", summary)
        self.assertIn(f"`output/corpus_entities_{LABEL}.csv`", summary)

    def test_old_article_found_only_through_the_html_container(self) -> None:
        old = "https://www.record.pt/noticia.asp?id=2"
        self.write_article(old, "20020101000000", ":.: Jornal Record :.: Rafa Silva marcou.",
                           html="<html><body><aux>Rafa Silva marcou.</aux></body></html>")
        without = corpus_entities.run(self.root, self.vocab, use_body=True, corpus_label=LABEL)
        self.assertNotIn(old, {r["artigo"] for r in without})
        rows = corpus_entities.run(self.root, self.vocab, use_body=True, corpus_label=LABEL,
                                   use_html=True)
        self.assertIn((old, "Rafa Silva"), {(r["artigo"], r["rotulo"]) for r in rows})
        summary = (self.root / "output" / f"corpus_entities_{LABEL}_summary.md").read_text("utf-8")
        self.assertIn("html:aux 1", summary)

    def test_entities_rdf_on_labelled_corpus(self) -> None:
        corpus_entities.run(self.root, self.vocab, club_map_path=self.club_map,
                            use_body=True, corpus_label=LABEL)
        graph, stats, _ = corpus_entities_rdf.run(self.root, corpus_label=LABEL,
                                                  vocabulary_path=self.vocab)
        self.assertTrue((self.root / "output" / f"corpus_entities_{LABEL}.ttl").is_file())
        self.assertEqual(stats["entidades_wikidata"], 2)
        self.assertIn("http://www.wikidata.org/entity/Q131499", {str(s) for s in graph.subjects()})

    def test_candidates_run_on_labelled_corpus(self) -> None:
        corpus_candidate_entities.run(self.root, self.vocab, corpus_label=LABEL)
        path = self.root / "output" / f"corpus_candidate_entities_{LABEL}.csv"
        with path.open(encoding="utf-8") as handle:
            self.assertIsInstance(list(csv.DictReader(handle)), list)
        self.assertFalse((self.root / "output" / "corpus_candidate_entities.csv").exists())


if __name__ == "__main__":
    unittest.main()
