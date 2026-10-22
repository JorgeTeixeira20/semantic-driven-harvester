"""Abordagem híbrida (`wikidata_candidates.py`): respostas SPARQL simuladas,
sem rede. Os QIDs dos itens são fictícios, exceto onde indicado."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from semantic_harvester.corpus_entities import load_vocabulary
from semantic_harvester.wikidata_candidates import (
    ACCEPTED, AMBIGUOUS, FAILED, NEW_VARIANT, NO_MATCH, OUT_OF_SCOPE, WRONG_TYPE,
    candidate_query, decide, parse_matches, run,
)
from semantic_harvester.wikidata_vocabulary_alargado import CachingClient
from tests.support import OfflineTestCase


def binding(qid: str, label: str = "", kind: str = "", pt: bool | None = None) -> dict:
    b = {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{qid}"}}
    if label:
        b["label"] = {"type": "literal", "value": label}
    if kind:
        b["kind"] = {"type": "literal", "value": kind}
        b["pt"] = {"type": "literal", "value": "true" if pt else "false"}
    return b


class Response:
    def __init__(self, content: bytes, fail: bool = False) -> None:
        self.content, self.fail = content, fail

    def raise_for_status(self) -> None:
        if self.fail:
            raise RuntimeError("500")


class FakeSession:
    """Responde pelo nome que aparece na query; regista os nomes pedidos."""

    def __init__(self, answers: dict[str, list[dict] | None]) -> None:
        self.answers, self.headers, self.asked = answers, {}, []

    def get(self, url: str, params: dict, timeout: int) -> Response:
        name = next(n for n in self.answers if f'"{n}"@pt' in params["query"])
        self.asked.append(name)
        bindings = self.answers[name]
        if bindings is None:
            return Response(b"", fail=True)
        return Response(json.dumps({"results": {"bindings": bindings}}).encode())


class QueryTests(unittest.TestCase):
    def test_query_escapes_and_searches_pt_and_en(self) -> None:
        query = candidate_query('Estádio "Novo"')
        self.assertIn('"Estádio \\"Novo\\""@pt', query)
        self.assertIn('"Estádio \\"Novo\\""@en', query)
        for needed in ("wd:Q45", "wd:Q35572", "wdt:P664", "wdt:P6087", "'treinador'", "'estadio'"):
            self.assertIn(needed, query)


class DecideTests(unittest.TestCase):
    def test_single_valid_item_is_accepted(self) -> None:
        m = parse_matches([binding("Q1", "Estádio da Luz", "estadio", True)])
        d = decide("Estádio da Luz", 5, m, set())
        self.assertEqual((d.decision, d.kind, d.qid), (ACCEPTED, "estadio", "Q1"))

    def test_person_who_is_coach_and_player_is_coach(self) -> None:
        m = parse_matches([binding("Q1", "Jorge Jesus", "jogador", True),
                           binding("Q1", "Jorge Jesus", "treinador", True)])
        self.assertEqual(decide("Jorge Jesus", 9, m, set()).kind, "treinador")

    def test_two_valid_items_are_ambiguous(self) -> None:
        m = parse_matches([binding("Q1", kind="clube", pt=True), binding("Q2", kind="clube", pt=True)])
        self.assertEqual(decide("Académico", 3, m, set()).decision, AMBIGUOUS)

    def test_valid_item_wins_over_out_of_scope_one(self) -> None:
        m = parse_matches([binding("Q1", kind="clube", pt=True), binding("Q2", kind="clube", pt=False)])
        self.assertEqual(decide("Nome", 3, m, set()).qid, "Q1")

    def test_foreign_wrong_type_and_no_match(self) -> None:
        foreign = parse_matches([binding("Q1", kind="clube", pt=False)])
        self.assertEqual(decide("Real Madrid", 4, foreign, set()).decision, OUT_OF_SCOPE)
        city = parse_matches([binding("Q1", "Lisboa")])
        self.assertEqual(decide("Lisboa", 4, city, set()).decision, WRONG_TYPE)
        self.assertEqual(decide("Nada Disto", 4, {}, set()).decision, NO_MATCH)

    def test_known_qid_is_a_new_variant(self) -> None:
        m = parse_matches([binding("Q131499", kind="clube", pt=True)])  # Benfica (QID real)
        self.assertEqual(decide("Sport Lisboa Benfica", 4, m, {"Q131499"}).decision, NEW_VARIANT)


class RunTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "output").mkdir()
        rows = [("Estádio da Luz", 12), ("Estádio do Sport Lisboa e Benfica", 4),
                ("Liga dos Campeões", 30), ("Sport Lisboa Benfica", 5),
                ("Real Madrid", 20), ("Notícias Recentes", 50), ("Falha Rede", 3),
                ("Raro Demais", 2)]
        with (self.root / "output" / "corpus_candidate_entities_por_ano.csv").open(
                "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("candidato", "artigos", "ocorrencias", "exemplo_artigo"))
            writer.writerows((c, n, n, "https://www.record.pt/x") for c, n in rows)
        vocab = self.root / "data" / "processed" / "caminho_b_vocabulario_wikidata_alargado.csv"
        vocab.parent.mkdir(parents=True)
        vocab.write_text(
            "tipo,categoria,rotulo,variantes,wikidata,modalidade,clubes,homonimos\n"
            "entidade,clube,Sport Lisboa e Benfica,Benfica,Q131499,futebol,,1\n"
            "entidade,jogador,Rafa Silva,,Q1,futebol,Sport Lisboa e Benfica,1\n", encoding="utf-8")
        self.before = vocab.read_bytes()
        self.vocab = vocab
        self.session = FakeSession({
            "Estádio da Luz": [binding("Q100", "Estádio do Sport Lisboa e Benfica", "estadio", True)],
            "Estádio do Sport Lisboa e Benfica": [binding("Q100", "Estádio do Sport Lisboa e Benfica", "estadio", True)],
            "Liga dos Campeões": [binding("Q101", "Liga dos Campeões da UEFA", "competicao", True)],
            "Sport Lisboa Benfica": [binding("Q131499", "Sport Lisboa e Benfica", "clube", True)],
            "Real Madrid": [binding("Q102", "Real Madrid", "clube", False)],
            "Notícias Recentes": [],
            "Falha Rede": None,
            "Raro Demais": [],
        })
        client = CachingClient(self.root / "raw", session=self.session, pause=0, sleep=lambda s: None)
        self.decisions = {d.candidate: d for d in run(self.root, min_articles=3, client=client)}

    def test_min_articles_and_decisions(self) -> None:
        self.assertNotIn("Raro Demais", self.session.asked)
        self.assertEqual({c: d.decision for c, d in self.decisions.items()}, {
            "Estádio da Luz": ACCEPTED, "Estádio do Sport Lisboa e Benfica": ACCEPTED,
            "Liga dos Campeões": ACCEPTED, "Sport Lisboa Benfica": NEW_VARIANT,
            "Real Madrid": OUT_OF_SCOPE, "Notícias Recentes": NO_MATCH, "Falha Rede": FAILED,
        })

    def test_hybrid_vocabulary(self) -> None:
        self.assertEqual(self.vocab.read_bytes(), self.before)
        path = self.root / "data" / "processed" / "caminho_b_vocabulario_hibrido_por_ano.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = {r["wikidata"]: r for r in csv.DictReader(handle)}
        self.assertEqual(rows["Q1"]["origem"], "lista_fechada")
        self.assertEqual(rows["Q131499"]["origem"], "lista_fechada+candidato")
        self.assertEqual(rows["Q131499"]["variantes"], "Benfica|Sport Lisboa Benfica")
        # Duas formas do mesmo estádio: uma linha, rótulo da Wikidata, formas como variantes.
        self.assertEqual((rows["Q100"]["rotulo"], rows["Q100"]["variantes"], rows["Q100"]["categoria"]),
                         ("Estádio do Sport Lisboa e Benfica", "Estádio da Luz", "estadio"))
        self.assertEqual(rows["Q101"]["origem"], "candidato")
        self.assertNotIn("Q102", rows)
        terms = {t.rotulo: t for t in load_vocabulary(path)}
        self.assertIn(("estadio", "da", "luz"), terms["Estádio do Sport Lisboa e Benfica"].variants)

    def test_decisions_csv_and_raw(self) -> None:
        with (self.root / "output" / "wikidata_candidatos_por_ano.csv").open(encoding="utf-8") as h:
            self.assertEqual(len(list(csv.DictReader(h))), 7)
        self.assertTrue(any((self.root / "raw").glob("candidato_*.json")))


if __name__ == "__main__":
    unittest.main()
