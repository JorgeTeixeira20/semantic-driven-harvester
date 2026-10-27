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

Com `--fonte sparql`, os artigos, as capturas, os títulos, os temas e as menções
vêm de consultas SPARQL (`queries/painel/*.rq`) ao store do grafo completo
(`sparql_corpus.py`, artigos + Caminho B) em vez do N-Triples e do CSV; o
vocabulário, a tabela de clubes e a origem do corpo continuam a vir dos
ficheiros (não estão no grafo). As duas fontes têm de dar o mesmo `data.js`
(teste em `tests/test_sparql_corpus.py`).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .boilerplate import MIN_ARTICLES_ANY_TIME
from .corpus_classification import article_url_scheme
from .corpus_entities import ORIGIN_TEXT, ORIGIN_URL, fold
from .corpus_entities_rdf import mencao_uri, primary_qid, url_club_qids
from .corpus_redundancy import corpus_graph_path, read_graph_index
from .navigation_corpus_page import PAGE
from .rdf_mapper import article_uri
from .sparql_corpus import MissingDependencyError, open_store, run_query

DEFAULT_LABEL = "por_ano"
DEFAULT_VOCABULARY = Path("data") / "processed" / "caminho_b_vocabulario_wikidata_alargado.csv"
DEFAULT_CLUB_MAP = Path("data") / "processed" / "caminho_b_clubes_url.csv"
WAYBACK = "https://arquivo.pt/wayback/"
PAINEL_QUERIES = Path(__file__).resolve().parents[2] / "queries" / "painel"
SOURCE_SPARQL, SOURCE_FILES = "sparql", "ficheiros"

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
# Nome de cada modalidade para mostrar (o URL não tem acentos); as outras
# mostram-se com a primeira letra em maiúscula e espaços (`modalidade_label`).
MODALIDADE_LABELS = {
    "hoquei-em-patins": "Hóquei em patins", "tenis": "Ténis", "tenis-de-mesa": "Ténis de mesa",
    "natacao": "Natação", "ginastica": "Ginástica", "raguebi": "Râguebi", "orientacao": "Orientação",
    "desporto-universitario": "Desporto universitário", "jogos-olimpicos": "Jogos Olímpicos",
    "polo-aquatico": "Polo aquático", "nfl": "NFL", "mma": "MMA",
}
# Sufixo do site no título ("… - Futebol - Jornal Record", por vezes cortado:
# "… - Jornal Re"): o último segmento e, antes dele, a secção (até 4 palavras).
_SEGMENT = re.compile(r"\s+[-–|]\s+")
SECTION_MAX_WORDS = 4
# Um título igual em pelo menos tantas notícias é o nome do site (":.: Jornal
# Record :.:"), não o da notícia: o painel mostra-a como "sem título". Mesmo
# limiar das frases repetidas na filtragem do texto (`boilerplate.py`).
GENERIC_TITLE_MIN_ARTICLES = MIN_ARTICLES_ANY_TIME
CLUB_CATEGORY = "clube"
OTHER_CATEGORIES = ("treinador", "estadio", "competicao")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")


def modalidade_label(value: str) -> str:
    return MODALIDADE_LABELS.get(value) or value.replace("-", " ").capitalize()


def display_title(title: str) -> str:
    """Título sem o sufixo do site; o título completo continua no grafo."""

    parts = _SEGMENT.split(title.strip())
    last = parts[-1].strip()
    if len(parts) < 2 or not ("jornal record".startswith(last.lower()) or re.search(r"\brecord\b", last, re.I)):
        return title
    parts = parts[:-1]
    if len(parts) >= 2 and len(parts[-1].split()) <= SECTION_MAX_WORDS:
        parts = parts[:-1]
    return " - ".join(parts)


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
    variants: tuple[str, ...] = ()


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
            variants=tuple(v for v in (row.get("variantes") or "").split("|") if v and v != row["rotulo"]),
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


@dataclass
class Sources:
    """O que o painel lê do grafo e do Caminho B, venha dos ficheiros ou do SPARQL."""

    resources: list[tuple[str, str, str, bool]] = field(default_factory=list)  # URL, título, tstamp, texto
    themes: dict[str, dict[str, list[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list)))
    mentions: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def read_sources_files(graph_path: Path, entities_csv: Path) -> Sources:
    """Grafo dos artigos em streaming e o CSV do Caminho B (`--fonte ficheiros`)."""

    index = read_graph_index(graph_path)
    sources = Sources()
    for resource in index.resources:
        url = str(index.original_url[resource])
        captures = sorted(index.captures.get(resource, ()),
                          key=lambda c: str(index.capture_fields[c].get("tstamp", "")))
        tstamp = str(index.capture_fields[captures[0]].get("tstamp", "")) if captures else ""
        has_text = any("text_node" in index.capture_fields[c] for c in captures)
        sources.resources.append((url, str(index.labels.get(article_uri(url), "") or url), tstamp, has_text))
    with entities_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["origem"] == ORIGIN_URL:
                sources.themes[row["artigo"]][row["categoria"]].append(row["rotulo"])
            elif row["origem"] == ORIGIN_TEXT:
                sources.mentions[row["artigo"]].append(row["rotulo"])
    return sources


def read_sources_sparql(store) -> tuple[Sources, dict[str, float], int]:
    """As mesmas fontes por consultas SPARQL (`queries/painel/*.rq`) ao store do
    grafo completo (`sparql_corpus.open_store`). Devolve também o tempo de cada
    consulta e quantos artigos têm mais de um título no grafo."""

    sources, seconds = Sources(), {}
    result = run_query(store, "artigos", queries_dir=PAINEL_QUERIES)
    seconds["artigos"] = result.seconds
    several_titles = 0
    for row in result.rows:
        url = row["url"]
        several_titles += (row["titulos"] or 0) > 1
        sources.resources.append((url, row["titulo"] or url, row["primeira"] or "", (row["textos"] or 0) > 0))
    result = run_query(store, "temas", queries_dir=PAINEL_QUERIES)
    seconds["temas"] = result.seconds
    for row in result.rows:
        sources.themes[row["url"]][row["categoria"]].append(row["valor"])
    result = run_query(store, "mencoes", queries_dir=PAINEL_QUERIES)
    seconds["mencoes"] = result.seconds
    for row in result.rows:
        # A entidade pode ter vários rótulos; o da menção é o que gerou o seu URI.
        if row["mencao"] == str(mencao_uri(row["url"], row["rotulo"])):
            sources.mentions[row["url"]].append(row["rotulo"])
    return sources, seconds, several_titles


def build_articles(
    sources: Sources,
    body_csv: Path,
    vocabulary: dict[str, Entity],
    club_map: dict[str, tuple[str, str]],
) -> tuple[list[Article], dict[str, str]]:
    """Artigos com o preenchimento feito, e nome de cada chave de clube."""

    themes, mentions = sources.themes, sources.mentions
    bodies = load_body_sources(body_csv)

    club_names: dict[str, str] = {}
    for entity in vocabulary.values():
        if entity.categoria == CLUB_CATEGORY:
            club_names[entity.key] = entity.name
    articles = []
    for url, title, tstamp, has_text in sources.resources:
        article = Article(
            url=url, title=display_title(title), tstamp=tstamp,
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


def generic_titles(articles: list[Article]) -> Counter:
    """Títulos repetidos em `GENERIC_TITLE_MIN_ARTICLES` ou mais notícias, com a contagem."""

    counts = Counter(a.title for a in articles)
    return Counter({t: n for t, n in counts.items() if n >= GENERIC_TITLE_MIN_ARTICLES})


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
    generic = generic_titles(articles)
    return {
        "label": label,
        "eras": eras,
        "modalidades": modalidades,
        "modalidadeNomes": [modalidade_label(m) for m in modalidades],
        "bodies": bodies,
        "clubs": [{"k": k, "n": club_names.get(k, k)} for k in club_keys],
        "entities": [{"k": k, "n": by_key[k].name, "c": by_key[k].categoria,
                      "m": by_key[k].modalidade, "q": by_key[k].qid, "o": by_key[k].origin,
                      "a": list(by_key[k].variants)}
                     for k in entity_keys],
        # [tstamp, título ("" se genérico), URL, época, modalidades, origem, clubes, origem, entidades, corpo]
        "articles": [
            [a.tstamp, "" if a.title in generic else a.title, a.url, era_index[a.era], [mod_index[m] for m in a.modalidades],
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
    generic = generic_titles(articles)
    lines += [f"## Títulos repetidos em {GENERIC_TITLE_MIN_ARTICLES} ou mais notícias "
              "(mostrados como sem título)\n",
              f"Notícias afetadas: {sum(generic.values())}.\n",
              *_table(("Título", "Notícias"), generic.most_common())]
    if any(origins):  # só com um vocabulário que tem a coluna `origem` (o híbrido)
        lines += ["## Origem das entidades mencionadas no vocabulário\n",
                  *_table(("Origem", "Entidades distintas"), sorted(origins.items(), key=lambda kv: -kv[1]))]
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def write_sparql_note(path: Path, label: str, load, seconds: dict[str, float], several_titles: int) -> None:
    """Como foram obtidos os dados do painel por SPARQL (fora do `resumo.md`, que fica igual)."""

    lines = [
        f"# Dados do painel `prototipo_{label}` obtidos por SPARQL\n",
        "Artigos, capturas, títulos, temas e menções lidos por consultas SPARQL "
        "(`queries/painel/*.rq`) ao store com o grafo dos artigos e o do Caminho B "
        "(`sparql_corpus.py`). Vêm de ficheiros só o vocabulário (categoria, modalidade e "
        "variantes das entidades), a tabela dos clubes do URL e a origem do corpo.\n",
        f"- Triplos no store: {load.triples}",
        f"- Carga do store: {load.seconds:.1f} s" + (f" (reutilizado, carregado em {load.loaded_at})" if load.reused else ""),
        *(f"- Consulta `{name}`: {value:.1f} s" for name, value in seconds.items()),
        f"- Artigos com mais de um título no grafo: {several_titles}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    project_root: Path | None = None,
    label: str = DEFAULT_LABEL,
    vocabulary_path: Path | None = None,
    club_map_path: Path | None = None,
    source: str = SOURCE_FILES,
    target_name: str | None = None,
    reload: bool = False,
) -> Path:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    club_map_file = root / (club_map_path or DEFAULT_CLUB_MAP)
    vocabulary = load_vocabulary(root / (vocabulary_path or DEFAULT_VOCABULARY), url_club_qids(club_map_file))
    club_map = load_club_map(club_map_file)
    target = output / (target_name or f"prototipo_{label}")
    target.mkdir(parents=True, exist_ok=True)
    if source == SOURCE_SPARQL:
        store, load = open_store(root, label, reload)
        sources, seconds, several_titles = read_sources_sparql(store)
        del store
        write_sparql_note(target / "fonte_sparql.md", label, load, seconds, several_titles)
    else:
        sources = read_sources_files(corpus_graph_path(root, label), output / f"corpus_entities_{label}.csv")
    articles, club_names = build_articles(
        sources, output / f"corpus_entities_{label}_corpo.csv", vocabulary, club_map,
    )
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
    parser.add_argument("--fonte", choices=(SOURCE_FILES, SOURCE_SPARQL), default=SOURCE_SPARQL,
                        help="por omissão, consultas SPARQL ao store do sparql_corpus (desde 2026-10-27, "
                        "depois de dar um data.js idêntico no por_ano); ficheiros: o N-Triples e o CSV")
    parser.add_argument("--destino", metavar="PASTA",
                        help="pasta em output/ (por omissão prototipo_<etiqueta>)")
    parser.add_argument("--recarregar", action="store_true", help="refaz a carga do store SPARQL")
    args = parser.parse_args(argv)
    try:
        target = run(label=args.corpus, vocabulary_path=args.vocabulario, club_map_path=args.clubes_url,
                     source=args.fonte, target_name=args.destino, reload=args.recarregar)
    except (MissingDependencyError, FileNotFoundError, RuntimeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    print(f"Protótipo: {target / 'index.html'} (resumo em {target / 'resumo.md'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
