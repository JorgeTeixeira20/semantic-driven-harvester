"""Caminho D, variante (b) do pré-processamento — remoção do "chrome" do site.

Implementa o ponto 3(b) do desenho em `docs/experiments.md`: remover
n-gramas de palavras presentes numa fração alta das capturas **de artigos
diferentes**, critério derivado só do corpus (sem marcadores manuais por
site). Não altera o grafo, o raw nem as saídas da variante (a).

- A frequência de um n-grama conta **artigos distintos** (sobre as capturas
  da Camada 1), não capturas: um artigo capturado muitas vezes não faz o seu
  próprio conteúdo passar por chrome. Um n-grama só é chrome se aparecer em
  pelo menos `MIN_ARTICLES` artigos e numa fração ≥ `fracao` dos artigos com
  texto.
- Cada palavra coberta por um n-grama de chrome é retirada; a similaridade é
  a mesma da variante (a), Jaccard de conjuntos de palavras, sobre o texto que
  sobra.
- A fração de corte não é fixada aqui: `--so-distribuicao` gera apenas a
  distribuição das frequências, para a fração ser escolhida a partir dela
  antes de olhar para os rótulos; só depois se corre a avaliação com
  `--fracao`.

Com `--fracao`, recalcula a distribuição e a tabela de sensibilidade da
Camada 1 com o texto sem chrome e compara a similaridade dos 60 pares de
`output/corpus_redundancy_label_sample.csv` com os rótulos manuais.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .corpus_redundancy import (
    SENSITIVITY_THRESHOLDS, Capture, describe, jaccard, load_corpus,
    normalize_text, sensitivity_table, _WORD_RE,
)

DEFAULT_N = 5
SENSITIVITY_N = (3, 5, 8)
MIN_ARTICLES = 2
LABEL_SAME = "mesma versão"
LABEL_CHANGED = "texto alterado"
LABEL_THRESHOLDS = SENSITIVITY_THRESHOLDS
# Pontos de corte em que a distribuição é resumida (fração de artigos).
FRACTION_GRID = (0.02, 0.03, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.75)


def tokens(text: str) -> list[str]:
    return _WORD_RE.findall(normalize_text(text))


def ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def article_frequency(
    corpus_tokens: dict[str, list[list[str]]], n: int
) -> Counter[tuple[str, ...]]:
    """Nº de artigos distintos em que cada n-grama aparece (em qualquer captura)."""

    frequency: Counter[tuple[str, ...]] = Counter()
    for captures in corpus_tokens.values():
        seen: set[tuple[str, ...]] = set()
        for words in captures:
            seen |= ngrams(words, n)
        frequency.update(seen)
    return frequency


def chrome_ngrams(
    frequency: Counter[tuple[str, ...]], n_articles: int, fraction: float
) -> set[tuple[str, ...]]:
    minimum = min_articles(fraction, n_articles)
    return {gram for gram, count in frequency.items() if count >= minimum}


def strip_chrome(
    words: list[str], chrome: set[tuple[str, ...]], n: int
) -> list[str]:
    """Remove as palavras cobertas por pelo menos um n-grama de chrome."""

    covered = [False] * len(words)
    for i in range(len(words) - n + 1):
        if tuple(words[i:i + n]) in chrome:
            for j in range(i, i + n):
                covered[j] = True
    return [word for word, hit in zip(words, covered) if not hit]


# --- Distribuição das frequências -------------------------------------------


@dataclass(frozen=True)
class CutRow:
    fraction: float
    min_articles: int
    chrome_ngrams: int
    tokens_removed_share: float


def frequency_buckets(
    frequency: Counter[tuple[str, ...]], n_articles: int
) -> list[tuple[str, int]]:
    """Nº de n-gramas distintos por número de artigos em que aparecem."""

    edges = [e for e in (1, 2, 3, 6, 11, 21, 31, 51, 76, 101) if e <= n_articles]
    edges.append(n_articles + 1)
    buckets = [(low, high - 1) for low, high in zip(edges, edges[1:])]
    counts = Counter()
    for count in frequency.values():
        for low, high in buckets:
            if low <= count <= high:
                counts[(low, high)] += 1
                break
    return [
        (f"{low}" if low == high else f"{low}–{high}", counts[(low, high)])
        for low, high in buckets
    ]


def min_articles(fraction: float, n_articles: int) -> int:
    return max(MIN_ARTICLES, math.ceil(fraction * n_articles))


def cut_table(
    corpus_tokens: dict[str, list[list[str]]],
    frequency: Counter[tuple[str, ...]],
    n: int,
    fractions: tuple[float, ...] = FRACTION_GRID,
) -> list[CutRow]:
    n_articles = len(corpus_tokens)
    total = sum(len(words) for caps in corpus_tokens.values() for words in caps)
    rows = []
    for fraction in fractions:
        chrome = chrome_ngrams(frequency, n_articles, fraction)
        kept = sum(
            len(strip_chrome(words, chrome, n))
            for caps in corpus_tokens.values() for words in caps
        )
        rows.append(CutRow(
            fraction,
            min_articles(fraction, n_articles),
            len(chrome),
            1 - kept / total if total else 0.0,
        ))
    return rows


# --- Avaliação contra os rótulos manuais ------------------------------------


@dataclass(frozen=True)
class LabelledPair:
    par_id: str
    faixa: str
    article: str
    tstamp_a: str
    tstamp_b: str
    label: str
    similarity_with_chrome: float


def load_labelled_pairs(path: Path) -> list[LabelledPair]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    pairs = []
    for row in rows:
        if row["rotulo_manual"] not in (LABEL_SAME, LABEL_CHANGED):
            raise ValueError(f"Par {row['par_id']} sem rótulo manual válido")
        pairs.append(LabelledPair(
            row["par_id"], row["faixa"], row["artigo"], row["tstamp_a"],
            row["tstamp_b"], row["rotulo_manual"], float(row["similaridade"]),
        ))
    return pairs


@dataclass(frozen=True)
class Separation:
    clean: bool
    min_same: float
    max_changed: float
    ambiguous: list[tuple[str, str, float]]


def separation(labelled: list[tuple[str, str, float]]) -> Separation:
    """`labelled` = (par_id, rótulo, similaridade). Separa se max(alterado) < min(mesma)."""

    same = [s for _, label, s in labelled if label == LABEL_SAME]
    changed = [s for _, label, s in labelled if label == LABEL_CHANGED]
    min_same, max_changed = min(same), max(changed)
    ambiguous = sorted(
        [(pid, label, s) for pid, label, s in labelled
         if (label == LABEL_SAME and s <= max_changed)
         or (label == LABEL_CHANGED and s >= min_same)],
        key=lambda item: item[2],
    )
    return Separation(max_changed < min_same, min_same, max_changed, ambiguous)


def errors_by_threshold(
    labelled: list[tuple[str, str, float]],
    thresholds: tuple[float, ...] = LABEL_THRESHOLDS,
) -> list[tuple[float, int, int]]:
    return [
        (t,
         sum(label == LABEL_SAME and s < t for _, label, s in labelled),
         sum(label == LABEL_CHANGED and s >= t for _, label, s in labelled))
        for t in thresholds
    ]


# --- Execução ----------------------------------------------------------------


def layer1_tokens(corpus: dict[str, list[Capture]]) -> dict[str, list[list[str]]]:
    """Tokens das capturas da Camada 1 por artigo, só artigos com algum texto."""

    result = {}
    for article, captures in corpus.items():
        words = [tokens(c.text or "") for c in captures if c.in_layer1]
        if words:
            result[article] = words
    return result


def _num(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _pct(value: float) -> str:
    return f"{100 * value:.1f}%".replace(".", ",")


def evaluate(
    corpus: dict[str, list[Capture]],
    pairs: list[LabelledPair],
    n: int,
    fraction: float,
) -> dict:
    corpus_tokens = layer1_tokens(corpus)
    n_articles = len(corpus_tokens)
    frequency = article_frequency(corpus_tokens, n)
    chrome = chrome_ngrams(frequency, n_articles, fraction)

    by_key = {
        (c.article, c.tstamp): c for caps in corpus.values() for c in caps
    }

    def clean_set(article: str, tstamp: str) -> frozenset[str]:
        return frozenset(strip_chrome(tokens(by_key[(article, tstamp)].text or ""), chrome, n))

    labelled = []
    rows = []
    for pair in pairs:
        a, b = clean_set(pair.article, pair.tstamp_a), clean_set(pair.article, pair.tstamp_b)
        sim = jaccard(a, b)
        labelled.append((pair.par_id, pair.label, sim))
        rows.append((pair, sim, len(a), len(b)))

    cleaned_words = {
        article: [frozenset(strip_chrome(words, chrome, n)) for words in caps]
        for article, caps in corpus_tokens.items()
    }
    consecutive = [
        jaccard(a, b) for caps in cleaned_words.values() for a, b in zip(caps, caps[1:])
    ]
    return {
        "n": n,
        "fraction": fraction,
        "n_articles": n_articles,
        "n_captures": sum(len(c) for c in corpus_tokens.values()),
        "chrome_size": len(chrome),
        "labelled": labelled,
        "rows": rows,
        "separation": separation(labelled),
        "errors": errors_by_threshold(labelled),
        "sensitivity": sensitivity_table(cleaned_words),
        "consecutive": consecutive,
        "empty_after": sum(1 for caps in cleaned_words.values() for w in caps if not w),
    }


def write_label_csv(result: dict, path: Path) -> None:
    fields = ("par_id", "faixa", "artigo", "tstamp_a", "tstamp_b", "rotulo_manual",
              "sim_com_chrome", "sim_sem_chrome", "n_palavras_a_sem_chrome",
              "n_palavras_b_sem_chrome")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for pair, sim, size_a, size_b in result["rows"]:
            writer.writerow({
                "par_id": pair.par_id, "faixa": pair.faixa, "artigo": pair.article,
                "tstamp_a": pair.tstamp_a, "tstamp_b": pair.tstamp_b,
                "rotulo_manual": pair.label,
                "sim_com_chrome": f"{pair.similarity_with_chrome:.6f}",
                "sim_sem_chrome": f"{sim:.6f}",
                "n_palavras_a_sem_chrome": size_a, "n_palavras_b_sem_chrome": size_b,
            })


def distribution_lines(
    corpus_tokens: dict[str, list[list[str]]], n: int
) -> list[str]:
    frequency = article_frequency(corpus_tokens, n)
    n_articles = len(corpus_tokens)
    lines = [
        f"## Distribuição das frequências dos {n}-gramas\n",
        f"Base: {sum(len(c) for c in corpus_tokens.values())} capturas da Camada 1 "
        f"de {n_articles} artigos com texto; frequência = nº de artigos distintos "
        f"em que o {n}-grama aparece. {len(frequency)} {n}-gramas distintos.\n",
        "| Artigos em que aparece | " + f"{n}-gramas distintos |",
        "| --- | ---: |",
        *(f"| {label} | {count} |" for label, count in frequency_buckets(frequency, n_articles)),
        "",
        "Efeito de cada fração de corte (chrome = presente em ≥ fração dos artigos "
        f"e em ≥ {MIN_ARTICLES} artigos):\n",
        "| Fração | Mín. artigos | n-gramas de chrome | Palavras removidas (todas as capturas) |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for row in cut_table(corpus_tokens, frequency, n):
        lines.append(
            f"| {_num(row.fraction, 2)} | {row.min_articles} | {row.chrome_ngrams} | "
            f"{_pct(row.tokens_removed_share)} |"
        )
    lines.append("")
    return lines


def write_summary(
    corpus: dict[str, list[Capture]],
    path: Path,
    n: int,
    result: dict | None,
    sensitivity_n: list[dict],
) -> None:
    corpus_tokens = layer1_tokens(corpus)
    lines = [
        "# Caminho D — variante (b): remoção do chrome\n",
        "Execução real, sem pedidos à API, sobre `output/corpus_articles.ttl` e "
        "`data/raw/texts/`. Não altera o grafo, o raw nem as saídas da variante (a). "
        "Chrome = n-gramas de palavras presentes numa fração alta dos artigos "
        "distintos (critério derivado do corpus).\n",
        *distribution_lines(corpus_tokens, n),
    ]
    if result is None:
        lines.append(
            "**Fração de corte ainda não escolhida**: só a distribuição foi gerada "
            "(`--so-distribuicao`); a avaliação contra os rótulos não foi corrida.\n"
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    sep = result["separation"]
    stats = describe(result["consecutive"])
    lines += [
        f"## Avaliação com n = {n} e fração = {_num(result['fraction'], 2)}\n",
        f"- n-gramas de chrome: {result['chrome_size']}",
        f"- Capturas da Camada 1 que ficam sem nenhuma palavra: {result['empty_after']} "
        f"(de {result['n_captures']}; Jaccard de dois conjuntos vazios = 1)",
        "",
        "### Pares consecutivos da Camada 1, texto sem chrome\n",
        "| n | mín. | p10 | mediana | p90 | máx. |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {stats['n']} | {_num(stats['min'])} | {_num(stats['p10'])} | "
        f"{_num(stats['mediana'])} | {_num(stats['p90'])} | {_num(stats['max'])} |",
        "",
        "### Sensibilidade ao limiar (Camada 1, texto sem chrome)\n",
        "| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | "
        "Versões (último rep.) | Divergências |",
        "| ---: | ---: | ---: | ---: | ---: |",
        *(f"| {_num(s.threshold)} | {s.redundant_last_rep} | {s.redundant_consecutive} | "
          f"{s.versions_last_rep} | {s.disagreements} |" for s in result["sensitivity"]),
        "",
        "### Os 60 pares rotulados, texto sem chrome\n",
        "| Limiar | \"mesma versão\" abaixo do limiar (de 58) | "
        "\"texto alterado\" acima do limiar (de 2) |",
        "| ---: | ---: | ---: |",
        *(f"| {_num(t, 2)} | {below} | {above} |" for t, below, above in result["errors"]),
        "",
        f"- Mínimo \"mesma versão\": {_num(sep.min_same)}; máximo \"texto alterado\": "
        f"{_num(sep.max_changed)}.",
        f"- Separação limpa: **{'sim' if sep.clean else 'não'}**.",
    ]
    if not sep.clean:
        lines.append(f"- Pares ambíguos ({len(sep.ambiguous)}):")
        lines += [f"  - par {pid} ({label}): {_num(s)}" for pid, label, s in sep.ambiguous]
    lines += [
        "",
        "Detalhe por par em `output/corpus_chrome_label_eval.csv`.\n",
        "### Sensibilidade a n (mesma fração)\n",
        "| n | n-gramas de chrome | mín. \"mesma versão\" | máx. \"texto alterado\" | "
        "separação limpa |",
        "| ---: | ---: | ---: | ---: | --- |",
        *(f"| {r['n']} | {r['chrome_size']} | {_num(r['separation'].min_same)} | "
          f"{_num(r['separation'].max_changed)} | "
          f"{'sim' if r['separation'].clean else 'não'} |" for r in sensitivity_n),
        "",
        "Estes valores são o resultado real desta execução, não uma estimativa.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    project_root: Path | None = None,
    n: int = DEFAULT_N,
    fraction: float | None = None,
) -> dict | None:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    corpus = load_corpus(output / "corpus_articles.ttl", root)
    summary = output / "corpus_chrome_summary.md"
    if fraction is None:
        write_summary(corpus, summary, n, None, [])
        return None

    pairs = load_labelled_pairs(output / "corpus_redundancy_label_sample.csv")
    result = evaluate(corpus, pairs, n, fraction)
    sensitivity_n = [
        result if other == n else evaluate(corpus, pairs, other, fraction)
        for other in SENSITIVITY_N
    ]
    write_label_csv(result, output / "corpus_chrome_label_eval.csv")
    write_summary(corpus, summary, n, result, sensitivity_n)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.corpus_chrome",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="tamanho dos n-gramas")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fracao", type=float, help="fração de artigos para um n-grama ser chrome")
    group.add_argument("--so-distribuicao", action="store_true",
                       help="só gera a distribuição das frequências, sem avaliar")
    args = parser.parse_args(argv)
    if args.fracao is not None and not 0.0 < args.fracao <= 1.0:
        parser.error("--fracao tem de estar em ]0, 1]")

    result = run(n=args.n, fraction=args.fracao)
    print("Resumo: output/corpus_chrome_summary.md")
    if result is not None:
        sep = result["separation"]
        print(f"Separação limpa nos 60 pares: {'sim' if sep.clean else 'não'} "
              f"(mín. mesma versão {sep.min_same:.3f}, máx. texto alterado "
              f"{sep.max_changed:.3f})")
        print("Detalhe: output/corpus_chrome_label_eval.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
