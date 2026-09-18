from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path

from rdflib import RDF

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_rdf import (
    build_corpus_graph, build_one_article_graph, load_captures_from_raw,
    load_retained_articles, normalize_captures_to_canonical_url,
    normalize_for_grouping, url_hash16,
)
from semantic_harvester.rdf_mapper import SDH, article_uri, capture_uri
from tests.support import FIXTURES, ORIGINAL_URL, OfflineTestCase


def write_version_history_raw(
    directory: Path, original_url: str, offset: int, response_items: list[dict],
    next_page: str | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    url_hash = url_hash16(original_url)
    path = directory / (
        f"version_history_{url_hash}_all-all_offset-{offset:06d}_max-50.json"
    )
    payload = {
        "estimated_nr_results": len(response_items),
        "next_page": next_page,
        "response_items": response_items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class UrlHashTests(unittest.TestCase):
    def test_matches_raw_python_sha256_prefix(self) -> None:
        url = "https://www.record.pt/exemplo"
        expected = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(url_hash16(url), expected)


class NormalizeForGroupingTests(unittest.TestCase):
    """Casos reais observados no raw de version_history da Fase 2/passo final."""

    def test_scheme_variant_normalizes_the_same(self) -> None:
        a = normalize_for_grouping("http://www.record.pt/futebol/detalhe/x.html")
        b = normalize_for_grouping("https://www.record.pt/futebol/detalhe/x.html")
        self.assertEqual(a, b)

    def test_double_slash_variant_normalizes_the_same(self) -> None:
        a = normalize_for_grouping("http://www.record.pt/entrevistas/detalhe/x.html")
        b = normalize_for_grouping("http://www.record.pt/entrevistas//detalhe/x.html")
        self.assertEqual(a, b)

    def test_trailing_slash_variant_normalizes_the_same(self) -> None:
        a = normalize_for_grouping("http://www.record.pt/sporting/detalhe/x.html")
        b = normalize_for_grouping("http://www.record.pt/sporting/detalhe/x.html/")
        self.assertEqual(a, b)

    def test_different_path_does_not_normalize_the_same(self) -> None:
        a = normalize_for_grouping("http://www.record.pt/futebol/detalhe/x.html")
        b = normalize_for_grouping("http://www.record.pt/futebol/detalhe/y.html")
        self.assertNotEqual(a, b)


class NormalizeCapturesToCanonicalUrlTests(unittest.TestCase):
    def test_rewrites_cosmetic_variants_and_keeps_all_captures(self) -> None:
        canonical = "http://www.record.pt/entrevistas/detalhe/exemplo.html"
        captures = [
            {"originalURL": canonical, "tstamp": "3"},
            {"originalURL": "http://www.record.pt/entrevistas//detalhe/exemplo.html",
             "tstamp": "2"},
            {"originalURL": "https://www.record.pt/entrevistas/detalhe/exemplo.html",
             "tstamp": "1"},
        ]

        normalized, dropped, rewritten = normalize_captures_to_canonical_url(
            captures, canonical
        )

        self.assertEqual(dropped, 0)
        self.assertEqual(rewritten, 2)
        self.assertEqual(len(normalized), 3)
        self.assertTrue(all(c["originalURL"] == canonical for c in normalized))
        self.assertEqual([c["tstamp"] for c in normalized], ["3", "2", "1"])

    def test_drops_captures_for_an_unrelated_url(self) -> None:
        canonical = "http://www.record.pt/futebol/detalhe/exemplo.html"
        captures = [
            {"originalURL": canonical, "tstamp": "1"},
            {"originalURL": "http://www.record.pt/futebol/detalhe/outro-artigo.html",
             "tstamp": "2"},
        ]

        normalized, dropped, rewritten = normalize_captures_to_canonical_url(
            captures, canonical
        )

        self.assertEqual(dropped, 1)
        self.assertEqual(rewritten, 0)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["tstamp"], "1")


class LoadCapturesFromRawTests(OfflineTestCase):
    def test_concatenates_multiple_pages_in_order(self) -> None:
        raw_dir = self.root / "version_history"
        write_version_history_raw(
            raw_dir, ORIGINAL_URL, offset=0,
            response_items=[{"originalURL": ORIGINAL_URL, "tstamp": "1"}],
        )
        write_version_history_raw(
            raw_dir, ORIGINAL_URL, offset=50,
            response_items=[{"originalURL": ORIGINAL_URL, "tstamp": "2"}],
        )

        captures = load_captures_from_raw(ORIGINAL_URL, raw_dir)

        self.assertEqual([c["tstamp"] for c in captures], ["1", "2"])

    def test_raises_file_not_found_when_no_raw_preserved(self) -> None:
        raw_dir = self.root / "version_history"
        raw_dir.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(FileNotFoundError):
            load_captures_from_raw(ORIGINAL_URL, raw_dir)


class LoadRetainedArticlesTests(OfflineTestCase):
    def test_only_rows_marked_as_artigo_are_returned(self) -> None:
        classification_csv = self.root / "corpus_classification.csv"
        with classification_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["original_url", "title", "captures", "is_artigo", "reason"],
            )
            writer.writeheader()
            writer.writerow({
                "original_url": "https://www.record.pt/mantido",
                "title": "Mantido", "captures": "3",
                "is_artigo": "True", "reason": "artigo",
            })
            writer.writerow({
                "original_url": "https://www.record.pt/sabermais/excluido",
                "title": "Saber Mais: Excluído", "captures": "300",
                "is_artigo": "False", "reason": "sabermais",
            })

        retained = load_retained_articles(classification_csv)

        self.assertEqual([row["original_url"] for row in retained], [
            "https://www.record.pt/mantido",
        ])


class BuildOneArticleGraphTests(OfflineTestCase):
    """Generaliza o mapeamento do M3 (um artigo, dado um manifesto já construído)
    para partir diretamente do raw de version_history preservado em disco."""

    def setUp(self) -> None:
        super().setUp()
        self.raw_content = (FIXTURES / "version_history/sample_history.json").read_bytes()
        self.payload = json.loads(self.raw_content)
        self.text_content = (FIXTURES / "texts/sample_text.txt").read_bytes()

        self.raw_dir = self.root / "data" / "raw"
        self.version_history_dir = self.raw_dir / "version_history"
        self.version_history_dir.mkdir(parents=True, exist_ok=True)
        write_version_history_raw(
            self.version_history_dir, ORIGINAL_URL, offset=0,
            response_items=self.payload["response_items"],
        )

    def test_generalized_mapping_matches_direct_history_pipeline_call(self) -> None:
        session = self.fixture_session(
            *((capture["linkToExtractedText"], self.text_content)
              for capture in self.payload["response_items"]),
        )
        client = ArquivoClient(data_dir=self.raw_dir, session=session)

        graph, result = build_one_article_graph(
            client,
            ORIGINAL_URL,
            "Artigo sintético para testes",
            self.version_history_dir,
            self.root,
        )

        self.assertIsNotNone(graph)
        self.assertIsNone(result.error)
        self.assertEqual(result.captures_used, 2)
        self.assertEqual(result.texts_downloaded_now, 2)
        self.assertEqual(result.texts_reused, 0)
        self.assertEqual(result.texts_failed, 0)

        self.assertIn((article_uri(ORIGINAL_URL), RDF.type, SDH.Artigo), graph)
        self.assertEqual(
            len(set(graph.subjects(RDF.type, SDH.CapturaArquivada))), 2,
        )
        self.assertIn(
            (capture_uri(ORIGINAL_URL, "20200101000000"), RDF.type, SDH.CapturaArquivada),
            graph,
        )

    def test_missing_raw_reports_error_without_raising(self) -> None:
        # Sessão sem respostas preparadas: confirma que nenhum pedido HTTP é
        # feito quando o raw de version_history está em falta.
        empty_session = self.fixture_session()
        client = ArquivoClient(data_dir=self.raw_dir, session=empty_session)

        graph, result = build_one_article_graph(
            client,
            "https://news.example.test/articles/sem-raw",
            "Sem raw preservado",
            self.version_history_dir,
            self.root,
        )

        self.assertIsNone(graph)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.captures_used, 0)


class BuildOneArticleGraphWithUrlVariantsTests(OfflineTestCase):
    """Regressão: version_history devolvendo variantes cosméticas de originalURL
    não deve rejeitar o manifesto (caso real encontrado em 32 dos 127 artigos
    retidos — ver docs/experiments.md)."""

    def test_scheme_and_slash_variants_are_merged_into_one_article(self) -> None:
        canonical = "http://www.record.pt/entrevistas/detalhe/exemplo-sintetico.html"
        raw_dir = self.root / "data" / "raw"
        version_history_dir = raw_dir / "version_history"

        def item(url: str, tstamp: str) -> dict:
            return {
                "originalURL": url, "tstamp": tstamp,
                "title": url, "linkToArchive": f"https://archive.example.test/{tstamp}",
                "linkToExtractedText": f"https://archive.example.test/text/{tstamp}",
                "mimeType": "text/html", "contentLength": 100, "digest": f"DIGEST-{tstamp}",
                "encoding": "UTF-8", "collection": "SYNTHETIC", "statusCode": 200,
            }

        response_items = [
            item(canonical, "20171025042728"),
            item(canonical.replace("/entrevistas/", "/entrevistas//"), "20171013025023"),
            item(canonical.replace("http://", "https://"), "20171006052208"),
        ]
        write_version_history_raw(version_history_dir, canonical, offset=0, response_items=response_items)

        session = self.fixture_session(
            *((it["linkToExtractedText"], b"texto sintetico") for it in response_items),
        )
        client = ArquivoClient(data_dir=raw_dir, session=session)

        graph, result = build_one_article_graph(
            client, canonical, "Artigo sintético", version_history_dir, self.root,
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.captures_used, 3)
        self.assertEqual(result.captures_url_variants_normalized, 2)
        self.assertEqual(result.captures_dropped_mismatched_url, 0)
        self.assertEqual(
            len(set(graph.subjects(RDF.type, SDH.CapturaArquivada))), 3,
        )
        self.assertEqual(
            len(set(graph.subjects(RDF.type, SDH.Artigo))), 1,
        )
        for tstamp in ("20171025042728", "20171013025023", "20171006052208"):
            self.assertIn(
                (capture_uri(canonical, tstamp), RDF.type, SDH.CapturaArquivada), graph,
            )


class BuildCorpusGraphTests(OfflineTestCase):
    """Testa a fusão de vários artigos num único grafo (não só o caso de um artigo)."""

    def test_merges_two_articles_into_one_graph(self) -> None:
        raw_dir = self.root / "data" / "raw"
        version_history_dir = raw_dir / "version_history"
        output_dir = self.root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        url_a = "https://news.example.test/articles/artigo-a"
        url_b = "https://news.example.test/articles/artigo-b"

        capture_a = {
            "originalURL": url_a, "tstamp": "20200101000000",
            "title": "Artigo A", "linkToArchive": "https://archive.example.test/a",
            "linkToExtractedText": "https://archive.example.test/text/a",
            "mimeType": "text/html", "contentLength": 111, "digest": "DIGEST-A",
            "encoding": "UTF-8", "collection": "SYNTHETIC", "statusCode": 200,
        }
        capture_b = {
            "originalURL": url_b, "tstamp": "20200303000000",
            "title": "Artigo B", "linkToArchive": "https://archive.example.test/b",
            "linkToExtractedText": "https://archive.example.test/text/b",
            "mimeType": "text/html", "contentLength": 222, "digest": "DIGEST-B",
            "encoding": "UTF-8", "collection": "SYNTHETIC", "statusCode": 200,
        }
        write_version_history_raw(version_history_dir, url_a, offset=0, response_items=[capture_a])
        write_version_history_raw(version_history_dir, url_b, offset=0, response_items=[capture_b])

        classification_csv = output_dir / "corpus_classification.csv"
        with classification_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["original_url", "title", "captures", "is_artigo", "reason"],
            )
            writer.writeheader()
            writer.writerow({
                "original_url": url_a, "title": "Artigo A",
                "captures": "1", "is_artigo": "True", "reason": "artigo",
            })
            writer.writerow({
                "original_url": url_b, "title": "Artigo B",
                "captures": "1", "is_artigo": "True", "reason": "artigo",
            })

        text_content = b"texto sintetico"
        session = self.fixture_session(
            ("https://archive.example.test/text/a", text_content),
            ("https://archive.example.test/text/b", text_content),
        )
        client = ArquivoClient(data_dir=raw_dir, session=session)

        graph, results = build_corpus_graph(self.root, client=client)

        self.assertEqual(len(results), 2)
        self.assertEqual({r.original_url for r in results}, {url_a, url_b})
        self.assertEqual(
            len(set(graph.subjects(RDF.type, SDH.Artigo))), 2,
        )
        self.assertIn((article_uri(url_a), RDF.type, SDH.Artigo), graph)
        self.assertIn((article_uri(url_b), RDF.type, SDH.Artigo), graph)
        # A editora é partilhada entre os dois artigos, não duplicada.
        self.assertEqual(
            len(set(graph.subjects(RDF.type, SDH.Jornal))), 1,
        )


if __name__ == "__main__":
    unittest.main()
