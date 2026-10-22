"""Abordagem híbrida: confirmar na Wikidata os candidatos a entidade frequentes.

Decisão do autor (2026-10-22, `docs/experiments.md`, "Abordagem híbrida"):
os candidatos de `corpus_candidate_entities` (nomes capitalizados que o
vocabulário fechado não cobre) que aparecem em pelo menos `--min-artigos`
artigos (por omissão 3) são procurados na Wikidata pelo nome exato (rótulo
ou nome alternativo, pt/en) e, se isso não der nenhum item válido, pela
pesquisa da Wikidata (rótulos que começam pelo nome). Um item é válido se for
de um tipo permitido (clube, atleta, treinador, estádio/recinto, competição).
Um candidato é aceite se houver um só item válido ou, havendo vários, se o
mais proeminente (nº de artigos da Wikipédia) tiver pelo menos o dobro do
segundo; senão fica ambíguo.

A ligação a Portugal é sempre registada (coluna `portugal`) e, com
`--so-portugal`, exigida (a regra inicial de 2026-10-22):

- clube desportivo, estádio/recinto desportivo: país (`P17`) Portugal;
- atleta, treinador: nacionalidade (`P27`) Portugal, ou passagem (`P54`) ou
  cargo de treinador (`P6087`) numa equipa com país Portugal;
- competição: país Portugal, ou organizada (`P664`) pela UEFA, FIFA ou COI.

Escreve, sem tocar no vocabulário alargado:

- `output/wikidata_candidatos_<etiqueta>.csv`: a decisão de cada candidato
  (aceite, variante nova de uma entidade já na lista, ambíguo, fora do
  âmbito, tipo não aceite, sem correspondência, falha do pedido);
- `data/processed/caminho_b_vocabulario_hibrido_<etiqueta>.csv`: a lista
  fechada mais as entidades confirmadas, com a coluna `origem`
  (`lista_fechada`, `candidato`, ou `lista_fechada+candidato` quando o
  candidato era só uma forma em falta de uma entidade já conhecida).

Rede: um pedido SPARQL por candidato, um de cada vez, raw em
`data/raw/wikidata/candidatos_<etiqueta>/`; `--reutilizar` relê o raw.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .corpus_entities import match_tokens
from .wikidata_vocabulary_alargado import CachingClient

PORTUGAL = "Q45"
HUMAN = "Q5"
ATHLETE = "Q2066131"
COACH = "Q41583"
SPORTS_CLUB = "Q847017"
SPORTS_VENUE = "Q1076486"
COMPETITION_CLASSES = ("Q13406554", "Q623109", "Q167170")  # competição, liga, evento multidesportivo
ORGANIZERS = ("Q35572", "Q253414", "Q40970")  # UEFA, FIFA, COI
# Prioridade quando um item é de vários tipos (um ex-jogador que é treinador).
KINDS = ("clube", "estadio", "competicao", "treinador", "jogador")
DEFAULT_MIN_ARTICLES = 3
DEFAULT_LABEL = "por_ano"
BASE_VOCABULARY = Path("data") / "processed" / "caminho_b_vocabulario_wikidata_alargado.csv"

ORIGIN_CLOSED = "lista_fechada"
ORIGIN_CANDIDATE = "candidato"
ORIGIN_BOTH = "lista_fechada+candidato"

ACCEPTED = "aceite"
NEW_VARIANT = "variante_nova"
AMBIGUOUS = "ambiguo"
OUT_OF_SCOPE = "fora_do_ambito"
WRONG_TYPE = "tipo_nao_aceite"
NO_MATCH = "sem_correspondencia"
FAILED = "falha_pedido"
DECISION_FIELDS = ("candidato", "artigos", "decisao", "categoria", "wikidata",
                   "rotulo_wikidata", "portugal", "metodo", "desempate", "itens_encontrados")
METHOD_EXACT = "nome_exato"
METHOD_SEARCH = "pesquisa"
TIE_UNIQUE = "unico"
TIE_PROMINENCE = "proeminencia"
PROMINENCE_RATIO = 2


def _literal(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def candidate_query(name: str, search: bool = False) -> str:
    """Itens pelo nome exato ou, com `search`, pela pesquisa da Wikidata
    (`EntitySearch`, rótulos e nomes alternativos que começam pelo nome)."""

    lit = _literal(name)
    pt = f"wd:{PORTUGAL}"
    competitions = " ".join(f"wd:{q}" for q in COMPETITION_CLASSES)
    organizers = " ".join(f"wd:{q}" for q in ORGANIZERS)
    team_in_portugal = f"?t wdt:P17 {pt}"
    find = (
        "SERVICE wikibase:mwapi { bd:serviceParam wikibase:endpoint 'www.wikidata.org' ; "
        f"wikibase:api 'EntitySearch' ; mwapi:search {lit} ; mwapi:language 'pt' ; "
        "mwapi:limit '20' . ?item wikibase:apiOutputItem mwapi:item . } "
        if search else
        f"VALUES ?name {{ {lit}@pt {lit}@en }} ?item rdfs:label|skos:altLabel ?name . "
    )
    return (
        "SELECT DISTINCT ?item ?label ?labelEn ?links ?kind ?pt WHERE { "
        f"{find}"
        "OPTIONAL { ?item rdfs:label ?label FILTER(lang(?label) = 'pt') } "
        "OPTIONAL { ?item rdfs:label ?labelEn FILTER(lang(?labelEn) = 'en') } "
        "OPTIONAL { ?item wikibase:sitelinks ?links } "
        "OPTIONAL { "
        f"{{ ?item wdt:P31 wd:{HUMAN} ; wdt:P106/wdt:P279* wd:{COACH} . BIND('treinador' AS ?kind) "
        f"BIND(EXISTS {{ ?item wdt:P27 {pt} }} || EXISTS {{ ?item wdt:P6087|wdt:P54 ?t . {team_in_portugal} }} AS ?pt) }} "
        f"UNION {{ ?item wdt:P31 wd:{HUMAN} ; wdt:P106/wdt:P279* wd:{ATHLETE} . BIND('jogador' AS ?kind) "
        f"BIND(EXISTS {{ ?item wdt:P27 {pt} }} || EXISTS {{ ?item wdt:P54 ?t . {team_in_portugal} }} AS ?pt) }} "
        f"UNION {{ ?item wdt:P31/wdt:P279* wd:{SPORTS_CLUB} . BIND('clube' AS ?kind) "
        f"BIND(EXISTS {{ ?item wdt:P17 {pt} }} AS ?pt) }} "
        f"UNION {{ ?item wdt:P31/wdt:P279* wd:{SPORTS_VENUE} . BIND('estadio' AS ?kind) "
        f"BIND(EXISTS {{ ?item wdt:P17 {pt} }} AS ?pt) }} "
        f"UNION {{ VALUES ?cc {{ {competitions} }} ?item wdt:P31/wdt:P279* ?cc . BIND('competicao' AS ?kind) "
        f"BIND(EXISTS {{ ?item wdt:P17 {pt} }} || EXISTS {{ VALUES ?o {{ {organizers} }} ?item wdt:P664 ?o }} AS ?pt) }} "
        "} }"
    )


@dataclass
class Match:
    qid: str
    label: str = ""
    links: int = 0
    kinds_in_scope: set[str] = field(default_factory=set)
    kinds_out_of_scope: set[str] = field(default_factory=set)

    @property
    def kinds(self) -> set[str]:
        return self.kinds_in_scope | self.kinds_out_of_scope


def parse_matches(bindings: list[dict[str, Any]]) -> dict[str, Match]:
    matches: dict[str, Match] = {}
    for b in bindings:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        match = matches.setdefault(qid, Match(qid))
        if "label" in b:
            match.label = b["label"]["value"]
        elif "labelEn" in b and not match.label:
            # Sem rótulo pt (por exemplo, Lionel Messi, Premier League): o inglês.
            match.label = b["labelEn"]["value"]
        if "links" in b:
            match.links = max(match.links, int(b["links"]["value"]))
        if "kind" in b:
            in_scope = b.get("pt", {}).get("value") in ("true", "1")
            (match.kinds_in_scope if in_scope else match.kinds_out_of_scope).add(b["kind"]["value"])
    return matches


@dataclass(frozen=True)
class Decision:
    candidate: str
    articles: int
    decision: str
    kind: str = ""
    qid: str = ""
    wikidata_label: str = ""
    found: int = 0
    portugal: bool | None = None
    method: str = ""
    tie: str = ""


def decide(candidate: str, articles: int, matches: dict[str, Match],
           known_qids: set[str], only_portugal: bool = False,
           method: str = METHOD_EXACT) -> Decision:
    valid = {qid: m for qid, m in matches.items()
             if (m.kinds_in_scope if only_portugal else m.kinds)}
    if not valid:
        if any(m.kinds_out_of_scope for m in matches.values()):
            return Decision(candidate, articles, OUT_OF_SCOPE, found=len(matches), method=method)
        return Decision(candidate, articles, WRONG_TYPE if matches else NO_MATCH,
                        found=len(matches), method=method)

    ranked = sorted(valid.values(), key=lambda m: (-m.links, m.qid))
    tie = TIE_UNIQUE
    if len(ranked) > 1:
        # Popularidade como desempate: o mais citado na Wikipédia, se claramente à frente.
        if ranked[0].links == 0 or ranked[0].links < PROMINENCE_RATIO * ranked[1].links:
            return Decision(candidate, articles, AMBIGUOUS, found=len(matches), method=method)
        tie = TIE_PROMINENCE
    match = ranked[0]
    kinds = match.kinds_in_scope if only_portugal else match.kinds
    kind = next(k for k in KINDS if k in kinds)
    decision = NEW_VARIANT if match.qid in known_qids else ACCEPTED
    return Decision(candidate, articles, decision, kind, match.qid, match.label, len(matches),
                    portugal=kind in match.kinds_in_scope, method=method, tie=tie)


def load_candidates(path: Path, min_articles: int) -> list[tuple[str, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [(r["candidato"], int(r["artigos"])) for r in csv.DictReader(handle)]
    return [(c, n) for c, n in rows if n >= min_articles]


def build_hybrid_vocabulary(
    base_rows: list[dict[str, str]], decisions: list[Decision],
) -> list[dict[str, str]]:
    """A lista fechada intacta, com `origem`, mais as entidades confirmadas.

    Um candidato que é só outra forma de uma entidade já na lista entra como
    variante dessa linha. Uma entidade nova fica com o rótulo da Wikidata se
    tiver 2+ palavras e não for já forma de outra linha; senão, com a forma
    vista no texto (a mais frequente). As formas são todas variantes.
    """

    # A lista fechada só tem desporto português (regra do vocabulário alargado).
    rows = [dict(row, origem=ORIGIN_CLOSED, portugal="sim") for row in base_rows]
    # Uma linha de homónimos tem vários QIDs; uma forma nova de um deles junta-se a essa linha.
    by_qid = {qid: row for row in rows for qid in (row.get("wikidata") or "").split("|") if qid}
    taken = {tuple(match_tokens(form)) for row in rows
             for form in [row["rotulo"], *(row.get("variantes") or "").split("|")] if form}

    grouped: dict[str, list[Decision]] = defaultdict(list)
    for d in decisions:
        if d.decision in (ACCEPTED, NEW_VARIANT):
            grouped[d.qid].append(d)

    for qid, ds in grouped.items():
        forms = [d.candidate for d in sorted(ds, key=lambda d: (-d.articles, d.candidate))]
        if qid in by_qid:
            row = by_qid[qid]
            variants = [v for v in (row.get("variantes") or "").split("|") if v]
            row["variantes"] = "|".join(variants + [f for f in forms if f not in variants])
            row["origem"] = ORIGIN_BOTH
            continue
        label = ds[0].wikidata_label
        usable = len(label.split()) >= 2 and tuple(match_tokens(label)) not in taken
        rotulo = label if usable else forms[0]
        new = {key: "" for key in rows[0]} if rows else {}
        new.update({
            "tipo": "entidade", "categoria": ds[0].kind, "rotulo": rotulo,
            "variantes": "|".join(f for f in forms if f != rotulo), "wikidata": qid,
            "homonimos": "1", "origem": ORIGIN_CANDIDATE,
            "portugal": "sim" if ds[0].portugal else "nao",
        })
        taken.update(tuple(match_tokens(f)) for f in [rotulo, *forms])
        rows.append(new)
    return rows


def write_rows(rows: list[dict[str, str]], fields: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(
    project_root: Path | None = None,
    label: str = DEFAULT_LABEL,
    min_articles: int = DEFAULT_MIN_ARTICLES,
    client: CachingClient | None = None,
    reuse: bool = False,
    only_portugal: bool = False,
) -> list[Decision]:
    root = project_root or Path(__file__).resolve().parents[2]
    candidates = load_candidates(root / "output" / f"corpus_candidate_entities_{label}.csv", min_articles)
    with (root / BASE_VOCABULARY).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        base_fields = list(reader.fieldnames or [])
        base_rows = list(reader)
    known_qids = {q for row in base_rows for q in (row.get("wikidata") or "").split("|") if q}

    client = client or CachingClient(root / "data" / "raw" / "wikidata" / f"candidatos_{label}", reuse=reuse)
    decisions = []
    for i, (candidate, articles) in enumerate(candidates, start=1):
        decision = None
        for method, suffix, search in ((METHOD_EXACT, "", False), (METHOD_SEARCH, "_pesquisa", True)):
            failures_before = len(client.failures)
            bindings = client.query(f"candidato_{i:05d}{suffix}", candidate_query(candidate, search))
            if len(client.failures) > failures_before:
                decision = Decision(candidate, articles, FAILED, method=method)
                break
            decision = decide(candidate, articles, parse_matches(bindings), known_qids,
                              only_portugal, method)
            # A pesquisa (mais larga) só quando o nome exato não deu nenhum item válido.
            if decision.decision not in (NO_MATCH, WRONG_TYPE, OUT_OF_SCOPE):
                break
        decisions.append(decision)

    write_rows([{"candidato": d.candidate, "artigos": d.articles, "decisao": d.decision,
                 "categoria": d.kind, "wikidata": d.qid, "rotulo_wikidata": d.wikidata_label,
                 "portugal": "" if d.portugal is None else ("sim" if d.portugal else "nao"),
                 "metodo": d.method, "desempate": d.tie, "itens_encontrados": d.found}
                for d in decisions],
               list(DECISION_FIELDS), root / "output" / f"wikidata_candidatos_{label}.csv")
    hybrid = build_hybrid_vocabulary(base_rows, decisions)
    write_rows(hybrid, base_fields + ["origem", "portugal"],
               root / "data" / "processed" / f"caminho_b_vocabulario_hibrido_{label}.csv")
    return decisions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.wikidata_candidates",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", default=DEFAULT_LABEL, metavar="ETIQUETA")
    parser.add_argument("--min-artigos", type=int, default=DEFAULT_MIN_ARTICLES,
                        help="mínimo de artigos para um candidato ser procurado (por omissão 3)")
    parser.add_argument("--so-portugal", action="store_true",
                        help="exige ligação a Portugal (a regra inicial); por omissão só se regista")
    parser.add_argument("--reutilizar", action="store_true",
                        help="reutiliza as respostas já gravadas em data/raw/wikidata/ (sem rede)")
    args = parser.parse_args(argv)
    if args.min_artigos < 1:
        parser.error("--min-artigos tem de ser ≥ 1")
    decisions = run(label=args.corpus, min_articles=args.min_artigos, reuse=args.reutilizar,
                    only_portugal=args.so_portugal)
    counts = Counter(d.decision for d in decisions)
    print(f"Candidatos procurados: {len(decisions)} — " +
          ", ".join(f"{k} {v}" for k, v in counts.most_common()))
    print(f"Saídas: output/wikidata_candidatos_{args.corpus}.csv, "
          f"data/processed/caminho_b_vocabulario_hibrido_{args.corpus}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
