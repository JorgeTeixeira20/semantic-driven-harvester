"""Corpo do artigo pelo contentor do HTML (`html_body.py`) e a sua ligação à
c′ (`to_body_corpus(use_html=True)`). HTML sintético com a estrutura medida
em 2026-10-22 (2 páginas por template), não HTML real."""

from __future__ import annotations

import unittest

from semantic_harvester.corpus_redundancy import Capture, to_body_corpus
from semantic_harvester.html_body import decode_html, extract_html_body, strip_signature
from tests.support import OfflineTestCase

READER_BODY_2017 = """<html><body><div class="article-body"><div id="readerBody">
<p>Rafa Silva marcou dois golos.</p>
<div id="escondec" class="lerMaisCont">Continuar a ler</div>
<div id="restText"><p>O Benfica venceu em casa.</p></div>
<div id="relacContainer"><a>Relacionados: outra notícia</a></div>
<p class="autorDetalhe">Autor: Lusa</p>
</div></div><div>Menu Sporting FC Porto</div></body></html>"""

TEXT_CONTAINER_2021 = """<html><head><meta charset="utf-8"></head><body>
<div class="text_container">Primeira linha do corpo.<br>Segunda linha.
<div class="pub_inside_text"><script>googletag.cmd.push(1)</script>PUB</div>
<div id="incontent">anúncio</div>Terceira linha.</div></body></html>"""

BODYBOX_AMP = """<html><body><div class="bodybox"><h1>Título</h1>
<h2 class="subtitle">Subtítulo</h2><figure class="imgDestaque"><img src="x">Foto: Créditos</figure>
<ul class="texto_socialShare"><li>Partilhar</li></ul>
<p>Corpo da notícia AMP.</p><div class="adbox">PUB</div>
<span class="texto_autor">Por Jornalista</span>
<ul class="texto_socialShare"><li>Partilhar</li></ul></div></body></html>"""

BODYBOX_AMP_IN_DETALHE = """<html><body><div class="bodybox"><p>Corpo verdadeiro.</p>
<amp-analytics><script type="application/json">{}</script></amp-analytics>
<h3>Relacionadas</h3><a>Outra notícia</a><h3>O Record recomenda para si</h3><a>Mais</a>
<h3>Últimas Notícias</h3><a>Ainda mais</a></div></body></html>"""


class ExtractHtmlBodyTests(unittest.TestCase):
    def test_reader_body_keeps_rest_text_and_drops_chrome(self) -> None:
        body = extract_html_body(READER_BODY_2017.encode("utf-8"))
        self.assertEqual(body.container, "readerBody")
        self.assertEqual(body.text, "Rafa Silva marcou dois golos. O Benfica venceu em casa.")

    def test_text_container_drops_ads(self) -> None:
        body = extract_html_body(TEXT_CONTAINER_2021.encode("utf-8"))
        self.assertEqual(body.container, "text_container")
        self.assertEqual(body.text, "Primeira linha do corpo. Segunda linha. Terceira linha.")

    def test_bodybox_keeps_subtitle_drops_title_photo_share_ads_author(self) -> None:
        body = extract_html_body(BODYBOX_AMP.encode("utf-8"))
        self.assertEqual(body.container, "bodybox")
        self.assertEqual(body.text, "Subtítulo Corpo da notícia AMP.")

    def test_chrome_blocks_inside_bodybox_are_cut(self) -> None:
        body = extract_html_body(BODYBOX_AMP_IN_DETALHE.encode("utf-8"))
        self.assertEqual(body.text, "Corpo verdadeiro.")

    def test_aux_in_latin1_with_unclosed_tags(self) -> None:
        html = ('<html><body><span class="v12_black"><aux>O Benfica venceu em Alvalade.'
                '<br>João marcou.<p>Fim da notícia.</aux></span><p>Rodapé</p></body></html>')
        body = extract_html_body(html.encode("latin-1"))
        self.assertEqual(body.container, "aux")
        self.assertEqual(body.text, "O Benfica venceu em Alvalade. João marcou. Fim da notícia.")

    def test_utf8_bytes_with_a_wrong_iso_declaration(self) -> None:
        html = ('<html><head><meta http-equiv="Content-Type" content="text/html; '
                'charset=iso-8859-1"></head><body><aux>Guimarães</aux></body></html>')
        self.assertEqual(extract_html_body(html.encode("utf-8")).text, "Guimarães")
        self.assertEqual(decode_html("Guimarães".encode("latin-1")), "Guimarães")

    def test_premium_marker_and_paywall_class_alone(self) -> None:
        premium = '<div class="text_container">Lead.</div><div class="container_assinatura">Assine</div>'
        self.assertTrue(extract_html_body(premium.encode()).premium)
        self.assertTrue(extract_html_body(b'<article class="article-premium"></article>').premium)
        self.assertFalse(extract_html_body(b'<div class="paywall text_container">Livre.</div>').premium)

    def test_page_without_known_container(self) -> None:
        body = extract_html_body(b"<html><body><div>Menu e mais nada</div></body></html>")
        self.assertFalse(body.found)
        self.assertIsNone(body.container)


class ValidationRegressionTests(unittest.TestCase):
    """Falhas da validação sobre 60 HTML reais (2026-10-22), uma por teste."""

    def test_longest_of_two_text_containers(self) -> None:
        html = ('<div class="text_container">Em direto Record Talks</div>'
                '<div class="text_container">O médio brasileiro Lucas Fernandes renovou '
                'o contrato com o clube por mais duas épocas.</div>')
        self.assertTrue(extract_html_body(html.encode()).text.startswith("O médio brasileiro"))

    def test_related_block_mid_body_is_skipped_not_cut(self) -> None:
        html = ('<div class="text_container">Antes do bloco.<div class="relacionadas">'
                '<h2 class="moduleTitle">Relacionadas</h2><a>Outra notícia</a></div>'
                'Rui Pedro Soares falou depois.</div>')
        self.assertEqual(extract_html_body(html.encode()).text,
                         "Antes do bloco. Rui Pedro Soares falou depois.")

    def test_2018_read_more_button(self) -> None:
        html = ('<div class="text_container">Corpo.<div class="lerMais">'
                '<a class="btLerMais">Continuar a ler</a></div></div>')
        self.assertEqual(extract_html_body(html.encode()).text, "Corpo.")

    def test_comment_button_and_detail_ads_inside_bodybox(self) -> None:
        html = ('<div class="bodybox"><p>Corpo da AMP.</p><div class="detalheAds">'
                '<div class="pub">PUB</div></div><div class="comentarBtn">Deixe o seu '
                'comentário</div><div class="comentarBtn">Comentar</div></div>')
        self.assertEqual(extract_html_body(html.encode()).text, "Corpo da AMP.")

    def test_photo_gallery_text_comes_from_subtitle(self) -> None:
        html = ('<div class="bodybox"><h1>Só à altura das lendas</h1><h2 class="subtitle">'
                'Cristiano Ronaldo no treino da seleção.</h2><div class="comentarBtn">'
                'Deixe o seu comentário</div></div>')
        self.assertEqual(extract_html_body(html.encode()).text,
                         "Cristiano Ronaldo no treino da seleção.")

    def test_cp1252_quotes_in_old_pages(self) -> None:
        raw = "<aux>no livro “Futebol e Rock N’Roll”, que – diz</aux>".encode("cp1252")
        self.assertEqual(extract_html_body(raw).text,
                         "no livro “Futebol e Rock N’Roll”, que – diz")


NOTICIA_ASPX_2009 = """<html><head><meta charset="utf-8"></head><body><table width="980"><tr>
<td width="180"><span class="apreto12n">Menu lateral</span></td>
<td width="600"><table width="100%"><tr><td>
<script>document.write('<scr'+'ipt src="pub.js"></scr'+'ipt>')</script>
<span class="apreto12n">12-03-2009</span>
<span class="apreto12n">Carolina Salgada disse ao juiz de instrução que não sabia de nada.<br><br>
Segundo a ex-companheira, o processo arrasta-se.<b>"À espera do MP"</b><br><br>O caso segue.</span>
</td></tr></table></td>
<td width="200"><form id="votacao"><span class="apreto12n">Concorda com a decisão do juiz de
instrução no processo Apito Dourado, tendo em conta tudo o que foi dito em tribunal até hoje
e as declarações de todas as testemunhas ouvidas ao longo das várias sessões?</span></form></td>
</tr></table></body></html>"""


class NoticiaAspxTests(unittest.TestCase):
    """noticia.aspx (2009): medição de 2026-10-22, 20 páginas, esqueleto em
    output/html_corpo_noticia_aspx.md (fora do Git)."""

    def test_longest_span_inside_the_main_column(self) -> None:
        body = extract_html_body(NOTICIA_ASPX_2009.encode("utf-8"))
        self.assertEqual(body.container, "apreto12n")
        self.assertTrue(body.text.startswith("Carolina Salgada disse ao juiz"))
        self.assertTrue(body.text.endswith("O caso segue."))
        self.assertNotIn("Concorda", body.text)
        self.assertNotIn("scr", body.text)

    def test_span_outside_the_main_column_is_not_a_body(self) -> None:
        html = '<table><tr><td width="200"><span class="apreto12n">Votação longa</span></td></tr></table>'
        self.assertFalse(extract_html_body(html.encode()).found)

    def test_aux_still_wins_in_noticia_asp(self) -> None:
        html = ('<table><tr><td width="600"><span class="apreto12n"><aux>Corpo 2007.</aux>'
                '</span></td></tr></table>')
        self.assertEqual(extract_html_body(html.encode()).container, "aux")


TN_1999 = """<form name="thisForm"><html><body><table width="600"><tr><td width="480">
<table width="100%"><tr><td><div align="left"><font size="2" color="#000000"><b>LATERAL DESILUDIDO
COM SEGUNDO PENALTY</b></font></div></td></tr>
<tr><td><div align="left"><font size="6" color="#FF0000"><b>Cristiano: «Ninguém sofre mais do que eu»</b></font></div></td></tr>
<tr><td><table width="100%"><tr><td><font size="3" color="#000000"><i><b>O lateral-esquerdo aveirense
lamenta o resultado.</b></i></font></td></tr></table></td></tr>
<tr><td><p><font size="2" face="Arial, Helvetica, sans-serif"><p>O LATERAL-ESQUERDO Cristiano foi o
réu da noite.<p>Este é, de resto, o segundo penálti da época.<p>CARLOS OLIVEIRA</font></td></tr>
<tr><td><font size="0"><b>Data:</b> <i>Terça-Feira, 23 de Novembro de 1999 19:50</i></font></td></tr>
</table></td><td width="120"><font size="2">Menu</font></td></tr></table></body></html></form>"""


class OldSite1999Tests(unittest.TestCase):
    """tn0cs/tn1cs.asp (1999–2000): medição de 2026-10-22, 40 páginas, esqueletos
    em output/html_corpo_tn0cs.md e output/html_corpo_tn1cs.md (fora do Git)."""

    def test_lead_and_body_without_title_date_kicker_and_signature(self) -> None:
        body = extract_html_body(TN_1999.encode("cp1252"))
        self.assertEqual(body.container, "td480")
        self.assertEqual(body.text, "O lateral-esquerdo aveirense lamenta o resultado. "
                         "O LATERAL-ESQUERDO Cristiano foi o réu da noite. "
                         "Este é, de resto, o segundo penálti da época.")

    def test_signatures_found_in_the_validation(self) -> None:
        """As 6 assinaturas que a primeira regra deixava (validação de 2026-10-22)."""
        cases = {
            '…ximo jogo." JOÃO PEDRO ABECASIS, JOÃO RUI RODRIGUES e LUÍS PEDRO SOUSA': '…ximo jogo."',
            "…o resto. ANTÓNIO JOSÉ OLIVEIRA e JOÃO ALMEIDA MOREIRA": "…o resto.",
            "…foi bom. PEDRO ALVES E P.": "…foi bom.",
            "…acabou. M.V.": "…acabou.",
            "…acabou. LUSA": "…acabou.",
            "…Boavista, 1 CARLOS ARSÉNIO": "…Boavista, 1",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(strip_signature(text), expected)

    def test_signatures_found_in_the_count_over_2352_pages(self) -> None:
        """Os dois padrões que ficavam na contagem de 2026-10-22 (18 páginas)."""
        cases = {
            '…manutenção." JOÃO LOPES, com LINO DE SOUSA': '…manutenção."',
            '…o resultado é justo." <p>MARCELO SOARES, com LUÍS LEAL': '…o resultado é justo."',
            '…o confortar." JOÃO CARTAXANA, com AUGUSTO LEITE E MARCO AURÉLIO': '…o confortar."',
            "…tendo apontado um total de 11 golos VÍTOR PINTO E RUI SOUSA": "…tendo apontado um total de 11 golos",
            "…se acertou ou não em cheio na aposta JOÃO ALMEIDA MOREIRA": "…se acertou ou não em cheio na aposta",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(strip_signature(text), expected)

    def test_text_that_is_not_a_signature_stays(self) -> None:
        for text in ("O LATERAL-ESQUERDO Cristiano foi bom.", "…golos. Fim do jogo, SL BENFICA ganhou",
                     "…ver a nota. A", "…marcou aos 30 minutos.", "…a vitória foi do FC PORTO",
                     "…ganhou o SL BENFICA", "…empatado com o BOAVISTA", "…golo de JARDEL"):
            with self.subTest(text=text):
                self.assertEqual(strip_signature(text), text)

    def test_table_body_keeps_its_names(self) -> None:
        html = ('<td width="480"><p><font size="2"><table><tr><td>1º Benfica B</td>'
                '<td>2º Sporting B</td></tr></table></font></td>')
        self.assertIn("1º Benfica B", extract_html_body(html.encode()).text)

    def test_font_rules_only_inside_the_old_column(self) -> None:
        html = '<aux><font size="2" color="#000000">Corpo de 2006.</font></aux>'
        self.assertEqual(extract_html_body(html.encode()).text, "Corpo de 2006.")


class BodyCorpusWithHtmlTests(OfflineTestCase):
    def capture(self, text: str, html: str | None) -> Capture:
        path = None
        if html is not None:
            path = self.root / f"{len(list(self.root.iterdir()))}.html"
            path.write_text(html, encoding="utf-8")
        return Capture("a", "1", None, None, None, text, html_path=path)

    def convert(self, capture: Capture) -> Capture:
        return to_body_corpus({"a": [capture]}, use_html=True)["a"][0]

    def test_c_prime_body_is_kept_when_found(self) -> None:
        text = "Título - Record - Jornal Record Menu Título O corpo pela c′."
        result = self.convert(self.capture(text, READER_BODY_2017))
        self.assertEqual(result.body_source, "c′")
        self.assertEqual(result.text, "Título O corpo pela c′.")

    def test_html_body_when_c_prime_finds_nothing(self) -> None:
        html = "<html><body><aux>Corpo antigo.</aux></body></html>"
        result = self.convert(self.capture(":.: Jornal Record :.: Corpo antigo.", html))
        self.assertEqual(result.body_source, "html:aux")
        self.assertEqual(result.text, "Corpo antigo.")
        self.assertTrue(result.in_layer1)

    def test_premium_has_no_body(self) -> None:
        text = "Título - Record - Jornal Record Título Só o lead."
        html = '<div class="text_container">Só o lead.</div><div class="container_assinatura"></div>'
        result = self.convert(self.capture(text, html))
        self.assertEqual(result.body_source, "premium")
        self.assertFalse(result.in_layer1)

    def test_no_body_anywhere(self) -> None:
        result = self.convert(self.capture(":.: Jornal Record :.:", None))
        self.assertEqual(result.body_source, "sem_corpo")
        self.assertFalse(result.in_layer1)

    def test_without_use_html_nothing_changes(self) -> None:
        capture = self.capture(":.: Jornal Record :.:", "<aux>Corpo antigo.</aux>")
        result = to_body_corpus({"a": [capture]})["a"][0]
        self.assertIsNone(result.body_source)
        self.assertTrue(result.body_missing)


if __name__ == "__main__":
    unittest.main()
