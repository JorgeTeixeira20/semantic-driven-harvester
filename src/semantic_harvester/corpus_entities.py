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
`clube`), `rotulo` (forma canónica) e `variantes` (formas alternativas
separadas por `|`; o rótulo conta sempre como variante).
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
from .corpus_redundancy import Capture, load_corpus

DEFAULT_CHROME_FRACTION = 0.10
ORIGIN_URL = "url"
ORIGIN_TEXT = "texto"
TECHNICAL_SEGMENTS = {"detalhe", "amp"}
CSV_FIELDS = (
    "artigo", "tipo", "categoria", "rotulo", "origem", "capturas_com_mencao",
    "capturas_com_texto", "ocorrencias", "persistente", "uma_so_captura",
)

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
        terms.append(Term(row["tipo"], row["categoria"], row["rotulo"], tuple(variants)))
    return terms


def count_mentions(segments: list[list[str]], terms: list[Term]) -> Counter[str]:
    """Ocorrências de cada termo (por rótulo) em segmentos de palavras já normalizadas.

    Não há correspondências entre segmentos: um bloco de chrome removido não
    junta as palavras que estavam de um lado e do outro.
    """

    counts: Counter[str] = Counter()
    for term in terms:
        for segment in segments:
            for variant in term.variants:
                size = len(variant)
                counts[term.rotulo] += sum(
                    1 for i in range(len(segment) - size + 1)
                    if tuple(segment[i:i + size]) == variant
                )
    return +counts


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
) -> list[dict[str, str]]:
    rows = [
        {
            "artigo": article, "tipo": "tema", "categoria": categoria,
            "rotulo": valor, "origem": ORIGIN_URL, "capturas_com_mencao": "",
            "capturas_com_texto": "", "ocorrencias": "", "persistente": "",
            "uma_so_captura": "",
        }
        for categoria, valor in themes_from_url(article)
    ]

    texts = [c.text or "" for c in captures if c.in_layer1]
    per_capture = [count_mentions(text_segments(t, chrome, n), terms) for t in texts]
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


def write_summary(
    corpus: dict[str, list[Capture]],
    rows: list[dict[str, str]],
    vocabulary_path: Path,
    chrome_fraction: float | None,
    path: Path,
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
        f"sem o chrome persistente (5-gramas em ≥ {chrome_fraction:g} dos artigos)"
        if chrome_fraction is not None else "completo, **sem** remoção do chrome"
    )
    lines = [
        "# Caminho B — temas e entidades mencionadas\n",
        "Sem pedidos à API; não altera o grafo nem o raw. Anotação por artigo. "
        f"Vocabulário: `{vocabulary_path}`. Texto pesquisado: {chrome_text}.\n",
        f"- Artigos: {len(articles)}; com texto (Camada 1): {len(with_text)}; "
        f"com uma só captura com texto (sem proteção de persistência): {len(single)}.",
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
        "",
        "| Entidade | Artigos (persistência) | Artigos (≥ 1 captura) |",
        "| --- | ---: | ---: |",
        *(f"| {label} | {strong_counts[label]} | {count} |"
          for label, count in sorted(weak_counts.items(), key=lambda kv: (-strong_counts[kv[0]], -kv[1], kv[0]))),
        "",
        "Detalhe por artigo em `output/corpus_entities.csv`. Contagens descritivas "
        "desta amostra; não são uma avaliação de precisão.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    project_root: Path | None = None,
    vocabulary_path: Path | None = None,
    chrome_fraction: float | None = DEFAULT_CHROME_FRACTION,
) -> list[dict[str, str]]:
    root = project_root or Path(__file__).resolve().parents[2]
    if vocabulary_path is None:
        raise ValueError("É preciso indicar o vocabulário fechado (--vocabulario).")
    output = root / "output"
    corpus = load_corpus(output / "corpus_articles.ttl", root)
    terms = load_vocabulary(vocabulary_path)
    chrome = build_chrome(corpus, chrome_fraction)

    rows = [
        row for article, captures in corpus.items()
        for row in analyse_article(article, captures, terms, chrome)
    ]
    write_csv(rows, output / "corpus_entities.csv")
    write_summary(corpus, rows, vocabulary_path, chrome_fraction,
                  output / "corpus_entities_summary.md")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.corpus_entities",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument("--vocabulario", type=Path, required=True,
                        help="CSV do vocabulário fechado de entidades")
    parser.add_argument("--fracao-chrome", type=float, default=DEFAULT_CHROME_FRACTION,
                        help="fração de artigos para um 5-grama ser chrome (por omissão 0,10)")
    parser.add_argument("--sem-remocao-chrome", action="store_true",
                        help="procura no texto completo, sem remover o chrome")
    args = parser.parse_args(argv)
    fraction = None if args.sem_remocao_chrome else args.fracao_chrome
    if fraction is not None and not 0.0 < fraction <= 1.0:
        parser.error("--fracao-chrome tem de estar em ]0, 1]")

    rows = run(vocabulary_path=args.vocabulario, chrome_fraction=fraction)
    print(f"Linhas (temas e entidades por artigo): {len(rows)}")
    print("Saídas: output/corpus_entities.csv, output/corpus_entities_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
