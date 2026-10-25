"""Texto repetido entre artigos (`boilerplate.py`), a tabela lateral do `<aux>`
e a ligação ao Caminho B (`analyse_article(boilerplate=...)`). Casos do
diagnóstico de 2026-10-25, com texto sintético."""

from __future__ import annotations

import unittest
from collections import Counter

from semantic_harvester.boilerplate import build, sentence_spans
from semantic_harvester.corpus_entities import Term, analyse_article, match_tokens
from semantic_harvester.corpus_redundancy import Capture
from semantic_harvester.html_body import extract_html_body, looks_like_table
from semantic_harvester.navigation_corpus import MODALIDADE_ALIASES

FOOTER = "Caso não esteja registado no site do Record, efectue o seu registo gratuito."
QUOTE = "Vamos lutar até ao fim pelo título, disse Rui Vitória."
TABLE = ("Clara 37 15 Varzim 32 16 Salgueiros 30 17 Farense 28 18 Alverca 27 Campeonato 2001/02 "
         "1 Jardel (Sporting) 42 2 Derlei (U. Leiria) 21 3 Fary (Beira-Mar) 18 4 Hugo "
         "Henrique (V. Setúbal) 16 5 Gaúcho (Marítimo) 15")


def term(rotulo: str, *variants: str, categoria: str = "atleta") -> Term:
    return Term("entidade", categoria, rotulo,
                tuple(tuple(match_tokens(f)) for f in (rotulo, *variants)))


def corpus(texts_by_month: dict[str, list[str]]) -> dict[str, list[tuple[str, str]]]:
    """artigo → [(tstamp, corpo)], com artigos numerados por mês."""

    out, n = {}, 0
    for month, texts in texts_by_month.items():
        for text in texts:
            n += 1
            out[f"a{n}"] = [(f"{month}01120000", text)]
    return out


class RepeatedSentenceTests(unittest.TestCase):
    def test_footer_spread_over_months_is_removed(self) -> None:
        bodies = corpus({m: [f"Notícia {m} {i}. {FOOTER}" for i in range(7)]
                         for m in ("201901", "201902", "201903")})
        result = build(bodies, {})
        self.assertEqual(len(result.repeated), 1)
        self.assertEqual([p.strip() for p in result.pieces(f"O Benfica ganhou. {FOOTER}", "x")],
                         ["O Benfica ganhou."])

    def test_quote_repeated_in_one_month_is_kept(self) -> None:
        # Uma citação em 25 notícias do mesmo acontecimento (o mesmo mês) não é chrome.
        bodies = corpus({"201905": [f"Jogo {i}. {QUOTE}" for i in range(25)]})
        result = build(bodies, {})
        self.assertEqual(result.repeated, set())
        key = next(iter(result.sentence_stats))
        self.assertEqual(result.sentence_stats[key], (25, 1))  # medida, mas protegida
        self.assertIn("Rui Vitória", " ".join(result.pieces(f"Antevisão. {QUOTE}", "x")))

    def test_below_twenty_articles_is_kept(self) -> None:
        bodies = corpus({m: [f"Texto {m}. {FOOTER}"] * 3 for m in ("201901", "201902", "201903",
                                                                     "201904", "201905", "201906")})
        self.assertEqual(build(bodies, {}).repeated, set())  # 18 artigos

    def test_sentence_spans_cut_at_final_punctuation(self) -> None:
        text = "Primeira frase. Segunda frase! 3 golos marcados."
        self.assertEqual([text[a:b] for a, b in sentence_spans(text)],
                         ["Primeira frase.", "Segunda frase!", "3 golos marcados."])


class HeadlineTests(unittest.TestCase):
    TITLES = {"outro": "Maradona elogia jogadores do Benfica na Argentina",
              "proprio": "Benfica vence o FC Porto no clássico de domingo"}

    def setUp(self) -> None:
        self.result = build({}, self.TITLES)

    def test_other_article_title_in_a_list_is_removed(self) -> None:
        text = ("O treino decorreu à porta fechada. Mais notícias "
                "Maradona elogia jogadores do Benfica na Argentina Sporting prepara dérbi")
        pieces, reasons = self.result.split(text, "proprio")
        self.assertEqual(reasons, ["manchete"])
        self.assertNotIn("Maradona", " ".join(pieces))

    def test_own_title_is_never_removed(self) -> None:
        text = "Benfica vence o FC Porto no clássico de domingo Golos de Rafa."
        self.assertEqual(self.result.split(text, "proprio")[1], [])

    def test_title_continuing_in_lowercase_is_part_of_the_text(self) -> None:
        text = "Maradona elogia jogadores do Benfica na Argentina durante uma entrevista."
        self.assertEqual(self.result.split(text, "proprio")[1], [])

    def test_short_titles_are_ignored(self) -> None:
        self.assertEqual(build({}, {"curto": "Benfica vence FC Porto"}).titles, {})


class AnalyseArticleTests(unittest.TestCase):
    def test_mentions_only_in_removed_text_are_dropped(self) -> None:
        bodies = corpus({m: [f"Notícia {m} {i}. Tabela: 4 Hugo Henrique marcou 16." for i in range(7)]
                         for m in ("200201", "200202", "200203")})
        result = build(bodies, {})
        capture = Capture("https://www.record.pt/noticia.asp?id=1", "20020301120000", None, None,
                          None, "Derlei treinou hoje. Tabela: 4 Hugo Henrique marcou 16.")
        terms = [term("Hugo Henrique"), term("Derlei")]
        removed: Counter = Counter()
        rows = analyse_article(capture.article, [capture], terms, None,
                               boilerplate=result, removed=removed)
        self.assertEqual([r["rotulo"] for r in rows if r["origem"] == "texto"], ["Derlei"])
        self.assertEqual(removed["frase_repetida"], 1)
        # Sem a limpeza, as duas contam (o comportamento anterior não muda).
        rows = analyse_article(capture.article, [capture], terms, None)
        self.assertEqual(sorted(r["rotulo"] for r in rows if r["origem"] == "texto"),
                         ["Derlei", "Hugo Henrique"])

    def test_words_on_both_sides_of_a_removed_piece_do_not_join(self) -> None:
        result = build({}, {"outro": "Treinador anuncia saída do clube no final da época"})
        capture = Capture("https://www.record.pt/x", "20190101120000", None, None, None,
                          "Vitória Treinador anuncia saída do clube no final da época Guimarães")
        rows = analyse_article(capture.article, [capture], [term("Vitória Guimarães")], None,
                               boilerplate=result)
        self.assertEqual([r for r in rows if r["origem"] == "texto"], [])


class AuxTableTests(unittest.TestCase):
    def test_league_table_is_not_a_body(self) -> None:
        self.assertTrue(looks_like_table(TABLE))
        report = ("O Benfica venceu ontem o FC Porto por 2-1, com golos de Simão aos 23 minutos "
                  "e de Mantorras aos 78, num jogo da 30.ª jornada perante 60 mil espectadores.")
        self.assertFalse(looks_like_table(report))
        self.assertFalse(looks_like_table("1 2 3 4"))  # curto demais para decidir

    def test_aux_table_is_skipped_and_the_news_kept(self) -> None:
        html = f"<aux>{TABLE}</aux><aux>O Beira-Mar empatou em Aveiro.</aux>"
        body = extract_html_body(html.encode())
        self.assertEqual((body.container, body.text), ("aux", "O Beira-Mar empatou em Aveiro."))

    def test_page_with_only_the_table_has_no_body(self) -> None:
        body = extract_html_body(f"<aux>{TABLE}</aux>".encode())
        self.assertEqual((body.found, body.text), (False, ""))


class ModalidadeAliasTests(unittest.TestCase):
    def test_same_sport_different_names(self) -> None:
        self.assertEqual(MODALIDADE_ALIASES["rugby"], "raguebi")
        self.assertEqual(MODALIDADE_ALIASES["record-pela-patagonia"], "aventura")


if __name__ == "__main__":
    unittest.main()
