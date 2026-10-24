from __future__ import annotations

import csv
import unittest
from pathlib import Path

from semantic_harvester.corpus_classification import (
    REASON_ARTIGO, REASON_MULTIMEDIA, REASON_OBJECT_MOVED, REASON_SABERMAIS, REASON_URL_NOT_ARTICLE,
    article_url_scheme, canonical_key, classify, classify_corpus, run_classification,
)
from semantic_harvester.url_identity import normalize_for_grouping
from tests.support import OfflineTestCase

PHASE1_FIELDS = (
    "original_url", "tstamp", "title", "facets", "queries",
    "num_queries_matched", "divergent",
)


def write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def phase1_row(url: str, title: str, tstamp: str = "20180101000000") -> dict:
    return {"original_url": url, "tstamp": tstamp, "title": title, "facets": "modalidade",
            "queries": "futebol", "num_queries_matched": "1", "divergent": "False"}


class ArticleUrlSchemeTests(unittest.TestCase):
    """Sinal de caminho de URL que substitui "mais de 100 capturas" (2026-10-20)."""

    def test_current_site_detalhe_and_amp(self) -> None:
        self.assertEqual(article_url_scheme("https://www.record.pt/futebol/detalhe/x"), "detalhe")
        self.assertEqual(article_url_scheme("https://www.record.pt/futebol/amp/x"), "amp")
        self.assertEqual(article_url_scheme("https://www.record.pt/futebol/detalhe/AMP/x"), "detalhe")

    def test_old_site_content_id_plain_and_encoded(self) -> None:
        for url in ("http://www.record.pt/Futebol/interior.aspx?content_id=730429",
                    "http://www.record.pt/Futebol/interior.aspx?content_id/x3d730429"):
            self.assertEqual(article_url_scheme(url), "interior.aspx?content_id")
        self.assertIsNone(article_url_scheme("http://www.record.pt/interior.aspx?other=1"))

    def test_old_site_2010_2015_premium_is_an_article_but_galleries_are_not(self) -> None:
        self.assertEqual(
            article_url_scheme("https://record.xl.pt/futebol/nacional/1a_liga/sporting/interior_premium.aspx?content_id=924976"),
            "interior_premium.aspx?content_id")
        for url in ("https://record.xl.pt/multimedia/fotos/interior.aspx?content_id=1",
                    "https://record.xl.pt/galerias/videos/interior.aspx?content_id=1",
                    "https://record.xl.pt/multimedia/videos/interior_premium.aspx?content_id=1"):
            self.assertIsNone(article_url_scheme(url), url)
        # O /detalhe/ do site atual não é afetado por esta exclusão.
        self.assertEqual(article_url_scheme("https://www.record.pt/multimedia/detalhe/x"), "detalhe")

    def test_1999_2000_site_tn0cs_tn1cs(self) -> None:
        self.assertEqual(article_url_scheme("https://record.pt/tn0cs.asp?nid=40907"), "tn0cs.asp?nid")
        self.assertEqual(article_url_scheme("https://record.pt/TN1CS.asp?nid=56007"), "tn1cs.asp?nid")

    def test_2000_2009_site_noticia_and_shownews(self) -> None:
        self.assertEqual(article_url_scheme("https://record.pt/noticia.asp?id=1&idcanal=2"), "noticia.asp?id")
        self.assertEqual(article_url_scheme("https://record.pt/shownews.asp?id=7"), "shownews.asp?id")
        self.assertEqual(article_url_scheme("https://record.pt/noticia.aspx?id=3"), "noticia.aspx?id")
        # Outra query no mesmo ficheiro não é página de notícia.
        self.assertIsNone(article_url_scheme("https://record.pt/noticia.aspx?idcanal=3"))

    def test_other_pages_are_not_article_urls(self) -> None:
        for url in ("https://www.record.pt/futebol", "https://www.record.pt/jogos-em-direto/live/78799",
                    "https://record.pt/imprimir.asp?id=1", "https://record.pt/enviar.asp?id=1",
                    "https://record.pt/canal.asp?idcanal=1"):
            self.assertIsNone(article_url_scheme(url), url)


class ClassifyUnitTests(unittest.TestCase):
    """Testa classify() diretamente, sem passar pelos CSV agregados."""

    def test_detalhe_page_is_artigo_regardless_of_capture_count(self) -> None:
        for captures in (1, 500):
            result = classify("https://www.record.pt/futebol/detalhe/exemplo", "Exemplo", captures)
            self.assertTrue(result.is_artigo)
            self.assertEqual(result.reason, REASON_ARTIGO)

    def test_sabermais_profile_page_is_excluded(self) -> None:
        result = classify("https://www.record.pt/sabermais/exemplo-jogador", "Saber Mais")
        self.assertEqual((result.is_artigo, result.reason), (False, REASON_SABERMAIS))

    def test_object_moved_title_is_excluded_even_with_article_url(self) -> None:
        result = classify("http://www.record.pt/Futebol/Nacional/interior.aspx?content_id/x3d123456",
                          "Object moved")
        self.assertEqual((result.is_artigo, result.reason), (False, REASON_OBJECT_MOVED))

    def test_url_outside_article_schemes_is_excluded(self) -> None:
        result = classify("https://www.record.pt/futebol", "Futebol - Jornal Record")
        self.assertEqual((result.is_artigo, result.reason), (False, REASON_URL_NOT_ARTICLE))


class ClassifyCorpusTests(OfflineTestCase):
    """classify_corpus() só com o CSV da Fase 1 (sem Fase 2)."""

    def test_scheme_variants_merge_into_single_canonical_result(self) -> None:
        captures_csv = self.root / "captures.csv"
        url = "www.record.pt/multimedia/videos/detalhe/exemplo.html"
        write_csv(captures_csv, PHASE1_FIELDS, [
            phase1_row("http://" + url, "Vídeo", "20170702024006"),
            phase1_row("https://" + url, "Vídeo", "20170702024006"),
            phase1_row("https://" + url, "Vídeo", "20170801000000"),
        ])

        (result,) = classify_corpus(captures_csv)

        self.assertEqual(result.original_url, "https://" + url)
        self.assertEqual(result.variantes, "http://" + url)
        self.assertEqual(result.captures, 2)  # tstamps distintos da forma com mais capturas
        self.assertEqual(result.reason, REASON_ARTIGO)

    def test_mixed_corpus_classifies_each_category(self) -> None:
        captures_csv = self.root / "captures.csv"
        write_csv(captures_csv, PHASE1_FIELDS, [
            phase1_row("https://www.record.pt/futebol/detalhe/noticia-real", "Notícia real"),
            phase1_row("https://www.record.pt/sabermais/jogador-exemplo", "Saber Mais"),
            phase1_row("http://www.record.pt/Futebol/interior.aspx?content_id/x3d1", "Object moved"),
            phase1_row("https://record.pt/imprimir.asp?id=1", ":.: Jornal Record :.:"),
        ])

        reasons = {r.original_url: r.reason for r in classify_corpus(captures_csv)}

        self.assertEqual(reasons, {
            "https://www.record.pt/futebol/detalhe/noticia-real": REASON_ARTIGO,
            "https://www.record.pt/sabermais/jogador-exemplo": REASON_SABERMAIS,
            "http://www.record.pt/Futebol/interior.aspx?content_id/x3d1": REASON_OBJECT_MOVED,
            "https://record.pt/imprimir.asp?id=1": REASON_URL_NOT_ARTICLE,
        })

    def test_run_writes_labelled_outputs_and_not_the_125_article_classification(self) -> None:
        output = self.root / "output"
        output.mkdir()
        write_csv(output / "corpus_phase1_por_ano_captures.csv", PHASE1_FIELDS,
                  [phase1_row("https://www.record.pt/futebol/detalhe/x", "X")])

        results = run_classification(self.root, label="por_ano")

        self.assertEqual(len(results), 1)
        self.assertTrue((output / "corpus_classification_por_ano.csv").is_file())
        summary = (output / "corpus_classification_por_ano_summary.md").read_text("utf-8")
        self.assertIn("**Classificados como Artigo: 1**", summary)
        self.assertFalse((output / "corpus_classification.csv").exists())


class TrackingParameterTests(OfflineTestCase):
    """Variantes só em parâmetros de rastreio são o mesmo recurso; a query do
    site antigo (`content_id`) identifica artigos diferentes e é mantida."""

    BASE = "https://www.record.pt/record-mais/detalhe/exemplo"
    OLD = "http://www.record.pt/Futebol/interior.aspx?content_id/x3d"

    def test_canonical_key_ignores_only_tracking_parameters(self) -> None:
        self.assertEqual(canonical_key(self.BASE + "?ref=HP_A"), canonical_key(self.BASE))
        self.assertEqual(
            canonical_key(self.BASE + "?utm_medium=Social&utm_source=X&act=0&est=Aberto"),
            canonical_key(self.BASE),
        )
        self.assertNotEqual(canonical_key(self.OLD + "1"), canonical_key(self.OLD + "2"))
        self.assertEqual(canonical_key(self.BASE + "?page=2&ref=x"), canonical_key(self.BASE + "?page=2"))

    def test_tracking_variants_merge_and_content_ids_stay_apart(self) -> None:
        captures_csv = self.root / "captures.csv"
        a, b = self.BASE + "?ref=HP_A", self.BASE + "?ref=HP_B"
        rows = [phase1_row(a, "Exemplo", "20180101000000")]
        rows += [phase1_row(b, "Exemplo", f"2018010{day}000000") for day in range(1, 4)]
        rows += [phase1_row(self.OLD + "1", "Artigo 1"), phase1_row(self.OLD + "2", "Artigo 2")]
        write_csv(captures_csv, PHASE1_FIELDS, rows)

        results = classify_corpus(captures_csv)

        self.assertEqual(len(results), 3)
        merged = next(r for r in results if r.original_url.startswith(self.BASE))
        # Canónico: o URL real com mais capturas; capturas somadas; a outra forma como variante.
        self.assertEqual((merged.original_url, merged.captures, merged.variantes), (b, 4, a))
        self.assertTrue(all(r.is_artigo for r in results))


class ExcludeMultimediaTests(unittest.TestCase):
    VIDEO = "https://record.xl.pt/multimedia/videos/detalhe/lewandowski-provoca-benfica.html"
    TEXT = "https://record.xl.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/carrillo-assinou-ate-2021.html"

    def test_default_keeps_multimedia_detalhe_as_artigo(self) -> None:
        self.assertTrue(classify(self.VIDEO, "Vídeos").is_artigo)

    def test_option_excludes_videos_and_galleries_only(self) -> None:
        video = classify(self.VIDEO, "Vídeos", exclude_multimedia=True)
        self.assertEqual((video.is_artigo, video.reason), (False, REASON_MULTIMEDIA))
        gallery = classify("https://record.xl.pt/galerias/fotos/detalhe/x.html", "x", exclude_multimedia=True)
        self.assertEqual(gallery.reason, REASON_MULTIMEDIA)
        self.assertTrue(classify(self.TEXT, "Carrillo", exclude_multimedia=True).is_artigo)



class SameSiteHostTests(OfflineTestCase):
    """`record.pt` e `record.xl.pt` (com ou sem `www.`) são o mesmo site; outros
    subdomínios e caminhos diferentes continuam diferentes."""

    PATH = "/futebol/nacional/liga_honra/belenenses/interior.aspx?content_id=462145"

    def test_the_four_hosts_give_the_same_key(self) -> None:
        keys = {
            canonical_key(f"{scheme}://{host}{self.PATH}")
            for scheme in ("http", "https")
            for host in ("record.pt", "www.record.pt", "record.xl.pt", "www.record.xl.pt")
        }
        self.assertEqual(len(keys), 1)

    def test_other_hosts_and_other_paths_stay_apart(self) -> None:
        base = canonical_key("https://record.xl.pt" + self.PATH)
        self.assertNotEqual(base, canonical_key("https://liga.record.pt" + self.PATH))
        self.assertNotEqual(base, canonical_key("https://record.xl.pt/outro" + self.PATH))
        self.assertNotEqual(base, canonical_key("https://record.xl.pt" + self.PATH + "1"))
        self.assertEqual(normalize_for_grouping("https://www.record.xl.pt/a/?ref=x"),
                         normalize_for_grouping("http://record.pt/a"))
        self.assertNotEqual(normalize_for_grouping("https://record.pt.exemplo.com/a"),
                            normalize_for_grouping("https://record.pt/a"))

    def test_host_variants_merge_into_one_recurso(self) -> None:
        captures_csv = self.root / "captures.csv"
        a = "https://record.xl.pt" + self.PATH
        b = "https://www.record.pt" + self.PATH
        write_csv(captures_csv, PHASE1_FIELDS, [phase1_row(a, "Exemplo"), phase1_row(b, "Exemplo")])

        (result,) = classify_corpus(captures_csv)

        self.assertTrue(result.is_artigo)
        self.assertEqual(sorted([result.original_url, result.variantes]), sorted([a, b]))


if __name__ == "__main__":
    unittest.main()
