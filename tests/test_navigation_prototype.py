from __future__ import annotations

import re
import unittest
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, URIRef

from semantic_harvester.navigation_prototype import generate, run_query
from semantic_harvester.rdf_mapper import (
    SDH, article_uri, capture_uri, extracted_text_uri, resource_uri,
)
from tests.support import OfflineTestCase

QUERIES = Path(__file__).resolve().parents[1] / "queries"
URL_A = "https://news.example.test/a"
URL_B = "https://news.example.test/b"


def build_graph() -> Graph:
    """A: 3 capturas (inseridas fora de ordem), 2 com texto, uma 404 sem texto.
    B: 1 captura sem texto, título com caracteres a escapar."""

    graph = Graph()
    spec = {
        URL_A: ("Artigo A", [("20190301000000", 200, True), ("20170101000000", 200, True),
                             ("20180601000000", 404, False)]),
        URL_B: ("Título <b> & companhia", [("20180101000000", 200, False)]),
    }
    for url, (title, captures) in spec.items():
        article, resource = article_uri(url), resource_uri(url)
        graph.add((article, RDF.type, SDH.Artigo))
        graph.add((article, RDFS.label, Literal(title)))
        graph.add((article, SDH.temRecursoWeb, resource))
        graph.add((resource, RDF.type, SDH.RecursoWeb))
        graph.add((resource, SDH.originalURL, Literal(url, datatype=XSD.anyURI)))
        for tstamp, status, has_text in captures:
            capture = capture_uri(url, tstamp)
            graph.add((resource, SDH.temCaptura, capture))
            graph.add((capture, RDF.type, SDH.CapturaArquivada))
            graph.add((capture, SDH.tstamp, Literal(tstamp, datatype=XSD.string)))
            iso = f"{tstamp[:4]}-{tstamp[4:6]}-{tstamp[6:8]}T00:00:00+00:00"
            graph.add((capture, SDH.capturedAt, Literal(iso, datatype=XSD.dateTime)))
            graph.add((capture, SDH.statusCode, Literal(status, datatype=XSD.integer)))
            graph.add((capture, SDH.archiveURL, Literal(
                f"https://arquivo.pt/wayback/{tstamp}/{url}", datatype=XSD.anyURI)))
            if has_text:
                text = extracted_text_uri(url, tstamp)
                graph.add((capture, SDH.temTextoExtraido, text))
                graph.add((text, RDF.type, SDH.TextoExtraido))
                graph.add((text, SDH.filePath, Literal(f"data/raw/texts/{tstamp}.txt")))
    return graph


class QueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = build_graph()

    def test_articles_count_captures_and_texts_separately(self) -> None:
        rows = {r["url"]: r for r in run_query(self.graph, QUERIES, "artigos")}
        self.assertEqual((rows[URL_A]["capturas"], rows[URL_A]["textos"]), (3, 2))
        self.assertEqual((rows[URL_B]["capturas"], rows[URL_B]["textos"]), (1, 0))
        self.assertEqual(rows[URL_A]["primeira"].year, 2017)
        self.assertEqual(rows[URL_A]["ultima"].year, 2019)

    def test_history_is_filtered_by_article_and_chronological(self) -> None:
        rows = run_query(self.graph, QUERIES, "historico_artigo",
                         {"artigo": URIRef(article_uri(URL_A))})
        self.assertEqual([r["tstamp"] for r in rows],
                         ["20170101000000", "20180601000000", "20190301000000"])
        self.assertEqual([r["status"] for r in rows], [200, 404, 200])
        self.assertIsNone(rows[1]["ficheiro"])

    def test_aggregates_by_year_and_status(self) -> None:
        per_year = {r["ano"]: r for r in run_query(self.graph, QUERIES, "capturas_por_ano")}
        self.assertEqual({y: (r["capturas"], r["textos"], r["artigos"]) for y, r in per_year.items()},
                         {2017: (1, 1, 1), 2018: (2, 0, 2), 2019: (1, 1, 1)})
        per_status = {r["status"]: (r["capturas"], r["com_texto"])
                      for r in run_query(self.graph, QUERIES, "textos_por_status")}
        self.assertEqual(per_status, {200: (3, 2), 404: (1, 0)})


class GenerateTests(OfflineTestCase):
    def test_pages_link_to_existing_files_and_escape_titles(self) -> None:
        ttl = self.root / "corpus.ttl"
        build_graph().serialize(destination=ttl, format="turtle")
        out = self.root / "prototipo"

        result = generate(ttl, QUERIES, out)

        self.assertEqual(result["linhas_de_historico"], 4)
        index = (out / "index.html").read_text("utf-8")
        local = [h for h in re.findall(r'href="([^"]+)"', index) if not h.startswith("http")]
        self.assertEqual(len(set(local)), 2)
        for href in local:
            self.assertTrue((out / href).is_file(), href)
        self.assertIn("Título &lt;b&gt; &amp; companhia", index)
        self.assertNotIn("<b> &", index)
        page = next((out / "artigos").glob("*.html")).read_text("utf-8")
        self.assertIn('href="../index.html"', page)


if __name__ == "__main__":
    unittest.main()
