from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from semantic_harvester.corpus_chrome import ngrams, tokens
from semantic_harvester.corpus_entities import (
    Term, analyse_article, club_coherence, count_mentions, fold, load_vocabulary,
    match_tokens, run, text_segments, themes_from_url,
)
from semantic_harvester.corpus_redundancy import Capture
from semantic_harvester.rdf_mapper import (
    SDH, capture_uri, extracted_text_uri, resource_uri,
)
from tests.support import OfflineTestCase

MENU = "Menu Record Benfica Sporting FC Porto Modalidades Opinião Vídeos"
ARTICLE = "https://www.record.pt/futebol/futebol-nacional/liga-nos/sporting/detalhe/exemplo.html"


def term(rotulo: str, *variants: str, categoria: str = "atleta",
         clubs: tuple[str, ...] = ()) -> Term:
    forms = [rotulo, *variants]
    return Term("entidade", categoria, rotulo, tuple(tuple(match_tokens(f)) for f in forms),
                frozenset(clubs))


CLUB_MAP = {"sporting": "Sporting Clube de Portugal", "benfica": "Sport Lisboa e Benfica"}


def capture(tstamp: str, text: str | None, status: int = 200) -> Capture:
    return Capture(ARTICLE, tstamp, "D" + tstamp, 10, status, text)


class NormalizationTests(unittest.TestCase):
    def test_fold_removes_accents_and_case(self) -> None:
        self.assertEqual(fold("Nélson ÉVORA"), "nelson evora")
        self.assertEqual(fold("Nélson"), "nelson")

    def test_match_tokens(self) -> None:
        self.assertEqual(match_tokens("F.C. Porto, João Félix!"), ["f", "c", "porto", "joao", "felix"])


class CountMentionsTests(unittest.TestCase):
    def test_accent_and_case_insensitive(self) -> None:
        counts = count_mentions([match_tokens("Nelson Évora venceu; NÉLSON évora sorriu")],
                                [term("Nelson Évora")])
        self.assertEqual(counts["Nelson Évora"], 2)

    def test_word_boundaries(self) -> None:
        counts = count_mentions([match_tokens("O Portimonense ganhou no Porto-Alegre")],
                                [term("FC Porto", categoria="clube")])
        self.assertEqual(counts["FC Porto"], 0)
        counts = count_mentions([match_tokens("O Portimonense recebe o FC Porto")],
                                [term("FC Porto", categoria="clube")])
        self.assertEqual(counts["FC Porto"], 1)

    def test_multiword_needs_contiguous_words(self) -> None:
        counts = count_mentions([match_tokens("Bruno marcou e Fernandes assistiu")],
                                [term("Bruno Fernandes")])
        self.assertEqual(counts["Bruno Fernandes"], 0)

    def test_variants_count_for_the_label(self) -> None:
        counts = count_mentions([match_tokens("CR7 e Cristiano Ronaldo")],
                                [term("Cristiano Ronaldo", "CR7")])
        self.assertEqual(counts["Cristiano Ronaldo"], 2)

    def test_no_match_across_segments(self) -> None:
        counts = count_mentions([["fc"], ["porto"]], [term("FC Porto", categoria="clube")])
        self.assertEqual(counts["FC Porto"], 0)


class TextSegmentsTests(unittest.TestCase):
    def test_chrome_menu_removed(self) -> None:
        chrome = ngrams(tokens(MENU), 5)
        segments = text_segments(f"{MENU} Telma Monteiro conquistou o ouro", chrome)
        counts = count_mentions(segments, [term("Benfica", categoria="clube"), term("Telma Monteiro")])
        self.assertEqual(counts["Benfica"], 0)
        self.assertEqual(counts["Telma Monteiro"], 1)

    def test_without_chrome_menu_is_matched(self) -> None:
        segments = text_segments(f"{MENU} Telma Monteiro", None)
        counts = count_mentions(segments, [term("Benfica", categoria="clube")])
        self.assertEqual(counts["Benfica"], 1)

    def test_removed_block_splits_segments(self) -> None:
        chrome = ngrams(tokens(MENU), 5)
        segments = text_segments(f"o fc {MENU} porto", chrome)
        self.assertEqual(segments, [["o", "fc"], ["porto"]])


class ThemesFromUrlTests(unittest.TestCase):
    def test_national_football_with_club(self) -> None:
        self.assertEqual(themes_from_url(ARTICLE), [
            ("secao", "futebol"), ("modalidade", "futebol"),
            ("competicao", "liga-nos"), ("clube", "sporting"),
        ])

    def test_amp_variant(self) -> None:
        url = "https://www.record.pt/futebol/futebol-nacional/liga-nos/boavista/amp/yusupha"
        self.assertIn(("clube", "boavista"), themes_from_url(url))

    def test_other_sport(self) -> None:
        url = "https://www.record.pt/modalidades/judo/detalhe/telma.html"
        self.assertEqual(themes_from_url(url), [("secao", "modalidades"), ("modalidade", "judo")])

    def test_international_competition(self) -> None:
        url = ("https://www.record.pt/internacional/competicoes-de-selecoes/europeu/"
               "euro-2016/detalhe/x.html")
        self.assertEqual(themes_from_url(url), [("secao", "internacional"), ("competicao", "europeu")])

    def test_multimedia_has_section_only(self) -> None:
        url = "https://www.record.pt/multimedia/videos/detalhe/zungu.html"
        self.assertEqual(themes_from_url(url), [("secao", "multimedia")])

    def test_path_without_detalhe_drops_last_segment(self) -> None:
        self.assertEqual(themes_from_url("https://www.record.pt/jogos-em-direto/live/78799"),
                         [("secao", "jogos-em-direto")])


class AnalyseArticleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.terms = [term("Telma Monteiro"), term("Bruno Fernandes")]

    def test_persistent_vs_headline_only_in_one_capture(self) -> None:
        captures = [
            capture("1", "Telma Monteiro venceu. Manchete: Bruno Fernandes renova"),
            capture("2", "Telma Monteiro venceu. Manchete: outro assunto"),
        ]
        rows = {r["rotulo"]: r for r in analyse_article(ARTICLE, captures, self.terms, None)
                if r["origem"] == "texto"}
        self.assertEqual(rows["Telma Monteiro"]["persistente"], "True")
        self.assertEqual(rows["Telma Monteiro"]["capturas_com_mencao"], "2")
        self.assertEqual(rows["Bruno Fernandes"]["persistente"], "False")
        self.assertEqual(rows["Bruno Fernandes"]["capturas_com_mencao"], "1")
        self.assertEqual(rows["Bruno Fernandes"]["uma_so_captura"], "False")

    def test_url_themes_always_present(self) -> None:
        rows = analyse_article(ARTICLE, [capture("1", None)], self.terms, None)
        self.assertEqual({r["origem"] for r in rows}, {"url"})
        self.assertIn("sporting", {r["rotulo"] for r in rows})

    def test_capture_without_text_or_not_200_is_ignored(self) -> None:
        captures = [capture("1", "Telma Monteiro"), capture("2", None),
                    capture("3", "Bruno Fernandes", status=404)]
        rows = [r for r in analyse_article(ARTICLE, captures, self.terms, None)
                if r["origem"] == "texto"]
        self.assertEqual([r["rotulo"] for r in rows], ["Telma Monteiro"])
        self.assertEqual(rows[0]["capturas_com_texto"], "1")
        self.assertEqual(rows[0]["uma_so_captura"], "True")


class ClubCoherenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sporting_player = term("Bas Dost", clubs=("Sporting Clube de Portugal",))
        self.benfica_player = term("Jonas", clubs=("Sport Lisboa e Benfica",))
        self.two_clubs = term("Gelson", clubs=("Sporting Clube de Portugal", "Outro Clube"))

    def test_same_club_is_sim(self) -> None:
        self.assertEqual(club_coherence(self.sporting_player, ["sporting"], CLUB_MAP), "sim")
        self.assertEqual(club_coherence(self.two_clubs, ["sporting"], CLUB_MAP), "sim")

    def test_different_club_is_nao(self) -> None:
        self.assertEqual(club_coherence(self.benfica_player, ["sporting"], CLUB_MAP), "nao")

    def test_article_without_club_theme_is_sem_tema(self) -> None:
        self.assertEqual(club_coherence(self.benfica_player, [], CLUB_MAP), "sem_tema")

    def test_unmapped_slug_fails_loudly(self) -> None:
        with self.assertRaises(ValueError):
            club_coherence(self.benfica_player, ["clube-desconhecido"], CLUB_MAP)

    def test_analyse_article_fills_column_without_removing_mentions(self) -> None:
        captures = [capture("1", "Bas Dost marcou. Manchete: Jonas no Benfica")]
        rows = {r["rotulo"]: r for r in analyse_article(
            ARTICLE, captures, [self.sporting_player, self.benfica_player], None,
            club_map=CLUB_MAP) if r["origem"] == "texto"}
        self.assertEqual(rows["Bas Dost"]["clube_coerente"], "sim")
        self.assertEqual(rows["Jonas"]["clube_coerente"], "nao")

    def test_url_without_club_gives_sem_tema(self) -> None:
        url = "https://www.record.pt/futebol/futebol-nacional/liga-nos/detalhe/cronica.html"
        rows = [r for r in analyse_article(url, [capture("1", "Jonas marcou")],
                                           [self.benfica_player], None, club_map=CLUB_MAP)
                if r["origem"] == "texto"]
        self.assertEqual(rows[0]["clube_coerente"], "sem_tema")

    def test_without_club_map_column_is_empty(self) -> None:
        rows = [r for r in analyse_article(ARTICLE, [capture("1", "Jonas")],
                                           [self.benfica_player], None)
                if r["origem"] == "texto"]
        self.assertEqual(rows[0]["clube_coerente"], "")


class VocabularyTests(OfflineTestCase):
    def test_load_vocabulary_with_variants(self) -> None:
        path = self.root / "vocab.csv"
        path.write_text("tipo,categoria,rotulo,variantes\n"
                        "entidade,atleta,Cristiano Ronaldo,CR7|Ronaldo\n", encoding="utf-8")
        (t,) = load_vocabulary(path)
        self.assertEqual(t.variants, (("cristiano", "ronaldo"), ("cr7",), ("ronaldo",)))

    def test_load_vocabulary_reads_clubs(self) -> None:
        path = self.root / "vocab.csv"
        path.write_text("tipo,categoria,rotulo,variantes,clubes\n"
                        "entidade,jogador,Jonas,,Sport Lisboa e Benfica|Valencia\n", encoding="utf-8")
        (t,) = load_vocabulary(path)
        self.assertEqual(t.clubs, frozenset({"Sport Lisboa e Benfica", "Valencia"}))

    def test_themes_are_not_accepted_in_vocabulary(self) -> None:
        path = self.root / "vocab.csv"
        path.write_text("tipo,categoria,rotulo,variantes\ntema,clube,Benfica,\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_vocabulary(path)


class RunOnSyntheticCorpusTests(OfflineTestCase):
    def _write(self) -> Path:
        graph = Graph()
        texts_dir = self.root / "data" / "raw" / "texts"
        texts_dir.mkdir(parents=True)
        spec = {ARTICLE: [("20200101000000", f"{MENU} Telma Monteiro brilhou"),
                          ("20200102000000", f"{MENU} Telma Monteiro brilhou")]}
        for i in range(9):
            spec[f"https://www.record.pt/modalidades/judo/detalhe/o{i}.html"] = [
                ("20200101000000", f"{MENU} texto próprio número {i} sem atletas")]
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
        vocab.write_text("tipo,categoria,rotulo,variantes\n"
                         "entidade,atleta,Telma Monteiro,\n"
                         "entidade,clube,Benfica,SL Benfica\n", encoding="utf-8")
        return vocab

    def test_run_removes_menu_mentions_and_is_non_destructive(self) -> None:
        vocab = self._write()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

        rows = run(self.root, vocab, chrome_fraction=0.5)

        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        text_rows = [r for r in rows if r["origem"] == "texto"]
        self.assertEqual([(r["artigo"], r["rotulo"]) for r in text_rows], [(ARTICLE, "Telma Monteiro")])
        with (self.root / "output" / "corpus_entities.csv").open(encoding="utf-8") as h:
            self.assertEqual(len(list(csv.DictReader(h))), len(rows))
        summary = (self.root / "output" / "corpus_entities_summary.md").read_text("utf-8")
        self.assertIn("| Telma Monteiro | 1 | 1 |", summary)
        self.assertIn("1 pela regra de persistência; destes, 0 são de artigos com uma só", summary)
        self.assertIn("≥ 0,50 dos artigos", summary)

    def test_run_with_club_map_reports_coherence(self) -> None:
        vocab = self._write()
        vocab.write_text("tipo,categoria,rotulo,variantes,clubes\n"
                         "entidade,atleta,Telma Monteiro,,Sporting Clube de Portugal\n",
                         encoding="utf-8")
        club_map = self.root / "clubes.csv"
        club_map.write_text("slug,wikidata,clube\nsporting,Q75729,Sporting Clube de Portugal\n",
                            encoding="utf-8")
        rows = run(self.root, vocab, chrome_fraction=0.5, club_map_path=club_map)
        (row,) = [r for r in rows if r["origem"] == "texto"]
        self.assertEqual(row["clube_coerente"], "sim")
        summary = (self.root / "output" / "corpus_entities_summary.md").read_text("utf-8")
        self.assertIn("| sim | 1 | 1 |", summary)
        self.assertIn("| nao | 0 | 0 |", summary)

    def test_without_chrome_removal_menu_club_is_found_everywhere(self) -> None:
        vocab = self._write()
        rows = run(self.root, vocab, chrome_fraction=None)
        benfica = [r for r in rows if r["rotulo"] == "Benfica" and r["origem"] == "texto"]
        self.assertEqual(len(benfica), 10)


if __name__ == "__main__":
    unittest.main()
