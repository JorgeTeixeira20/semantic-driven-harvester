"""Caminho B — vocabulário alargado (1999–2024, 39 modalidades) a partir da Wikidata.

Alarga o vocabulário fechado de `wikidata_vocabulary` (que fica intocado e
reproduzível) a clubes e jogadores/atletas de todas as modalidades usadas na
descoberta (`corpus_phase1.MODALIDADES`), no intervalo 1999–2024. Decisões e
números em `docs/experiments.md`, "Vocabulário alargado 1999–2024: medição e
construção".

Fontes (endpoint SPARQL público da Wikidata, um pedido de cada vez, pausa de
1 s, consultas partidas por época, liga, clube e modalidade):

- **Clubes de futebol** = participantes (`wdt:P1923`) das épocas 1999–2000 a
  2023–24 da Primeira e da Segunda Liga (só algumas épocas os têm)
  ∪ clubes portugueses com `wdt:P118` (liga) Primeira ou Segunda Liga
  ∪ tabela explícita `CLUBES_QID` (os 57 clubes da descoberta, resolvidos à
  mão para QIDs) ∪ os 10 de `caminho_b_clubes_url.csv`.
- **Jogadores de futebol** = futebolistas com uma passagem (`p:P54`) por esses
  clubes que cumpra a regra das datas (`stint_reason`).
- **Outros desportos de equipa** = jogadores (ocupação da modalidade ou
  subclasse) com passagem por um clube português (`wdt:P17 wd:Q45`) que cumpra
  a regra das datas ∪ jogadores portugueses (`wdt:P27 wd:Q45`) dessa ocupação
  ativos no intervalo; clubes = os clubes portugueses dessas passagens.
- **Desportos individuais** = atletas portugueses da ocupação da modalidade
  (ou subclasse) ativos no intervalo (`person_reason`).

Regra das datas: passagem com início conhecido conta se início ≤ 2024 e
(fim ≥ 1999 ou sem fim); só com fim, se fim ≥ 1999; sem datas, conta se a
pessoa estiver ativa no intervalo. Pessoa ativa: pelo período de atividade
(`P2031`/`P2032`) se existir; senão pela data de nascimento como aproximação
(idade de 15 a 40 anos algures em 1999–2024, isto é nascida em 1959–2009, e
sem morte antes de 1999); sem nenhuma destas datas fica de fora.

Vocabulário: as regras de `wikidata_vocabulary` (rótulo pt ou en; variante =
rótulo noutra língua, sempre; nomes alternativos só com 2+ palavras; homónimos
fundidos numa linha com todos os QIDs; variantes partilhadas descartadas),
aplicadas a clubes e jogadores juntos, para que os homónimos entre modalidades
e entre clube e jogador também fiquem numa linha. Nomes de clube de uma
palavra que são nome de município/cidade/distrito português ("Porto",
"Braga") não entram; se o rótulo for um desses, usa-se a forma mais longa sem
ambiguidade ("FC Porto") e, sem nenhuma, o clube fica de fora.

Respostas em bruto em `data/raw/wikidata/alargado/` (byte a byte, antes de
interpretar); vocabulário em
`data/processed/caminho_b_vocabulario_wikidata_alargado.csv`; resumo da
medição em `output/wikidata_vocabulario_alargado.md`. Nunca escreve nos
caminhos do vocabulário original.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .corpus_entities import fold
from .corpus_phase1 import CLUBES, MODALIDADES, slugify
from .wikidata_vocabulary import (
    FOOTBALL_PLAYER, WikidataClient, _qid, _year, clean_name, season_query,
)

YEAR_FROM = 1999
YEAR_TO = 2024
AGE_FROM = 15
AGE_TO = 40
BIRTH_FROM = YEAR_FROM - AGE_TO  # 1959
BIRTH_TO = YEAR_TO - AGE_FROM  # 2009
PORTUGAL = "Q45"
NATIONAL_TEAM = "Q1194951"  # seleção nacional (desporto)
# Formas de clube de uma palavra que são palavras comuns em português (lista
# manual, decisão documentada): não entram, como os nomes de lugar.
COMMON_WORDS = frozenset({"aves", "estrela", "nacional", "naval", "real", "tecnico",
                          "uniao", "vitoria"})
LEAGUES = {"Primeira Liga": "Q182994", "Segunda Liga": "Q754488"}
FIRST_SEASON = 1999  # 1999–2000
LAST_SEASON = 2023  # 2023–24
LABEL_BATCH = 150
RETRY_SLEEP_SECONDS = 10.0
RAW_SUBDIR = Path("data") / "raw" / "wikidata" / "alargado"
VOCAB_PATH = Path("data") / "processed" / "caminho_b_vocabulario_wikidata_alargado.csv"
REPORT_PATH = Path("output") / "wikidata_vocabulario_alargado.md"
URL_CLUBS_PATH = Path("data") / "processed" / "caminho_b_clubes_url.csv"
# Vocabulário original: este módulo nunca escreve nele.
PROTECTED_NAME = "caminho_b_vocabulario_wikidata.csv"
VOCAB_FIELDS = (
    "tipo", "categoria", "rotulo", "variantes", "wikidata", "modalidade",
    "clubes", "homonimos",
)
# Tipos de lugar português cujo nome, sozinho, não identifica um clube.
PLACE_TYPES = (
    "Q13217644",  # município de Portugal
    "Q15647906",  # cidade de Portugal
    "Q15303838",  # sede de município
    "Q3032141",  # distrito de Portugal
    "Q1549591",  # cidade grande
)

TEAM = "equipa"
INDIVIDUAL = "individual"
UNMAPPED = "sem_mapeamento"


@dataclass(frozen=True)
class Modalidade:
    tipo: str
    desportos: tuple[str, ...] = ()
    ocupacoes: tuple[str, ...] = ()  # raízes; a consulta inclui subclasses (P279*)
    motivo: str = ""


# Uma entrada por termo de `corpus_phase1.MODALIDADES` (o teste verifica-o).
# QIDs verificados por consulta à Wikidata em 2026-10-21 (rótulos no resumo).
MAPEAMENTO: dict[str, Modalidade] = {
    "futebol": Modalidade(TEAM, ("Q2736",), (FOOTBALL_PLAYER,)),
    "basquetebol": Modalidade(TEAM, ("Q5372",), ("Q3665646",)),
    "andebol": Modalidade(TEAM, ("Q8418",), ("Q12840545",)),
    "voleibol": Modalidade(TEAM, ("Q1734",), ("Q15117302",)),
    "hóquei em patins": Modalidade(TEAM, ("Q1748406",), ("Q20900796",)),
    "rugby": Modalidade(TEAM, ("Q5378", "Q5849"), ("Q13415036", "Q14089670")),
    "pólo aquático": Modalidade(TEAM, ("Q7707",), ("Q17524364",)),
    "atletismo": Modalidade(INDIVIDUAL, ("Q542",), ("Q11513337",)),
    "ciclismo": Modalidade(INDIVIDUAL, ("Q2215841",), ("Q2309784",)),
    "judo": Modalidade(INDIVIDUAL, ("Q11420",), ("Q6665249",)),
    "motores": Modalidade(
        INDIVIDUAL, ("Q5367",),
        ("Q10349745", "Q378622", "Q10842936", "Q10841764", "Q3014296", "Q12327806"),
        "termo guarda-chuva: pilotos de automóveis, ralis e motociclismo",
    ),
    "natação": Modalidade(INDIVIDUAL, ("Q31920",), ("Q10843402",)),
    "desporto-universitario": Modalidade(
        UNMAPPED, motivo="enquadramento competitivo (desporto universitário), não "
        "uma modalidade: os atletas pertencem às modalidades que praticam"),
    "jogos-europeus": Modalidade(
        UNMAPPED, motivo="evento multidesportivo, não uma modalidade"),
    "ténis": Modalidade(INDIVIDUAL, ("Q847",), ("Q10833314",)),
    "surf": Modalidade(INDIVIDUAL, ("Q159992",), ("Q13561328",)),
    "jogos olímpicos": Modalidade(
        UNMAPPED, motivo="evento multidesportivo, não uma modalidade"),
    "golfe": Modalidade(INDIVIDUAL, ("Q5377",), ("Q11303721",)),
    "desportos de combate": Modalidade(
        INDIVIDUAL, ("Q7128792",),
        ("Q11338576", "Q11296761", "Q9017214", "Q13382533", "Q12369333", "Q12839983"),
        "termo guarda-chuva: boxe, kickboxing, karaté, taekwondo e luta "
        "(judo e MMA têm termo próprio)",
    ),
    "canoagem": Modalidade(INDIVIDUAL, ("Q213934",), ("Q13382566", "Q16004471")),
    "ténis de mesa": Modalidade(INDIVIDUAL, ("Q3930",), ("Q13382519",)),
    "triatlo": Modalidade(INDIVIDUAL, ("Q10980",), ("Q15306067",)),
    "ginástica": Modalidade(INDIVIDUAL, ("Q43450",), ("Q16947675",)),
    "padel": Modalidade(INDIVIDUAL, ("Q1582389",), ("Q59716278",)),
    "NFL": Modalidade(
        UNMAPPED, motivo="liga estrangeira (futebol americano nos EUA): entidades "
        "estrangeiras fora do âmbito do vocabulário português"),
    "orientação": Modalidade(INDIVIDUAL, ("Q29358",), ("Q13581129",)),
    "desportos radicais": Modalidade(
        INDIVIDUAL, ("Q309162",),
        ("Q17502714", "Q108886510", "Q17362882", "Q3951423", "Q86135347"),
        "termo guarda-chuva: skate, BMX, bodyboard e escalada",
    ),
    "vela": Modalidade(INDIVIDUAL, ("Q14085739",), ("Q476246", "Q13382487", "Q17519504")),
    "remo": Modalidade(INDIVIDUAL, ("Q159354",), ("Q13382576",)),
    "desporto escolar": Modalidade(
        UNMAPPED, motivo="enquadramento competitivo (escolar), não uma modalidade"),
    "badminton": Modalidade(INDIVIDUAL, ("Q7291",), ("Q13141064",)),
    "snooker": Modalidade(INDIVIDUAL, ("Q11015",), ("Q17165321",)),
    "MMA": Modalidade(INDIVIDUAL, ("Q114466",), ("Q11607585",)),
    "aventura": Modalidade(
        UNMAPPED, motivo="secção que agrega atividades de ar livre (trail, corridas "
        "de aventura, montanha) sem ocupação de atleta própria na Wikidata"),
    "tiro": Modalidade(INDIVIDUAL, ("Q206989",), ("Q17486376",)),
    "esgrima": Modalidade(INDIVIDUAL, ("Q12100",), ("Q13381863",)),
    "desportos de inverno": Modalidade(
        INDIVIDUAL, ("Q204686",),
        ("Q4144610", "Q13382608", "Q16029547", "Q13219587", "Q15709642", "Q19801627"),
        "termo guarda-chuva: esqui alpino e de fundo, biatlo, patinagem "
        "artística, snowboard e esqui de montanha",
    ),
    "desporto adaptado": Modalidade(
        INDIVIDUAL, ("Q589184",), ("Q25439032", "Q114414171"),
        "atletas paralímpicos/para-atletas, qualquer que seja a modalidade",
    ),
    "xadrez": Modalidade(INDIVIDUAL, ("Q718",), ("Q10873124",)),
}

# Os 57 clubes de `corpus_phase1.CLUBES`, resolvidos à mão para QIDs a partir
# de uma consulta por rótulo/nome alternativo (clubes portugueses de futebol),
# escolhendo o clube masculino principal; verificados no resumo da execução.
CLUBES_QID: dict[str, str] = {
    "Benfica": "Q131499", "Sporting": "Q75729", "Porto": "Q128446",
    "SC Braga": "Q75684", "Vitória de Guimarães": "Q223450", "Rio Ave": "Q622432",
    "Vitória de Setúbal": "Q208585", "Marítimo": "Q216503",
    "Portimonense": "Q621120", "Boavista": "Q219703", "Tondela": "Q1023227",
    "Chaves": "Q543467", "Aves": "Q1023163", "Feirense": "Q671042",
    "Famalicão": "Q1387105", "Belenenses": "Q216510",
    "Paços de Ferreira": "Q371136", "Moreirense": "Q1346314",
    "Santa Clara": "Q740637", "Estoril Praia": "Q634829",
    "Gil Vicente": "Q926438", "Nacional": "Q216459", "Leixões": "Q623730",
    "Académica": "Q243235", "Farense": "Q744353", "Belenenses SAD": "Q59212899",
    "Arouca": "Q1386869", "Varzim": "Q1429473", "União da Madeira": "Q1762119",
    "Cova da Piedade": "Q17524289", "Sporting da Covilhã": "Q1891367",
    "Académico de Viseu": "Q2410944", "Vilafranquense": "Q3551877",
    "Oliveirense": "Q2061414", "Benfica B": "Q7387221", "Casa Pia": "Q1046440",
    "Vizela": "Q1387855", "Penafiel": "Q1387471",
    "Estrela da Amadora": "Q838134", "Mafra": "Q618990",
    "Olhanense": "Q621259", "FC Porto B": "Q5423714", "Sporting B": "Q3494112",
    "Fafe": "Q290860", "Real Sport Clube": "Q3106966", "SC Braga B": "Q7387158",
    "AVS": "Q120775987", "Vitória de Guimarães B": "Q17518847",
    "Freamunde": "Q1031307", "Trofense": "Q1023233", "Torreense": "Q1853273",
    "União de Leiria": "Q211401", "Lank Vilaverdense": "Q7930110",
    "Sporting Clube Oriental": "Q2749186", "Felgueiras": "Q1387110",
    "Atlético Clube de Portugal": "Q757422", "Alverca": "Q1386850",
}

_SEASON_LABEL = re.compile(r"^(\d{4})[–-]\d{2,4} ")


# --- Consultas ----------------------------------------------------------------


def _values(qids: list[str] | tuple[str, ...]) -> str:
    return " ".join(f"wd:{q}" for q in qids)


_PERSON_OPTIONALS = (
    "OPTIONAL { ?player wdt:P569 ?birth } OPTIONAL { ?player wdt:P570 ?death } "
    "OPTIONAL { ?player wdt:P2031 ?wstart } OPTIONAL { ?player wdt:P2032 ?wend } "
    "OPTIONAL { ?player rdfs:label ?label FILTER(lang(?label) IN ('pt', 'en')) "
    "BIND(lang(?label) AS ?lang) } "
    "OPTIONAL { ?player skos:altLabel ?alt FILTER(lang(?alt) IN ('pt', 'en')) } "
)


def league_seasons_query(league_qid: str) -> str:
    return (
        "SELECT ?season ?label (COUNT(DISTINCT ?club) AS ?clubs) WHERE { "
        f"?season wdt:P3450 wd:{league_qid} . "
        "OPTIONAL { ?season rdfs:label ?label FILTER(lang(?label) = 'en') } "
        "OPTIONAL { ?season wdt:P1923 ?club } } GROUP BY ?season ?label"
    )


def league_clubs_query(league_qid: str) -> str:
    return (
        "SELECT DISTINCT ?club WHERE { "
        f"?club p:P118 ?st . ?st ps:P118 wd:{league_qid} . "
        f"?club wdt:P17 wd:{PORTUGAL} . FILTER NOT EXISTS {{ ?club wdt:P31 wd:Q5 }} }}"
    )


def football_club_query(club_qid: str) -> str:
    return (
        "SELECT DISTINCT ?player ?start ?end ?birth ?death ?wstart ?wend ?label ?lang ?alt "
        f"WHERE {{ ?player p:P54 ?st . ?st ps:P54 wd:{club_qid} . "
        f"?player wdt:P106 wd:{FOOTBALL_PLAYER} . "
        "OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } "
        + _PERSON_OPTIONALS + "}"
    )


def team_stints_query(occupations: tuple[str, ...]) -> str:
    return (
        "SELECT DISTINCT ?player ?club ?start ?end ?birth ?death ?wstart ?wend ?label ?lang ?alt "
        f"WHERE {{ VALUES ?root {{ {_values(occupations)} }} "
        "?player wdt:P106 ?occ . ?occ wdt:P279* ?root . "
        "?player p:P54 ?st . ?st ps:P54 ?club . "
        f"?club wdt:P17 wd:{PORTUGAL} . "

        "OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } "
        + _PERSON_OPTIONALS + "}"
    )


def portuguese_athletes_query(occupations: tuple[str, ...]) -> str:
    return (
        "SELECT DISTINCT ?player ?birth ?death ?wstart ?wend ?label ?lang ?alt "
        f"WHERE {{ VALUES ?root {{ {_values(occupations)} }} "
        f"?player wdt:P27 wd:{PORTUGAL} ; wdt:P106 ?occ . ?occ wdt:P279* ?root . "
        + _PERSON_OPTIONALS + "}"
    )


def national_teams_query() -> str:
    """Seleções portuguesas (não são clubes: as passagens por elas não contam)."""

    return (
        "SELECT DISTINCT ?club WHERE { "
        f"?club wdt:P17 wd:{PORTUGAL} ; wdt:P31 ?type . ?type wdt:P279* wd:{NATIONAL_TEAM} . }}"
    )


def portuguese_count_query(occupations: tuple[str, ...]) -> str:
    return (
        "SELECT (COUNT(DISTINCT ?player) AS ?n) WHERE { "
        f"VALUES ?root {{ {_values(occupations)} }} "
        f"?player wdt:P27 wd:{PORTUGAL} ; wdt:P106 ?occ . ?occ wdt:P279* ?root . }}"
    )


def labels_query(qids: list[str]) -> str:
    return (
        "SELECT DISTINCT ?item ?label ?lang ?alt ?country WHERE { "
        f"VALUES ?item {{ {_values(qids)} }} "
        "OPTIONAL { ?item rdfs:label ?label FILTER(lang(?label) IN ('pt', 'en')) "
        "BIND(lang(?label) AS ?lang) } "
        "OPTIONAL { ?item skos:altLabel ?alt FILTER(lang(?alt) IN ('pt', 'en')) } "
        "OPTIONAL { ?item wdt:P17 ?country } }"
    )


def mapping_query(qids: list[str]) -> str:
    return (
        "SELECT ?item ?label ?lang WHERE { "
        f"VALUES ?item {{ {_values(qids)} }} "
        "?item rdfs:label ?label FILTER(lang(?label) IN ('pt', 'en')) "
        "BIND(lang(?label) AS ?lang) }"
    )


def places_query(names: list[str]) -> str:
    literals = " ".join(
        f'"{n}"@{lang}' for n in names for lang in ("pt", "en") if '"' not in n and "\\" not in n
    )
    return (
        "SELECT DISTINCT ?name ?place WHERE { "
        f"VALUES ?name {{ {literals} }} VALUES ?type {{ {_values(PLACE_TYPES)} }} "
        f"?place rdfs:label ?name ; wdt:P17 wd:{PORTUGAL} ; wdt:P31 ?type . }}"
    )


# --- Cliente ------------------------------------------------------------------


class CachingClient(WikidataClient):
    """Como `WikidataClient`, mas pode reutilizar o raw já gravado (sem rede)
    e repete uma vez um pedido falhado; regista as falhas em vez de parar."""

    def __init__(self, raw_dir: Path, session: Any | None = None, pause: float = 1.0,
                 reuse: bool = False, sleep: Callable[[float], None] = time.sleep) -> None:
        super().__init__(raw_dir, session=session, pause=pause)
        self.reuse = reuse
        self.sleep = sleep
        self.failures: list[str] = []
        self.requests = 0

    def query(self, name: str, sparql: str) -> list[dict[str, Any]]:
        raw, rq = self.raw_dir / f"{name}.json", self.raw_dir / f"{name}.rq"
        if self.reuse and raw.exists() and rq.exists() and rq.read_text(encoding="utf-8") == sparql + "\n":
            return json.loads(raw.read_bytes())["results"]["bindings"]
        for attempt in (1, 2):
            self.requests += 1
            try:
                return super().query(name, sparql)
            except Exception:  # noqa: BLE001 — erro do endpoint (timeout, 5xx, rede)
                if attempt == 1:
                    self.sleep(RETRY_SLEEP_SECONDS)
        self.failures.append(name)
        return []


# --- Regras das datas ---------------------------------------------------------


@dataclass
class Person:
    qid: str
    labels: dict[str, str] = field(default_factory=dict)
    alt_labels: set[str] = field(default_factory=set)
    birth: int | None = None
    death: int | None = None
    wstart: int | None = None
    wend: int | None = None
    stints: set[tuple[str, int | None, int | None]] = field(default_factory=set)
    portuguese: bool = False


def period_overlaps(start: int | None, end: int | None) -> bool:
    """Período com alguma data sobreposto a 1999–2024 (sem datas: não)."""

    if start is not None:
        return start <= YEAR_TO and (end is None or end >= YEAR_FROM)
    return end is not None and end >= YEAR_FROM


def person_reason(person: Person) -> str | None:
    """Pessoa ativa no intervalo: período de atividade ou, sem ele, nascimento."""

    if person.wstart is not None or person.wend is not None:
        return "atividade" if period_overlaps(person.wstart, person.wend) else None
    if person.birth is not None:
        alive = person.death is None or person.death >= YEAR_FROM
        return "nascimento" if alive and BIRTH_FROM <= person.birth <= BIRTH_TO else None
    return None


def stint_reason(start: int | None, end: int | None, person: Person) -> str | None:
    """Motivo pelo qual a passagem conta (ou None). Ordem: datas da passagem
    (as únicas aceites pelo vocabulário original), só fim, e sem datas →
    atividade/nascimento da pessoa."""

    if start is not None:
        return "passagem_datada" if period_overlaps(start, end) else None
    if end is not None:
        return "passagem_so_fim" if period_overlaps(None, end) else None
    reason = person_reason(person)
    return f"passagem_sem_datas_{reason}" if reason else None


def _merge_years(old: int | None, new: int | None, pick: Callable[[int, int], int]) -> int | None:
    if new is None:
        return old
    return new if old is None else pick(old, new)


def collect_people(bindings: list[dict[str, Any]], club: str | None = None,
                   portuguese: bool = False) -> dict[str, Person]:
    people: dict[str, Person] = {}
    for b in bindings:
        person = people.setdefault(_qid(b, "player"), Person(_qid(b, "player")))
        person.portuguese = person.portuguese or portuguese
        person.birth = _merge_years(person.birth, _year(b, "birth"), min)
        person.death = _merge_years(person.death, _year(b, "death"), min)
        person.wstart = _merge_years(person.wstart, _year(b, "wstart"), min)
        person.wend = _merge_years(person.wend, _year(b, "wend"), max)
        club_qid = club or (_qid(b, "club") if "club" in b else None)
        if club_qid:
            person.stints.add((club_qid, _year(b, "start"), _year(b, "end")))
        if "label" in b:
            person.labels[b["lang"]["value"]] = clean_name(b["label"]["value"])
        if "alt" in b:
            person.alt_labels.add(clean_name(b["alt"]["value"]))
    return people


def merge_people(target: dict[str, Person], source: dict[str, Person]) -> None:
    for qid, p in source.items():
        t = target.setdefault(qid, Person(qid))
        t.labels.update(p.labels)
        t.alt_labels |= p.alt_labels
        t.birth = _merge_years(t.birth, p.birth, min)
        t.death = _merge_years(t.death, p.death, min)
        t.wstart = _merge_years(t.wstart, p.wstart, min)
        t.wend = _merge_years(t.wend, p.wend, max)
        t.stints |= p.stints
        t.portuguese = t.portuguese or p.portuguese


_REASON_ORDER = (
    "passagem_datada", "passagem_so_fim", "passagem_sem_datas_atividade",
    "passagem_sem_datas_nascimento", "atividade", "nascimento",
)


def select_people(people: dict[str, Person]) -> tuple[dict[str, tuple[str, set[str]]], dict[str, int]]:
    """Pessoas incluídas → (melhor motivo, clubes das passagens que contam)."""

    selected: dict[str, tuple[str, set[str]]] = {}
    stats: Counter[str] = Counter()
    for qid, person in people.items():
        reasons, clubs = set(), set()
        for club, start, end in person.stints:
            stats["passagens_" + ("datadas" if start is not None else "so_fim" if end is not None else "sem_datas")] += 1
            reason = stint_reason(start, end, person)
            if reason:
                reasons.add(reason)
                clubs.add(club)
        if person.portuguese:
            reason = person_reason(person)
            if reason:
                reasons.add(reason)
            if person.wstart is None and person.wend is None:
                stats["portugueses_" + ("so_nascimento" if person.birth is not None else "sem_datas")] += 1
            else:
                stats["portugueses_com_atividade"] += 1
        if reasons:
            best = min(reasons, key=_REASON_ORDER.index)
            selected[qid] = (best, clubs)
            stats["incluidos_" + best] += 1
        else:
            stats["excluidos"] += 1
            if any(start is None and end is None for _, start, end in person.stints):
                stats["excluidos_com_passagem_sem_datas"] += 1
                if person_reason(person) is None and person.birth is None \
                        and person.wstart is None and person.wend is None:
                    stats["excluidos_sem_nenhuma_data"] += 1
    stats["pessoas"] = len(people)
    stats["incluidos"] = len(selected)
    stats["incluidos_regra_original"] = stats["incluidos_passagem_datada"]
    return selected, dict(stats)


# --- Vocabulário --------------------------------------------------------------


@dataclass
class Entity:
    categoria: str  # "clube" ou "jogador"
    qid: str
    labels: dict[str, str]
    alt_labels: set[str]
    modalidades: set[str] = field(default_factory=set)
    clubs: set[str] = field(default_factory=set)  # QIDs de clubes (jogadores)


def club_forms(entity: Entity, places: set[str]) -> tuple[str | None, list[str], int]:
    """Rótulo e variantes de um clube, sem nomes de lugar de uma palavra.

    Ao contrário dos jogadores, os nomes alternativos de uma palavra contam
    ("Benfica", "Marítimo"), exceto se forem nome de lugar português ("Porto",
    "Braga"; regra das cidades) ou palavra comum (`COMMON_WORDS`). Se o rótulo for um desses lugares, usa-se a
    forma mais longa com 2+ palavras; sem nenhuma, o rótulo é None.
    Devolve (rótulo, variantes, nº de formas descartadas por serem lugar).
    """

    def is_place(name: str) -> bool:
        return len(name.split()) == 1 and (fold(name) in places or fold(name) in COMMON_WORDS)

    forms = [*entity.labels.values(), *sorted(entity.alt_labels)]
    dropped = len({n for n in forms if is_place(n)})
    label = entity.labels.get("pt") or entity.labels.get("en")
    if label and is_place(label):
        candidates = [n for n in forms if len(n.split()) >= 2]
        label = max(candidates, key=lambda n: (len(n), n)) if candidates else None
    variants = sorted({n for n in forms if n != label and not is_place(n)})
    return label, variants, dropped


def build_vocabulary(
    entities: list[Entity], club_names: dict[str, str], places: set[str]
) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: dict[str, dict[str, Any]] = {}
    stats: Counter[str] = Counter()
    for entity in entities:
        if entity.categoria == "clube":
            if not entity.labels:
                stats["clube_sem_rotulo"] += 1
                continue
            label, other_labels, dropped = club_forms(entity, places)
            stats["formas_de_lugar_ou_palavra_comum_descartadas"] += dropped
            if label is None:
                stats["clubes_sem_forma_inequivoca"] += 1
                continue
            stats["clube_variantes_uma_palavra_admitidas"] += sum(
                len(n.split()) == 1 for n in other_labels)
            alt_labels: set[str] = set()
        else:
            label = entity.labels.get("pt") or entity.labels.get("en")
            other_labels = list(entity.labels.values())
            alt_labels = entity.alt_labels
        if not label:
            stats[f"{entity.categoria}_sem_rotulo"] += 1
            continue
        key = label.casefold()
        row = rows.setdefault(key, {
            "rotulo": label, "categorias": set(), "qids": set(), "modalidades": set(),
            "clubs": set(), "variants": set(), "entities": set(),
        })
        row["categorias"].add(entity.categoria)
        row["qids"].add(entity.qid)
        row["entities"].add((entity.categoria, entity.qid))
        row["modalidades"] |= entity.modalidades
        row["clubs"] |= {club_names.get(c, c) for c in entity.clubs}
        for name in other_labels:
            if name.casefold() != key:
                row["variants"].add(name)
        for name in alt_labels - set(entity.labels.values()):
            if name.casefold() == key:
                continue
            if len(name.split()) < 2:
                stats["variantes_uma_palavra_descartadas"] += 1
                continue
            row["variants"].add(name)

    owners: dict[str, set[str]] = defaultdict(set)
    for key, row in rows.items():
        owners[key].add(key)
        for variant in row["variants"]:
            owners[variant.casefold()].add(key)
    vocabulary = []
    for key, row in sorted(rows.items()):
        variants = sorted(v for v in row["variants"] if len(owners[v.casefold()]) == 1)
        stats["variantes_partilhadas_descartadas"] += len(row["variants"]) - len(variants)
        homonyms = len(row["entities"])
        if homonyms > 1:
            stats["rotulos_com_homonimos"] += 1
            if len(row["categorias"]) > 1:
                stats["homonimos_clube_jogador"] += 1
            if len(row["modalidades"]) > 1:
                stats["homonimos_entre_modalidades"] += 1
        vocabulary.append({
            "tipo": "entidade",
            "categoria": "|".join(sorted(row["categorias"])),
            "rotulo": row["rotulo"],
            "variantes": "|".join(variants),
            "wikidata": "|".join(sorted(row["qids"])),
            "modalidade": "|".join(sorted(row["modalidades"])),
            "clubes": "|".join(sorted(row["clubs"])),
            "homonimos": str(homonyms),
        })
    stats["rotulos"] = len(vocabulary)
    stats["rotulos_uma_palavra"] = sum(len(r["rotulo"].split()) == 1 for r in vocabulary)
    return vocabulary, dict(stats)


def write_vocabulary(rows: list[dict[str, str]], path: Path) -> None:
    if path.name == PROTECTED_NAME:
        raise ValueError(f"{path} é o vocabulário original: não se sobrescreve")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(VOCAB_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# --- Execução -----------------------------------------------------------------


def season_start(label: str) -> int | None:
    match = _SEASON_LABEL.match(label)
    return int(match.group(1)) if match else None


def load_url_clubs(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["wikidata"]: row["clube"] for row in csv.DictReader(handle)}


def run(project_root: Path | None = None, client: CachingClient | None = None,
        reuse: bool = False) -> tuple[list[dict[str, str]], dict[str, Any]]:
    root = project_root or Path(__file__).resolve().parents[2]
    client = client or CachingClient(root / RAW_SUBDIR, reuse=reuse)
    m: dict[str, Any] = {}

    # 0. Itens de desporto e ocupações do mapeamento (rótulos, para verificação).
    mapped = sorted({q for mod in MAPEAMENTO.values() for q in (*mod.desportos, *mod.ocupacoes)})
    names: dict[str, dict[str, str]] = defaultdict(dict)
    for b in client.query("mapeamento", mapping_query(mapped)):
        names[_qid(b, "item")][b["lang"]["value"]] = b["label"]["value"]
    m["mapeamento"] = {
        termo: {"tipo": mod.tipo,
                "desportos": {q: names[q].get("pt") or names[q].get("en") for q in mod.desportos},
                "ocupacoes": {q: names[q].get("pt") or names[q].get("en") for q in mod.ocupacoes},
                "nota": mod.motivo}
        for termo, mod in MAPEAMENTO.items()
    }
    m["mapeamento_sem_rotulo"] = sorted(q for q in mapped if not names[q])

    # 1. Clubes de futebol: épocas, liga (P118) e tabela explícita.
    season_clubs: dict[str, set[str]] = {}
    m["epocas"] = {}
    for league, lqid in LEAGUES.items():
        rows = client.query(f"epocas_{lqid}", league_seasons_query(lqid))
        in_range = []
        for b in rows:
            start = season_start(b.get("label", {}).get("value", ""))
            if start is not None and FIRST_SEASON <= start <= LAST_SEASON:
                in_range.append((start, _qid(b, "season"), int(b["clubs"]["value"])))
        with_clubs = sorted((s, q) for s, q, n in in_range if n > 0)
        m["epocas"][league] = {
            "no_intervalo": len({s for s, _, _ in in_range}),
            "itens_no_intervalo": len(in_range),
            "com_participantes": [f"{s}-{(s + 1) % 100:02d}" for s, _ in with_clubs],
        }
        for start, sqid in with_clubs:
            bindings = client.query(f"epoca_{sqid}", season_query(sqid))
            season_clubs.setdefault("epocas", set()).update(_qid(b, "club") for b in bindings)
    league_clubs: set[str] = set()
    for league, lqid in LEAGUES.items():
        league_clubs |= {_qid(b, "club") for b in client.query(f"liga_{lqid}", league_clubs_query(lqid))}
    url_clubs = load_url_clubs(root / URL_CLUBS_PATH)
    explicit = set(CLUBES_QID.values()) | set(url_clubs)
    from_seasons = season_clubs.get("epocas", set())
    football_clubs = from_seasons | league_clubs | explicit
    m["clubes_futebol"] = {
        "epocas_P1923": len(from_seasons), "liga_P118": len(league_clubs),
        "epocas_ou_liga": len(from_seasons | league_clubs),
        "tabela_explicita": len(explicit), "total": len(football_clubs),
    }
    covered = from_seasons | league_clubs
    m["clubes_descoberta_fora_da_wikidata"] = sorted(
        name for name, q in CLUBES_QID.items() if q not in covered)
    m["clubes_url_fora_da_wikidata"] = sorted(
        name for q, name in url_clubs.items() if q not in covered)

    # 2. Pessoas por modalidade.
    people_by_mod: dict[str, dict[str, Person]] = {}
    m["modalidades"] = {}
    football = {}
    for club in sorted(football_clubs):
        merge_people(football, collect_people(
            client.query(f"futebol_clube_{club}", football_club_query(club)), club=club))
    people_by_mod["futebol"] = football
    pt_count = client.query("futebol_portugueses_contagem", portuguese_count_query((FOOTBALL_PLAYER,)))
    m["futebol_portugueses_total"] = int(pt_count[0]["n"]["value"]) if pt_count else None
    for termo, mod in MAPEAMENTO.items():
        if mod.tipo == UNMAPPED or termo == "futebol":
            continue
        slug = slugify(termo)
        people: dict[str, Person] = {}
        if mod.tipo == TEAM:
            merge_people(people, collect_people(client.query(
                f"modalidade_{slug}_passagens", team_stints_query(mod.ocupacoes))))
        merge_people(people, collect_people(client.query(
            f"modalidade_{slug}_portugueses", portuguese_athletes_query(mod.ocupacoes)),
            portuguese=True))
        people_by_mod[termo] = people

    national = {_qid(b, "club") for b in client.query("selecoes_nacionais", national_teams_query())}
    m["selecoes_nacionais_excluidas"] = len(national)
    for termo, people in people_by_mod.items():
        for person in people.values():
            person.stints = {st for st in person.stints if st[0] not in national}

    # 3. Seleção pela regra das datas.
    selected_by_mod: dict[str, dict[str, tuple[str, set[str]]]] = {}
    for termo, people in people_by_mod.items():
        selected, stats = select_people(people)
        selected_by_mod[termo] = selected
        m["modalidades"][termo] = stats

    # 4. Clubes como entidade: futebol + clubes das passagens que contam.
    club_mods: dict[str, set[str]] = defaultdict(set)
    for club in football_clubs:
        club_mods[club].add("futebol")
    for termo, selected in selected_by_mod.items():
        if MAPEAMENTO[termo].tipo == TEAM and termo != "futebol":
            for _, clubs in selected.values():
                for club in clubs:
                    club_mods[club].add(termo)
    club_qids = sorted(club_mods)
    club_labels: dict[str, dict[str, str]] = defaultdict(dict)
    club_alts: dict[str, set[str]] = defaultdict(set)
    for i in range(0, len(club_qids), LABEL_BATCH):
        batch = club_qids[i:i + LABEL_BATCH]
        for b in client.query(f"clubes_rotulos_{i // LABEL_BATCH + 1:03d}", labels_query(batch)):
            qid = _qid(b, "item")
            if "label" in b:
                club_labels[qid][b["lang"]["value"]] = clean_name(b["label"]["value"])
            if "alt" in b:
                club_alts[qid].add(clean_name(b["alt"]["value"]))
    one_word = sorted({n for q in club_qids
                       for n in [*club_labels[q].values(), *club_alts[q]] if len(n.split()) == 1})
    places = set()
    if one_word:
        places = {fold(b["name"]["value"]) for b in client.query("localidades", places_query(one_word))}
    m["nomes_de_clube_uma_palavra"] = len(one_word)
    m["nomes_de_clube_que_sao_lugar"] = sorted(n for n in one_word if fold(n) in places)
    m["nomes_de_clube_palavra_comum"] = sorted(n for n in one_word if fold(n) in COMMON_WORDS)

    entities = [Entity("clube", q, dict(club_labels[q]), set(club_alts[q]), set(club_mods[q]))
                for q in club_qids]
    club_display: dict[str, str] = {}
    for entity in entities:
        label, _, _ = club_forms(entity, places)
        if label:
            club_display[entity.qid] = label
    people_entities: dict[str, Entity] = {}
    for termo, selected in selected_by_mod.items():
        for qid, (_, clubs) in selected.items():
            person = people_by_mod[termo][qid]
            entity = people_entities.setdefault(
                qid, Entity("jogador", qid, {}, set()))
            entity.labels.update(person.labels)
            entity.alt_labels |= person.alt_labels
            entity.modalidades.add(termo)
            entity.clubs |= clubs
    m["pessoas_em_varias_modalidades"] = sum(len(e.modalidades) > 1 for e in people_entities.values())
    entities += [people_entities[q] for q in sorted(people_entities)]
    vocabulary, stats = build_vocabulary(entities, club_display, places)
    write_vocabulary(vocabulary, root / VOCAB_PATH)

    # 5. Totais e verificação dos clubes da descoberta no vocabulário.
    per_cat_mod: Counter[tuple[str, str]] = Counter()
    for row in vocabulary:
        for cat in row["categoria"].split("|"):
            for mod in row["modalidade"].split("|"):
                per_cat_mod[(cat, mod)] += 1
    vocab_qids = {q for row in vocabulary if "clube" in row["categoria"] for q in row["wikidata"].split("|")}
    m["clubes_descoberta_em_falta_no_vocabulario"] = sorted(
        name for name, q in CLUBES_QID.items() if q not in vocab_qids)
    m["clubes_url_em_falta_no_vocabulario"] = sorted(
        name for q, name in url_clubs.items() if q not in vocab_qids)
    m["clube_formas_uma_palavra_no_vocabulario"] = sorted(
        f for row in vocabulary if "clube" in row["categoria"]
        for f in [row["rotulo"], *row["variantes"].split("|")] if f and len(f.split()) == 1)
    m["linhas_por_categoria"] = dict(Counter(r["categoria"] for r in vocabulary))
    m["linhas_por_categoria_e_modalidade"] = {f"{c}/{mod}": n for (c, mod), n in sorted(per_cat_mod.items())}
    m["sem_mapeamento"] = {t: mod.motivo for t, mod in MAPEAMENTO.items() if mod.tipo == UNMAPPED}
    m["vocabulario"] = stats
    m["pedidos_feitos"] = client.requests
    m["consultas_falhadas"] = list(client.failures)
    write_report(m, root / REPORT_PATH)
    return vocabulary, m


def write_report(m: dict[str, Any], path: Path) -> None:
    lines = [
        "# Vocabulário alargado 1999–2024 (Wikidata): medição e construção\n",
        "Gerado por `python -m semantic_harvester.wikidata_vocabulary_alargado`. "
        f"Intervalo {YEAR_FROM}–{YEAR_TO}; nascimento como aproximação: "
        f"{BIRTH_FROM}–{BIRTH_TO} (idade {AGE_FROM}–{AGE_TO}).\n",
        "```json",
        json.dumps(m, ensure_ascii=False, indent=2, sort_keys=False),
        "```",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.wikidata_vocabulary_alargado",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument("--reutilizar-raw", action="store_true",
                        help="usa as respostas já gravadas em data/raw/wikidata/alargado/ "
                        "(sem rede para essas consultas)")
    args = parser.parse_args(argv)
    vocabulary, m = run(reuse=args.reutilizar_raw)
    print(json.dumps({k: m[k] for k in ("clubes_futebol", "linhas_por_categoria",
                                         "pedidos_feitos", "consultas_falhadas")},
                     ensure_ascii=False))
    print(f"Vocabulário: {VOCAB_PATH} ({len(vocabulary)} linhas); resumo: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
