"""Sugestões para a tabela slug → clube (`club_url_map.py`), com um vocabulário sintético."""

from __future__ import annotations

import csv
import unittest

from semantic_harvester.club_url_map import run, slug_tokens, suggest
from semantic_harvester.corpus_entities import match_tokens
from tests.support import OfflineTestCase


def club(qid: str, name: str, *variants: str):
    return (qid, name, [tuple(match_tokens(f)) for f in (name, *variants)])


CLUBS = [
    club("Q131499", "Sport Lisboa e Benfica", "Benfica"),
    club("Q7387221", "Sport Lisboa e Benfica B", "Benfica B"),
    club("Q208585", "Vitória Futebol Clube", "Vitória de Setúbal"),
    club("Q5423714", "Futebol Clube do Porto B", "FC Porto B"),
]


class SuggestTests(unittest.TestCase):
    def test_initials_in_slugs(self) -> None:
        self.assertEqual(slug_tokens("v--setubal"), [("v", True), ("setubal", False)])
        self.assertEqual(suggest("v--setubal", CLUBS), ("unico", [("Q208585", "Vitória Futebol Clube")]))

    def test_main_club_preferred_over_b_team(self) -> None:
        self.assertEqual(suggest("benfica", CLUBS), ("unico", [("Q131499", "Sport Lisboa e Benfica")]))

    def test_only_b_team_needs_review_and_unknown_is_none(self) -> None:
        self.assertEqual(suggest("fc-porto", CLUBS)[0], "ambiguo")
        self.assertEqual(suggest("rio-ave", CLUBS), ("sem", []))


class RunTests(OfflineTestCase):
    def test_suggestions_and_apply_keep_existing_rows(self) -> None:
        processed = self.root / "data" / "processed"
        processed.mkdir(parents=True)
        (processed / "caminho_b_vocabulario_wikidata_alargado.csv").write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos\n"
            "entidade,clube,Sport Lisboa e Benfica,Benfica,Q131499|Q2029819,basquetebol|futebol,,2\n"
            "entidade,clube,Rio Ave Futebol Clube,Rio Ave,Q622432,futebol,,1\n", encoding="utf-8")
        table = processed / "caminho_b_clubes_url.csv"
        table.write_text("slug,wikidata,clube\nbenfica,Q131499,Sport Lisboa e Benfica\n", encoding="utf-8")
        (self.root / "output").mkdir()
        (self.root / "output" / "corpus_entities_por_ano.csv").write_text(
            "artigo,tipo,categoria,rotulo,origem\n"
            "u1,tema,clube,rio-ave,url\nu2,tema,clube,rio-ave,url\nu3,tema,clube,benfica,url\n",
            encoding="utf-8")
        rows = run(self.root, apply=True)
        self.assertEqual([(r["slug"], r["artigos"], r["wikidata"], r["estado"]) for r in rows],
                         [("rio-ave", 2, "Q622432", "unico")])
        with table.open(encoding="utf-8") as h:
            self.assertEqual([r["slug"] for r in csv.DictReader(h)], ["benfica", "rio-ave"])


if __name__ == "__main__":
    unittest.main()


class PrimaryQidTests(OfflineTestCase):
    """Correção de 2026-10-23: Benfica, Sporting e Braga eram "homónimos" (vários
    QIDs com o mesmo rótulo) e ficavam sem QID no RDF e no painel."""

    def test_rdf_and_dashboard_use_the_qid_from_the_club_table(self) -> None:
        from semantic_harvester.corpus_entities_rdf import (
            WIKIDATA_ENTITY, entity_uri, load_vocabulary_identity,
        )
        from semantic_harvester.navigation_corpus import load_vocabulary

        vocab = self.root / "vocab.csv"
        vocab.write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos\n"
            "entidade,clube,Sport Lisboa e Benfica,Benfica,Q131499|Q2029819,futebol,,2\n"
            "entidade,clube,Leixões SC,,Q1|Q2,futebol,,2\n"
            "entidade,jogador,Pedro Mendes,,Q3|Q4,futebol,,2\n", encoding="utf-8")
        club_qids = {"Q131499"}
        identity = load_vocabulary_identity(vocab, club_qids)
        self.assertEqual(str(entity_uri("Sport Lisboa e Benfica", identity)), WIKIDATA_ENTITY + "Q131499")
        self.assertFalse(str(entity_uri("Leixões SC", identity)).startswith(WIKIDATA_ENTITY))
        self.assertFalse(str(entity_uri("Pedro Mendes", identity)).startswith(WIKIDATA_ENTITY))
        dashboard = load_vocabulary(vocab, club_qids)
        self.assertEqual((dashboard["Sport Lisboa e Benfica"].key, dashboard["Sport Lisboa e Benfica"].qid),
                         ("Q131499", "Q131499"))
        self.assertEqual(dashboard["Pedro Mendes"].qid, "")
