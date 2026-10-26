"""Protótipo do corpus da Fase 1 (`navigation_corpus.py`): dados do painel e
preenchimento de modalidade/clube com a origem registada. Dados sintéticos."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from semantic_harvester.corpus_redundancy import corpus_graph_path
from semantic_harvester.history_pipeline import captured_at
from semantic_harvester.navigation_corpus import (
    GENERIC_TITLE_MIN_ARTICLES, ORIGIN_FALLBACK, ORIGIN_FROM_URL, ORIGIN_NONE, Article, build_data,
    display_title, era_of, generic_titles, modalidade_label, run, slug,
)
from semantic_harvester.rdf_mapper import build_article_history_graph, stable_hash
from tests.support import OfflineTestCase

LABEL = "por_ano"
MODERN = "https://www.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/a.html"
OLD = "https://www.record.pt/noticia.asp?id=1"
OLDEST = "https://www.record.pt/tn0cs.asp?nid=5"
OTHER_CLUB = "https://www.record.pt/futebol/futebol-nacional/liga-2/academico-de-viseu/detalhe/b.html"


def entity_row(url: str, categoria: str, rotulo: str, origem: str) -> dict[str, str]:
    return {"artigo": url, "tipo": "tema" if origem == "url" else "entidade",
            "categoria": categoria, "rotulo": rotulo, "origem": origem}


class NavigationCorpusTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        nt = corpus_graph_path(self.root, LABEL)
        nt.parent.mkdir(parents=True)
        for url, tstamp, title in ((MODERN, "20190301120000", "Rafa Silva bisa na Luz - Benfica - Jornal Record"),
                                   (OLD, "20020505000000", ":.: Jornal Record :.:"),
                                   (OLDEST, "19991128140726", "Record On-Line"),
                                   (OTHER_CLUB, "20200101000000", "Viseu perde")):
            record = {"article_id": stable_hash(url), "original_url": url, "tstamp": tstamp,
                      "captured_at": captured_at(tstamp), "extracted_text_path": None,
                      "text_download_success": False}
            with nt.open("a", encoding="utf-8") as handle:
                handle.write(build_article_history_graph([record], title, self.root).serialize(format="nt"))

        output = self.root / "output"
        output.mkdir()
        rows = [
            entity_row(MODERN, "secao", "futebol", "url"),
            entity_row(MODERN, "modalidade", "futebol", "url"),
            entity_row(MODERN, "clube", "benfica", "url"),
            entity_row(MODERN, "jogador", "Rafa Silva", "texto"),
            entity_row(OLD, "clube", "Sport Lisboa e Benfica", "texto"),
            entity_row(OTHER_CLUB, "clube", "academico-de-viseu", "url"),
        ]
        with (output / f"corpus_entities_{LABEL}.csv").open("w", encoding="utf-8", newline="") as h:
            writer = csv.DictWriter(h, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        (output / f"corpus_entities_{LABEL}_corpo.csv").write_text(
            "artigo,tstamp,origem_corpo\n"
            f"{MODERN},20190301120000,c′\n{OLD},20020505000000,html:aux\n", encoding="utf-8")
        (output / f"corpus_phase1_{LABEL}_captures.csv").write_text(
            "original_url,tstamp,title,facets,queries,num_queries_matched,divergent,url_variants\n"
            "http://www.record.pt/noticia.asp?id=1,20020505000000,x,clube;modalidade,"
            "Benfica;hóquei em patins,2,False,\n", encoding="utf-8")
        processed = self.root / "data" / "processed"
        (processed / "vocab.csv").write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos\n"
            "entidade,jogador,Rafa Silva,,Q1,futebol,Sport Lisboa e Benfica,1\n"
            "entidade,clube,Sport Lisboa e Benfica,Benfica,Q131499,futebol,,1\n"
            "entidade,jogador,Pedro Mendes,,Q2|Q3,futebol,,2\n", encoding="utf-8")
        (processed / "clubes.csv").write_text(
            "slug,wikidata,clube\nbenfica,Q131499,Sport Lisboa e Benfica\n", encoding="utf-8")

        self.target = run(self.root, LABEL, Path("data/processed/vocab.csv"),
                          Path("data/processed/clubes.csv"))
        text = (self.target / "data.js").read_text(encoding="utf-8")
        self.data = json.loads(text.removeprefix("window.SDH_DATA = ").rstrip().rstrip(";"))
        self.rows = {row[2]: row for row in self.data["articles"]}

    def test_all_articles_sorted_by_capture_date(self) -> None:
        self.assertEqual([r[2] for r in self.data["articles"]], [OLDEST, OLD, MODERN, OTHER_CLUB])
        self.assertEqual(self.rows[MODERN][1], "Rafa Silva bisa na Luz")

    def test_era_from_url_scheme(self) -> None:
        eras = self.data["eras"]
        self.assertEqual(eras[self.rows[OLDEST][3]], "1999–2000")
        self.assertEqual(eras[self.rows[OLD][3]], "2000–2015 (ASP.NET)")
        self.assertEqual(eras[self.rows[MODERN][3]], "2015–2024")
        self.assertEqual(era_of("https://www.record.pt/sabermais/x"), "outro")
        # Esquemas de record.xl.pt (2010–2016): ASP.NET até 2015, /detalhe/ desde 2015.
        for url in ("https://record.xl.pt/futebol/nacional/1a_liga/sporting/interior.aspx?content_id=1",
                    "https://record.xl.pt/futebol/nacional/1a_liga/sporting/interior_premium.aspx?content_id=1",
                    "https://record.xl.pt/noticia.aspx?id=3&idcanal=2"):
            self.assertEqual(era_of(url), "2000–2015 (ASP.NET)", url)
        self.assertEqual(
            era_of("https://record.xl.pt/futebol/futebol-nacional/liga-nos/sporting/detalhe/x.html"),
            "2015–2024")

    def test_modalidade_only_from_url(self) -> None:
        mods = self.data["modalidades"]
        self.assertEqual(([mods[i] for i in self.rows[MODERN][4]], self.rows[MODERN][5]),
                         (["futebol"], ORIGIN_FROM_URL))
        # O termo de pesquisa ("hóquei em patins") já não dá modalidade (2026-10-25):
        # a TextSearch encontra-o no menu do site.
        self.assertEqual((self.rows[OLD][4], self.rows[OLD][5]), ([], ORIGIN_NONE))
        self.assertNotIn("hoquei-em-patins", mods)
        self.assertEqual((self.rows[OLDEST][4], self.rows[OLDEST][5]), ([], ORIGIN_NONE))

    def test_club_from_url_then_text_share_the_qid(self) -> None:
        clubs = self.data["clubs"]
        modern = [clubs[i]["k"] for i in self.rows[MODERN][6]]
        old = [clubs[i]["k"] for i in self.rows[OLD][6]]
        self.assertEqual((modern, self.rows[MODERN][7]), (["Q131499"], ORIGIN_FROM_URL))
        self.assertEqual((old, self.rows[OLD][7]), (["Q131499"], ORIGIN_FALLBACK))
        unmapped = [clubs[i] for i in self.rows[OTHER_CLUB][6]]
        self.assertEqual(unmapped, [{"k": "slug:academico-de-viseu", "n": "academico-de-viseu"}])

    def test_entities_keyed_by_qid_and_body_source(self) -> None:
        entities = self.data["entities"]
        self.assertEqual([entities[i]["k"] for i in self.rows[MODERN][8]], ["Q1"])
        self.assertEqual(entities[self.rows[MODERN][8][0]]["q"], "Q1")
        bodies = self.data["bodies"]
        self.assertEqual(bodies[self.rows[OLD][9]], "html:aux")
        self.assertEqual(bodies[self.rows[OLDEST][9]], "sem_texto")

    def test_title_without_site_suffix_and_entity_variants(self) -> None:
        self.assertEqual(self.rows[MODERN][1], "Rafa Silva bisa na Luz")
        self.assertEqual(self.rows[OLD][1], ":.: Jornal Record :.:")
        entities = {e["k"]: e for e in self.data["entities"]}
        self.assertEqual(entities["Q131499"]["a"], ["Benfica"])
        self.assertEqual(self.data["modalidadeNomes"], ["Futebol"])

    def test_page_and_summary(self) -> None:
        page = (self.target / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script src="data.js"></script>', page)
        summary = (self.target / "resumo.md").read_text(encoding="utf-8")
        self.assertIn("- Artigos: 4", summary)
        self.assertIn("- Modalidade pelo URL / nenhuma: 1 / 3", summary)
        self.assertIn("- Clube pelo URL / pelo texto / nenhum: 2 / 1 / 1", summary)
        self.assertIn("| Sport Lisboa e Benfica | 1 |", summary)
        self.assertIn("| Rafa Silva | futebol | 1 |", summary)


class HybridVocabularyInDashboardTests(OfflineTestCase):
    def test_other_categories_and_origin(self) -> None:
        nt = corpus_graph_path(self.root, LABEL)
        nt.parent.mkdir(parents=True)
        record = {"article_id": stable_hash(MODERN), "original_url": MODERN, "tstamp": "20190301120000",
                  "captured_at": captured_at("20190301120000"), "extracted_text_path": None,
                  "text_download_success": False}
        nt.write_text(build_article_history_graph([record], "Jogo na Luz", self.root).serialize(format="nt"),
                      encoding="utf-8")
        output = self.root / "output"
        output.mkdir()
        (output / f"corpus_entities_{LABEL}.csv").write_text(
            "artigo,tipo,categoria,rotulo,origem\n"
            f"{MODERN},entidade,estadio,Estádio do Sport Lisboa e Benfica,texto\n"
            f"{MODERN},entidade,jogador,Rafa Silva,texto\n", encoding="utf-8")
        (output / f"corpus_phase1_{LABEL}_captures.csv").write_text(
            "original_url,tstamp,title,facets,queries,num_queries_matched,divergent,url_variants\n",
            encoding="utf-8")
        processed = self.root / "data" / "processed"
        (processed / "hibrido.csv").write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos,origem\n"
            "entidade,jogador,Rafa Silva,,Q1,futebol,,1,lista_fechada\n"
            "entidade,estadio,Estádio do Sport Lisboa e Benfica,Estádio da Luz,Q100,,,1,candidato\n",
            encoding="utf-8")
        (processed / "clubes.csv").write_text("slug,wikidata,clube\n", encoding="utf-8")
        target = run(self.root, LABEL, Path("data/processed/hibrido.csv"), Path("data/processed/clubes.csv"))
        data = json.loads((target / "data.js").read_text(encoding="utf-8")
                          .removeprefix("window.SDH_DATA = ").rstrip().rstrip(";"))
        self.assertEqual({e["k"]: (e["c"], e["o"]) for e in data["entities"]},
                         {"Q1": ("jogador", "lista_fechada"), "Q100": ("estadio", "candidato")})
        summary = (target / "resumo.md").read_text(encoding="utf-8")
        self.assertIn("| Estádio do Sport Lisboa e Benfica | estadio | 1 |", summary)
        self.assertIn("| candidato | 1 |", summary)
        self.assertNotIn("Estádio do Sport Lisboa e Benfica | futebol", summary)


class DisplayTests(unittest.TestCase):
    def test_display_title(self) -> None:
        self.assertEqual(display_title("Servette-Sp. Braga, 1-2: Dois hinos - Liga Europa - Jornal Record"),
                         "Servette-Sp. Braga, 1-2: Dois hinos")
        self.assertEqual(display_title("Alaphilippe vence segunda etapa - Ciclismo - Jornal Re"),
                         "Alaphilippe vence segunda etapa")
        self.assertEqual(display_title("SC Braga x Vitória SC - Record Jogos em Direto"), "SC Braga x Vitória SC")
        self.assertEqual(display_title("Basquetebol - Jornal Record"), "Basquetebol")
        self.assertEqual(display_title("Benfica - Sporting: o dérbi"), "Benfica - Sporting: o dérbi")

    def test_title_repeated_in_many_articles_is_shown_as_untitled(self) -> None:
        generic = ":.: Jornal Record :.:"
        articles = [Article(f"u{i}", generic, "2002", "outro", "c′")
                    for i in range(GENERIC_TITLE_MIN_ARTICLES)]
        articles += [Article("a", "Benfica vence", "2002", "outro", "c′"),
                     Article(f"r{GENERIC_TITLE_MIN_ARTICLES}", "Record", "2002", "outro", "c′")]
        self.assertEqual(generic_titles(articles), {generic: GENERIC_TITLE_MIN_ARTICLES})
        titles = [row[1] for row in build_data(articles, {}, {}, "t")["articles"]]
        self.assertEqual(titles.count(""), GENERIC_TITLE_MIN_ARTICLES)
        self.assertIn("Benfica vence", titles)
        self.assertIn("Record", titles)  # só uma vez: fica

    def test_modalidade_label(self) -> None:
        self.assertEqual(modalidade_label("hoquei-em-patins"), "Hóquei em patins")
        self.assertEqual(modalidade_label("desportos-de-combate"), "Desportos de combate")


class SlugTests(unittest.TestCase):
    def test_slug(self) -> None:
        self.assertEqual(slug("Hóquei em Patins"), "hoquei-em-patins")
        self.assertEqual(slug("desporto-universitario"), "desporto-universitario")


if __name__ == "__main__":
    unittest.main()
