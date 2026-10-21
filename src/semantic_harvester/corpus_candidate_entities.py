"""Teste exploratório — candidatos a entidade fora do vocabulário fechado.

Implementa a proposta discutida (não em `experiments.md` antes desta sessão)
para avaliar, a baixo custo, se vale a pena perguntar à Wikidata por nomes
próprios que o vocabulário fechado do Caminho B (`corpus_entities.py`) não
cobre — sem implementar NER nem qualquer pedido à Wikidata. Não altera o
Caminho B, o grafo nem o raw.

Heurística (deliberadamente simples, não um modelo de NER):

1. O texto é partido em frases por pontuação final (`.`, `!`, `?`).
2. Um candidato é uma sequência de 2 ou mais palavras capitalizadas,
   podendo incluir no meio os conectores portugueses "de", "da", "do",
   "das", "dos" e "e" (para apanhar nomes como "Estádio da Pedreira"),
   desde que a sequência **não comece na primeira palavra da frase** — é
   assim que se evita contar a capitalização normal de início de frase
   como candidato.
3. Candidatos cuja forma normalizada (igual à usada em `corpus_entities.py`:
   NFC, minúsculas, sem acentos, limites de palavra) corresponde a uma
   variante já presente no vocabulário fechado indicado são descartados —
   só interessam os que o vocabulário atual não encontraria.

Agrega por artigo (Camada 1, corpo do artigo por omissão, variante c′) e
reporta, por candidato: em quantos artigos distintos aparece, quantas
ocorrências no total e um `originalURL` de exemplo para inspeção manual.
Não decide se um candidato é uma entidade real; isso é trabalho de
inspeção manual de uma amostra, fora deste script.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from .corpus_entities import load_vocabulary, match_tokens
from .corpus_redundancy import Capture, load_corpus, to_body_corpus

CONNECTORS = frozenset({"de", "da", "do", "das", "dos", "e"})
CSV_FIELDS = ("candidato", "artigos", "ocorrencias", "exemplo_artigo")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_SPLIT_RE = re.compile(r"[,;:()\"'«»]+")
_TOKEN_RE = re.compile(r"\w+")


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _is_capitalized(word: str) -> bool:
    return word[:1].isupper()


def _run_candidates(words: list[str], start: int) -> list[str]:
    candidates = []
    n = len(words)
    i = start
    while i < n:
        if not _is_capitalized(words[i]):
            i += 1
            continue
        run = [words[i]]
        k = i + 1
        while k < n:
            word = words[k]
            if _is_capitalized(word):
                run.append(word)
                k += 1
            elif word.lower() in CONNECTORS and k + 1 < n and _is_capitalized(words[k + 1]):
                run.append(word)
                k += 1
            else:
                break
        if sum(1 for w in run if _is_capitalized(w)) >= 2:
            candidates.append(" ".join(run))
        i = k if k > i else i + 1
    return candidates


def capitalized_candidates(text: str) -> list[str]:
    """Sequências de 2+ palavras capitalizadas, com conectores pt no meio,
    que não começam na primeira palavra da frase.

    Cada frase (delimitada por `.`, `!`, `?`) é ainda partida em cláusulas
    por vírgula/ponto e vírgula/parênteses/aspas, para que duas sequências
    separadas por uma vírgula (ex. "no Estádio da Luz, Bruno Fernandes
    marcou") não sejam fundidas num só candidato — a tokenização por
    palavra (`\\w+`) por si só descartaria essa vírgula. A exclusão do
    início só se aplica à primeira cláusula de cada frase: uma cláusula
    depois de uma vírgula pode começar com um candidato legítimo.
    """

    candidates = []
    for sentence in sentences(text):
        for clause_index, clause in enumerate(_CLAUSE_SPLIT_RE.split(sentence)):
            words = _TOKEN_RE.findall(clause)
            start = 1 if clause_index == 0 else 0
            candidates.extend(_run_candidates(words, start))
    return candidates


def is_known(candidate: tuple[str, ...], variants: frozenset[tuple[str, ...]]) -> bool:
    """O candidato (já normalizado) corresponde a, ou contém, uma variante do vocabulário?"""

    n = len(candidate)
    return any(
        candidate[start:start + len(variant)] == variant
        for variant in variants
        for start in range(n - len(variant) + 1)
    )


def unseen_candidates(
    corpus: dict[str, list[Capture]], variants: frozenset[tuple[str, ...]]
) -> list[dict[str, str]]:
    occurrences: Counter[tuple[str, ...]] = Counter()
    articles: dict[tuple[str, ...], set[str]] = defaultdict(set)
    forms: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    example: dict[tuple[str, ...], str] = {}

    for article, captures in corpus.items():
        for capture in captures:
            if not capture.in_layer1:
                continue
            for candidate in capitalized_candidates(capture.text or ""):
                key = tuple(match_tokens(candidate))
                if len(key) < 2 or is_known(key, variants):
                    continue
                occurrences[key] += 1
                articles[key].add(article)
                forms[key][candidate] += 1
                example.setdefault(key, article)

    rows = [
        {
            "candidato": forms[key].most_common(1)[0][0],
            "artigos": str(len(articles[key])),
            "ocorrencias": str(occurrences[key]),
            "exemplo_artigo": example[key],
        }
        for key in occurrences
    ]
    rows.sort(key=lambda r: (-int(r["artigos"]), -int(r["ocorrencias"]), r["candidato"]))
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    rows: list[dict[str, str]], n_articles: int, vocabulary_path: Path, use_body: bool, path: Path
) -> None:
    text_kind = (
        "só o corpo do artigo (variante c′)" if use_body else "texto completo, sem remoção de chrome"
    )
    lines = [
        "# Candidatos a entidade fora do vocabulário fechado (teste exploratório)\n",
        "Heurística (sequências de palavras capitalizadas fora do início de frase), "
        "não NER; descarta candidatos já cobertos pelo vocabulário fechado indicado. "
        "Não avalia se os candidatos são entidades reais — isso é inspeção manual de "
        f"uma amostra, fora deste script. Vocabulário: `{vocabulary_path}`. Texto "
        f"pesquisado: {text_kind}.\n",
        f"- Artigos no corpus: {n_articles}",
        f"- Candidatos distintos fora do vocabulário: {len(rows)}",
        "",
        "| Candidato | Artigos | Ocorrências | Exemplo de artigo |",
        "| --- | ---: | ---: | --- |",
    ]
    lines += [
        f"| {r['candidato']} | {r['artigos']} | {r['ocorrencias']} | {r['exemplo_artigo']} |"
        for r in rows
    ]
    lines.append(
        "\nDetalhe em `output/corpus_candidate_entities.csv`. Lista descritiva desta "
        "amostra, não uma avaliação de precisão nem uma proposta de pipeline."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    project_root: Path | None = None,
    vocabulary_path: Path | None = None,
    use_body: bool = True,
) -> list[dict[str, str]]:
    root = project_root or Path(__file__).resolve().parents[2]
    if vocabulary_path is None:
        raise ValueError("É preciso indicar o vocabulário fechado (--vocabulario).")
    output = root / "output"
    corpus = load_corpus(output / "corpus_articles.ttl", root)
    terms = load_vocabulary(vocabulary_path)
    variants = frozenset(variant for term in terms for variant in term.variants)
    if use_body:
        corpus = to_body_corpus(corpus)

    rows = unseen_candidates(corpus, variants)
    write_csv(rows, output / "corpus_candidate_entities.csv")
    write_summary(rows, len(corpus), vocabulary_path, use_body,
                  output / "corpus_candidate_entities_summary.md")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.corpus_candidate_entities",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument("--vocabulario", type=Path, required=True,
                        help="CSV do vocabulário fechado de entidades (Caminho B)")
    parser.add_argument("--texto", choices=("corpo", "completo"), default="corpo",
                        help="corpo do artigo (variante c′, por omissão) ou texto completo")
    args = parser.parse_args(argv)

    rows = run(vocabulary_path=args.vocabulario, use_body=args.texto == "corpo")
    print(f"Candidatos distintos fora do vocabulário: {len(rows)}")
    print("Saídas: output/corpus_candidate_entities.csv, "
          "output/corpus_candidate_entities_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
