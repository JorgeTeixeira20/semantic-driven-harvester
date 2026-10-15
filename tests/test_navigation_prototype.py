from __future__ import annotations

import re
import unittest
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, URIRef

from semantic_harvester.navigation_prototype import (
    ARTICLES_DIR, ENTIDADES_PAGE, TEMAS_PAGE, generate, run_query,
)
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


def build_redundancy_graph() -> Graph:
    """Caminho D: a captura de 2019 de A é marcada cópia da de 2017."""

    graph = Graph()
    old, new = capture_uri(URL_A, "20170101000000"), capture_uri(URL_A, "20190301000000")
    graph.add((new, SDH.versaoDe, old))
    graph.add((new, SDH.similaridade, Literal(0.95, datatype=XSD.float)))
    return graph


def build_entities_graph() -> Graph:
    """Caminho B: um Tema e uma Mencao persistente para o artigo A."""

    graph = Graph()
    tema = URIRef("urn:test:tema/futebol")
    graph.add((tema, RDF.type, SDH.Tema))
    graph.add((tema, SDH.categoriaTema, Literal("modalidade")))
    graph.add((tema, SDH.valorTema, Literal("futebol")))
    graph.add((tema, RDFS.label, Literal("modalidade: futebol")))
    graph.add((article_uri(URL_A), SDH.temTema, tema))

    entity = URIRef("http://www.wikidata.org/entity/Q1")
    mencao = URIRef("urn:test:mencao/a")
    graph.add((entity, RDF.type, SDH.EntidadeMencionada))
    graph.add((entity, RDFS.label, Literal("Jogador Exemplo")))
    graph.add((article_uri(URL_A), SDH.mencionaEntidade, entity))
    graph.add((article_uri(URL_A), SDH.temMencao, mencao))
    graph.add((mencao, RDF.type, SDH.Mencao))
    graph.add((mencao, SDH.sobreEntidade, entity))
    graph.add((mencao, SDH.ocorrencias, Literal(3, datatype=XSD.nonNegativeInteger)))
    graph.add((mencao, SDH.persistente, Literal(True, datatype=XSD.boolean)))
    graph.add((mencao, SDH.clubeCoerente, Literal("sim")))
    graph.add((mencao, SDH.capturasComMencao, Literal(2, datatype=XSD.nonNegativeInteger)))
    graph.add((mencao, SDH.capturasComTexto, Literal(2, datatype=XSD.nonNegativeInteger)))
    return graph


def merge_into(graph: Graph, other: Graph) -> None:
    for triple in other:
        graph.add(triple)


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


class DbAnnotationQueryTests(unittest.TestCase):
    """Queries novas (D e B), juntando os três grafos como `generate()` faz."""

    def setUp(self) -> None:
        self.graph = build_graph()
        merge_into(self.graph, build_redundancy_graph())
        merge_into(self.graph, build_entities_graph())

    def test_historico_artigo_mostra_redundancia_do_caminho_d(self) -> None:
        rows = {r["tstamp"]: r for r in run_query(
            self.graph, QUERIES, "historico_artigo", {"artigo": URIRef(article_uri(URL_A))}
        )}
        self.assertEqual(rows["20190301000000"]["representanteTstamp"], "20170101000000")
        self.assertAlmostEqual(rows["20190301000000"]["similaridade"], 0.95, places=2)
        self.assertIsNone(rows["20170101000000"]["representanteTstamp"])
        # Artigo B não tem anotação de D: sem representanteTstamp nenhures.
        rows_b = run_query(self.graph, QUERIES, "historico_artigo",
                           {"artigo": URIRef(article_uri(URL_B))})
        self.assertTrue(all(r["representanteTstamp"] is None for r in rows_b))

    def test_temas_e_mencoes_por_artigo(self) -> None:
        temas = run_query(self.graph, QUERIES, "temas_artigo",
                          {"artigo": URIRef(article_uri(URL_A))})
        self.assertEqual([t["rotulo"] for t in temas], ["modalidade: futebol"])

        mencoes = run_query(self.graph, QUERIES, "mencoes_artigo",
                            {"artigo": URIRef(article_uri(URL_A))})
        self.assertEqual(len(mencoes), 1)
        self.assertEqual(mencoes[0]["rotulo"], "Jogador Exemplo")
        self.assertEqual(mencoes[0]["ocorrencias"], 3)
        self.assertTrue(mencoes[0]["persistente"])

        # Artigo B não tem Tema nem Mencao.
        self.assertEqual(run_query(self.graph, QUERIES, "temas_artigo",
                                   {"artigo": URIRef(article_uri(URL_B))}), [])

    def test_resumos_globais(self) -> None:
        temas = run_query(self.graph, QUERIES, "temas_resumo")
        self.assertEqual(temas, [{"categoria": "modalidade", "valor": "futebol",
                                   "rotulo": "modalidade: futebol", "artigos": 1}])

        entidades = run_query(self.graph, QUERIES, "entidades_resumo")
        self.assertEqual(len(entidades), 1)
        self.assertEqual(entidades[0]["artigosPersistentes"], 1)
        self.assertEqual(entidades[0]["ocorrenciasTotal"], 3)

        redundancia = run_query(self.graph, QUERIES, "redundancia_resumo")
        self.assertEqual(redundancia[0]["capturasRedundantes"], 1)


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

    def test_generate_without_db_files_skips_extra_pages(self) -> None:
        ttl = self.root / "corpus.ttl"
        build_graph().serialize(destination=ttl, format="turtle")
        out = self.root / "prototipo"

        result = generate(
            ttl, QUERIES, out,
            redundancy_ttl=self.root / "nao_existe_redundancy.ttl",
            entities_ttl=self.root / "nao_existe_entities.ttl",
        )

        self.assertEqual(result["temas"], [])
        self.assertEqual(result["entidades"], [])
        self.assertEqual(result["capturas_redundantes"], 0)
        self.assertFalse((out / TEMAS_PAGE).exists())
        self.assertFalse((out / ENTIDADES_PAGE).exists())
        index = (out / "index.html").read_text("utf-8")
        self.assertNotIn(TEMAS_PAGE, index)
        self.assertNotIn(ENTIDADES_PAGE, index)

    def test_generate_with_db_files_adds_temas_e_entidades(self) -> None:
        ttl = self.root / "corpus.ttl"
        build_graph().serialize(destination=ttl, format="turtle")
        redundancy_ttl = self.root / "corpus_redundancy.ttl"
        build_redundancy_graph().serialize(destination=redundancy_ttl, format="turtle")
        entities_ttl = self.root / "corpus_entities.ttl"
        build_entities_graph().serialize(destination=entities_ttl, format="turtle")
        out = self.root / "prototipo"

        result = generate(ttl, QUERIES, out, redundancy_ttl=redundancy_ttl, entities_ttl=entities_ttl)

        self.assertEqual(len(result["temas"]), 1)
        self.assertEqual(len(result["entidades"]), 1)
        self.assertEqual(result["capturas_redundantes"], 1)

        index = (out / "index.html").read_text("utf-8")
        self.assertIn(TEMAS_PAGE, index)
        self.assertIn(ENTIDADES_PAGE, index)

        temas_html = (out / TEMAS_PAGE).read_text("utf-8")
        self.assertIn("modalidade: futebol", temas_html)

        entidades_html = (out / ENTIDADES_PAGE).read_text("utf-8")
        self.assertIn("Jogador Exemplo", entidades_html)
        self.assertIn("http://www.wikidata.org/entity/Q1", entidades_html)

        article_a = out / ARTICLES_DIR / f"{article_uri(URL_A).rsplit('/', 1)[-1][:16]}.html"
        page_a = article_a.read_text("utf-8")
        self.assertIn("modalidade: futebol", page_a)
        self.assertIn("Jogador Exemplo", page_a)
        self.assertIn("cópia de 20170101000000", page_a)


if __name__ == "__main__":
    unittest.main()
