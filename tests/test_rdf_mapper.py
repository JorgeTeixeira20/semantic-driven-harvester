from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph, Literal, OWL, RDF, XSD
from rdflib.compare import isomorphic

from semantic_harvester.arquivo_client import ArquivoClient
from tests.support import FIXTURES, ORIGINAL_URL, TSTAMP as SAMPLE_TSTAMP, OfflineTestCase

from semantic_harvester.rdf_mapper import (
    CAPTURE_FIELDS,
    SDH,
    article_uri,
    build_sample_graph,
    capture_uri,
    extracted_text_uri,
    load_sample_result,
    resource_uri,
    stable_hash,
    tstamp_as_xsd_datetime,
)


class RdfMapperTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project_root = self.root
        # Replace only the M2 selection; production mapping still runs normally.
        self.enterContext(patch("semantic_harvester.rdf_mapper.SAMPLE_ORIGINAL_URL", ORIGINAL_URL))
        self.enterContext(patch("semantic_harvester.rdf_mapper.SAMPLE_TSTAMP", SAMPLE_TSTAMP))
        self.ontology = Graph().parse(
            Path(__file__).resolve().parents[1] / "ontology" / "semantic_harvester.ttl",
            format="turtle",
        )
        self.raw_content = (FIXTURES / "textsearch/sample_search.json").read_bytes()
        self.text_content = (FIXTURES / "texts/sample_text.txt").read_bytes()
        self.source_result = json.loads(self.raw_content)["response_items"][0]
        self.session = self.fixture_session(
            (ArquivoClient.SEARCH_URL, self.raw_content),
            (self.source_result["linkToExtractedText"], self.text_content),
        )
        client = ArquivoClient(data_dir=self.root / "responses", session=self.session)
        self.response = client.search(query="sintético", max_items=1)
        self.download = client.download_extracted_text(self.response.results[0])
        self.assertTrue(self.download.success)
        self.sample = build_sample_graph(
            self.response.results[0], self.download.path, self.root,
        )

    def test_textsearch_response_is_processed_and_raw_bytes_preserved(self) -> None:
        payload = json.loads(self.raw_content)
        self.assertEqual(self.response.results, payload["response_items"])
        self.assertEqual(self.response.raw_response, payload)
        self.assertEqual(self.response.raw_path.read_bytes(), self.raw_content)
        self.assertEqual(
            dict(self.session.calls[0][1]["params"]), {"q": "sintético", "maxItems": 1},
        )

    def test_sample_result_is_loaded_from_fixture(self) -> None:
        result, source = load_sample_result(FIXTURES / "textsearch")
        self.assertEqual(result, self.source_result)
        self.assertEqual(source, FIXTURES / "textsearch/sample_search.json")

    def test_ontology_defines_base_classes(self) -> None:
        for rdf_class in (
            SDH.Artigo,
            SDH.Jornal,
            SDH.RecursoWeb,
            SDH.CapturaArquivada,
            SDH.TextoExtraido,
            SDH.EntidadeMencionada,
            SDH.Tema,
        ):
            self.assertIn((rdf_class, RDF.type, OWL.Class), self.ontology)

    def test_sample_contains_required_instances(self) -> None:
        for rdf_class in (
            SDH.Artigo, SDH.Jornal, SDH.RecursoWeb, SDH.CapturaArquivada, SDH.TextoExtraido,
        ):
            self.assertEqual(len(set(self.sample.subjects(RDF.type, rdf_class))), 1)
        self.assertEqual(len(self.sample), 23)

    def test_capture_has_fixture_tstamp_and_links(self) -> None:
        original_url = self.source_result["originalURL"]
        web_resource = resource_uri(original_url)
        capture = capture_uri(original_url, SAMPLE_TSTAMP)
        extracted_texts = list(self.sample.objects(capture, SDH.temTextoExtraido))

        self.assertIn(
            (capture, SDH.tstamp, Literal(SAMPLE_TSTAMP, datatype=XSD.string)),
            self.sample,
        )
        self.assertIn((web_resource, SDH.temCaptura, capture), self.sample)
        self.assertEqual(len(extracted_texts), 1)
        self.assertIn((extracted_texts[0], RDF.type, SDH.TextoExtraido), self.sample)

    def test_captured_at_is_derived_from_tstamp(self) -> None:
        capture = capture_uri(self.source_result["originalURL"], SAMPLE_TSTAMP)
        self.assertEqual(
            tstamp_as_xsd_datetime(SAMPLE_TSTAMP),
            Literal("2020-01-01T00:00:00Z", datatype=XSD.dateTime),
        )
        self.assertIn(
            (capture, SDH.capturedAt, tstamp_as_xsd_datetime(SAMPLE_TSTAMP)),
            self.sample,
        )

    def test_selected_result_is_linked_as_article(self) -> None:
        original_url = self.source_result["originalURL"]
        article = article_uri(original_url)
        web_resource = resource_uri(original_url)
        newspaper = SDH["newspaper/record"]

        self.assertIn((article, RDF.type, SDH.Artigo), self.sample)
        self.assertIn((article, SDH.publicadoPor, newspaper), self.sample)
        self.assertIn((article, SDH.temRecursoWeb, web_resource), self.sample)

    def test_identifiers_are_deterministic(self) -> None:
        original_url = self.source_result["originalURL"]
        digest = "b366ac3c8369c859429913e0d91bc312b2af8a516af137d73dd785506ec94f87"
        self.assertEqual(stable_hash(original_url), digest)
        self.assertEqual(resource_uri(original_url), SDH[f"resource-web/{digest}"])
        self.assertEqual(article_uri(original_url), SDH[f"article/{digest}"])
        self.assertEqual(
            capture_uri(original_url, SAMPLE_TSTAMP),
            SDH[f"capture/{digest}/{SAMPLE_TSTAMP}"],
        )
        self.assertEqual(
            extracted_text_uri(original_url, SAMPLE_TSTAMP),
            SDH[f"extracted-text/{digest}/{SAMPLE_TSTAMP}"],
        )
        rebuilt = build_sample_graph(dict(self.source_result), self.download.path, self.root)
        self.assertTrue(isomorphic(self.sample, rebuilt))

    def test_extracted_text_file_exists(self) -> None:
        text = next(self.sample.subjects(RDF.type, SDH.TextoExtraido))
        file_path = self.sample.value(text, SDH.filePath)

        self.assertIsNotNone(file_path)
        self.assertTrue((self.project_root / str(file_path)).is_file())
        self.assertEqual((self.project_root / str(file_path)).read_bytes(), self.text_content)

    def test_capture_metadata_matches_source(self) -> None:
        capture = next(self.sample.subjects(RDF.type, SDH.CapturaArquivada))
        original_url = self.source_result["originalURL"]
        web_resource = resource_uri(original_url)

        self.assertIn(
            (
                web_resource,
                SDH.originalURL,
                Literal(original_url, datatype=XSD.anyURI),
            ),
            self.sample,
        )

        for source_field, (predicate, datatype) in CAPTURE_FIELDS.items():
            values = list(self.sample.objects(capture, predicate))
            source_value = self.source_result.get(source_field)
            if source_value is None:
                self.assertEqual(values, [], source_field)
                continue

            expected_value = (
                int(source_value)
                if datatype == XSD.nonNegativeInteger
                else str(source_value)
            )
            self.assertEqual(len(values), 1, source_field)
            self.assertEqual(values[0].toPython(), expected_value, source_field)
            self.assertEqual(values[0].datatype, datatype, source_field)

    def test_absent_optional_metadata_is_omitted(self) -> None:
        result = dict(self.source_result)
        del result["snippet"]
        result["encoding"] = None
        graph = build_sample_graph(result, self.download.path, self.root)
        capture = capture_uri(ORIGINAL_URL, SAMPLE_TSTAMP)
        self.assertEqual(list(graph.objects(capture, SDH.snippet)), [])
        self.assertEqual(list(graph.objects(capture, SDH.encoding)), [])

    def test_generated_turtle_can_be_loaded_again(self) -> None:
        path = self.root / "sample.ttl"
        self.sample.serialize(destination=path, format="turtle")
        self.assertTrue(isomorphic(Graph().parse(path, format="turtle"), self.sample))


if __name__ == "__main__":
    unittest.main()
