"""Sugestões para a tabela slug do URL → clube (`caminho_b_clubes_url.csv`).

No corpus alargado, 49 clubes do URL não estavam na tabela (2026-10-23,
`docs/experiments.md`): o painel mostrava "rio-ave" e "Rio Ave Futebol
Clube" como clubes diferentes e `clube_coerente` ficava `sem_mapa`. Este
comando propõe, para cada slug sem mapa, o clube de futebol do vocabulário
alargado cujo nome contém as palavras do slug pela mesma ordem (uma letra
seguida de `--` é uma inicial: `v--setubal` → "Vitória … Setúbal").

Escreve `output/clubes_url_sugestao_<etiqueta>.csv` (slug, artigos, QID,
clube, estado `unico`/`ambiguo`/`sem`, alternativas) para revisão. Com
`--aplicar`, acrescenta à tabela só as sugestões `unico` (as linhas
existentes ficam). Sem rede.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from .corpus_entities import ORIGIN_URL, match_tokens
from .corpus_entities_rdf import primary_qid, url_club_qids

DEFAULT_LABEL = "por_ano"
VOCABULARY = Path("data") / "processed" / "caminho_b_vocabulario_wikidata_alargado.csv"
CLUB_MAP = Path("data") / "processed" / "caminho_b_clubes_url.csv"
FIELDS = ("slug", "artigos", "wikidata", "clube", "estado", "alternativas")


def slug_tokens(slug: str) -> list[tuple[str, bool]]:
    """(palavra, é inicial): `v--setubal` → [("v", True), ("setubal", False)]."""

    result = []
    for part, rest in zip(slug.split("--"), [True] * slug.count("--") + [False]):
        words = [w for w in part.split("-") if w]
        for j, word in enumerate(words):
            result.append((word, rest and j == len(words) - 1 and len(word) == 1))
    return result


def form_matches(slug: str, form: tuple[str, ...]) -> bool:
    """As palavras do slug aparecem pela mesma ordem no nome (iniciais por prefixo)."""

    position = 0
    for word, initial in slug_tokens(slug):
        while position < len(form) and not (
            form[position] == word or (initial and form[position].startswith(word))
        ):
            position += 1
        if position == len(form):
            return False
        position += 1
    return True


def football_clubs(vocabulary: Path, club_qids: set[str] | None = None) -> list[tuple[str, str, list[tuple[str, ...]]]]:
    """(QID, nome, formas normalizadas) dos clubes com futebol entre as modalidades.

    Um clube com vários QIDs fica com o da tabela de clubes, se houver só um;
    senão fica de fora (não se pode escolher).
    """

    clubs = []
    with vocabulary.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["categoria"] != "clube" or "futebol" not in (row.get("modalidade") or "").split("|"):
                continue
            qid = row["wikidata"]
            if "|" in qid:
                qid = primary_qid(row, club_qids or set())
                if not qid:
                    continue
            forms = [row["rotulo"], *[v for v in (row.get("variantes") or "").split("|") if v]]
            clubs.append((qid, row["rotulo"], [tuple(match_tokens(f)) for f in forms]))
    return clubs


def exact_form(slug: str, form: tuple[str, ...]) -> bool:
    """O nome é só as palavras do slug (sem palavras a mais, como o "B" das equipas B)."""

    return len(form) == len(slug_tokens(slug)) and form_matches(slug, form)


def suggest(slug: str, clubs: list[tuple[str, str, list[tuple[str, ...]]]]) -> tuple[str, list[tuple[str, str]]]:
    matching = [(qid, name, forms) for qid, name, forms in clubs if any(form_matches(slug, f) for f in forms)]
    # Preferências, por ordem: um nome que é exatamente o slug; depois, não a equipa B.
    exact = [c for c in matching if any(exact_form(slug, f) for f in c[2])]
    if exact:
        matching = exact
    main = [c for c in matching if not c[1].endswith(" B")]
    if main:
        matching = main
    found = [(qid, name) for qid, name, _ in matching]
    if not found:
        return "sem", []
    if all(name.endswith(" B") for _, name in found):
        return "ambiguo", found  # só a equipa B corresponde: rever à mão
    return ("unico" if len(found) == 1 else "ambiguo"), found


def run(project_root: Path | None = None, label: str = DEFAULT_LABEL, apply: bool = False) -> list[dict]:
    root = project_root or Path(__file__).resolve().parents[2]
    with (root / CLUB_MAP).open(encoding="utf-8", newline="") as handle:
        existing = {row["slug"] for row in csv.DictReader(handle)}
    articles: Counter[str] = Counter()
    with (root / "output" / f"corpus_entities_{label}.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["origem"] == ORIGIN_URL and row["categoria"] == "clube" and row["rotulo"] not in existing:
                articles[row["rotulo"]] += 1
    clubs = football_clubs(root / VOCABULARY, url_club_qids(root / CLUB_MAP))
    rows = []
    for slug, count in sorted(articles.items(), key=lambda kv: (-kv[1], kv[0])):
        state, found = suggest(slug, clubs)
        rows.append({
            "slug": slug, "artigos": count,
            "wikidata": found[0][0] if state == "unico" else "",
            "clube": found[0][1] if state == "unico" else "",
            "estado": state,
            "alternativas": "; ".join(f"{q} {n}" for q, n in found) if state == "ambiguo" else "",
        })
    out = root / "output" / f"clubes_url_sugestao_{label}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    if apply:
        with (root / CLUB_MAP).open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            for row in rows:
                if row["estado"] == "unico":
                    writer.writerow((row["slug"], row["wikidata"], row["clube"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.club_url_map",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", default=DEFAULT_LABEL, metavar="ETIQUETA")
    parser.add_argument("--aplicar", action="store_true",
                        help="acrescenta à tabela as sugestões únicas (depois de revistas)")
    args = parser.parse_args(argv)
    rows = run(label=args.corpus, apply=args.aplicar)
    states = Counter(r["estado"] for r in rows)
    print(f"Slugs sem mapa: {len(rows)} — " + ", ".join(f"{k} {v}" for k, v in states.most_common()))
    print(f"Sugestões: output/clubes_url_sugestao_{args.corpus}.csv"
          + (f"; acrescentadas {states['unico']} a {CLUB_MAP}" if args.aplicar else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
