"""Abordagem híbrida (`wikidata_candidates.py`): respostas SPARQL simuladas,
sem rede. Os QIDs dos itens são fictícios, exceto onde indicado."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from semantic_harvester.corpus_entities import load_vocabulary
from semantic_harvester.wikidata_candidates import (
    ACCEPTED, AMBIGUOUS, BAD_FORM, FAILED, NEW_VARIANT, NO_MATCH, OUT_OF_SCOPE, REJECTED_ITEM,
    WRONG_TYPE,
    candidate_query, decide, form_problem, parse_matches, run,
)
from semantic_harvester.wikidata_vocabulary_alargado import CachingClient
from tests.support import OfflineTestCase


def binding(qid: str, label: str = "", kind: str = "", pt: bool | None = None, links: int = 0) -> dict:
    b = {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{qid}"},
         "links": {"type": "literal", "value": str(links)}}
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
    """Responde pelo nome na query (nome exato ou pesquisa); regista os pedidos."""

    def __init__(self, answers: dict[str, list[dict] | None],
                 search: dict[str, list[dict]] | None = None) -> None:
        self.answers, self.search, self.headers, self.asked = answers, search or {}, {}, []

    def get(self, url: str, params: dict, timeout: int) -> Response:
        query = params["query"]
        if "EntitySearch" in query:
            name = next(n for n in self.answers if f'mwapi:search "{n}"' in query)
            self.asked.append(("pesquisa", name))
            bindings = self.search.get(name, [])
            return Response(json.dumps({"results": {"bindings": bindings}}).encode())
        name = next(n for n in self.answers if f'"{n}"@pt' in query)
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
        for needed in ("wd:Q45", "wd:Q35572", "wdt:P664", "wdt:P6087", "'treinador'", "'estadio'",
                       "wikibase:sitelinks"):
            self.assertIn(needed, query)
        search = candidate_query("Liga dos Campeões", search=True)
        self.assertIn('mwapi:search "Liga dos Campeões"', search)
        self.assertNotIn("skos:altLabel ?name", search)


class DecideTests(unittest.TestCase):
    def test_single_valid_item_is_accepted(self) -> None:
        m = parse_matches([binding("Q1", "Estádio da Luz", "estadio", True)])
        d = decide("Estádio da Luz", 5, m, set())
        self.assertEqual((d.decision, d.kind, d.qid), (ACCEPTED, "estadio", "Q1"))

    def test_person_who_is_coach_and_player_is_coach(self) -> None:
        m = parse_matches([binding("Q1", "Jorge Jesus", "jogador", True),
                           binding("Q1", "Jorge Jesus", "treinador", True)])
        self.assertEqual(decide("Jorge Jesus", 9, m, set()).kind, "treinador")

    def test_two_valid_items_without_a_clear_leader_are_ambiguous(self) -> None:
        m = parse_matches([binding("Q1", kind="clube", pt=True), binding("Q2", kind="clube", pt=True)])
        self.assertEqual(decide("Académico", 3, m, set()).decision, AMBIGUOUS)
        close = parse_matches([binding("Q1", kind="estadio", pt=True, links=10),
                               binding("Q2", kind="estadio", pt=True, links=8)])
        self.assertEqual(decide("Estádio", 3, close, set()).decision, AMBIGUOUS)

    def test_prominence_breaks_the_tie(self) -> None:
        # Estádio atual (muitas Wikipédias) e o antigo com o mesmo nome (poucas).
        m = parse_matches([binding("Q287359", kind="estadio", pt=True, links=40),
                           binding("Q3059094", kind="estadio", pt=True, links=6)])
        d = decide("Estádio José Alvalade", 9, m, set())
        self.assertEqual((d.decision, d.qid, d.tie), (ACCEPTED, "Q287359", "proeminencia"))

    def test_foreign_is_accepted_and_recorded_unless_only_portugal(self) -> None:
        foreign = parse_matches([binding("Q1", kind="clube", pt=False)])
        d = decide("Real Madrid", 4, foreign, set())
        self.assertEqual((d.decision, d.portugal), (ACCEPTED, False))
        self.assertEqual(decide("Real Madrid", 4, foreign, set(), only_portugal=True).decision,
                         OUT_OF_SCOPE)
        mixed = parse_matches([binding("Q1", kind="clube", pt=True, links=1),
                               binding("Q2", kind="clube", pt=False, links=1)])
        self.assertEqual(decide("Nome", 3, mixed, set(), only_portugal=True).qid, "Q1")

    def test_label_falls_back_to_english(self) -> None:
        en_only = {**binding("Q615", kind="jogador", pt=False, links=200),
                   "labelEn": {"type": "literal", "value": "Lionel Messi"}}
        self.assertEqual(decide("Lionel Messi", 9, parse_matches([en_only]), set()).wikidata_label,
                         "Lionel Messi")
        both = {**binding("Q1", "Estádio do Dragão", "estadio", True),
                "labelEn": {"type": "literal", "value": "Dragão Stadium"}}
        self.assertEqual(parse_matches([both])["Q1"].label, "Estádio do Dragão")

    def test_wrong_type_and_no_match(self) -> None:
        city = parse_matches([binding("Q1", "Lisboa")])
        self.assertEqual(decide("Lisboa", 4, city, set()).decision, WRONG_TYPE)
        self.assertEqual(decide("Nada Disto", 4, {}, set()).decision, NO_MATCH)

    def test_known_qid_is_a_new_variant(self) -> None:
        m = parse_matches([binding("Q131499", kind="clube", pt=True)])  # Benfica (QID real)
        self.assertEqual(decide("Sport Lisboa Benfica", 4, m, {"Q131499"}).decision, NEW_VARIANT)


class Corrections20261023Tests(unittest.TestCase):
    """Erros vistos no topo do corpus alargado (relatório da cadeia, 2026-10-23)."""

    def test_sentence_fragments_are_not_candidates(self) -> None:
        for candidate in ("A Liga", "O Sp", "FIM DA", "DE MARÇO", "QUARTOS DE FINAL",
                          "Nacional E", "Vuelta O", "Grupo B", "FC Porto V"):
            with self.subTest(candidate=candidate):
                self.assertIsNotNone(form_problem(candidate))
        for candidate in ("Liga dos Campeões", "Real Madrid", "Estádio da Luz", "FC Porto",
                          "Jorge Jesus", "II Liga", "Euro 2004"):
            with self.subTest(candidate=candidate):
                self.assertIsNone(form_problem(candidate))

    def test_search_needs_a_label_starting_with_the_candidate(self) -> None:
        lithuanian = parse_matches([binding("Q1", "Campeonato Lituano de Futebol", "competicao", False, 30)])
        self.assertEqual(decide("I Liga", 9, lithuanian, set(), method="pesquisa").decision, REJECTED_ITEM)
        airport = parse_matches([binding("Q2", "Aeroporto Internacional do Rio de Janeiro", "estadio", False)])
        self.assertEqual(decide("Rio de Janeiro", 9, airport, set(), method="pesquisa").decision,
                         REJECTED_ITEM)
        champions = parse_matches([binding("Q18756", "Liga dos Campeões da UEFA", "competicao", True, 90)])
        self.assertEqual(decide("Liga dos Campeões", 9, champions, set(), method="pesquisa").decision,
                         ACCEPTED)

    def test_seasons_editions_and_federations_are_rejected(self) -> None:
        season = parse_matches([binding("Q3", "Liga NOS de 2016–17", "competicao", True, 20)])
        self.assertEqual(decide("Liga NOS", 9, season, set()).decision, REJECTED_ITEM)
        club_season = {**binding("Q4", kind="competicao", pt=True),
                       "labelEn": {"type": "literal", "value": "2014–15 F.C. Porto season"}}
        self.assertEqual(decide("FC Porto", 9, parse_matches([club_season]), set()).decision, REJECTED_ITEM)
        federation = parse_matches([binding("Q5", "Federação de Ginástica de Portugal", "clube", True)])
        self.assertEqual(decide("Federação Portuguesa", 9, federation, set()).decision, REJECTED_ITEM)
        with_year = parse_matches([binding("Q6", "Euro 2004", "competicao", True)])
        self.assertEqual(decide("Euro 2004", 9, with_year, set()).decision, ACCEPTED)

    def test_the_real_competition_wins_over_its_season(self) -> None:
        both = parse_matches([binding("Q7", "Taça UEFA", "competicao", True, 40),
                              binding("Q8", "Copa da UEFA de 2006-07", "competicao", True, 50)])
        self.assertEqual(decide("Taça UEFA", 9, both, set()).qid, "Q7")


class RunTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "output").mkdir()
        rows = [("A Liga", 40), ("Estádio da Luz", 12), ("Estádio do Sport Lisboa e Benfica", 4),
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
            "A Liga": [binding("Q999", "Campeonato Lituano de Futebol", "competicao", False)],
            "Estádio da Luz": [binding("Q100", "Estádio do Sport Lisboa e Benfica", "estadio", True)],
            "Estádio do Sport Lisboa e Benfica": [binding("Q100", "Estádio do Sport Lisboa e Benfica", "estadio", True)],
            "Liga dos Campeões": [binding("Q102000", "Liga dos Campeões")],  # desambiguação
            "Sport Lisboa Benfica": [binding("Q131499", "Sport Lisboa e Benfica", "clube", True)],
            "Real Madrid": [binding("Q102", "Real Madrid", "clube", False)],
            "Notícias Recentes": [],
            "Falha Rede": None,
            "Raro Demais": [],
        }, search={
            "Liga dos Campeões": [binding("Q101", "Liga dos Campeões da UEFA", "competicao", True, 80),
                                  binding("Q103", "Liga dos Campeões da AFC", "competicao", False, 20)],
        })
        client = CachingClient(self.root / "raw", session=self.session, pause=0, sleep=lambda s: None)
        self.decisions = {d.candidate: d for d in run(self.root, min_articles=3, client=client)}

    def test_min_articles_and_decisions(self) -> None:
        self.assertNotIn("Raro Demais", self.session.asked)
        self.assertNotIn("A Liga", self.session.asked)
        self.assertEqual(self.decisions.pop("A Liga").decision, BAD_FORM)
        # A numeração das respostas guardadas não muda: "Estádio da Luz" continua a ser o 2.º.
        self.assertTrue((self.root / "raw" / "candidato_00002.json").is_file())
        self.assertEqual({c: d.decision for c, d in self.decisions.items()}, {
            "Estádio da Luz": ACCEPTED, "Estádio do Sport Lisboa e Benfica": ACCEPTED,
            "Liga dos Campeões": ACCEPTED, "Sport Lisboa Benfica": NEW_VARIANT,
            "Real Madrid": ACCEPTED, "Notícias Recentes": NO_MATCH, "Falha Rede": FAILED,
        })
        champions = self.decisions["Liga dos Campeões"]
        self.assertEqual((champions.qid, champions.method, champions.tie),
                         ("Q101", "pesquisa", "proeminencia"))
        # A pesquisa só quando o nome exato não dá nenhum item válido.
        self.assertNotIn(("pesquisa", "Estádio da Luz"), self.session.asked)
        self.assertIn(("pesquisa", "Notícias Recentes"), self.session.asked)

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
        self.assertEqual((rows["Q102"]["origem"], rows["Q102"]["portugal"]), ("candidato", "nao"))
        self.assertEqual(rows["Q1"]["portugal"], "sim")
        terms = {t.rotulo: t for t in load_vocabulary(path)}
        self.assertIn(("estadio", "da", "luz"), terms["Estádio do Sport Lisboa e Benfica"].variants)

    def test_decisions_csv_and_raw(self) -> None:
        with (self.root / "output" / "wikidata_candidatos_por_ano.csv").open(encoding="utf-8") as h:
            self.assertEqual(len(list(csv.DictReader(h))), 8)
        self.assertTrue(any((self.root / "raw").glob("candidato_*.json")))


if __name__ == "__main__":
    unittest.main()
