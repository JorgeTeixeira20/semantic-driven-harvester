from __future__ import annotations

import unittest

from semantic_harvester.corpus_body import extract_body, label_rows
from semantic_harvester.corpus_chrome import LABEL_CHANGED, LABEL_SAME
from semantic_harvester.corpus_chrome import LabelledPair

MENU = "Menu Record Login Home Últimas Notícias Benfica Sporting FC Porto"
TITLE = "Jonas renova com o Benfica"
NORMAL = (f"{TITLE} - Benfica - Jornal Record {MENU} Notícias MAIS 06h33 - Sporting Outra manchete "
          f"{TITLE} O avançado brasileiro assinou até 2020. Mais notícias 05h00 Bas Dost marca "
          f"Voltar {TITLE} Enviar artigo por email")


class ExtractBodyTests(unittest.TestCase):
    def test_repeated_title_body_ends_at_first_marker_after_it(self) -> None:
        body = extract_body(NORMAL)
        self.assertTrue(body.found)
        # "Últimas Notícias"/"Notícias MAIS" do menu vêm antes do corpo e não cortam nada.
        self.assertEqual(body.text, f"{TITLE} O avançado brasileiro assinou até 2020.")
        self.assertEqual(body.end_marker, "Mais notícias")

    def test_amp_page_without_title_suffix(self) -> None:
        text = (f"{TITLE} Home Últimas Notícias Taça Record Premium Assinatura Digital Saiba mais "
                f"{TITLE} Avançado tranquilo. PUB Comentar O Record recomenda para si Liga NOS ...")
        body = extract_body(text)
        self.assertEqual(body.text, f"{TITLE} Avançado tranquilo. PUB Comentar")

    def test_capture_without_the_article_has_no_body(self) -> None:
        text = f"Quarta-feira, 15 de março de 2017 Todas as Capas {MENU} Mais notícias 18h07 Gil Vicente"
        body = extract_body(text)
        self.assertFalse(body.found)
        self.assertEqual(body.text, "")

    def test_title_only_in_the_page_title_has_no_body(self) -> None:
        self.assertFalse(extract_body(f"SC Braga x Vitória SC - Record Jogos em Direto {MENU}").found)

    def test_text_without_any_marker_keeps_everything_after_the_title(self) -> None:
        text = f"{TITLE} - Benfica - Jornal Record {TITLE} O avançado renovou. Fim."
        self.assertEqual(extract_body(text).text, f"{TITLE} O avançado renovou. Fim.")

    def test_lowercase_marker_in_prose_does_not_cut(self) -> None:
        """Regressão do artigo da Record Auto (Xiaomi, 64ba9625…): "Os mais recentes
        rumores" a meio de uma frase não é cabeçalho de bloco."""

        title = "Xiaomi: gigante dos telemóveis vai lançar SUV"
        text = (f"{title} - Record Auto - Jornal Record {MENU} {title} O SUV terá muita tecnologia. "
                "Os mais recentes rumores dão conta de que chegará em breve. Por Aquela Máquina "
                "Últimas Notícias Mais Recentes 19:41 Fora de Campo")
        body = extract_body(text)
        self.assertIn("Os mais recentes rumores dão conta de que chegará em breve.", body.text)
        self.assertTrue(body.text.endswith("Por Aquela Máquina"))
        self.assertEqual(body.end_marker, "Últimas Notícias")

    def test_marker_needs_word_boundaries(self) -> None:
        text = (f"{TITLE} - Benfica - Jornal Record {TITLE} Adeptos do Leicester e... "
                "cerveja também não faltam. Veja também outras notícias")
        body = extract_body(text)
        self.assertIn("cerveja também não faltam.", body.text)
        self.assertEqual(body.end_marker, "Veja também")

    def test_title_listed_in_menu_right_before_a_marker_is_skipped(self) -> None:
        """Coluna de opinião cujo título aparece no menu, seguido de "Notícias MAIS"."""

        title = "Hora zero: hora de recomeçar?"
        text = (f"{title} - Opinião - Jornal Record Opinião MAIS {title} Notícias MAIS 06h33 Benfica "
                f"{title} Chegou 2017 e, com ele, a esperança. Mais notícias")
        self.assertEqual(extract_body(text).text, f"{title} Chegou 2017 e, com ele, a esperança.")


class LabelRowsTests(unittest.TestCase):
    def test_pairs_with_a_capture_without_body_get_no_similarity(self) -> None:
        bodies = {("a", "1"): extract_body(NORMAL),
                  ("a", "2"): extract_body(f"Quarta-feira {MENU}"),
                  ("a", "3"): extract_body(NORMAL)}
        pairs = [LabelledPair("1", "baixa", "a", "1", "2", LABEL_CHANGED, 0.43),
                 LabelledPair("2", "alta", "a", "1", "3", LABEL_SAME, 0.9)]
        rows = label_rows(pairs, bodies)
        self.assertIsNone(rows[0]["sim"])
        self.assertEqual(rows[1]["sim"], 1.0)


if __name__ == "__main__":
    unittest.main()
