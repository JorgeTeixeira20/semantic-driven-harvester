from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.corpus_rdf import (
    CacheOnlyClient, build_corpus_graph, build_one_article_graph,
    load_captures_from_raw, load_retained_articles, main as corpus_rdf_main,
    normalize_captures_to_canonical_url, normalize_for_grouping,
    rebuild_graph_offline, rebuild_offline, url_hash16,
)
from semantic_harvester.rdf_mapper import (
    SDH, article_uri, capture_uri, extracted_text_uri,
)
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

    def test_tracking_parameters_are_ignored_but_content_ids_are_not(self) -> None:
        base = "https://www.record.pt/record-mais/detalhe/x"
        self.assertEqual(normalize_for_grouping(base + "?ref=HP_A"), normalize_for_grouping(base))
        old = "http://www.record.pt/Futebol/interior.aspx?content_id/x3d"
        self.assertNotEqual(normalize_for_grouping(old + "1"), normalize_for_grouping(old + "2"))

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

    def test_resumes_without_repeating_already_processed_articles(self) -> None:
        """Regressão: sem isto, uma retoma reprocessava todos os artigos desde
        o início (incluindo novas tentativas de rede para os já concluídos),
        nunca avançando o suficiente entre cortes por falta de memória."""

        raw_dir = self.root / "data" / "raw"
        version_history_dir = raw_dir / "version_history"
        output_dir = self.root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        url_a = "https://news.example.test/articles/retoma-a"
        url_b = "https://news.example.test/articles/retoma-b"
        capture_a = {
            "originalURL": url_a, "tstamp": "20200101000000",
            "title": "Artigo A", "linkToArchive": "https://archive.example.test/ra",
            "linkToExtractedText": "https://archive.example.test/text/ra",
            "mimeType": "text/html", "contentLength": 111, "digest": "DIGEST-RA",
            "encoding": "UTF-8", "collection": "SYNTHETIC", "statusCode": 200,
        }
        capture_b = {
            "originalURL": url_b, "tstamp": "20200303000000",
            "title": "Artigo B", "linkToArchive": "https://archive.example.test/rb",
            "linkToExtractedText": "https://archive.example.test/text/rb",
            "mimeType": "text/html", "contentLength": 222, "digest": "DIGEST-RB",
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
        first_session = self.fixture_session(
            ("https://archive.example.test/text/ra", text_content),
            ("https://archive.example.test/text/rb", text_content),
        )
        first_client = ArquivoClient(data_dir=raw_dir, session=first_session)
        first_graph, first_results = build_corpus_graph(self.root, client=first_client)

        self.assertEqual(len(first_results), 2)
        self.assertEqual(len(set(first_graph.subjects(RDF.type, SDH.Artigo))), 2)

        # Sessão sem respostas preparadas: qualquer pedido HTTP nesta segunda
        # chamada falha a asserção da fixture, provando que nada foi repetido.
        second_session = self.fixture_session()
        second_client = ArquivoClient(data_dir=raw_dir, session=second_session)
        second_graph, second_results = build_corpus_graph(self.root, client=second_client)

        self.assertEqual(len(second_results), 2)
        self.assertEqual({r.original_url for r in second_results}, {url_a, url_b})
        self.assertEqual(len(set(second_graph.subjects(RDF.type, SDH.Artigo))), 2)
        self.assertIn((article_uri(url_a), RDF.type, SDH.Artigo), second_graph)
        self.assertIn((article_uri(url_b), RDF.type, SDH.Artigo), second_graph)


REBUILD_URL = "https://news.example.test/articles/reconstrucao"
REBUILD_TSTAMPS = ("20200101000000", "20200202000000")


class OfflineRebuildTestCase(OfflineTestCase):
    """Raiz sintética com um artigo de duas capturas e uma cache de textos vazia."""

    def setUp(self) -> None:
        super().setUp()
        self.raw_dir = self.root / "data" / "raw"
        self.output_dir = self.root / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        items = [
            {
                "originalURL": REBUILD_URL, "tstamp": tstamp, "title": REBUILD_URL,
                "linkToArchive": f"https://archive.example.test/{tstamp}",
                "mimeType": "text/html", "contentLength": 100,
                "digest": f"DIGEST-{tstamp}", "encoding": "UTF-8",
                "collection": "SYNTHETIC", "statusCode": 200,
            }
            for tstamp in REBUILD_TSTAMPS
        ]
        write_version_history_raw(
            self.raw_dir / "version_history", REBUILD_URL, offset=0, response_items=items,
        )
        with (self.output_dir / "corpus_classification.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["original_url", "title", "captures", "is_artigo", "reason"],
            )
            writer.writeheader()
            writer.writerow({
                "original_url": REBUILD_URL, "title": "Artigo de reconstrução",
                "captures": "2", "is_artigo": "True", "reason": "artigo",
            })
        (self.raw_dir / "texts").mkdir(parents=True, exist_ok=True)

    def cache_text(self, tstamp: str, content: bytes = b"texto sintetico") -> Path:
        name = ArquivoClient._text_filename({"originalURL": REBUILD_URL, "tstamp": tstamp})
        path = self.raw_dir / "texts" / name
        path.write_bytes(content)
        return path

    def write_retry_report(self, *outcomes: str) -> None:
        with (self.output_dir / "corpus_text_retry_report.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=["original_url", "tstamp", "outcome"])
            writer.writeheader()
            for tstamp, outcome in zip(REBUILD_TSTAMPS, outcomes):
                writer.writerow({"original_url": REBUILD_URL, "tstamp": tstamp, "outcome": outcome})

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file() and path.parts[-2] != "version_history"
        }


class CacheOnlyClientTests(OfflineRebuildTestCase):
    def test_cached_text_is_available_without_any_request(self) -> None:
        cached = self.cache_text(REBUILD_TSTAMPS[0], b"ja na cache")
        client = CacheOnlyClient(data_dir=self.raw_dir)

        result = client.download_extracted_text(
            {"originalURL": REBUILD_URL, "tstamp": REBUILD_TSTAMPS[0]},
            skip_existing=True, derive_url_when_missing=True,
        )

        self.assertTrue(result.success)
        self.assertFalse(result.downloaded)
        self.assertEqual(result.path, cached)
        self.assertEqual(result.size_bytes, len(b"ja na cache"))

    def test_missing_text_is_unavailable_without_any_request(self) -> None:
        client = CacheOnlyClient(data_dir=self.raw_dir)

        result = client.download_extracted_text(
            {"originalURL": REBUILD_URL, "tstamp": REBUILD_TSTAMPS[0]},
            skip_existing=True, derive_url_when_missing=True,
        )

        self.assertFalse(result.success)
        self.assertIsNone(result.path)
        self.assertIn("offline", result.error)

    def test_the_underlying_session_refuses_network(self) -> None:
        client = CacheOnlyClient(data_dir=self.raw_dir)
        with self.assertRaises(RuntimeError):
            client.session.get("https://arquivo.pt/textextracted?m=x")


class RebuildGraphOfflineTests(OfflineRebuildTestCase):
    def test_new_cached_text_adds_only_that_texts_triples(self) -> None:
        """Um texto aparece na cache entre duas construções: só os triplos desse
        texto são acrescentados (o teste proposto em docs/experiments.md)."""

        self.cache_text(REBUILD_TSTAMPS[0])
        first, first_results = rebuild_graph_offline(self.root)
        self.assertEqual(len(set(first.subjects(RDF.type, SDH.TextoExtraido))), 1)
        self.assertEqual(first_results[0].texts_failed, 1)

        new_path = self.cache_text(REBUILD_TSTAMPS[1])
        second, second_results = rebuild_graph_offline(self.root)

        self.assertEqual(len(first - second), 0)
        added = set(second - first)
        capture = capture_uri(REBUILD_URL, REBUILD_TSTAMPS[1])
        text = extracted_text_uri(REBUILD_URL, REBUILD_TSTAMPS[1])
        relative = new_path.relative_to(self.root).as_posix()
        self.assertEqual(added, {
            (capture, SDH.temTextoExtraido, text),
            (text, RDF.type, SDH.TextoExtraido),
            (text, SDH.filePath, Literal(relative, datatype=XSD.string)),
        })
        self.assertEqual(second_results[0].texts_failed, 0)
        self.assertEqual(second_results[0].texts_downloaded_now, 0)
        self.assertEqual(second_results[0].texts_reused, 2)


class RebuildOfflineTests(OfflineRebuildTestCase):
    def check_map(self, checks) -> dict[str, bool | None]:
        return {check.name: check.passed for check in checks}

    def test_first_rebuild_writes_outputs_that_reload_identically(self) -> None:
        self.cache_text(REBUILD_TSTAMPS[0])

        checks, results, graph = rebuild_offline(self.root)

        self.assertNotIn(False, self.check_map(checks).values())
        reloaded = Graph().parse(self.output_dir / "corpus_articles.ttl", format="turtle")
        self.assertEqual(set(reloaded), set(graph))
        with (self.output_dir / "corpus_rdf_report.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["texts_reused"], rows[0]["texts_failed"]), ("1", "1"))
        summary = (self.output_dir / "corpus_rdf_summary.md").read_text(encoding="utf-8")
        self.assertIn("offline", summary)
        # Uma retoma normal encontra tudo concluído e reconstrói o mesmo grafo.
        resumed, _ = build_corpus_graph(self.root)
        self.assertEqual(set(resumed), set(graph))

    def test_recovered_text_is_incorporated_and_all_checks_pass(self) -> None:
        self.cache_text(REBUILD_TSTAMPS[0])
        rebuild_offline(self.root)
        before = Graph().parse(self.output_dir / "corpus_articles.ttl", format="turtle")

        self.cache_text(REBUILD_TSTAMPS[1])
        self.write_retry_report("failed", "success")
        checks, _, _ = rebuild_offline(self.root)

        states = self.check_map(checks)
        self.assertEqual(states["textos_esperados"], True)
        self.assertEqual(states["antigo_contido_no_novo"], True)
        self.assertEqual(states["diferenca_so_textos"], True)
        self.assertNotIn(False, states.values())
        after = Graph().parse(self.output_dir / "corpus_articles.ttl", format="turtle")
        self.assertEqual(len(before - after), 0)
        self.assertEqual(len(after - before), 3)

    def test_check_only_does_not_write_anything(self) -> None:
        self.cache_text(REBUILD_TSTAMPS[0])
        rebuild_offline(self.root)
        self.cache_text(REBUILD_TSTAMPS[1])
        before = self.snapshot()

        checks, _, _ = rebuild_offline(self.root, apply=False)

        self.assertNotIn(False, self.check_map(checks).values())
        self.assertEqual(self.snapshot(), before)

    def test_failed_verification_leaves_existing_outputs_untouched(self) -> None:
        self.cache_text(REBUILD_TSTAMPS[0])
        removable = self.cache_text(REBUILD_TSTAMPS[1])
        rebuild_offline(self.root)
        # Cache incompleta: um texto que estava no grafo antigo desapareceu.
        removable.unlink()
        before = self.snapshot()

        checks, _, new_graph = rebuild_offline(self.root)

        states = self.check_map(checks)
        self.assertEqual(states["antigo_contido_no_novo"], False)
        self.assertEqual(len(set(new_graph.subjects(RDF.type, SDH.TextoExtraido))), 1)
        self.assertEqual(self.snapshot(), before)

    def test_unexpected_text_count_fails_the_retry_report_check(self) -> None:
        self.cache_text(REBUILD_TSTAMPS[0])
        rebuild_offline(self.root)
        self.cache_text(REBUILD_TSTAMPS[1])
        # O relatório afirma 0 recuperadas, mas apareceu um texto novo.
        self.write_retry_report("failed", "failed")

        checks, _, _ = rebuild_offline(self.root, apply=False)

        self.assertEqual(self.check_map(checks)["textos_esperados"], False)

    def test_check_only_requires_rebuild_offline(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            corpus_rdf_main(["--check-only"])
        self.assertEqual(raised.exception.code, 2)


VARIANT_A = "https://news.example.test/record-mais/detalhe/variante?ref=HP_A"
VARIANT_B = "https://news.example.test/record-mais/detalhe/variante?ref=HP_B"


class TrackingVariantsTests(OfflineTestCase):
    """Um artigo cujas capturas estão no raw de duas variantes `?ref=…`."""

    def setUp(self) -> None:
        super().setUp()
        self.raw_dir = self.root / "data" / "raw"
        self.output_dir = self.root / "output"
        self.output_dir.mkdir(parents=True)
        (self.raw_dir / "texts").mkdir(parents=True)

        def item(url: str, tstamp: str) -> dict:
            return {"originalURL": url, "tstamp": tstamp, "title": url,
                    "linkToArchive": f"https://archive.example.test/{tstamp}",
                    "mimeType": "text/html", "contentLength": 100, "digest": f"D-{tstamp}",
                    "encoding": "UTF-8", "collection": "SYNTHETIC", "statusCode": 200}

        write_version_history_raw(self.raw_dir / "version_history", VARIANT_A, 0,
                                  [item(VARIANT_A, "20200101000000"), item(VARIANT_A, "20200303000000")])
        write_version_history_raw(self.raw_dir / "version_history", VARIANT_B, 0,
                                  [item(VARIANT_B, "20200202000000"), item(VARIANT_B, "20200303000000")])
        # Os textos ficaram em cache com o hash de cada variante (eram artigos separados).
        for url, tstamp in ((VARIANT_A, "20200101000000"), (VARIANT_B, "20200202000000")):
            name = ArquivoClient._text_filename({"originalURL": url, "tstamp": tstamp})
            (self.raw_dir / "texts" / name).write_bytes(b"texto")

    def write_classification(self, rows: list[dict]) -> None:
        with (self.output_dir / "corpus_classification.csv").open("w", encoding="utf-8", newline="") as h:
            writer = csv.DictWriter(h, fieldnames=["original_url", "title", "captures", "is_artigo",
                                                   "reason", "variantes"])
            writer.writeheader()
            writer.writerows(rows)

    def test_captures_of_all_variants_are_merged_and_cached_texts_found(self) -> None:
        graph, result = build_one_article_graph(
            CacheOnlyClient(data_dir=self.raw_dir), VARIANT_B, "Variante",
            self.raw_dir / "version_history", self.root, [VARIANT_A],
        )
        self.assertIsNone(result.error)
        # 2 + 2 capturas, uma repetida nas duas variantes.
        self.assertEqual(result.captures_used, 3)
        self.assertEqual(len(set(graph.subjects(RDF.type, SDH.CapturaArquivada))), 3)
        self.assertEqual({str(o) for o in graph.objects(None, SDH.originalURL)}, {VARIANT_B})
        # O texto guardado com o hash da variante A continua a ser encontrado.
        self.assertEqual(result.texts_reused, 2)

    def test_rebuild_merging_variants_passes_checks_and_detects_lost_articles(self) -> None:
        self.write_classification([
            {"original_url": VARIANT_A, "title": "Variante", "captures": "2", "is_artigo": "True",
             "reason": "artigo", "variantes": ""},
            {"original_url": VARIANT_B, "title": "Variante", "captures": "2", "is_artigo": "True",
             "reason": "artigo", "variantes": ""},
        ])
        rebuild_offline(self.root)  # estado antigo: dois artigos separados
        self.write_classification([
            {"original_url": VARIANT_B, "title": "Variante", "captures": "3", "is_artigo": "True",
             "reason": "artigo", "variantes": VARIANT_A},
        ])

        checks, _, graph = rebuild_offline(self.root, apply=False)

        states = {c.name: c.passed for c in checks}
        self.assertNotIn(False, states.values(), checks)
        self.assertTrue(states["variantes_fundidas"])
        self.assertTrue(states["ficheiros_de_texto_preservados"])
        self.assertEqual(len(set(graph.subjects(RDF.type, SDH.Artigo))), 1)

        # Sem declarar a variante, o desaparecimento da variante A é um artigo perdido.
        self.write_classification([
            {"original_url": VARIANT_B, "title": "Variante", "captures": "2", "is_artigo": "True",
             "reason": "artigo", "variantes": ""},
        ])
        checks, _, _ = rebuild_offline(self.root, apply=False)
        states = {c.name: c.passed for c in checks}
        self.assertFalse(states["variantes_fundidas"])
        self.assertFalse(states["antigo_contido_no_novo"])


if __name__ == "__main__":
    unittest.main()
