from __future__ import annotations

import csv
import hashlib
import json
import unittest

from semantic_harvester.corpus_entities import load_vocabulary
from semantic_harvester.corpus_phase1 import MODALIDADES
from semantic_harvester.wikidata_vocabulary_alargado import (
    CLUBES_QID, INDIVIDUAL, MAPEAMENTO, PROTECTED_NAME, TEAM, UNMAPPED, VOCAB_PATH,
    CachingClient, Entity, Person, build_vocabulary, collect_people,
    football_club_query, person_reason, portuguese_athletes_query, run,
    season_start, select_people, stint_reason, team_stints_query, write_vocabulary,
)
from tests.support import FixtureResponse, OfflineTestCase

WD = "http://www.wikidata.org/entity/"


def person_binding(player: str, label: str | None = None, lang: str = "pt",
                   alt: str | None = None, club: str | None = None,
                   start: str | None = None, end: str | None = None,
                   birth: str | None = None, wstart: str | None = None) -> dict:
    b: dict = {"player": {"value": WD + player}}
    for key, value in (("start", start), ("end", end), ("birth", birth), ("wstart", wstart)):
        if value:
            b[key] = {"value": f"{value}-01-01T00:00:00Z"}
    if club:
        b["club"] = {"value": WD + club}
    if label:
        b["label"] = {"value": label}
        b["lang"] = {"value": lang}
    if alt:
        b["alt"] = {"value": alt}
    return b


class MappingTests(unittest.TestCase):
    def test_every_discovery_modality_is_mapped_or_explained(self) -> None:
        self.assertEqual(set(MAPEAMENTO), set(MODALIDADES))
        for termo, mod in MAPEAMENTO.items():
            if mod.tipo == UNMAPPED:
                self.assertTrue(mod.motivo, termo)
                self.assertFalse(mod.ocupacoes, termo)
            else:
                self.assertIn(mod.tipo, (TEAM, INDIVIDUAL))
                self.assertTrue(mod.desportos and mod.ocupacoes, termo)
        for termo in ("aventura", "desporto escolar", "jogos olímpicos", "NFL",
                      "desporto-universitario", "jogos-europeus"):
            self.assertEqual(MAPEAMENTO[termo].tipo, UNMAPPED)

    def test_discovery_clubs_all_resolved(self) -> None:
        from semantic_harvester.corpus_phase1 import CLUBES
        self.assertEqual(set(CLUBES_QID), set(CLUBES))

    def test_season_label(self) -> None:
        self.assertEqual(season_start("1999–2000 Primeira Liga"), 1999)
        self.assertEqual(season_start("2023–24 Liga Portugal 2"), 2023)
        self.assertIsNone(season_start("2016 Primeira Liga"))


class QueryTests(unittest.TestCase):
    def test_queries(self) -> None:
        q = football_club_query("Q131499")
        self.assertIn("ps:P54 wd:Q131499", q)
        self.assertIn("wdt:P569 ?birth", q)
        self.assertIn("wdt:P2031 ?wstart", q)
        q = team_stints_query(("Q3665646",))
        self.assertIn("?occ wdt:P279* ?root", q)
        self.assertIn("?club wdt:P17 wd:Q45", q)
        q = portuguese_athletes_query(("Q6665249", "Q1"))
        self.assertIn("VALUES ?root { wd:Q6665249 wd:Q1 }", q)
        self.assertIn("?player wdt:P27 wd:Q45", q)


class DateRuleTests(unittest.TestCase):
    def test_stint_rules(self) -> None:
        nobody = Person("P")
        self.assertEqual(stint_reason(2005, 2010, nobody), "passagem_datada")
        self.assertEqual(stint_reason(2020, None, nobody), "passagem_datada")
        self.assertIsNone(stint_reason(1990, 1998, nobody))
        self.assertIsNone(stint_reason(2025, None, nobody))
        self.assertEqual(stint_reason(None, 2001, nobody), "passagem_so_fim")
        self.assertIsNone(stint_reason(None, 1997, nobody))
        self.assertIsNone(stint_reason(None, None, nobody))
        self.assertEqual(stint_reason(None, None, Person("P", birth=1980)),
                         "passagem_sem_datas_nascimento")
        self.assertEqual(stint_reason(None, None, Person("P", wstart=2010)),
                         "passagem_sem_datas_atividade")

    def test_person_rules(self) -> None:
        self.assertEqual(person_reason(Person("P", birth=1959)), "nascimento")
        self.assertEqual(person_reason(Person("P", birth=2009)), "nascimento")
        self.assertIsNone(person_reason(Person("P", birth=1958)))
        self.assertIsNone(person_reason(Person("P", birth=2010)))
        self.assertIsNone(person_reason(Person("P", birth=1970, death=1995)))
        # O período de atividade prevalece sobre o nascimento.
        self.assertIsNone(person_reason(Person("P", birth=1980, wstart=1980, wend=1990)))
        self.assertEqual(person_reason(Person("P", birth=1930, wstart=1990, wend=2000)), "atividade")
        self.assertIsNone(person_reason(Person("P")))

    def test_select_people_counts_original_rule(self) -> None:
        people = collect_people([
            person_binding("P1", "Datado", club="C1", start="2005"),
            person_binding("P2", "Sem Datas Novo", club="C1", birth="1990"),
            person_binding("P3", "Sem Datas Velho", club="C1", birth="1940"),
        ])
        selected, stats = select_people(people)
        self.assertEqual(set(selected), {"P1", "P2"})
        self.assertEqual(stats["incluidos_regra_original"], 1)
        self.assertEqual(stats["passagens_sem_datas"], 2)
        self.assertEqual(stats["excluidos_com_passagem_sem_datas"], 1)
        self.assertNotIn("excluidos_sem_nenhuma_data", stats)
        self.assertEqual(selected["P2"], ("passagem_sem_datas_nascimento", {"C1"}))


class VocabularyTests(unittest.TestCase):
    def test_city_rule(self) -> None:
        places = {"porto", "braga"}
        entities = [
            Entity("clube", "Q1", {"pt": "Porto", "en": "FC Porto"}, {"Futebol Clube do Porto"}, {"futebol"}),
            Entity("clube", "Q2", {"pt": "Sporting Clube de Braga", "en": "Braga"}, set(), {"futebol"}),
            Entity("clube", "Q3", {"pt": "Braga"}, {"Braga"}, {"andebol"}),
            Entity("clube", "Q4", {"pt": "Sporting Clube de Portugal", "en": "Sporting"}, set(), {"futebol"}),
            Entity("clube", "Q5", {"pt": "Vitória Sport Clube"}, {"Vitória", "Vitória de Guimarães"}, {"futebol"}),
        ]
        rows, stats = build_vocabulary(entities, {}, places)
        by_label = {r["rotulo"]: r for r in rows}
        # Rótulo que é cidade → forma mais longa sem ambiguidade.
        self.assertIn("Futebol Clube do Porto", by_label)
        self.assertEqual(by_label["Futebol Clube do Porto"]["variantes"], "FC Porto")
        self.assertNotIn("Porto", by_label)
        self.assertEqual(by_label["Sporting Clube de Braga"]["variantes"], "")
        # Sem nenhuma forma sem ambiguidade, o clube fica de fora.
        self.assertEqual(stats["clubes_sem_forma_inequivoca"], 1)
        # Nome de uma palavra que não é lugar continua (rótulo noutra língua).
        self.assertEqual(by_label["Sporting Clube de Portugal"]["variantes"], "Sporting")
        # Palavra comum de uma palavra também não entra.
        self.assertEqual(by_label["Vitória Sport Clube"]["variantes"], "Vitória de Guimarães")

    def test_homonyms_across_modalities_and_categories(self) -> None:
        entities = [
            Entity("clube", "Q10", {"pt": "Sport Lisboa e Benfica"}, set(), {"futebol"}),
            Entity("clube", "Q11", {"pt": "Sport Lisboa e Benfica"}, set(), {"basquetebol"}),
            Entity("jogador", "P1", {"pt": "Rui Silva"}, set(), {"futebol"}, {"Q10"}),
            Entity("jogador", "P2", {"pt": "Rui Silva"}, set(), {"andebol"}),
            Entity("jogador", "P3", {"pt": "Académica"}, set(), {"rugby"}),
            Entity("clube", "Q12", {"pt": "Académica"}, set(), {"futebol"}),
        ]
        rows, stats = build_vocabulary(entities, {"Q10": "Sport Lisboa e Benfica"}, set())
        by_label = {r["rotulo"]: r for r in rows}
        self.assertEqual(by_label["Sport Lisboa e Benfica"]["wikidata"], "Q10|Q11")
        self.assertEqual(by_label["Sport Lisboa e Benfica"]["modalidade"], "basquetebol|futebol")
        self.assertEqual(by_label["Rui Silva"]["homonimos"], "2")
        self.assertEqual(by_label["Rui Silva"]["modalidade"], "andebol|futebol")
        self.assertEqual(by_label["Rui Silva"]["clubes"], "Sport Lisboa e Benfica")
        self.assertEqual(by_label["Académica"]["categoria"], "clube|jogador")
        self.assertEqual(stats["homonimos_entre_modalidades"], 3)
        self.assertEqual(stats["homonimos_clube_jogador"], 1)

    def test_player_rules_kept(self) -> None:
        entities = [
            Entity("jogador", "P1", {"pt": "Luís Miguel Afonso Fernandes", "en": "Pizzi"},
                   {"Pizzi", "Luís Fernandes"}, {"futebol"}),
            Entity("jogador", "P2", {"pt": "Rafa"}, {"Rafa Silva"}, {"futebol"}),
            Entity("jogador", "P3", {"pt": "Rafa Silva"}, set(), {"futebol"}),
        ]
        rows, stats = build_vocabulary(entities, {}, set())
        by_label = {r["rotulo"]: r for r in rows}
        self.assertEqual(by_label["Luís Miguel Afonso Fernandes"]["variantes"], "Luís Fernandes|Pizzi")
        self.assertEqual(by_label["Rafa"]["variantes"], "")
        self.assertEqual(stats["variantes_partilhadas_descartadas"], 1)

    def test_refuses_original_vocabulary_path(self) -> None:
        with self.assertRaises(ValueError):
            write_vocabulary([], VOCAB_PATH.parent / PROTECTED_NAME)


class FakeWikidata:
    """Responde por padrão da consulta; sem rede."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.queries: list[str] = []

    def get(self, url: str, params: dict, timeout: int) -> FixtureResponse:
        q = params["query"]
        self.queries.append(q)
        if "?season wdt:P3450" in q:
            b = [{"season": {"value": WD + "S1"}, "label": {"value": "2016–17 Primeira Liga"},
                  "clubs": {"value": "1"}},
                 {"season": {"value": WD + "S0"}, "label": {"value": "1990–91 Primeira Liga"},
                  "clubs": {"value": "3"}}] if "Q182994" in q else []
        elif "wdt:P1923" in q:
            b = [{"club": {"value": WD + "Q131499"}}]
        elif "p:P118" in q:
            b = [{"club": {"value": WD + "Q75684"}}]
        elif "COUNT(DISTINCT ?player)" in q:
            b = [{"n": {"value": "7"}}]
        elif "ps:P54 wd:Q131499" in q:
            b = [person_binding("P1", "Jogador Benfica", club=None, start="2010"),
                 person_binding("P9", "Antigo", start="1980", end="1985")]
        elif "ps:P54 ?club" in q and "Q3665646" in q:
            b = [person_binding("P2", "Jogador Benfica", club="Q131499", birth="1990"),
                 person_binding("P5", "Só Seleção", club="Q999", start="2010")]
        elif "wdt:P279* wd:Q1194951" in q:
            b = [{"club": {"value": WD + "Q999"}}]
        elif "?player wdt:P27" in q and "Q6665249" in q:
            b = [person_binding("P3", "Judoca Sintética", birth="1985")]
        elif "?item rdfs:label ?label" in q and "VALUES ?item" in q and "?country" not in q:
            b = [{"item": {"value": WD + "Q2736"}, "label": {"value": "futebol"}, "lang": {"value": "pt"}}]
        elif "VALUES ?item" in q:
            b = [{"item": {"value": WD + "Q131499"}, "label": {"value": "Sport Lisboa e Benfica"},
                  "lang": {"value": "pt"}},
                 {"item": {"value": WD + "Q75684"}, "label": {"value": "Braga"}, "lang": {"value": "pt"}}]
        elif "VALUES ?name" in q:
            b = [{"name": {"value": "Braga"}, "place": {"value": WD + "Q83247"}}]
        else:
            b = []
        return FixtureResponse(json.dumps({"results": {"bindings": b}}).encode("utf-8"))


class RunTests(OfflineTestCase):
    def test_run_offline_writes_new_paths_only(self) -> None:
        original = self.root / "data" / "processed" / PROTECTED_NAME
        original.parent.mkdir(parents=True)
        original.write_text("tipo,categoria,rotulo\nentidade,jogador,Intocado\n", encoding="utf-8")
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        session = FakeWikidata()
        sleeps: list[float] = []
        client = CachingClient(self.root / "data" / "raw" / "wikidata" / "alargado",
                               session=session, pause=0, sleep=sleeps.append)

        vocabulary, m = run(self.root, client)

        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), before)
        self.assertEqual(m["epocas"]["Primeira Liga"]["com_participantes"], ["2016-17"])
        self.assertEqual(m["clubes_futebol"]["epocas_P1923"], 1)
        self.assertEqual(m["clubes_futebol"]["liga_P118"], 1)
        self.assertEqual(m["futebol_portugueses_total"], 7)
        self.assertEqual(m["consultas_falhadas"], [])
        self.assertEqual(sleeps, [])
        raw = {p.name for p in (self.root / "data" / "raw" / "wikidata" / "alargado").iterdir()}
        self.assertIn("futebol_clube_Q131499.json", raw)
        self.assertIn("modalidade_judo_portugueses.json", raw)
        self.assertIn("localidades.rq", raw)
        rows = {r["rotulo"]: r for r in vocabulary}
        self.assertNotIn("Antigo", rows)
        # Passagem só por uma seleção nacional não conta.
        self.assertNotIn("Só Seleção", rows)
        self.assertEqual(m["selecoes_nacionais_excluidas"], 1)
        # Jogador de futebol (passagem datada) e de basquetebol (sem datas,
        # nascimento) fundidos como homónimos entre modalidades.
        self.assertEqual(rows["Jogador Benfica"]["wikidata"], "P1|P2")
        self.assertEqual(rows["Jogador Benfica"]["modalidade"], "basquetebol|futebol")
        self.assertEqual(rows["Sport Lisboa e Benfica"]["modalidade"], "basquetebol|futebol")
        self.assertEqual(rows["Judoca Sintética"]["modalidade"], "judo")
        self.assertNotIn("Braga", rows)  # clube só com nome de cidade
        path = self.root / VOCAB_PATH
        terms = load_vocabulary(path)
        self.assertEqual(len(terms), len(vocabulary))
        with path.open(encoding="utf-8") as h:
            self.assertIn("modalidade", csv.DictReader(h).fieldnames)
        self.assertTrue((self.root / "output" / "wikidata_vocabulario_alargado.md").exists())

        # Reutilizar o raw não faz pedidos.
        session2 = FakeWikidata()
        client2 = CachingClient(client.raw_dir, session=session2, pause=0, reuse=True)
        again, _ = run(self.root, client2)
        self.assertEqual(session2.queries, [])
        self.assertEqual(again, vocabulary)

    def test_failed_query_is_retried_then_recorded(self) -> None:
        class Failing:
            headers: dict = {}

            def get(self, *a, **k):
                raise RuntimeError("504")

        sleeps: list[float] = []
        client = CachingClient(self.root / "raw", session=Failing(), pause=0, sleep=sleeps.append)
        self.assertEqual(client.query("x", "SELECT"), [])
        self.assertEqual(client.failures, ["x"])
        self.assertEqual(len(sleeps), 1)
        self.assertEqual(client.requests, 2)


class LoadExistingVocabularyTests(unittest.TestCase):
    def test_new_csv_loads_with_load_vocabulary(self) -> None:
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / VOCAB_PATH
        if not path.exists():
            self.skipTest("vocabulário alargado não gerado neste clone")
        terms = load_vocabulary(path)
        self.assertTrue(terms)
        self.assertTrue(all(t.tipo == "entidade" for t in terms))


if __name__ == "__main__":
    unittest.main()
