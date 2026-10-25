"""Protótipo de navegação do corpus da Fase 1: painel, filtros e entidades.

Gera `output/prototipo_<etiqueta>/` (abrir `index.html`, sem servidor nem
dependências): um painel com resumos que reagem aos filtros (ano, época do
site, modalidade, clube, entidade, pesquisa no título) e a lista paginada
dos artigos filtrados, com ligação ao Arquivo.pt. O estado fica no endereço
(`#entidade=Q131499&ano=2019`), por isso cada vista é uma ligação.

Dados, sem rede e sem alterar nada:

- o grafo do corpus da Fase 1 (`data/processed/corpus_articles_<etiqueta>_triples.nt`,
  lido em streaming): URL, título do `Artigo`, captura e se há texto;
- o Caminho B (`output/corpus_entities_<etiqueta>.csv` e `_corpo.csv`): temas
  pelo URL, entidades no texto e origem do corpo;
- o vocabulário (QID, categoria, modalidade) e a tabela slug → clube.

Preenchimento, sempre com a origem registada: modalidade **só pelo URL**, com
os sinónimos juntos (`MODALIDADE_ALIASES`); clube pelo URL e, sem ele, pelos
clubes mencionados no texto. Os URLs do site de 1999–2009 não têm caminho
temático. A modalidade pelo termo de pesquisa (decisão de 2026-10-22) foi
retirada em 2026-10-25: a TextSearch encontra o termo no menu do site, e o
termo estava no título ou no corpo em só 6 de 100 artigos ("Diagnóstico de
falhas no painel", `docs/experiments.md`).

Também escreve `resumo.md`, com as tabelas para as conclusões.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .corpus_classification import article_url_scheme
from .corpus_entities import ORIGIN_TEXT, ORIGIN_URL, fold
from .corpus_entities_rdf import primary_qid, url_club_qids
from .corpus_redundancy import corpus_graph_path, read_graph_index
from .navigation_corpus_page import PAGE
from .rdf_mapper import article_uri

DEFAULT_LABEL = "por_ano"
DEFAULT_VOCABULARY = Path("data") / "processed" / "caminho_b_vocabulario_wikidata_alargado.csv"
DEFAULT_CLUB_MAP = Path("data") / "processed" / "caminho_b_clubes_url.csv"
WAYBACK = "https://arquivo.pt/wayback/"

# Épocas do site pelo esquema do URL. Os esquemas ASP.NET (`interior.aspx`,
# `noticia.aspx`) vão de 2000 a 2015 e o `/detalhe/` começa em 2015 (corpus
# `xl`, `record.xl.pt`), por isso os nomes descrevem o esquema e os anos
# observados, sem afirmar fronteiras exatas (extensão a 2010–2016).
ERAS = (
    ("1999–2000", {"tn0cs.asp?nid", "tn1cs.asp?nid"}),
    ("2000–2015 (ASP.NET)", {
        "noticia.asp?id", "shownews.asp?id", "noticia.aspx?id",
        "interior.aspx?content_id", "interior_premium.aspx?content_id",
    }),
    ("2015–2024", {"detalhe", "amp"}),
)
OTHER_ERA = "outro"
ORIGIN_NONE, ORIGIN_FROM_URL, ORIGIN_FALLBACK = 0, 1, 2
# A mesma modalidade com nomes diferentes no URL (diagnóstico de 2026-10-25):
# a grafia inglesa e os subtemas de aventura.
MODALIDADE_ALIASES = {
    "rugby": "raguebi",
    "aventura-em-mocambique": "aventura",
    "record-pela-patagonia": "aventura",
}
CLUB_CATEGORY = "clube"
OTHER_CATEGORIES = ("treinador", "estadio", "competicao")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")


def era_of(url: str) -> str:
    scheme = article_url_scheme(url)
    return next((name for name, schemes in ERAS if scheme in schemes), OTHER_ERA)


@dataclass
class Article:
    url: str
    title: str
    tstamp: str
    era: str
    body: str
    modalidades: list[str] = field(default_factory=list)
    modalidade_origin: int = ORIGIN_NONE
    clubs: list[str] = field(default_factory=list)
    club_origin: int = ORIGIN_NONE
    entities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Entity:
    key: str
    name: str
    categoria: str
    modalidade: str
    qid: str
    origin: str = ""


def entity_key(qids: str, homonyms: int, rotulo: str) -> str:
    return qids if homonyms == 1 and qids else f"h:{rotulo}"


def load_vocabulary(path: Path, club_qids: set[str] | None = None) -> dict[str, Entity]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    vocabulary = {}
    for row in rows:
        homonyms = int(row.get("homonimos") or 1)
        qid = row.get("wikidata") or ""
        primary = primary_qid(row, club_qids or set()) if homonyms > 1 else None
        if primary:  # clube "homónimo" com o QID de futebol na tabela de clubes
            qid, homonyms = primary, 1
        vocabulary[row["rotulo"]] = Entity(
            key=entity_key(qid, homonyms, row["rotulo"]), name=row["rotulo"],
            categoria=row["categoria"], modalidade=row.get("modalidade") or "",
            qid=qid if homonyms == 1 else "", origin=row.get("origem") or "",
        )
    return vocabulary


def load_club_map(path: Path) -> dict[str, tuple[str, str]]:
    """slug → (chave do clube, nome): o QID quando a tabela o tem."""

    with path.open(encoding="utf-8", newline="") as handle:
        return {row["slug"]: (row.get("wikidata") or f"slug:{row['slug']}", row["clube"])
                for row in csv.DictReader(handle)}


def load_body_sources(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        sources: dict[str, str] = {}
        for row in csv.DictReader(handle):
            sources.setdefault(row["artigo"], row["origem_corpo"])
    return sources


def build_articles(
    graph_path: Path,
    entities_csv: Path,
    body_csv: Path,
    vocabulary: dict[str, Entity],
    club_map: dict[str, tuple[str, str]],
) -> tuple[list[Article], dict[str, str]]:
    """Artigos com o preenchimento feito, e nome de cada chave de clube."""

    index = read_graph_index(graph_path)
    themes: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    mentions: dict[str, list[str]] = defaultdict(list)
    with entities_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["origem"] == ORIGIN_URL:
                themes[row["artigo"]][row["categoria"]].append(row["rotulo"])
            elif row["origem"] == ORIGIN_TEXT:
                mentions[row["artigo"]].append(row["rotulo"])
    bodies = load_body_sources(body_csv)

    club_names: dict[str, str] = {}
    for entity in vocabulary.values():
        if entity.categoria == CLUB_CATEGORY:
            club_names[entity.key] = entity.name
    articles = []
    for resource in index.resources:
        url = str(index.original_url[resource])
        captures = sorted(index.captures.get(resource, ()),
                          key=lambda c: str(index.capture_fields[c].get("tstamp", "")))
        tstamp = str(index.capture_fields[captures[0]].get("tstamp", "")) if captures else ""
        has_text = any("text_node" in index.capture_fields[c] for c in captures)
        article = Article(
            url=url, title=str(index.labels.get(article_uri(url), "") or url), tstamp=tstamp,
            era=era_of(url), body=bodies.get(url, "c′" if has_text else "sem_texto"),
        )

        url_mods = {MODALIDADE_ALIASES.get(m, m) for m in themes[url].get("modalidade", [])}
        if url_mods:
            article.modalidades, article.modalidade_origin = sorted(url_mods), ORIGIN_FROM_URL

        entities = [vocabulary[r] for r in mentions.get(url, []) if r in vocabulary]
        article.entities = sorted({e.key for e in entities})
        url_clubs = []
        for slug_value in themes[url].get("clube", []):
            key, name = club_map.get(slug_value, (f"slug:{slug_value}", slug_value))
            club_names.setdefault(key, name)
            url_clubs.append(key)
        text_clubs = sorted({e.key for e in entities if e.categoria == CLUB_CATEGORY})
        if url_clubs:
            article.clubs, article.club_origin = sorted(set(url_clubs)), ORIGIN_FROM_URL
        elif text_clubs:
            article.clubs, article.club_origin = text_clubs, ORIGIN_FALLBACK
        articles.append(article)
    articles.sort(key=lambda a: (a.tstamp, a.url))
    return articles, club_names


def build_data(
    articles: list[Article], vocabulary: dict[str, Entity], club_names: dict[str, str], label: str,
) -> dict:
    """Dicionários + uma linha compacta por artigo (o ficheiro tem de ser pequeno)."""

    def indexer(values):
        values = sorted(values)
        return values, {v: i for i, v in enumerate(values)}

    eras = [name for name, _ in ERAS] + [OTHER_ERA]
    era_index = {e: i for i, e in enumerate(eras)}
    modalidades, mod_index = indexer({m for a in articles for m in a.modalidades})
    bodies, body_index = indexer({a.body for a in articles})
    club_keys, club_index = indexer({c for a in articles for c in a.clubs})
    used = {k for a in articles for k in a.entities}
    by_key = {e.key: e for e in vocabulary.values()}
    entity_keys, entity_index = indexer(used)
    return {
        "label": label,
        "eras": eras,
        "modalidades": modalidades,
        "bodies": bodies,
        "clubs": [{"k": k, "n": club_names.get(k, k)} for k in club_keys],
        "entities": [{"k": k, "n": by_key[k].name, "c": by_key[k].categoria,
                      "m": by_key[k].modalidade, "q": by_key[k].qid, "o": by_key[k].origin}
                     for k in entity_keys],
        # [tstamp, título, URL, época, modalidades, origem, clubes, origem, entidades, corpo]
        "articles": [
            [a.tstamp, a.title, a.url, era_index[a.era], [mod_index[m] for m in a.modalidades],
             a.modalidade_origin, [club_index[c] for c in a.clubs], a.club_origin,
             [entity_index[e] for e in a.entities], body_index[a.body]]
            for a in articles
        ],
    }


def _table(header: tuple[str, ...], rows: list[tuple]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return lines + [""]


def write_summary(articles: list[Article], vocabulary: dict[str, Entity],
                  club_names: dict[str, str], path: Path, label: str) -> None:
    by_key = {e.key: e for e in vocabulary.values()}
    years = Counter(a.tstamp[:4] for a in articles)
    with_entity = Counter(a.tstamp[:4] for a in articles if a.entities)
    eras = [name for name, _ in ERAS] + [OTHER_ERA]
    body_by_era = Counter((a.era, a.body) for a in articles)
    bodies = sorted({a.body for a in articles})
    mod_origin = Counter(a.modalidade_origin for a in articles)
    club_origin = Counter(a.club_origin for a in articles)
    mod_counts = Counter(m for a in articles for m in a.modalidades)
    clubs_mentioned = Counter(k for a in articles for k in a.entities
                              if by_key[k].categoria == CLUB_CATEGORY)
    athletes = Counter(k for a in articles for k in a.entities
                       if by_key[k].categoria not in (CLUB_CATEGORY, *OTHER_CATEGORIES))
    others = Counter(k for a in articles for k in a.entities
                     if by_key[k].categoria in OTHER_CATEGORIES)
    origins = Counter(by_key[k].origin for k in {k for a in articles for k in a.entities})

    lines = [
        f"# Resumo do protótipo `prototipo_{label}`\n",
        "Gerado sem rede a partir do grafo da Fase 1 e do Caminho B. A data de "
        "cada artigo é a da captura mais antiga conhecida (aproximação da "
        "publicação). Contagens descritivas desta recolha, limitada pelo teto "
        "da descoberta (300 resultados por termo e ano).\n",
        f"- Artigos: {len(articles)}",
        f"- Com pelo menos uma entidade: {sum(1 for a in articles if a.entities)}",
        f"- Modalidade pelo URL / nenhuma: "
        f"{mod_origin[ORIGIN_FROM_URL]} / {mod_origin[ORIGIN_NONE]}",
        f"- Clube pelo URL / pelo texto / nenhum: "
        f"{club_origin[ORIGIN_FROM_URL]} / {club_origin[ORIGIN_FALLBACK]} / {club_origin[ORIGIN_NONE]}",
        "",
        "## Artigos por ano\n",
        *_table(("Ano", "Artigos", "Com entidade"),
                [(y, years[y], with_entity[y]) for y in sorted(years)]),
        "## Origem do corpo por época do site\n",
        *_table(("Época", *bodies),
                [(e, *(body_by_era[(e, b)] for b in bodies)) for e in eras
                 if any(body_by_era[(e, b)] for b in bodies)]),
        "## Modalidades (pelo URL)\n",
        *_table(("Modalidade", "Artigos"), mod_counts.most_common()),
        "## Clubes mais mencionados no texto\n",
        *_table(("Clube", "Artigos"),
                [(club_names.get(k, by_key[k].name), n) for k, n in clubs_mentioned.most_common(20)]),
        "## Atletas mais mencionados no texto\n",
        *_table(("Atleta", "Modalidade", "Artigos"),
                [(by_key[k].name, by_key[k].modalidade, n) for k, n in athletes.most_common(20)]),
    ]
    if others:
        lines += ["## Treinadores, estádios e competições mais mencionados\n",
                  *_table(("Entidade", "Categoria", "Artigos"),
                          [(by_key[k].name, by_key[k].categoria, n) for k, n in others.most_common(20)])]
    if any(origins):  # só com um vocabulário que tem a coluna `origem` (o híbrido)
        lines += ["## Origem das entidades mencionadas no vocabulário\n",
                  *_table(("Origem", "Entidades distintas"), sorted(origins.items(), key=lambda kv: -kv[1]))]
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def run(
    project_root: Path | None = None,
    label: str = DEFAULT_LABEL,
    vocabulary_path: Path | None = None,
    club_map_path: Path | None = None,
) -> Path:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    club_map_file = root / (club_map_path or DEFAULT_CLUB_MAP)
    vocabulary = load_vocabulary(root / (vocabulary_path or DEFAULT_VOCABULARY), url_club_qids(club_map_file))
    club_map = load_club_map(club_map_file)
    articles, club_names = build_articles(
        corpus_graph_path(root, label), output / f"corpus_entities_{label}.csv",
        output / f"corpus_entities_{label}_corpo.csv", vocabulary, club_map,
    )
    target = output / f"prototipo_{label}"
    target.mkdir(parents=True, exist_ok=True)
    data = build_data(articles, vocabulary, club_names, label)
    (target / "data.js").write_text(
        "window.SDH_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    (target / "index.html").write_text(PAGE, encoding="utf-8")
    write_summary(articles, vocabulary, club_names, target / "resumo.md", label)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.navigation_corpus",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", default=DEFAULT_LABEL, metavar="ETIQUETA",
                        help="corpus da Fase 1 (por omissão por_ano)")
    parser.add_argument("--vocabulario", type=Path, default=DEFAULT_VOCABULARY,
                        help="o vocabulário usado no Caminho B (por omissão o alargado)")
    parser.add_argument("--clubes-url", type=Path, default=DEFAULT_CLUB_MAP)
    args = parser.parse_args(argv)
    target = run(label=args.corpus, vocabulary_path=args.vocabulario, club_map_path=args.clubes_url)
    print(f"Protótipo: {target / 'index.html'} (resumo em {target / 'resumo.md'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
