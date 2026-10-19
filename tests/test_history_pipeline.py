from __future__ import annotations

import json
import unittest

import requests

from rdflib import Graph, Literal, RDF, XSD
from rdflib.compare import isomorphic

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.history_pipeline import (
    TEXT_POLICY_ALL, TEXT_POLICY_FIRST, build_manifest_records, calculate_metrics,
    collect_all_captures, write_manifest,
)
from semantic_harvester.rdf_mapper import (
    SDH, article_uri, build_article_history_graph, capture_uri,
    extracted_text_uri, load_manifest, resource_uri,
)
from tests.support import FIXTURES, ORIGINAL_URL, FixtureSession, OfflineTestCase


class HistoryPipelineTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.raw_content = (FIXTURES / "version_history/sample_history.json").read_bytes()
        self.payload = json.loads(self.raw_content)
        self.text_content = (FIXTURES / "texts/sample_text.txt").read_bytes()
        self.session = self.fixture_session(
            (ArquivoClient.SEARCH_URL, self.raw_content),
            *((capture["linkToExtractedText"], self.text_content)
              for capture in self.payload["response_items"]),
        )
        self.client = ArquivoClient(data_dir=self.root / "responses", session=self.session)
        self.captures, self.raw_paths, self.estimated = collect_all_captures(
            self.client, original_url=ORIGINAL_URL,
        )
        self.records = build_manifest_records(
            self.client, self.captures, self.root, text_policy=TEXT_POLICY_ALL
        )
        self.manifest_path = self.root / "captures.jsonl"
        write_manifest(self.records, self.manifest_path)
        self.graph = build_article_history_graph(
            load_manifest(self.manifest_path), self.captures[0]["title"], self.root,
        )

    def test_version_history_raw_is_processable(self) -> None:
        self.assertEqual(self.captures, self.payload["response_items"])
        self.assertEqual(len(self.captures), 2)
        self.assertEqual(self.estimated, 2)
        self.assertEqual(dict(self.session.calls[0][1]["params"]), {
            "versionHistory": ORIGINAL_URL, "maxItems": 50, "offset": 0,
        })

    def test_version_history_preserves_raw_bytes(self) -> None:
        self.assertEqual(len(self.raw_paths), 1)
        self.assertEqual(self.raw_paths[0].read_bytes(), self.raw_content)

    def test_version_history_pagination(self) -> None:
        pages = [
            {"estimated_nr_results": "2",
             "next_page": "https://archive.example.test/next",
             "response_items": self.captures[:1]},
            {"estimated_nr_results": "2", "next_page": None,
             "response_items": self.captures[1:]},
        ]
        contents = [json.dumps(page, ensure_ascii=False).encode("utf-8") for page in pages]
        session = self.fixture_session(
            *((ArquivoClient.SEARCH_URL, content) for content in contents),
        )
        client = ArquivoClient(data_dir=self.root / "paginated", session=session)
        captures, paths, estimated = collect_all_captures(
            client, original_url=ORIGINAL_URL, page_size=1,
        )
        self.assertEqual(captures, self.captures)
        self.assertEqual(estimated, 2)
        self.assertEqual(
            [dict(call[1]["params"])["offset"] for call in session.calls], [0, 1],
        )
        self.assertEqual([path.read_bytes() for path in paths], contents)

    def test_pagination_ignores_low_estimated_total(self) -> None:
        """estimated_nr_results não deve parar a paginação (Experiência 1).

        Regressão para o bug corrigido em 2026-09-18: collect_all_captures()
        usava `len(captures) >= estimated_total` como condição de paragem,
        apesar de a Experiência 1 já ter mostrado que a estimativa da API
        não é uma contagem fiável. Com `estimated_nr_results=1` reportado em
        todas as páginas mas 3 capturas reais disponíveis (páginas cheias
        com `next_page`, seguidas de uma página final sem `next_page`), a
        paginação deve continuar até à terceira página, não parar depois da
        primeira. `fixture_session` falha o teste se alguma das três
        respostas preparadas ficar por consumir.
        """
        pages = [
            {"estimated_nr_results": "1",
             "next_page": "https://archive.example.test/next",
             "response_items": [self.captures[0]]},
            {"estimated_nr_results": "1",
             "next_page": "https://archive.example.test/next",
             "response_items": [self.captures[1]]},
            {"estimated_nr_results": "1", "next_page": None,
             "response_items": [self.captures[0]]},
        ]
        contents = [json.dumps(page, ensure_ascii=False).encode("utf-8") for page in pages]
        session = self.fixture_session(
            *((ArquivoClient.SEARCH_URL, content) for content in contents),
        )
        client = ArquivoClient(data_dir=self.root / "low-estimate", session=session)
        captures, paths, estimated = collect_all_captures(
            client, original_url=ORIGINAL_URL, page_size=1,
        )
        self.assertEqual(len(captures), 3)
        self.assertEqual(estimated, 1)
        self.assertEqual(
            [dict(call[1]["params"])["offset"] for call in session.calls], [0, 1, 2],
        )
        self.assertEqual(len(paths), 3)

    def test_all_captures_share_article_id(self) -> None:
        self.assertEqual(len(self.records), 2)
        self.assertEqual({record["article_id"] for record in self.records}, {
            "b366ac3c8369c859429913e0d91bc312b2af8a516af137d73dd785506ec94f87",
        })
        self.assertEqual({record["original_url"] for record in self.records}, {ORIGINAL_URL})
        self.assertEqual(
            {record["tstamp"] for record in self.records},
            {"20200101000000", "20200202030405"},
        )

    def test_manifest_metadata_matches_source(self) -> None:
        self.assertEqual(load_manifest(self.manifest_path), self.records)
        fields = {
            "original_url": "originalURL", "tstamp": "tstamp",
            "archive_url": "linkToArchive", "title": "title", "digest": "digest",
            "content_length": "contentLength", "mime_type": "mimeType",
            "encoding": "encoding", "collection": "collection",
        }
        for record, capture in zip(self.records, self.captures, strict=True):
            for target, source in fields.items():
                self.assertEqual(record[target], capture[source], target)
            self.assertEqual(record["status_code"], 200)
            self.assertTrue(record["text_download_success"])
            self.assertTrue(record["text_downloaded_now"])
            self.assertEqual(record["text_size_bytes"], len(self.text_content))
            self.assertIsNone(record["text_error"])
        self.assertEqual([record["captured_at"] for record in self.records], [
            "2020-01-01T00:00:00Z", "2020-02-02T03:04:05Z",
        ])

    def test_rdf_identifiers_are_deterministic(self) -> None:
        rebuilt = build_article_history_graph(
            list(reversed(self.records)), self.captures[0]["title"], self.root,
        )
        self.assertTrue(isomorphic(rebuilt, self.graph))
        self.assertEqual(set(self.graph.subjects(RDF.type, SDH.CapturaArquivada)), {
            capture_uri(ORIGINAL_URL, "20200101000000"),
            capture_uri(ORIGINAL_URL, "20200202030405"),
        })

    def test_history_graph_has_expected_instance_counts(self) -> None:
        for rdf_class, count in (
            (SDH.Artigo, 1), (SDH.Jornal, 1), (SDH.RecursoWeb, 1),
            (SDH.CapturaArquivada, 2), (SDH.TextoExtraido, 2),
        ):
            self.assertEqual(len(set(self.graph.subjects(RDF.type, rdf_class))), count)
        self.assertEqual(len(self.graph), 38)

    def test_history_graph_links_and_capture_metadata(self) -> None:
        resource = resource_uri(ORIGINAL_URL)
        self.assertIn((article_uri(ORIGINAL_URL), SDH.temRecursoWeb, resource), self.graph)
        self.assertIn(
            (article_uri(ORIGINAL_URL), SDH.publicadoPor, SDH["newspaper/record"]),
            self.graph,
        )
        for record in self.records:
            capture = capture_uri(ORIGINAL_URL, record["tstamp"])
            text = extracted_text_uri(ORIGINAL_URL, record["tstamp"])
            self.assertIn((resource, SDH.temCaptura, capture), self.graph)
            self.assertEqual(list(self.graph.objects(capture, SDH.temTextoExtraido)), [text])
            self.assertIn((text, RDF.type, SDH.TextoExtraido), self.graph)
            for field, predicate, datatype in (
                ("tstamp", SDH.tstamp, XSD.string),
                ("captured_at", SDH.capturedAt, XSD.dateTime),
                ("archive_url", SDH.archiveURL, XSD.anyURI),
                ("title", SDH.title, XSD.string),
                ("digest", SDH.digest, XSD.string),
                ("content_length", SDH.contentLength, XSD.nonNegativeInteger),
                ("mime_type", SDH.mimeType, XSD.string),
                ("encoding", SDH.encoding, XSD.string),
                ("collection", SDH.collection, XSD.string),
                ("status_code", SDH.statusCode, XSD.integer),
            ):
                self.assertIn(
                    (capture, predicate, Literal(record[field], datatype=datatype)),
                    self.graph,
                )

    def test_every_rdf_text_points_to_real_file(self) -> None:
        texts = list(self.graph.subjects(RDF.type, SDH.TextoExtraido))
        self.assertEqual(len(texts), 2)
        for text in texts:
            file_path = self.graph.value(text, SDH.filePath)
            self.assertIsNotNone(file_path)
            path = self.root / str(file_path)
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), self.text_content)

    def test_existing_text_is_reused_without_request_or_byte_changes(self) -> None:
        request_count = len(self.session.calls)
        records = build_manifest_records(
            self.client, self.captures, self.root, text_policy=TEXT_POLICY_ALL
        )
        self.assertEqual(len(self.session.calls), request_count)
        for original, reused in zip(self.records, records, strict=True):
            self.assertEqual(reused, {**original, "text_downloaded_now": False})
            self.assertEqual(
                (self.root / reused["extracted_text_path"]).read_bytes(), self.text_content,
            )

    def test_generated_turtle_can_be_loaded_again(self) -> None:
        path = self.root / "history.ttl"
        self.graph.serialize(destination=path, format="turtle")
        self.assertTrue(isomorphic(Graph().parse(path, format="turtle"), self.graph))


OTHER_URL = "https://news.example.test/articles/outro"


def policy_capture(url: str, tstamp: str) -> dict:
    return {
        "originalURL": url, "tstamp": tstamp, "title": url, "statusCode": 200,
        "digest": f"D{tstamp}", "linkToArchive": f"https://archive.example.test/{tstamp}",
        "linkToExtractedText": f"https://archive.example.test/text/{tstamp}",
    }


class NotFoundSession(FixtureSession):
    """Como a FixtureSession, mas o texto da URL indicada responde 404."""

    def __init__(self, missing_url: str) -> None:
        super().__init__()
        self.missing_url = missing_url

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if url != self.missing_url:
            raise AssertionError(f"Unexpected fixture request: {url}")
        raise requests.HTTPError("404 Client Error: Not Found")


class FirstCaptureTextPolicyTests(OfflineTestCase):
    """Política para artigos novos: só o texto da captura mais antiga é pedido."""

    def test_only_oldest_capture_of_each_article_is_requested(self) -> None:
        # Ordem do version_history não cronológica, de propósito.
        captures = [
            policy_capture(ORIGINAL_URL, "20200301000000"),
            policy_capture(ORIGINAL_URL, "20200101000000"),
            policy_capture(OTHER_URL, "20210505000000"),
            policy_capture(ORIGINAL_URL, "20200201000000"),
        ]
        # A FixtureSession falha perante qualquer pedido fora destes dois.
        session = self.fixture_session(
            ("https://archive.example.test/text/20200101000000", b"texto A"),
            ("https://archive.example.test/text/20210505000000", b"texto B"),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        records = build_manifest_records(
            client, captures, self.root, text_policy=TEXT_POLICY_FIRST
        )

        self.assertEqual(len(records), 4)  # todas as capturas ficam no manifesto
        requested = {r["tstamp"]: r["text_requested"] for r in records}
        self.assertEqual(requested, {
            "20200101000000": True, "20210505000000": True,
            "20200201000000": False, "20200301000000": False,
        })
        for record in records:
            if record["text_requested"]:
                self.assertTrue(record["text_download_success"])
                continue
            self.assertEqual(
                (record["text_download_success"], record["text_downloaded_now"],
                 record["text_size_bytes"], record["text_error"],
                 record["extracted_text_path"]),
                (False, False, 0, None, None),
            )
        self.assertEqual(len(list(client.texts_dir.iterdir())), 2)

        metrics = calculate_metrics(records, estimated_total=None)
        self.assertEqual(
            (metrics.texts_obtained, metrics.text_failures, metrics.texts_not_requested),
            (2, 0, 2),
        )

    def test_failed_oldest_text_is_a_failure_without_fallback(self) -> None:
        captures = [
            policy_capture(ORIGINAL_URL, "20200101000000"),
            policy_capture(ORIGINAL_URL, "20200201000000"),
        ]
        session = NotFoundSession("https://archive.example.test/text/20200101000000")
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        records = build_manifest_records(
            client, captures, self.root, text_policy=TEXT_POLICY_FIRST
        )

        # Um só pedido: a segunda captura não é tentada como alternativa.
        self.assertEqual([url for url, _ in session.calls],
                         ["https://archive.example.test/text/20200101000000"])
        self.assertIsNotNone(records[0]["text_error"])
        self.assertIsNone(records[1]["text_error"])
        metrics = calculate_metrics(records, estimated_total=None)
        self.assertEqual((metrics.text_failures, metrics.texts_not_requested), (1, 1))

    def test_unknown_policy_is_rejected(self) -> None:
        client = ArquivoClient(data_dir=self.root / "raw", session=self.fixture_session())
        with self.assertRaises(ValueError):
            build_manifest_records(client, [], self.root, text_policy="nenhuma")

    def test_all_policy_marks_every_capture_as_requested(self) -> None:
        captures = [policy_capture(ORIGINAL_URL, t) for t in ("20200101000000", "20200201000000")]
        session = self.fixture_session(
            *((c["linkToExtractedText"], b"texto") for c in captures),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)
        records = build_manifest_records(client, captures, self.root, text_policy=TEXT_POLICY_ALL)
        self.assertEqual([r["text_requested"] for r in records], [True, True])


def policy_capture_with_html(url: str, tstamp: str) -> dict:
    return {**policy_capture(url, tstamp),
            "linkToOriginalFile": f"https://archive.example.test/original/{tstamp}"}


class HtmlAlongsideFirstCaptureTests(OfflineTestCase):
    """HTML em bruto (`docs/experiments.md`) pedido na mesma passagem que o
    texto da captura mais antiga, só sob `TEXT_POLICY_FIRST`."""

    def test_html_is_requested_only_for_the_oldest_capture_under_first_policy(self) -> None:
        captures = [
            policy_capture_with_html(ORIGINAL_URL, "20200301000000"),
            policy_capture_with_html(ORIGINAL_URL, "20200101000000"),
            policy_capture_with_html(OTHER_URL, "20210505000000"),
        ]
        # A FixtureSession falha perante qualquer pedido fora destes quatro:
        # só as capturas mais antigas de cada artigo pedem texto e HTML, pela
        # mesma ordem em que `build_manifest_records` os pede (texto, depois
        # HTML, por captura).
        session = self.fixture_session(
            ("https://archive.example.test/text/20200101000000", b"texto A"),
            ("https://archive.example.test/original/20200101000000", b"<html>A</html>"),
            ("https://archive.example.test/text/20210505000000", b"texto B"),
            ("https://archive.example.test/original/20210505000000", b"<html>B</html>"),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        records = build_manifest_records(
            client, captures, self.root, text_policy=TEXT_POLICY_FIRST
        )

        by_tstamp = {r["tstamp"]: r for r in records}
        oldest = by_tstamp["20200101000000"]
        self.assertEqual(
            (oldest["html_requested"], oldest["html_download_success"],
             oldest["html_downloaded_now"]),
            (True, True, True),
        )
        self.assertEqual(
            (self.root / oldest["original_html_path"]).read_bytes(), b"<html>A</html>",
        )
        self.assertTrue(by_tstamp["20210505000000"]["html_requested"])
        not_oldest = by_tstamp["20200301000000"]
        self.assertEqual(
            (not_oldest["html_requested"], not_oldest["html_download_success"],
             not_oldest["original_html_path"]),
            (False, False, None),
        )

    def test_all_policy_never_requests_html_even_when_field_is_present(self) -> None:
        captures = [policy_capture_with_html(ORIGINAL_URL, "20200101000000")]
        # Sob TEXT_POLICY_ALL só o texto pode ser pedido; um pedido de HTML
        # não registado faria a FixtureSession falhar o teste.
        session = self.fixture_session(
            ("https://archive.example.test/text/20200101000000", b"texto"),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        records = build_manifest_records(
            client, captures, self.root, text_policy=TEXT_POLICY_ALL
        )

        self.assertEqual(
            (records[0]["html_requested"], records[0]["html_download_success"],
             records[0]["original_html_path"]),
            (False, False, None),
        )

    def test_missing_html_field_fails_without_blocking_the_text(self) -> None:
        captures = [policy_capture(ORIGINAL_URL, "20200101000000")]  # sem linkToOriginalFile
        session = self.fixture_session(
            ("https://archive.example.test/text/20200101000000", b"texto"),
        )
        client = ArquivoClient(data_dir=self.root / "raw", session=session)

        records = build_manifest_records(
            client, captures, self.root, text_policy=TEXT_POLICY_FIRST
        )

        self.assertTrue(records[0]["text_download_success"])
        self.assertTrue(records[0]["html_requested"])
        self.assertFalse(records[0]["html_download_success"])
        self.assertEqual(records[0]["html_error"], "linkToOriginalFile ausente")


if __name__ == "__main__":
    unittest.main()
