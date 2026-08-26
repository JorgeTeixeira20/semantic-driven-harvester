from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, RDF

from semantic_harvester.arquivo_client import ArquivoClient
from semantic_harvester.rdf_mapper import SDH, capture_uri, resource_uri


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def json(self) -> dict:
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.headers: dict[str, str] = {}

    def get(self, *args, **kwargs) -> FakeResponse:
        return self.response


class HistoryPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        manifest_path = (
            cls.project_root / "data" / "processed" / "captures_manifest.jsonl"
        )
        cls.records = [
            json.loads(line)
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.graph = Graph().parse(
            cls.project_root / "output" / "article_history.ttl",
            format="turtle",
        )

    def test_version_history_raw_is_processable(self) -> None:
        raw_paths = sorted(
            (self.project_root / "data" / "raw" / "version_history").glob(
                "*.json"
            )
        )
        self.assertTrue(raw_paths)
        payloads = [json.loads(path.read_bytes()) for path in raw_paths]
        self.assertTrue(any(payload.get("response_items") for payload in payloads))
        self.assertTrue(
            all("estimated_nr_results" in payload for payload in payloads)
        )

    def test_version_history_preserves_raw_bytes(self) -> None:
        raw_content = (
            b'{ "estimated_nr_results": 1, "next_page": "next", '
            b'"response_items": [{"tstamp": "20200101000000"}] }'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            client = ArquivoClient(
                data_dir=Path(temporary_directory),
                session=FakeSession(FakeResponse(raw_content)),
            )
            response = client.version_history(
                original_url="https://example.test/article", max_items=1
            )
            self.assertEqual(response.raw_path.read_bytes(), raw_content)
            self.assertEqual(response.results[0]["tstamp"], "20200101000000")
            self.assertEqual(response.estimated_nr_results, 1)
            self.assertEqual(response.next_page, "next")

    def test_all_captures_share_article_id(self) -> None:
        self.assertTrue(self.records)
        self.assertEqual(len({record["article_id"] for record in self.records}), 1)
        self.assertEqual(
            len({record["original_url"] for record in self.records}), 1
        )

    def test_rdf_identifiers_are_deterministic(self) -> None:
        record = self.records[0]
        original_url = record["original_url"]
        tstamp = record["tstamp"]
        self.assertEqual(resource_uri(original_url), resource_uri(original_url))
        self.assertEqual(
            capture_uri(original_url, tstamp), capture_uri(original_url, tstamp)
        )

    def test_history_graph_has_expected_instance_counts(self) -> None:
        articles = set(self.graph.subjects(RDF.type, SDH.Artigo))
        resources = set(self.graph.subjects(RDF.type, SDH.RecursoWeb))
        captures = set(self.graph.subjects(RDF.type, SDH.CapturaArquivada))
        texts = set(self.graph.subjects(RDF.type, SDH.TextoExtraido))

        self.assertEqual(len(articles), 1)
        self.assertEqual(len(resources), 1)
        self.assertEqual(len(captures), len(self.records))
        self.assertEqual(
            len(texts),
            sum(record["text_download_success"] for record in self.records),
        )

    def test_every_rdf_text_points_to_real_file(self) -> None:
        for text in self.graph.subjects(RDF.type, SDH.TextoExtraido):
            file_path = self.graph.value(text, SDH.filePath)
            self.assertIsNotNone(file_path)
            self.assertTrue((self.project_root / str(file_path)).is_file())

    def test_generated_turtle_can_be_loaded_again(self) -> None:
        reloaded = Graph().parse(
            self.project_root / "output" / "article_history.ttl",
            format="turtle",
        )
        self.assertEqual(len(reloaded), len(self.graph))


if __name__ == "__main__":
    unittest.main()
