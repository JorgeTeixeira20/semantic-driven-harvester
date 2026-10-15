"""Título exato (Major Minors) vs. `digest` vs. redundância real por Jaccard.

Mede, sem pedidos à API, se dedupicar **antes de descarregar o texto** —
por título exato, como o "Major Minors" (Martins & Costa, Prémio Arquivo.pt
2021, ver `docs/PROJECT_STATUS.md`), ou por `digest`, já descartado em
`docs/experiments.md` por cobertura baixa (~81% dos grupos de texto
idêntico têm `digest` diferente) — teria chegado às mesmas decisões que o
Caminho D já tomou por Jaccard sobre o corpo do artigo (variante c′, limiar
0,90, `output/corpus_redundancy.csv`).

Os pares "realmente duplicados" e "realmente distintos" vêm do rótulo já
calculado pelo Caminho D (`redundante` vs. `representante`); nada é
recalculado aqui. O título e o `digest` por captura vêm do raw de
`version_history` já preservado pela Fase 2 (`data/raw/version_history/`,
lido com o mesmo código de produção do `corpus_rdf.py`). Não faz pedidos à
API e não altera nenhum output existente.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .corpus_rdf import load_article_captures, load_retained_articles, variants_of

LAYER_TEXT = "1_texto"
LABEL_REDUNDANT = "redundante"
LABEL_REPRESENTATIVE = "representante"

FIELD_TITLE = "title"
FIELD_DIGEST = "digest"


@dataclass
class Tally:
    """Contagem de uma estratégia de deduplicação contra o rótulo real (Jaccard)."""

    true_positive: int = 0  # valor igual, e são realmente duplicados
    false_negative: int = 0  # valor diferente, mas são duplicados (perda)
    true_negative: int = 0  # valor diferente, e são realmente distintos
    false_positive: int = 0  # valor igual, mas são distintos (fusão errada)
    sem_dado: int = 0  # valor em falta num dos dois lados do par

    def recall(self) -> float | None:
        total = self.true_positive + self.false_negative
        return self.true_positive / total if total else None

    def false_positive_rate(self) -> float | None:
        total = self.false_positive + self.true_negative
        return self.false_positive / total if total else None


def load_capture_fields(
    classification_csv: Path, version_history_dir: Path
) -> dict[str, dict[str, dict[str, str]]]:
    """Por artigo retido, `{tstamp: {"title": ..., "digest": ...}}` a partir do raw."""

    fields_by_article: dict[str, dict[str, dict[str, str]]] = {}
    for row in load_retained_articles(classification_csv):
        original_url = row["original_url"]
        captures, _ = load_article_captures(
            original_url, variants_of(row), version_history_dir
        )
        fields_by_article[original_url] = {
            str(capture.get("tstamp")): {
                FIELD_TITLE: str(capture.get("title") or ""),
                FIELD_DIGEST: str(capture.get("digest") or ""),
            }
            for capture in captures
        }
    return fields_by_article


def load_layer1_rows(redundancy_csv: Path) -> dict[str, list[dict[str, str]]]:
    """Linhas da Camada 1 (`1_texto`) de `corpus_redundancy.csv`, por artigo, em ordem temporal."""

    rows_by_article: dict[str, list[dict[str, str]]] = {}
    with redundancy_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["camada"] != LAYER_TEXT:
                continue
            rows_by_article.setdefault(row["artigo"], []).append(row)
    for rows in rows_by_article.values():
        rows.sort(key=lambda row: row["tstamp"])
    return rows_by_article


def build_pairs(
    rows_by_article: dict[str, list[dict[str, str]]]
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """(pares_duplicados, pares_distintos), cada par `(artigo, tstamp_a, tstamp_b)`.

    Duplicados: cada captura `redundante` com o seu `representante` (o par
    que o Caminho D já comparou por Jaccard). Distintos: representantes
    consecutivos do mesmo artigo — por construção, abaixo do limiar entre si.
    """

    duplicate_pairs: list[tuple[str, str, str]] = []
    distinct_pairs: list[tuple[str, str, str]] = []
    for article, rows in rows_by_article.items():
        representatives: list[str] = []
        for row in rows:
            if row["rotulo"] == LABEL_REDUNDANT:
                duplicate_pairs.append((article, row["tstamp"], row["representante"]))
            elif row["rotulo"] == LABEL_REPRESENTATIVE:
                representatives.append(row["tstamp"])
        for previous, current in zip(representatives, representatives[1:]):
            distinct_pairs.append((article, previous, current))
    return duplicate_pairs, distinct_pairs


def _value(
    fields_by_article: dict[str, dict[str, dict[str, str]]],
    article: str,
    tstamp: str,
    field: str,
) -> str:
    return fields_by_article.get(article, {}).get(tstamp, {}).get(field, "")


def evaluate(
    duplicate_pairs: list[tuple[str, str, str]],
    distinct_pairs: list[tuple[str, str, str]],
    fields_by_article: dict[str, dict[str, dict[str, str]]],
    field: str,
) -> Tally:
    tally = Tally()
    for article, tstamp_a, tstamp_b in duplicate_pairs:
        value_a = _value(fields_by_article, article, tstamp_a, field)
        value_b = _value(fields_by_article, article, tstamp_b, field)
        if not value_a or not value_b:
            tally.sem_dado += 1
        elif value_a == value_b:
            tally.true_positive += 1
        else:
            tally.false_negative += 1
    for article, tstamp_a, tstamp_b in distinct_pairs:
        value_a = _value(fields_by_article, article, tstamp_a, field)
        value_b = _value(fields_by_article, article, tstamp_b, field)
        if not value_a or not value_b:
            tally.sem_dado += 1
        elif value_a == value_b:
            tally.false_positive += 1
        else:
            tally.true_negative += 1
    return tally


def format_pct(value: float | None) -> str:
    return "indisponível" if value is None else f"{value:.1%}"


def write_summary_markdown(
    title_tally: Tally,
    digest_tally: Tally,
    duplicate_pairs: int,
    distinct_pairs: int,
    path: Path,
) -> None:
    lines = [
        "# Título exato vs. digest vs. redundância real (Caminho D)\n",
        'Compara, sem pedidos à API, se dedupicar **antes de descarregar o '
        'texto** — por título exato (como o "Major Minors", Martins & '
        "Costa, Prémio Arquivo.pt 2021) ou por `digest` — teria chegado às "
        "mesmas decisões que o Caminho D já tomou por Jaccard sobre o corpo "
        "(c′, limiar 0,90). Os pares vêm do rótulo já calculado em "
        "`output/corpus_redundancy.csv`; nada foi recalculado.\n",
        f"- Pares realmente duplicados (Camada 1): {duplicate_pairs}",
        f"- Pares realmente distintos, representantes consecutivos (Camada 1): {distinct_pairs}\n",
        "## Título exato\n",
        f"- Recall (duplicados reais que o título também apanha, logo "
        f"descartáveis sem descarregar): {format_pct(title_tally.recall())} "
        f"({title_tally.true_positive}/"
        f"{title_tally.true_positive + title_tally.false_negative})",
        f"- Falsos positivos (distintos que o título fundiria por engano): "
        f"{format_pct(title_tally.false_positive_rate())} "
        f"({title_tally.false_positive}/"
        f"{title_tally.false_positive + title_tally.true_negative})",
        f"- Pares sem título disponível num dos lados: {title_tally.sem_dado}\n",
        "## Digest (referência; cobertura baixa já reportada em docs/experiments.md)\n",
        f"- Recall: {format_pct(digest_tally.recall())} "
        f"({digest_tally.true_positive}/"
        f"{digest_tally.true_positive + digest_tally.false_negative})",
        f"- Falsos positivos: {format_pct(digest_tally.false_positive_rate())} "
        f"({digest_tally.false_positive}/"
        f"{digest_tally.false_positive + digest_tally.true_negative})",
        f"- Pares sem digest disponível num dos lados: {digest_tally.sem_dado}\n",
        "Estes números são o resultado real desta execução sobre o corpus "
        "atual, não uma estimativa.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(project_root: Path | None = None) -> tuple[Tally, Tally, int, int]:
    root = project_root or Path(__file__).resolve().parents[2]
    classification_csv = root / "output" / "corpus_classification.csv"
    redundancy_csv = root / "output" / "corpus_redundancy.csv"
    version_history_dir = root / "data" / "raw" / "version_history"

    fields_by_article = load_capture_fields(classification_csv, version_history_dir)
    rows_by_article = load_layer1_rows(redundancy_csv)
    duplicate_pairs, distinct_pairs = build_pairs(rows_by_article)

    title_tally = evaluate(duplicate_pairs, distinct_pairs, fields_by_article, FIELD_TITLE)
    digest_tally = evaluate(duplicate_pairs, distinct_pairs, fields_by_article, FIELD_DIGEST)

    write_summary_markdown(
        title_tally,
        digest_tally,
        len(duplicate_pairs),
        len(distinct_pairs),
        root / "output" / "corpus_dedup_strategy_check.md",
    )
    return title_tally, digest_tally, len(duplicate_pairs), len(distinct_pairs)


def main() -> int:
    title_tally, digest_tally, duplicate_pairs, distinct_pairs = run()
    print(f"Pares duplicados reais: {duplicate_pairs}; pares distintos: {distinct_pairs}")
    print(
        f"Título exato — recall: {format_pct(title_tally.recall())}, "
        f"falsos positivos: {format_pct(title_tally.false_positive_rate())}"
    )
    print(
        f"Digest — recall: {format_pct(digest_tally.recall())}, "
        f"falsos positivos: {format_pct(digest_tally.false_positive_rate())}"
    )
    print("Resumo: output/corpus_dedup_strategy_check.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
