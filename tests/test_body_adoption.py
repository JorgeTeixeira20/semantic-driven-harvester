"""Variante (c′) adotada nos Caminhos D (`corpus_redundancy`) e B (`corpus_entities`)."""

from __future__ import annotations

import csv
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from semantic_harvester import corpus_entities, corpus_redundancy
from semantic_harvester.rdf_mapper import SDH, capture_uri, extracted_text_uri, resource_uri
from tests.support import OfflineTestCase

URL = "https://news.example.test/futebol/detalhe/jonas-renova"
TITLE = "Jonas renova com o Benfica"
BODY = "O avançado brasileiro Jonas assinou até 2020 com os encarnados."
MENU = "Menu Record Home Últimas Notícias Benfica Sporting"


def page(headlines: str) -> str:
    """Página com estrutura real: título, menu, corpo e bloco de manchetes rotativas."""

    return (f"{TITLE} - Benfica - Jornal Record {MENU} {TITLE} {BODY} "
            f"Mais Premium {headlines} Últimas Notícias {headlines}")


NO_ARTICLE = f"Quarta-feira, 15 de março {MENU} Mais notícias Bas Dost marca"


class BodyAdoptionTestCase(OfflineTestCase):
    def write(self, captures: list[tuple[str, str]]) -> None:
        graph = Graph()
        texts = self.root / "data" / "raw" / "texts"
        texts.mkdir(parents=True)
        resource = resource_uri(URL)
        graph.add((resource, RDF.type, SDH.RecursoWeb))
        graph.add((resource, SDH.originalURL, Literal(URL, datatype=XSD.anyURI)))
        for tstamp, text in captures:
            node = capture_uri(URL, tstamp)
            graph.add((resource, SDH.temCaptura, node))
            graph.add((node, SDH.tstamp, Literal(tstamp)))
            graph.add((node, SDH.digest, Literal("D" + tstamp)))
            graph.add((node, SDH.contentLength, Literal(10, datatype=XSD.nonNegativeInteger)))
            graph.add((node, SDH.statusCode, Literal(200, datatype=XSD.integer)))
            path = texts / f"{tstamp}.txt"
            path.write_text(text, encoding="utf-8")
            text_node = extracted_text_uri(URL, tstamp)
            graph.add((node, SDH.temTextoExtraido, text_node))
            graph.add((text_node, SDH.filePath, Literal(str(path.relative_to(self.root)))))
        (self.root / "output").mkdir()
        graph.serialize(destination=self.root / "output" / "corpus_articles.ttl", format="turtle")

    def write_labels(self, rows: list[tuple[str, str, str, str]]) -> None:
        fields = ["par_id", "faixa", "artigo", "tstamp_a", "tstamp_b", "similaridade",
                  "n_palavras_so_a", "n_palavras_so_b", "palavras_so_a", "palavras_so_b",
                  "rotulo_manual", "notas"]
        with (self.root / "output" / "corpus_redundancy_label_sample.csv").open(
                "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for pid, a, b, label in rows:
                writer.writerow({"par_id": pid, "faixa": "baixa", "artigo": URL, "tstamp_a": a,
                                 "tstamp_b": b, "similaridade": "0.4", "rotulo_manual": label})


class RedundancyOnBodyTests(BodyAdoptionTestCase):
    def test_body_mode_ignores_rotating_chrome_and_separates_no_body(self) -> None:
        self.write([("20200101000000", page("Bas Dost marca dois golos")),
                    ("20200102000000", NO_ARTICLE),
                    ("20200103000000", page("Pepe renova contrato no Porto"))])
        self.write_labels([("1", "20200101000000", "20200103000000", "mesma versão"),
                           ("2", "20200101000000", "20200102000000", "texto alterado")])
        before = (self.root / "output" / "corpus_redundancy_label_sample.csv").read_bytes()

        rows, _, _ = corpus_redundancy.run(self.root, threshold=0.9, use_body=True)

        by_tstamp = {r["tstamp"]: r for r in rows}
        self.assertEqual(by_tstamp["20200102000000"]["camada"], corpus_redundancy.LAYER_NO_BODY)
        self.assertEqual(by_tstamp["20200102000000"]["tem_texto"], "True")
        # As manchetes diferem, o corpo não: a segunda captura com corpo é redundante.
        self.assertEqual(by_tstamp["20200103000000"]["rotulo"], corpus_redundancy.LABEL_REDUNDANT)
        self.assertEqual(by_tstamp["20200103000000"]["sim_consecutiva"], "1.000000")
        summary = (self.root / "output" / "corpus_redundancy_summary.md").read_text("utf-8")
        # Validação sobre o corpo: o par 1 passa a 1,0; o par 2 (sem corpo) fica à parte.
        self.assertIn("erro conservador): **0 de 1**", summary)
        self.assertIn("par 2 (texto alterado)", summary)
        self.assertEqual((self.root / "output" / "corpus_redundancy_label_sample.csv").read_bytes(),
                         before)

    def test_full_text_mode_keeps_the_previous_behaviour(self) -> None:
        self.write([("20200101000000", page("Bas Dost marca dois golos")),
                    ("20200102000000", NO_ARTICLE)])
        rows, _, _ = corpus_redundancy.run(self.root, threshold=0.9)
        self.assertEqual({r["camada"] for r in rows}, {corpus_redundancy.LAYER_TEXT})


class EntitiesOnBodyTests(BodyAdoptionTestCase):
    def test_headline_mentions_are_ignored_and_no_body_captures_do_not_count(self) -> None:
        self.write([("20200101000000", page("Bas Dost marca dois golos")),
                    ("20200102000000", NO_ARTICLE),
                    ("20200103000000", page("Bas Dost volta a marcar"))])
        vocab = self.root / "vocab.csv"
        vocab.write_text("tipo,categoria,rotulo,variantes\n"
                         "entidade,jogador,Jonas,\nentidade,jogador,Bas Dost,\n", encoding="utf-8")

        rows = corpus_entities.run(self.root, vocab, use_body=True)

        found = {r["rotulo"]: r for r in rows if r["origem"] == "texto"}
        self.assertEqual(set(found), {"Jonas"})
        # Persistente nas 2 capturas com corpo; a captura sem corpo não conta.
        self.assertEqual((found["Jonas"]["capturas_com_mencao"], found["Jonas"]["capturas_com_texto"],
                          found["Jonas"]["persistente"]), ("2", "2", "True"))
