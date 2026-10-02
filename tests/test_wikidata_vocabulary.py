from __future__ import annotations

import csv
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from semantic_harvester.corpus_entities import load_vocabulary
from semantic_harvester.wikidata_vocabulary import (
    SEASONS, WikidataClient, build_vocabulary, clean_name, collect_players,
    overlaps, run,
)
from tests.support import FixtureResponse, OfflineTestCase

WD = "http://www.wikidata.org/entity/"


def stint(player: str, start: str | None = None, end: str | None = None,
          label: str | None = None, lang: str = "pt", alt: str | None = None) -> dict:
    b = {"player": {"value": WD + player}}
    if start:
        b["start"] = {"value": f"{start}-07-01T00:00:00Z"}
    if end:
        b["end"] = {"value": f"{end}-06-30T00:00:00Z"}
    if label:
        b["label"] = {"value": label}
        b["lang"] = {"value": lang}
    if alt:
        b["alt"] = {"value": alt}
        b["altlang"] = {"value": "pt"}
    return b


class OverlapTests(unittest.TestCase):
    def test_rules(self) -> None:
        self.assertTrue(overlaps(2018, 2019))
        self.assertTrue(overlaps(2016, None))
        self.assertTrue(overlaps(2010, 2015))
        self.assertFalse(overlaps(2005, 2010))
        self.assertFalse(overlaps(2021, None))
        self.assertFalse(overlaps(None, None))
        self.assertFalse(overlaps(None, 2018))

    def test_clean_name(self) -> None:
        self.assertEqual(clean_name("Pizzi (futebolista)"), "Pizzi")


class CollectAndBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bindings = {
            "Q1": [
                stint("P1", "2018", "2019", label="João Félix"),
                stint("P1", "2018", "2019", label="Joao Felix", lang="en"),
                stint("P1", "2018", "2019", label="João Félix", alt="João Félix Sequeira"),
                stint("P1", "2018", "2019", label="João Félix", alt="Félix"),
                stint("P2", "1998", "2002", label="Veterano Antigo"),
                stint("P3", label="Sem Datas"),
                stint("P4", "2016", None, label="Bruno Fernandes"),
            ],
            "Q2": [
                stint("P5", "2015", "2017", label="Bruno Fernandes"),
                stint("P6", "2017", "2018", label="Rafa", alt="Rafa Silva"),
                stint("P7", "2017", "2018", label="Rafa Silva"),
            ],
        }

    def test_only_overlapping_stints_with_dates(self) -> None:
        players = collect_players(self.bindings)
        self.assertEqual(set(players), {"P1", "P4", "P5", "P6", "P7"})
        self.assertEqual(players["P1"].clubs, {"Q1"})

    def test_vocabulary_rules(self) -> None:
        vocabulary, stats = build_vocabulary(collect_players(self.bindings),
                                             {"Q1": "Benfica", "Q2": "Braga"})
        rows = {r["rotulo"]: r for r in vocabulary}
        # Rótulo pt; variantes = rótulo en e nomes alternativos com 2+ palavras.
        self.assertEqual(rows["João Félix"]["variantes"], "Joao Felix|João Félix Sequeira")
        self.assertEqual(stats["variantes_uma_palavra_descartadas"], 1)
        # Homónimos fundidos numa linha com todos os identificadores.
        self.assertEqual(rows["Bruno Fernandes"]["wikidata"], "P4|P5")
        self.assertEqual(rows["Bruno Fernandes"]["homonimos"], "2")
        self.assertEqual(rows["Bruno Fernandes"]["clubes"], "Benfica|Braga")
        # "Rafa Silva" é rótulo de P7 e variante de P6: variante ambígua descartada.
        self.assertEqual(rows["Rafa"]["variantes"], "")
        self.assertEqual(stats["variantes_partilhadas_descartadas"], 1)
        self.assertEqual(stats["rotulos_uma_palavra"], 1)
        self.assertNotIn("Veterano Antigo", rows)
        self.assertNotIn("Sem Datas", rows)


class RecordingSession:
    """Responde a cada consulta SPARQL com bindings sintéticos; sem rede."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.queries: list[str] = []

    def get(self, url: str, params: dict, timeout: int) -> FixtureResponse:
        query = params["query"]
        self.queries.append(query)
        if "wdt:P1923" in query:
            season = query.split("wd:")[1].split()[0]
            bindings = ([{"club": {"value": WD + "Q1"}, "label": {"value": "Clube Um"}}]
                        if season == SEASONS["2016-17"] else [])
        else:
            bindings = [stint("P1", "2017", "2018", label="Jogador Sintético")]
        return FixtureResponse(json.dumps({"results": {"bindings": bindings}}).encode("utf-8"))


class RunTests(OfflineTestCase):
    def test_run_preserves_raw_and_writes_loadable_vocabulary(self) -> None:
        session = RecordingSession()
        client = WikidataClient(self.root / "data" / "raw" / "wikidata", session=session, pause=0)

        vocabulary, stats = run(self.root, client)

        self.assertEqual(len(session.queries), len(SEASONS) + 1)
        self.assertNotIn("VALUES", " ".join(session.queries))
        raw = sorted(p.name for p in (self.root / "data" / "raw" / "wikidata").iterdir())
        self.assertIn("season_2016-17.json", raw)
        self.assertIn("club_Q1.json", raw)
        self.assertIn("club_Q1.rq", raw)
        self.assertEqual(stats["clubes"], 1)
        self.assertEqual(stats["clubes_por_epoca"]["2015-16"], 0)
        path = self.root / "data" / "processed" / "caminho_b_vocabulario_wikidata.csv"
        with path.open(encoding="utf-8") as h:
            self.assertEqual(list(csv.DictReader(h))[0]["clubes"], "Clube Um")
        (term,) = load_vocabulary(path)
        self.assertEqual(term.variants, (("jogador", "sintetico"),))
        self.assertEqual(session.headers["User-Agent"].split("/")[0], "semantic-driven-harvester")


if __name__ == "__main__":
    unittest.main()
