"""Caminho B — povoamento de `Tema` e `EntidadeMencionada` (vocabulário fechado).

Implementa a proposta de `docs/experiments.md` ("Caminho B — povoamento de
`Tema` e `EntidadeMencionada`"). Não faz pedidos à API e não altera o grafo
nem o raw. A anotação é por **artigo** (domínio de `sdh:temTema` e
`sdh:mencionaEntidade` na ontologia), agregada sobre as capturas da Camada 1.

- **Temas** a partir do `originalURL`, por regras posicionais sobre o caminho
  (secção, modalidade, competição, clube-secção): classificação editorial do
  próprio jornal, independente do texto.
- **Entidades** por correspondência exata de sequências de palavras de um
  vocabulário fechado (ficheiro CSV indicado em `--vocabulario`), com texto
  normalizado (NFC, minúsculas, sem acentos) e limites de palavra. Sem NER.
- Contra o chrome: procura no texto sem o chrome persistente (n-gramas da
  variante b do Caminho D, por omissão 5-gramas em ≥ 10% dos artigos), sem
  juntar palavras de lados opostos de um bloco removido; e regista em quantas
  capturas do artigo a entidade aparece, para a regra de persistência (todas
  as capturas com texto) e a regra fraca (≥ 1 captura).

O vocabulário tem as colunas `tipo` (`entidade`), `categoria` (ex.: `atleta`,
`clube`), `rotulo` (forma canónica), `variantes` (formas alternativas
separadas por `|`; o rótulo conta sempre como variante) e, opcionalmente,
`clubes` (clubes do jogador, separados por `|`).

Coluna `clube_coerente` (sinal, não filtro): compara os clubes do jogador com
o tema `clube` do URL do artigo, através da tabela explícita slug → clube
(`--clubes-url`): `sim`, `nao` ou `sem_tema` (URL sem clube).
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .corpus_chrome import (
    DEFAULT_N, article_frequency, chrome_coverage, chrome_ngrams, layer1_tokens,
    tokens,
)
from .corpus_redundancy import Capture, corpus_graph_path, load_corpus, to_body_corpus

DEFAULT_CHROME_FRACTION = 0.10
ORIGIN_URL = "url"
ORIGIN_TEXT = "texto"
TECHNICAL_SEGMENTS = {"detalhe", "amp"}
CSV_FIELDS = (
    "artigo", "tipo", "categoria", "rotulo", "origem", "capturas_com_mencao",
    "capturas_com_texto", "ocorrencias", "persistente", "uma_so_captura",
    "clube_coerente",
)
COHERENT_YES = "sim"
COHERENT_NO = "nao"
COHERENT_NO_THEME = "sem_tema"
COHERENT_UNMAPPED = "sem_mapa"
CLUB_CATEGORY = "clube"
DEFAULT_CLUB_MAP = Path("data") / "processed" / "caminho_b_clubes_url.csv"

_WORD_RE = re.compile(r"\w+")


def fold(text: str) -> str:
    """NFC, minúsculas e sem acentos: forma usada só para comparar."""

    text = unicodedata.normalize("NFC", text).casefold()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def match_tokens(text: str) -> list[str]:
    return _WORD_RE.findall(fold(text))


# --- Vocabulário --------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    tipo: str
    categoria: str
    rotulo: str
    variants: tuple[tuple[str, ...], ...]
    clubs: frozenset[str] = frozenset()


def load_vocabulary(path: Path) -> list[Term]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    terms = []
    for row in rows:
        if row["tipo"] != "entidade":
            raise ValueError(
                f"Tipo {row['tipo']!r} em {row['rotulo']!r}: o vocabulário só tem "
                "entidades; os temas vêm do URL."
            )
        forms = [row["rotulo"], *[v for v in (row.get("variantes") or "").split("|") if v.strip()]]
        variants = []
        for form in forms:
            folded = tuple(match_tokens(form))
            if folded and folded not in variants:
                variants.append(folded)
        clubs = frozenset(c for c in (row.get("clubes") or "").split("|") if c)
        terms.append(Term(row["tipo"], row["categoria"], row["rotulo"], tuple(variants), clubs))
    return terms


def load_club_map(path: Path) -> dict[str, str]:
    """Slug de clube no `originalURL` → nome do clube usado no vocabulário."""

    with path.open(encoding="utf-8", newline="") as handle:
        return {row["slug"]: row["clube"] for row in csv.DictReader(handle)}


def club_coherence(
    term: Term, article_club_slugs: list[str], club_map: dict[str, str],
    strict: bool = True,
) -> str:
    """Sinal transparente: o clube do jogador coincide com o tema `clube` do artigo?

    Não remove nem corrige nada; só compara. Uma entidade da categoria
    `clube` compara-se pelo próprio rótulo. Com `strict=False` (corpus da
    Fase 1, com muitos clubes no URL fora da tabela), um slug sem
    correspondência dá `sem_mapa` em vez de erro.
    """

    if not article_club_slugs:
        return COHERENT_NO_THEME
    missing = [slug for slug in article_club_slugs if slug not in club_map]
    if missing:
        if strict:
            raise ValueError(f"Clube do URL sem correspondência na tabela: {missing}")
        return COHERENT_UNMAPPED
    article_clubs = {club_map[slug] for slug in article_club_slugs}
    own = term.clubs | ({term.rotulo} if term.categoria == CLUB_CATEGORY else set())
    return COHERENT_YES if own & article_clubs else COHERENT_NO


def count_mentions(
    segments: list[list[str]], terms: list[Term], longest_match: bool = True
) -> Counter[str]:
    """Ocorrências de cada termo (por rótulo) em segmentos de palavras já normalizadas.

    Correspondência mais longa (por omissão desde 2026-10-22,
    `docs/experiments.md`): em cada posição conta só a variante mais comprida
    que aí começa, e a leitura continua depois dela — "Sporting de Braga" já
    não conta também "Sporting". Variantes de comprimento igual na mesma
    posição contam todas. Com `longest_match=False`, a contagem anterior: cada
    variante em todas as posições, mesmo dentro de outra mais longa.

    Não há correspondências entre segmentos: um bloco de chrome removido não
    junta as palavras que estavam de um lado e do outro.
    """

    # Índice pela primeira palavra: cada texto é percorrido uma só vez.
    index: dict[str, list[tuple[tuple[str, ...], str]]] = defaultdict(list)
    for term in terms:
        for variant in term.variants:
            index[variant[0]].append((variant, term.rotulo))
    counts: Counter[str] = Counter()
    if not longest_match:
        for segment in segments:
            for i, word in enumerate(segment):
                for variant, label in index.get(word, ()):
                    if tuple(segment[i:i + len(variant)]) == variant:
                        counts[label] += 1
        return counts
    for segment in segments:
        i = 0
        while i < len(segment):
            matches = [
                (len(variant), label)
                for variant, label in index.get(segment[i], ())
                if tuple(segment[i:i + len(variant)]) == variant
            ]
            if not matches:
                i += 1
                continue
            longest = max(length for length, _ in matches)
            for label in {label for length, label in matches if length == longest}:
                counts[label] += 1
            i += longest
    return counts


def text_segments(
    text: str, chrome: set[tuple[str, ...]] | None, n: int = DEFAULT_N
) -> list[list[str]]:
    """Palavras normalizadas para comparação, partidas onde havia chrome."""

    words = tokens(text)
    covered = chrome_coverage(words, chrome, n) if chrome else [False] * len(words)
    segments: list[list[str]] = [[]]
    for word, hit in zip(words, covered):
        if hit:
            if segments[-1]:
                segments.append([])
        else:
            segments[-1].extend(match_tokens(word))
    return [segment for segment in segments if segment]


# --- Temas a partir do URL ----------------------------------------------------


def themes_from_url(url: str) -> list[tuple[str, str]]:
    """(categoria, valor) a partir das posições do caminho do `originalURL`."""

    parts = [p.lower() for p in urlsplit(url).path.split("/") if p]
    cut = next((i for i, p in enumerate(parts) if p in TECHNICAL_SEGMENTS), None)
    path = parts[:cut] if cut is not None else parts[:-1]
    path = [p for p in path if p not in TECHNICAL_SEGMENTS]
    if not path:
        return []

    themes = [("secao", path[0])]
    if path[0] == "futebol":
        themes.append(("modalidade", "futebol"))
        if len(path) > 2 and path[1] == "futebol-nacional":
            themes.append(("competicao", path[2]))
            if len(path) > 3:
                themes.append(("clube", path[3]))
    if path[0] == "modalidades" and len(path) > 1:
        themes.append(("modalidade", path[1]))
    for i, part in enumerate(path[:-1]):
        if part.startswith("competicoes-de-"):
            themes.append(("competicao", path[i + 1]))
    return themes


# --- Análise por artigo -------------------------------------------------------


def analyse_article(
    article: str,
    captures: list[Capture],
    terms: list[Term],
    chrome: set[tuple[str, ...]] | None,
    n: int = DEFAULT_N,
    club_map: dict[str, str] | None = None,
    longest_match: bool = True,
    strict_clubs: bool = True,
) -> list[dict[str, str]]:
    themes = themes_from_url(article)
    club_slugs = [value for categoria, value in themes if categoria == "clube"]
    rows = [
        {
            "artigo": article, "tipo": "tema", "categoria": categoria,
            "rotulo": valor, "origem": ORIGIN_URL, "capturas_com_mencao": "",
            "capturas_com_texto": "", "ocorrencias": "", "persistente": "",
            "uma_so_captura": "", "clube_coerente": "",
        }
        for categoria, valor in themes
    ]

    texts = [c.text or "" for c in captures if c.in_layer1]
    per_capture = [count_mentions(text_segments(t, chrome, n), terms, longest_match) for t in texts]
    by_label = {term.rotulo: term for term in terms}
    present = sorted({label for counts in per_capture for label in counts})
    for label in present:
        with_mention = sum(1 for counts in per_capture if counts[label])
        term = by_label[label]
        rows.append({
            "artigo": article, "tipo": term.tipo, "categoria": term.categoria,
            "rotulo": label, "origem": ORIGIN_TEXT,
            "capturas_com_mencao": str(with_mention),
            "capturas_com_texto": str(len(texts)),
            "ocorrencias": str(sum(counts[label] for counts in per_capture)),
            "persistente": str(with_mention == len(texts)),
            "uma_so_captura": str(len(texts) == 1),
            "clube_coerente": (
                club_coherence(term, club_slugs, club_map, strict_clubs)
                if club_map is not None else ""
            ),
        })
    return rows


def build_chrome(
    corpus: dict[str, list[Capture]], fraction: float | None, n: int = DEFAULT_N
) -> set[tuple[str, ...]] | None:
    if fraction is None:
        return None
    corpus_tokens = layer1_tokens(corpus)
    return chrome_ngrams(article_frequency(corpus_tokens, n), len(corpus_tokens), fraction)


# --- Saídas -------------------------------------------------------------------


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _frequency_table(counter: Counter, header: str) -> list[str]:
    lines = [f"| {header} | Artigos |", "| --- | ---: |"]
    lines += [f"| {key} | {count} |" for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]
    return lines


def coherence_lines(
    entities: list[dict[str, str]], strong: list[dict[str, str]]
) -> list[str]:
    if not any(r["clube_coerente"] for r in entities):
        return []
    values = (COHERENT_YES, COHERENT_NO, COHERENT_NO_THEME)
    if any(r["clube_coerente"] == COHERENT_UNMAPPED for r in entities):
        values += (COHERENT_UNMAPPED,)
    weak_counts = Counter(r["clube_coerente"] for r in entities)
    strong_counts = Counter(r["clube_coerente"] for r in strong)
    return [
        "### Coerência de clube (sinal, não filtro)\n",
        "Para cada par artigo–jogador: `sim` se um clube do jogador no vocabulário "
        "coincide com o tema `clube` do URL do artigo; `nao` se não coincide "
        "(possível falso positivo, por exemplo uma manchete do chrome); `sem_tema` "
        "se o URL não tem clube. Uma entidade clube compara-se pelo próprio rótulo. "
        "`sem_mapa`: o clube do URL não está na tabela slug → clube. Nenhuma "
        "menção é removida.\n",
        "| clube_coerente | Pares (regra fraca) | Pares (persistência) |",
        "| --- | ---: | ---: |",
        *(f"| {v} | {weak_counts[v]} | {strong_counts[v]} |" for v in values),
        "",
    ]


def body_source_lines(corpus: dict[str, list[Capture]]) -> list[str]:
    sources = Counter(c.body_source for caps in corpus.values() for c in caps if c.body_source)
    if not sources:
        return []
    return ["- Origem do corpo, por captura com texto: " + "; ".join(
        f"{source} {count}" for source, count in sorted(sources.items(), key=lambda kv: (-kv[1], kv[0])))
        + "."]


def write_summary(
    corpus: dict[str, list[Capture]],
    rows: list[dict[str, str]],
    vocabulary_path: Path,
    chrome_fraction: float | None,
    path: Path,
    use_body: bool = False,
    csv_name: str = "corpus_entities.csv",
    unmapped_slugs: Counter | None = None,
    use_html: bool = False,
) -> None:
    articles = list(corpus)
    with_text = [a for a, caps in corpus.items() if any(c.in_layer1 for c in caps)]
    single = [a for a, caps in corpus.items() if sum(c.in_layer1 for c in caps) == 1]

    themes = [r for r in rows if r["origem"] == ORIGIN_URL]
    entities = [r for r in rows if r["origem"] == ORIGIN_TEXT]
    strong = [r for r in entities if r["persistente"] == "True"]

    theme_counts: dict[str, Counter] = defaultdict(Counter)
    for r in themes:
        theme_counts[r["categoria"]][r["rotulo"]] += 1
    articles_with: dict[str, set] = defaultdict(set)
    for r in themes:
        articles_with[r["categoria"]].add(r["artigo"])

    weak_counts = Counter(r["rotulo"] for r in entities)
    strong_counts = Counter(r["rotulo"] for r in strong)
    chrome_text = (
        "só o **corpo do artigo** (variante c′, `article_body.py`; com o HTML: Premium "
        "sem corpo e, quando a c′ não encontra corpo, o contentor do HTML, "
        "`html_body.py`; capturas sem corpo não contam)" if use_body and use_html else
        "só o **corpo do artigo** (variante c′, `article_body.py`; capturas sem corpo "
        "não contam)" if use_body else
        f"sem o chrome persistente (5-gramas em ≥ {chrome_fraction:.2f} dos artigos)".replace(".", ",", 1)
        if chrome_fraction is not None else "completo, **sem** remoção do chrome"
    )
    lines = [
        "# Caminho B — temas e entidades mencionadas\n",
        "Sem pedidos à API; não altera o grafo nem o raw. Anotação por artigo. "
        f"Vocabulário: `{vocabulary_path}`. Texto pesquisado: {chrome_text}.\n",
        f"- Artigos: {len(articles)}; com texto (Camada 1): {len(with_text)}; "
        f"com uma só captura com texto (sem proteção de persistência): {len(single)}.",
        *body_source_lines(corpus),
        "",
        "## Temas (a partir do `originalURL`)\n",
        "| Categoria | Artigos com tema | Valores distintos |",
        "| --- | ---: | ---: |",
        *(f"| {cat} | {len(articles_with[cat])} | {len(theme_counts[cat])} |"
          for cat in ("secao", "modalidade", "competicao", "clube")),
        "",
    ]
    for cat in ("modalidade", "competicao", "clube"):
        if theme_counts[cat]:
            lines += [f"### {cat}\n", *_frequency_table(theme_counts[cat], cat), ""]

    lines += [
        "## Entidades mencionadas (vocabulário fechado, no texto)\n",
        f"- Artigos com pelo menos uma entidade, regra de persistência (todas as "
        f"capturas com texto): {len({r['artigo'] for r in strong})}",
        f"- Artigos com pelo menos uma entidade, regra fraca (≥ 1 captura): "
        f"{len({r['artigo'] for r in entities})}",
        f"- Pares artigo–entidade: {len(entities)} pela regra fraca, {len(strong)} pela "
        f"regra de persistência; destes, {sum(r['uma_so_captura'] == 'True' for r in strong)} "
        "são de artigos com uma só captura com texto, onde a persistência não "
        "filtra nada.",
        "",
        *coherence_lines(entities, strong),
        "| Entidade | Artigos (persistência) | Artigos (≥ 1 captura) |",
        "| --- | ---: | ---: |",
        *(f"| {label} | {strong_counts[label]} | {count} |"
          for label, count in sorted(weak_counts.items(), key=lambda kv: (-strong_counts[kv[0]], -kv[1], kv[0]))),
        "",
        f"Detalhe por artigo em `output/{csv_name}`. Contagens descritivas "
        "desta amostra; não são uma avaliação de precisão.",
    ]
    if unmapped_slugs:
        lines += [
            "\n## Clubes do URL sem correspondência na tabela slug → clube\n",
            "Para alargar `data/processed/caminho_b_clubes_url.csv`; enquanto faltarem, "
            "os pares destes artigos ficam `sem_mapa`.\n",
            *_frequency_table(unmapped_slugs, "slug"),
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    project_root: Path | None = None,
    vocabulary_path: Path | None = None,
    chrome_fraction: float | None = DEFAULT_CHROME_FRACTION,
    club_map_path: Path | None = None,
    use_body: bool = False,
    longest_match: bool = True,
    corpus_label: str | None = None,
    use_html: bool = False,
) -> list[dict[str, str]]:
    """Sem `corpus_label`, o corpus de 125 artigos e as saídas oficiais; com
    uma etiqueta (ex. `por_ano`), o N-Triples desse corpus da Fase 1 e saídas
    `output/corpus_entities_<etiqueta>*`, sem tocar nas oficiais."""

    root = project_root or Path(__file__).resolve().parents[2]
    if vocabulary_path is None:
        raise ValueError("É preciso indicar o vocabulário fechado (--vocabulario).")
    output = root / "output"
    tag = f"_{corpus_label}" if corpus_label else ""
    corpus = load_corpus(corpus_graph_path(root, corpus_label), root)
    terms = load_vocabulary(vocabulary_path)
    if use_body:
        # Variante (c′): o corpo já exclui o chrome; capturas sem corpo deixam a Camada 1.
        corpus, chrome_fraction = to_body_corpus(corpus, use_html=use_html), None
    chrome = build_chrome(corpus, chrome_fraction)
    club_map = load_club_map(club_map_path) if club_map_path is not None else None

    rows = [
        row for article, captures in corpus.items()
        for row in analyse_article(article, captures, terms, chrome, club_map=club_map,
                                   longest_match=longest_match, strict_clubs=not corpus_label)
    ]
    unmapped = Counter(
        r["rotulo"] for r in rows
        if club_map is not None and r["origem"] == ORIGIN_URL and r["categoria"] == "clube"
        and r["rotulo"] not in club_map
    )
    output.mkdir(parents=True, exist_ok=True)
    write_csv(rows, output / f"corpus_entities{tag}.csv")
    write_summary(corpus, rows, vocabulary_path, chrome_fraction,
                  output / f"corpus_entities{tag}_summary.md", use_body,
                  csv_name=f"corpus_entities{tag}.csv", unmapped_slugs=unmapped,
                  use_html=use_html)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.corpus_entities",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument("--vocabulario", type=Path, required=True,
                        help="CSV do vocabulário fechado de entidades")
    parser.add_argument("--texto", choices=("corpo", "corpo-html", "sem-chrome", "completo"),
                        default="corpo",
                        help="corpo do artigo (variante c′, adotada; por omissão); corpo-html: "
                        "c′ e, sem corpo, o contentor do HTML, com Premium sem corpo; texto sem "
                        "o chrome persistente (histórico) ou texto completo")
    parser.add_argument("--fracao-chrome", type=float, default=DEFAULT_CHROME_FRACTION,
                        help="com --texto sem-chrome: fração de artigos para um 5-grama ser "
                        "chrome (por omissão 0,10)")
    parser.add_argument("--clubes-url", type=Path, default=DEFAULT_CLUB_MAP,
                        help="tabela slug do URL → clube do vocabulário, para a coluna "
                        "clube_coerente (por omissão data/processed/caminho_b_clubes_url.csv)")
    parser.add_argument("--correspondencia-simples", action="store_true",
                        help="contagem anterior a 2026-10-22: cada variante em todas as posições, "
                        "mesmo dentro de outra mais longa (por omissão, só a mais longa)")
    parser.add_argument("--corpus", metavar="ETIQUETA",
                        help="corpus da Fase 1 (ex. por_ano): lê "
                        "data/processed/corpus_articles_<ETIQUETA>_triples.nt e escreve "
                        "output/corpus_entities_<ETIQUETA>*; por omissão, o corpus de 125 artigos")
    args = parser.parse_args(argv)
    fraction = args.fracao_chrome if args.texto == "sem-chrome" else None
    if fraction is not None and not 0.0 < fraction <= 1.0:
        parser.error("--fracao-chrome tem de estar em ]0, 1]")

    rows = run(vocabulary_path=args.vocabulario, chrome_fraction=fraction,
               club_map_path=args.clubes_url, use_body=args.texto in ("corpo", "corpo-html"),
               use_html=args.texto == "corpo-html",
               longest_match=not args.correspondencia_simples, corpus_label=args.corpus)
    tag = f"_{args.corpus}" if args.corpus else ""
    print(f"Linhas (temas e entidades por artigo): {len(rows)}")
    print(f"Saídas: output/corpus_entities{tag}.csv, output/corpus_entities{tag}_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
