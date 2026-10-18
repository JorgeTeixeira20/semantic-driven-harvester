"""RDF dos Caminhos D (`corpus_redundancy_rdf`) e B (`corpus_entities_rdf`)."""

from __future__ import annotations

import csv
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, URIRef

from semantic_harvester import corpus_entities_rdf, corpus_redundancy_rdf
from semantic_harvester.rdf_mapper import SDH, article_uri, capture_uri, stable_hash
from tests.support import OfflineTestCase

ONTOLOGY = Path(__file__).resolve().parents[1] / "ontology" / "semantic_harvester.ttl"
A = "https://news.example.test/futebol/liga-nos/benfica/detalhe/a"
B = "https://news.example.test/futebol/liga-nos/benfica/detalhe/b"
TSTAMPS = ("20200101000000", "20200102000000", "20200103000000", "20200104000000", "20200105000000")


class AnnotationsTestCase(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "output").mkdir()
        (self.root / "data" / "processed").mkdir(parents=True)
        graph = Graph()
        for url in (A, B):
            graph.add((article_uri(url), RDF.type, SDH.Artigo))
            for tstamp in TSTAMPS:
                graph.add((capture_uri(url, tstamp), RDF.type, SDH.CapturaArquivada))
        self.articles_ttl = self.root / "output" / "corpus_articles.ttl"
        graph.serialize(destination=self.articles_ttl, format="turtle")
        self.articles_bytes = self.articles_ttl.read_bytes()

    def write_csv(self, name: str, rows: list[dict[str, str]]) -> None:
        with (self.root / "output" / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def assert_predicates_declared(self, graph: Graph) -> None:
        ontology = Graph().parse(ONTOLOGY, format="turtle")
        for predicate in set(graph.predicates()) - {RDF.type, RDFS.label}:
            self.assertIn(predicate, set(ontology.subjects()), predicate)


def redundancy_row(artigo, tstamp, camada, rotulo, representante="", similaridade="", limiar="0.9"):
    return {"artigo": artigo, "tstamp": tstamp, "tem_texto": "True", "status_code": "200",
            "camada": camada, "representante": representante, "similaridade": similaridade,
            "rotulo": rotulo, "limiar": limiar, "sim_consecutiva": "", "digest": "D",
            "content_length": "1", "grupo_digest": ""}


class RedundancyRdfTests(AnnotationsTestCase):
    def rows(self, limiar: str = "0.9") -> list[dict[str, str]]:
        return [
            redundancy_row(A, TSTAMPS[0], "1_texto", "representante", TSTAMPS[0], limiar=limiar),
            redundancy_row(A, TSTAMPS[1], "1_texto", "redundante", TSTAMPS[0], "0.975000", limiar),
            redundancy_row(A, TSTAMPS[2], "sem_corpo", "mantida_sem_corpo", limiar=limiar),
            redundancy_row(A, TSTAMPS[3], "2_sem_texto", "candidata_digest_nao_verificada", limiar=limiar),
            redundancy_row(B, TSTAMPS[0], "nao_avaliavel", "mantida_sem_texto", limiar=limiar),
        ]

    def test_only_redundant_layer1_captures_get_triples(self) -> None:
        self.write_csv("corpus_redundancy.csv", self.rows())

        graph, stats = corpus_redundancy_rdf.run(self.root)

        redundant, representative = capture_uri(A, TSTAMPS[1]), capture_uri(A, TSTAMPS[0])
        self.assertEqual(set(graph), {
            (redundant, SDH.versaoDe, representative),
            (redundant, SDH.similaridade, Literal(0.975, datatype=XSD.float)),
        })
        # Representante, sem_corpo, Camada 2 e não avaliáveis: nenhum triplo.
        for tstamp in (TSTAMPS[0], TSTAMPS[2], TSTAMPS[3]):
            self.assertNotIn(capture_uri(A, tstamp), set(graph.subjects()))
        self.assertEqual((stats["redundantes_com_triplos"], stats["representantes_sem_triplos"]), (1, 1))
        self.assertEqual(self.articles_ttl.read_bytes(), self.articles_bytes)
        reread = Graph().parse(self.root / "output" / "corpus_redundancy.ttl", format="turtle")
        self.assertEqual(set(reread), set(graph))
        self.assert_predicates_declared(graph)

    def test_unexpected_threshold_or_unknown_capture_fails(self) -> None:
        self.write_csv("corpus_redundancy.csv", self.rows(limiar="0.8"))
        with self.assertRaises(ValueError):
            corpus_redundancy_rdf.run(self.root)
        rows = self.rows()
        rows[1]["representante"] = "20991231000000"
        self.write_csv("corpus_redundancy.csv", rows)
        with self.assertRaises(ValueError):
            corpus_redundancy_rdf.run(self.root)


def entity_row(artigo, tipo, categoria, rotulo, origem, mencao="", texto="", ocorr="", pers="", coer=""):
    return {"artigo": artigo, "tipo": tipo, "categoria": categoria, "rotulo": rotulo,
            "origem": origem, "capturas_com_mencao": mencao, "capturas_com_texto": texto,
            "ocorrencias": ocorr, "persistente": pers, "uma_so_captura": "", "clube_coerente": coer}


class EntitiesRdfTests(AnnotationsTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "data" / "processed" / "caminho_b_vocabulario_wikidata.csv").write_text(
            "tipo,categoria,rotulo,variantes,wikidata,clubes,homonimos\n"
            "entidade,jogador,Jonas,,Q123,Sport Lisboa e Benfica,1\n"
            "entidade,jogador,Pedro Mendes,,Q1|Q2,Clube A|Clube B,2\n", encoding="utf-8")
        self.write_csv("corpus_entities.csv", [
            entity_row(A, "tema", "clube", "benfica", "url"),
            entity_row(B, "tema", "clube", "benfica", "url"),
            entity_row(A, "entidade", "jogador", "Jonas", "texto", "2", "3", "5", "False", "sim"),
            entity_row(B, "entidade", "jogador", "Jonas", "texto", "1", "1", "1", "True", "sim"),
            entity_row(B, "entidade", "jogador", "Pedro Mendes", "texto", "1", "1", "2", "True", "nao"),
        ])

    def test_nodes_identity_and_mention_metrics(self) -> None:
        graph, stats, homonym_rows = corpus_entities_rdf.run(self.root)

        jonas = URIRef("http://www.wikidata.org/entity/Q123")
        pedro = SDH[f"entity/{stable_hash('Pedro Mendes')}"]
        tema = SDH[f"tema/{stable_hash('clube|benfica')}"]
        # Nós partilhados: um Tema e uma entidade por rótulo, para os dois artigos.
        self.assertEqual(set(graph.subjects(RDF.type, SDH.Tema)), {tema})
        # Subclasse específica (ontology/semantic_harvester.ttl, 2026-10-18).
        self.assertIn((tema, RDF.type, SDH.Clube), graph)
        self.assertEqual(set(graph.subjects(RDF.type, SDH.EntidadeMencionada)), {jonas, pedro})
        self.assertEqual(set(graph.subjects(SDH.temTema, tema)), {article_uri(A), article_uri(B)})
        self.assertEqual(graph.value(tema, RDFS.label), Literal("clube: benfica"))
        self.assertEqual(graph.value(tema, SDH.valorTema), Literal("benfica", datatype=XSD.string))
        self.assertEqual(graph.value(pedro, RDFS.label), Literal("Pedro Mendes"))
        # Relação direta em paralelo com a Menção (n-ária).
        self.assertIn((article_uri(A), SDH.mencionaEntidade, jonas), graph)
        mencao = SDH[f"mencao/{stable_hash(A + '|Jonas')}"]
        self.assertIn((article_uri(A), SDH.temMencao, mencao), graph)
        self.assertEqual(graph.value(mencao, SDH.sobreEntidade), jonas)
        self.assertEqual(graph.value(mencao, SDH.capturasComMencao),
                         Literal(2, datatype=XSD.nonNegativeInteger))
        self.assertEqual(graph.value(mencao, SDH.capturasComTexto),
                         Literal(3, datatype=XSD.nonNegativeInteger))
        self.assertEqual(graph.value(mencao, SDH.ocorrencias),
                         Literal(5, datatype=XSD.nonNegativeInteger))
        self.assertEqual(graph.value(mencao, SDH.persistente), Literal(False, datatype=XSD.boolean))
        self.assertEqual(graph.value(mencao, SDH.clubeCoerente), Literal("sim", datatype=XSD.string))
        self.assertEqual((stats["temas"], stats["entidades"], stats["mencoes"]), (1, 2, 3))
        self.assertEqual((stats["entidades_wikidata"], stats["entidades_fallback"]), (1, 1))
        self.assertEqual(homonym_rows, [f"Pedro Mendes em {B}"])
        self.assertEqual(self.articles_ttl.read_bytes(), self.articles_bytes)
        self.assert_predicates_declared(graph)
        summary = (self.root / "output" / "corpus_entities_rdf_summary.md").read_text("utf-8")
        self.assertIn("Linhas de menção com rótulo homónimo no CSV atual: 1", summary)

    def test_entity_missing_from_vocabulary_fails(self) -> None:
        self.write_csv("corpus_entities.csv", [
            entity_row(A, "entidade", "jogador", "Desconhecido", "texto", "1", "1", "1", "True", "sim")])
        with self.assertRaises(ValueError):
            corpus_entities_rdf.run(self.root)

    def test_unknown_tema_category_fails(self) -> None:
        self.write_csv("corpus_entities.csv", [
            entity_row(A, "tema", "modalidade_nova", "surf", "url")])
        with self.assertRaises(ValueError):
            corpus_entities_rdf.run(self.root)
