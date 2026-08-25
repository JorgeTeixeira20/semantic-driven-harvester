from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Graph, Literal, OWL, RDF, XSD

from semantic_harvester.rdf_mapper import (
    CAPTURE_FIELDS,
    SDH,
    SAMPLE_TSTAMP,
    article_uri,
    capture_uri,
    load_sample_result,
    resource_uri,
    stable_hash,
    tstamp_as_xsd_datetime,
)


class RdfMapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.ontology = Graph().parse(
            cls.project_root / "ontology" / "semantic_harvester.ttl",
            format="turtle",
        )
        cls.sample = Graph().parse(
            cls.project_root / "output" / "sample_capture.ttl",
            format="turtle",
        )
        cls.source_result, _ = load_sample_result(
            cls.project_root / "data" / "raw" / "searches"
        )

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
        self.assertTrue(list(self.sample.subjects(RDF.type, SDH.RecursoWeb)))
        self.assertTrue(list(self.sample.subjects(RDF.type, SDH.CapturaArquivada)))
        self.assertTrue(list(self.sample.subjects(RDF.type, SDH.TextoExtraido)))

    def test_capture_has_real_tstamp_and_links(self) -> None:
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
        self.assertEqual(stable_hash(original_url), stable_hash(original_url))
        self.assertEqual(resource_uri(original_url), resource_uri(original_url))
        self.assertEqual(
            capture_uri(original_url, SAMPLE_TSTAMP),
            capture_uri(original_url, SAMPLE_TSTAMP),
        )

    def test_extracted_text_file_exists(self) -> None:
        text = next(self.sample.subjects(RDF.type, SDH.TextoExtraido))
        file_path = self.sample.value(text, SDH.filePath)

        self.assertIsNotNone(file_path)
        self.assertTrue((self.project_root / str(file_path)).is_file())

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


if __name__ == "__main__":
    unittest.main()
