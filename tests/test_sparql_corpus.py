"""Consultas SPARQL ao grafo do corpus (`sparql_corpus.py`): resultados das
queries de `queries/corpus/` e comparação com o resumo do painel, gerado pelo
próprio `navigation_corpus` sobre os mesmos dados sintéticos."""

from __future__ import annotations

import csv
import gc
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from semantic_harvester import sparql_corpus
from semantic_harvester.corpus_entities_rdf import WIKIDATA_ENTITY
from semantic_harvester.corpus_entities_rdf import run as entities_rdf_run
from semantic_harvester.corpus_redundancy import corpus_graph_path
from semantic_harvester.history_pipeline import captured_at
from semantic_harvester.navigation_corpus import run as navigation_run
from semantic_harvester.rdf_mapper import build_article_history_graph, stable_hash
from tests.support import OfflineTestCase

try:
    import pyoxigraph  # noqa: F401
    HAS_PYOXIGRAPH = True
except ImportError:
    HAS_PYOXIGRAPH = False

LABEL = "por_ano"
A = "https://www.record.pt/futebol/detalhe/a.html"
B = "https://www.record.pt/noticia.asp?id=1"
C = "https://www.record.pt/tn0cs.asp?nid=5"
D = "https://www.record.pt/futebol/detalhe/d.html"
BENFICA = WIKIDATA_ENTITY + "Q131499"


class MissingDependencyTests(unittest.TestCase):
    def test_clear_message_without_pyoxigraph(self) -> None:
        with patch.dict(sys.modules, {"pyoxigraph": None}):
            with self.assertRaisesRegex(sparql_corpus.MissingDependencyError, r"pyoxigraph.*\[sparql\]"):
                sparql_corpus.require_pyoxigraph()

    def test_qid_is_validated(self) -> None:
        self.assertEqual(sparql_corpus.entity_iri("Q131499"), BENFICA)
        for bad in ("131499", "Q1> } DROP ALL; {", "q1", "Q1\n", ""):
            with self.assertRaises(ValueError):
                sparql_corpus.entity_iri(bad)

    def test_parse_dashboard_summary(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resumo.md"
            path.write_text("# R\n\n- Artigos: 3\n\n## Atletas mais mencionados no texto\n\n"
                            "| Atleta | Modalidade | Artigos |\n| --- | ---: | ---: |\n"
                            "| Rui Costa | ciclismo|futebol | 7 |\n", encoding="utf-8")
            summary = sparql_corpus.parse_dashboard_summary(path)
        self.assertEqual(summary.totals, {"Artigos": 3})
        rows = summary.sections["Atletas mais mencionados no texto"]
        self.assertEqual((rows[0][0], rows[0][-1]), ("Rui Costa", "7"))


@unittest.skipUnless(HAS_PYOXIGRAPH, "pyoxigraph não instalado (dependência opcional)")
class SparqlCorpusTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        nt = corpus_graph_path(self.root, LABEL)
        nt.parent.mkdir(parents=True)
        # D tem duas capturas: conta no ano da mais antiga (2020), não no de 2021.
        for url, tstamps in ((A, ["20190301120000"]), (B, ["20020505000000"]),
                             (C, ["19991128140726"]), (D, ["20210101000000", "20201231000000"])):
            records = [{"article_id": stable_hash(url), "original_url": url, "tstamp": t,
                        "captured_at": captured_at(t), "extracted_text_path": None,
                        "text_download_success": False} for t in tstamps]
            with nt.open("a", encoding="utf-8") as handle:
                handle.write(build_article_history_graph(records, "Título", self.root).serialize(format="nt"))

        processed = self.root / "data" / "processed"
        (processed / "vocab.csv").write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos,origem\n"
            "entidade,jogador,Rafa Silva,,Q1,futebol,,1,lista_fechada\n"
            "entidade,clube,Sport Lisboa e Benfica,Benfica,Q131499,futebol,,1,lista_fechada\n"
            "entidade,jogador,Pedro Mendes,,Q2|Q3,futebol,,2,candidato\n", encoding="utf-8")
        (processed / "caminho_b_clubes_url.csv").write_text(
            "slug,wikidata,clube\nbenfica,Q131499,Sport Lisboa e Benfica\n", encoding="utf-8")
        output = self.root / "output"
        output.mkdir()
        mentions = [(A, "clube", "Sport Lisboa e Benfica"), (A, "jogador", "Rafa Silva"),
                    (B, "clube", "Sport Lisboa e Benfica"), (C, "jogador", "Rafa Silva"),
                    (C, "jogador", "Pedro Mendes")]
        rows = [{"artigo": url, "tipo": "entidade", "categoria": cat, "rotulo": rot, "origem": "texto",
                 "capturas_com_mencao": "1", "capturas_com_texto": "1", "ocorrencias": "1",
                 "persistente": "True", "clube_coerente": ""} for url, cat, rot in mentions]
        rows.append({**rows[0], "tipo": "tema", "categoria": "modalidade", "rotulo": "futebol", "origem": "url"})
        with (output / f"corpus_entities_{LABEL}.csv").open("w", encoding="utf-8", newline="") as h:
            writer = csv.DictWriter(h, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        vocab = Path("data/processed/vocab.csv")
        entities_rdf_run(self.root, LABEL, vocab)
        navigation_run(self.root, LABEL, vocab, Path("data/processed/caminho_b_clubes_url.csv"))

    def tearDown(self) -> None:
        gc.collect()  # liberta o store antes de apagar o diretório temporário
        super().tearDown()

    def results(self) -> dict:
        store, _ = sparql_corpus.open_store(self.root, LABEL)
        try:
            return sparql_corpus.run_queries(store, "Q131499")
        finally:
            del store

    def test_queries(self) -> None:
        results = self.results()
        self.assertEqual([(r["ano"], r["artigos"], r["comEntidade"]) for r in results["artigos_por_ano"].rows],
                         [("1999", 1, 1), ("2002", 1, 1), ("2019", 1, 1), ("2020", 1, 0)])
        self.assertEqual([(r["ano"], r["artigos"]) for r in results["entidade_por_ano"].rows],
                         [("2002", 1), ("2019", 1)])
        top = [(r["rotulo"], r["origem"], r["artigos"]) for r in results["entidades_mais_mencionadas"].rows]
        self.assertEqual(top, [("Rafa Silva", "lista_fechada", 2),
                               ("Sport Lisboa e Benfica", "lista_fechada", 2),
                               ("Pedro Mendes", "candidato", 1)])
        self.assertEqual([(r["outra"], r["artigos"]) for r in results["coocorrencias"].rows],
                         [(WIKIDATA_ENTITY + "Q1", 1)])
        self.assertEqual([(r["origem"], r["entidades"]) for r in results["entidades_por_origem"].rows],
                         [("lista_fechada", 2), ("candidato", 1)])

    def test_report_matches_dashboard_and_store_is_reused(self) -> None:
        report = sparql_corpus.run(self.root, LABEL, "Q131499", top=5)
        text = report.read_text(encoding="utf-8")
        self.assertIn("Triplos no store (distintos):", text)
        self.assertIn("Carga: nesta execução", text)
        self.assertIn("## Artigos que mencionam Sport Lisboa e Benfica (`wd:Q131499`), por ano", text)
        comparison = text.split("## Comparação com o painel", 1)[1]
        self.assertNotIn("diferente (", comparison)
        self.assertNotIn("sem correspondência (", comparison)
        self.assertIn("| 2020 | 1 | 1 | igual | 0 | 0 | igual |", comparison)
        self.assertIn("| Sport Lisboa e Benfica | 2 | 2 | igual |", comparison)
        self.assertIn("| candidato | 1 | 1 | igual |", comparison)
        self.assertIn("- Artigos: painel 4, SPARQL 4 — igual", comparison)
        gc.collect()

        text = sparql_corpus.run(self.root, LABEL, "Q131499").read_text(encoding="utf-8")
        self.assertIn("store reutilizado", text)
        gc.collect()
        text = sparql_corpus.run(self.root, LABEL, "Q131499", reload=True).read_text(encoding="utf-8")
        self.assertIn("Carga: nesta execução", text)

    def test_difference_is_reported(self) -> None:
        summary = self.root / "output" / f"prototipo_{LABEL}" / "resumo.md"
        summary.write_text(summary.read_text(encoding="utf-8").replace("| 2019 | 1 | 1 |", "| 2019 | 2 | 1 |"),
                           encoding="utf-8")
        text = sparql_corpus.run(self.root, LABEL, "Q131499").read_text(encoding="utf-8")
        self.assertIn("| 2019 | 2 | 1 | diferente (2 vs 1) |", text)

    def test_changed_graph_requires_reload(self) -> None:
        sparql_corpus.run(self.root, LABEL, "Q131499")
        gc.collect()
        with corpus_graph_path(self.root, LABEL).open("a", encoding="utf-8") as handle:
            handle.write("<urn:x> <urn:y> <urn:z> .\n")
        with self.assertRaisesRegex(RuntimeError, "--recarregar"):
            sparql_corpus.run(self.root, LABEL, "Q131499")


if __name__ == "__main__":
    unittest.main()
