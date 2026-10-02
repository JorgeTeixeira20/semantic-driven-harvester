"""Caminho B — vocabulário fechado de jogadores a partir da Wikidata.

Fonte decidida pelo autor (`docs/experiments.md`, "Caminho B"): jogadores dos
plantéis dos clubes da Primeira Liga (Liga NOS) nas épocas 2015–16 a 2019–20.
É uma fonte independente dos termos de pesquisa da Fase 1.

Passos (pedidos ao endpoint SPARQL público da Wikidata, um de cada vez):

1. Clubes participantes de cada época (`wdt:P1923` em cada item de época).
   Uma consulta por época: com `VALUES` o endpoint devolveu clubes de todas as
   épocas existentes (observado em 2026-10-02).
2. Por clube, os futebolistas (`wdt:P106 wd:Q937857`) com uma passagem
   (`p:P54`) cujas datas se sobrepõem ao intervalo: início ≤ 2020 e fim ≥ 2015
   ou sem fim. Passagens sem nenhuma data ficam de fora (não se pode confirmar
   o período). Rótulos e nomes alternativos em pt/en.

As respostas são guardadas byte a byte em `data/raw/wikidata/` antes de serem
interpretadas. O vocabulário (`data/processed/caminho_b_vocabulario_wikidata.csv`)
tem uma linha por rótulo: rótulo pt (ou en), variantes = outros rótulos e
nomes alternativos com 2 ou mais palavras (os de uma só palavra, como
"Ronaldo", ficam de fora por ambiguidade). Homónimos (o mesmo rótulo em vários
jogadores) são fundidos numa linha com todos os identificadores, porque a
correspondência por string não os distingue; variantes partilhadas por mais
de uma linha são descartadas.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = (
    "semantic-driven-harvester/0.1 (prototipo de dissertacao de mestrado; "
    "https://github.com/JorgeTeixeira20/semantic-driven-harvester)"
)
FOOTBALL_PLAYER = "Q937857"
# Itens de época da Primeira Liga, 2015–16 a 2019–20 (wdt:P3450 wd:Q182994).
SEASONS = {
    "2015-16": "Q20647787",
    "2016-17": "Q23991115",
    "2017-18": "Q29623740",
    "2018-19": "Q52119521",
    "2019-20": "Q63965166",
}
YEAR_FROM = 2015
YEAR_TO = 2020
PAUSE_SECONDS = 1.0
MAX_RESPONSE_BYTES = 20_000_000
VOCAB_FIELDS = ("tipo", "categoria", "rotulo", "variantes", "wikidata", "clubes", "homonimos")

_PARENS = re.compile(r"\s*\([^)]*\)\s*")


def season_query(season_qid: str) -> str:
    return (
        "SELECT ?club ?label WHERE { "
        f"wd:{season_qid} wdt:P1923 ?club . "
        "OPTIONAL { ?club rdfs:label ?label FILTER(lang(?label) = 'pt') } }"
    )


def club_players_query(club_qid: str) -> str:
    return (
        "SELECT ?player ?start ?end ?label ?lang ?alt ?altlang WHERE { "
        f"?player p:P54 ?st . ?st ps:P54 wd:{club_qid} . "
        f"?player wdt:P106 wd:{FOOTBALL_PLAYER} . "
        "OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } "
        "OPTIONAL { ?player rdfs:label ?label FILTER(lang(?label) IN ('pt', 'en')) "
        "BIND(lang(?label) AS ?lang) } "
        "OPTIONAL { ?player skos:altLabel ?alt FILTER(lang(?alt) IN ('pt', 'en')) "
        "BIND(lang(?alt) AS ?altlang) } }"
    )


class WikidataClient:
    """Pedidos SPARQL com sessão injetável; guarda cada resposta em bruto."""

    def __init__(self, raw_dir: Path, session: Any | None = None, pause: float = PAUSE_SECONDS) -> None:
        self.raw_dir = raw_dir
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
        })
        self.pause = pause

    def query(self, name: str, sparql: str) -> list[dict[str, Any]]:
        response = self.session.get(ENDPOINT, params={"query": sparql}, timeout=120)
        response.raise_for_status()
        content = response.content
        if len(content) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"Resposta de {name} com {len(content)} bytes: inesperada")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / f"{name}.json").write_bytes(content)
        (self.raw_dir / f"{name}.rq").write_text(sparql + "\n", encoding="utf-8")
        if self.pause:
            time.sleep(self.pause)
        return json.loads(content)["results"]["bindings"]


def _qid(binding: dict[str, Any], key: str) -> str:
    return binding[key]["value"].rsplit("/", 1)[-1]


def _year(binding: dict[str, Any], key: str) -> int | None:
    value = binding.get(key, {}).get("value", "")
    return int(value[:4]) if value[:4].isdigit() else None


def overlaps(start: int | None, end: int | None) -> bool:
    """Passagem com início ≤ YEAR_TO e fim ≥ YEAR_FROM (ou sem fim). Sem datas: não."""

    if start is None:
        return False
    return start <= YEAR_TO and (end is None or end >= YEAR_FROM)


def clean_name(name: str) -> str:
    return _PARENS.sub(" ", name).strip()


@dataclass
class Player:
    qid: str
    labels: dict[str, str] = field(default_factory=dict)
    alt_labels: set[str] = field(default_factory=set)
    clubs: set[str] = field(default_factory=set)


def collect_players(
    bindings_by_club: dict[str, list[dict[str, Any]]]
) -> dict[str, Player]:
    """Jogadores com pelo menos uma passagem sobreposta ao intervalo, com nomes."""

    players: dict[str, Player] = {}
    for club, bindings in bindings_by_club.items():
        selected = {
            _qid(b, "player") for b in bindings
            if overlaps(_year(b, "start"), _year(b, "end"))
        }
        for b in bindings:
            qid = _qid(b, "player")
            if qid not in selected:
                continue
            player = players.setdefault(qid, Player(qid))
            player.clubs.add(club)
            if "label" in b:
                player.labels[b["lang"]["value"]] = clean_name(b["label"]["value"])
            if "alt" in b:
                player.alt_labels.add(clean_name(b["alt"]["value"]))
    return players


def build_vocabulary(
    players: dict[str, Player], club_names: dict[str, str]
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Uma linha por rótulo; devolve também contagens das decisões tomadas."""

    rows: dict[str, dict[str, Any]] = {}
    stats = defaultdict(int)
    for player in players.values():
        label = player.labels.get("pt") or player.labels.get("en")
        if not label:
            stats["jogadores_sem_rotulo"] += 1
            continue
        key = label.casefold()
        row = rows.setdefault(key, {"rotulo": label, "qids": set(), "clubs": set(), "variants": set()})
        row["qids"].add(player.qid)
        row["clubs"] |= {club_names.get(c, c) for c in player.clubs}
        others = set(player.labels.values()) | player.alt_labels
        for name in others:
            if name.casefold() == key:
                continue
            if len(name.split()) < 2:
                stats["variantes_uma_palavra_descartadas"] += 1
                continue
            row["variants"].add(name)

    # Variantes que apontam para mais de uma linha (ou que são o rótulo de outra) são ambíguas.
    owners: dict[str, set[str]] = defaultdict(set)
    for key, row in rows.items():
        owners[key].add(key)
        for variant in row["variants"]:
            owners[variant.casefold()].add(key)
    vocabulary = []
    for key, row in sorted(rows.items()):
        variants = sorted(v for v in row["variants"] if len(owners[v.casefold()]) == 1)
        stats["variantes_partilhadas_descartadas"] += len(row["variants"]) - len(variants)
        homonyms = len(row["qids"])
        stats["rotulos_com_homonimos"] += homonyms > 1
        vocabulary.append({
            "tipo": "entidade",
            "categoria": "jogador",
            "rotulo": row["rotulo"],
            "variantes": "|".join(variants),
            "wikidata": "|".join(sorted(row["qids"])),
            "clubes": "|".join(sorted(row["clubs"])),
            "homonimos": str(homonyms),
        })
    stats["jogadores"] = len(players)
    stats["rotulos"] = len(vocabulary)
    stats["rotulos_uma_palavra"] = sum(len(r["rotulo"].split()) == 1 for r in vocabulary)
    return vocabulary, dict(stats)


def write_vocabulary(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(VOCAB_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(
    project_root: Path | None = None, client: WikidataClient | None = None
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    root = project_root or Path(__file__).resolve().parents[2]
    client = client or WikidataClient(root / "data" / "raw" / "wikidata")

    club_names: dict[str, str] = {}
    clubs_per_season: dict[str, int] = {}
    for season, qid in SEASONS.items():
        bindings = client.query(f"season_{season}", season_query(qid))
        clubs_per_season[season] = len(bindings)
        for b in bindings:
            club_names[_qid(b, "club")] = b.get("label", {}).get("value", _qid(b, "club"))

    bindings_by_club = {
        club: client.query(f"club_{club}", club_players_query(club)) for club in sorted(club_names)
    }
    players = collect_players(bindings_by_club)
    vocabulary, stats = build_vocabulary(players, club_names)
    write_vocabulary(vocabulary, root / "data" / "processed" / "caminho_b_vocabulario_wikidata.csv")
    return vocabulary, {"clubes_por_epoca": clubs_per_season, "clubes": len(club_names), **stats}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.wikidata_vocabulary",
        description=__doc__.splitlines()[0],
    )
    parser.parse_args(argv)
    vocabulary, stats = run()
    for key, value in stats.items():
        print(f"{key}: {value}")
    print("Vocabulário: data/processed/caminho_b_vocabulario_wikidata.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
