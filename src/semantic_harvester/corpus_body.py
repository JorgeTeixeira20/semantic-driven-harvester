"""Variante (c′) — avaliação do corpo do artigo contra D e B.

A delimitação do corpo está em `article_body.py` (adotada nos Caminhos D e B,
`docs/experiments.md`). Este módulo compara-a com as variantes anteriores:
os 60 pares rotulados do Caminho D (pares com captura "sem corpo" à parte)
e os pares artigo–jogador do Caminho B face à configuração sem chrome
persistente. Não altera as saídas oficiais de D nem de B.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .article_body import MARKERS, NO_BODY, Body, extract_body  # noqa: F401 (reexportados)
from .corpus_chrome import errors_by_threshold, load_labelled_pairs, separation
from .corpus_entities import (
    DEFAULT_CHROME_FRACTION, analyse_article, build_chrome, load_vocabulary,
)
from .corpus_redundancy import (
    Capture, describe, jaccard, load_corpus, sensitivity_table, word_set,
)

# --- Avaliação contra o Caminho D --------------------------------------------


def body_corpus(corpus: dict[str, list[Capture]]) -> dict[tuple[str, str], Body]:
    return {(c.article, c.tstamp): extract_body(c.text) for caps in corpus.values()
            for c in caps if c.in_layer1}


def label_rows(pairs, bodies) -> list[dict]:
    rows = []
    for pair in pairs:
        a, b = bodies[(pair.article, pair.tstamp_a)], bodies[(pair.article, pair.tstamp_b)]
        sim = jaccard(word_set(a.text), word_set(b.text)) if a.found and b.found else None
        rows.append({"pair": pair, "a": a, "b": b, "sim": sim})
    return rows


def layer1_body_words(corpus, bodies) -> dict[str, list[frozenset[str]]]:
    """Só capturas com corpo: as "sem corpo" ficam fora da comparação."""

    result = {}
    for article, caps in corpus.items():
        words = [word_set(bodies[(c.article, c.tstamp)].text) for c in caps
                 if c.in_layer1 and bodies[(c.article, c.tstamp)].found]
        if words:
            result[article] = words
    return result


# --- Avaliação contra o Caminho B --------------------------------------------


def body_captures(captures: list[Capture], bodies) -> list[Capture]:
    """Texto substituído pelo corpo; "sem corpo" deixa de ter texto (não conta)."""

    out = []
    for c in captures:
        if not c.in_layer1:
            out.append(c)
            continue
        body = bodies[(c.article, c.tstamp)]
        out.append(replace(c, text=body.text if body.found else None))
    return out


def entity_pairs(corpus, terms, bodies=None, chrome=None) -> list[dict[str, str]]:
    rows = []
    for article, caps in corpus.items():
        caps = body_captures(caps, bodies) if bodies is not None else caps
        # Avaliação histórica da c′: contagem anterior a 2026-10-22 (e às regras
        # dos nomes de 2026-10-23), para os números publicados continuarem reproduzíveis.
        rows += [r for r in analyse_article(article, caps, terms, chrome, longest_match=False,
                                            name_rules=False)
                 if r["origem"] == "texto"]
    return rows


# --- Saídas ------------------------------------------------------------------


def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}".replace(".", ",")


def run(project_root: Path | None = None, vocabulary: Path | None = None) -> dict:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    corpus = load_corpus(output / "corpus_articles.ttl", root)
    bodies = body_corpus(corpus)
    pairs = load_labelled_pairs(output / "corpus_redundancy_label_sample.csv")
    rows = label_rows(pairs, bodies)

    with (output / "corpus_body_label_eval.csv").open("w", encoding="utf-8", newline="") as h:
        writer = csv.writer(h, lineterminator="\n")
        writer.writerow(["par_id", "faixa", "rotulo_manual", "sim_com_chrome", "sim_corpo",
                         "corpo_a", "corpo_b", "palavras_corpo_a", "palavras_corpo_b"])
        for r in rows:
            p = r["pair"]
            writer.writerow([p.par_id, p.faixa, p.label, f"{p.similarity_with_chrome:.6f}",
                             "" if r["sim"] is None else f"{r['sim']:.6f}",
                             "sim" if r["a"].found else NO_BODY, "sim" if r["b"].found else NO_BODY,
                             len(word_set(r["a"].text)), len(word_set(r["b"].text))])

    comparable = [(r["pair"].par_id, r["pair"].label, r["sim"]) for r in rows if r["sim"] is not None]
    no_body = [r for r in rows if r["sim"] is None]
    sep = separation(comparable)
    errors = errors_by_threshold(comparable)
    words = layer1_body_words(corpus, bodies)
    consecutive = [jaccard(a, b) for caps in words.values() for a, b in zip(caps, caps[1:])]
    sensitivity = sensitivity_table(words)
    status = Counter("corpo" if b.found else NO_BODY for b in bodies.values())
    end_markers = Counter(b.end_marker or "(fim do texto)" for b in bodies.values() if b.found)

    result = {"rows": rows, "separation": sep, "errors": errors, "no_body": no_body,
              "status": status, "end_markers": end_markers, "consecutive": consecutive,
              "sensitivity": sensitivity}
    if vocabulary is not None:
        terms = load_vocabulary(vocabulary)
        # "Antes" = configuração fechada do Caminho B (sem o chrome persistente).
        result["b_before"] = entity_pairs(corpus, terms,
                                          chrome=build_chrome(corpus, DEFAULT_CHROME_FRACTION))
        result["b_after"] = entity_pairs(corpus, terms, bodies)
        with (output / "corpus_body_entities.csv").open("w", encoding="utf-8", newline="") as h:
            fields = ["artigo", "rotulo", "capturas_com_mencao", "capturas_com_texto",
                      "ocorrencias", "persistente", "uma_so_captura"]
            writer = csv.DictWriter(h, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(result["b_after"])
    write_summary(result, output / "corpus_body_summary.md")
    return result


def b_stats(rows: list[dict[str, str]]) -> dict[str, int]:
    strong = [r for r in rows if r["persistente"] == "True"]
    return {"fraca": len(rows), "persistencia": len(strong),
            "artigos_fraca": len({r["artigo"] for r in rows}),
            "artigos_persistencia": len({r["artigo"] for r in strong}),
            "jogadores_persistencia": len({r["rotulo"] for r in strong})}


def write_summary(result: dict, path: Path) -> None:
    sep, stats = result["separation"], describe(result["consecutive"])
    lines = [
        "# Variante (c′): corpo do artigo por âncoras literais\n",
        "Sem pedidos à API; não altera o grafo, o raw nem as saídas fechadas de D e B.\n",
        "## Delimitação do corpo nas capturas da Camada 1\n",
        "| Resultado | Capturas |", "| --- | ---: |",
        *(f"| {k} | {v} |" for k, v in result["status"].most_common()),
        "", "| Marcador que fechou o corpo | Capturas |", "| --- | ---: |",
        *(f"| {k} | {v} |" for k, v in result["end_markers"].most_common()),
        "", "## Caminho D: pares consecutivos da Camada 1 com corpo\n",
        "| n | mín. | p10 | mediana | p90 | máx. |", "| ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {stats['n']} | {_num(stats['min'])} | {_num(stats['p10'])} | {_num(stats['mediana'])} | "
        f"{_num(stats['p90'])} | {_num(stats['max'])} |",
        "", "| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | Versões (último rep.) |",
        "| ---: | ---: | ---: | ---: |",
        *(f"| {_num(s.threshold)} | {s.redundant_last_rep} | {s.redundant_consecutive} | "
          f"{s.versions_last_rep} |" for s in result["sensitivity"]),
        "", "## Caminho D: os 60 pares rotulados\n",
        f"Pares com alguma captura sem corpo (tratados à parte): {len(result['no_body'])} — "
        + ", ".join(f"par {r['pair'].par_id} ({r['pair'].label})" for r in result["no_body"]),
        "", f"Pares comparáveis: {sum(1 for r in result['rows'] if r['sim'] is not None)}.\n",
        "| Limiar | \"mesma versão\" abaixo do limiar | \"texto alterado\" acima do limiar |",
        "| ---: | ---: | ---: |",
        *(f"| {_num(t)} | {below} | {above} |" for t, below, above in result["errors"]),
        "",
        f"- Mínimo \"mesma versão\": {_num(sep.min_same)}; máximo \"texto alterado\": "
        f"{_num(sep.max_changed)}.",
        f"- Separação limpa: **{'sim' if sep.clean else 'não'}**.",
    ]
    if not sep.clean:
        lines.append(f"- Pares ambíguos ({len(sep.ambiguous)}): "
                     + ", ".join(f"par {pid} ({label}, {_num(s)})" for pid, label, s in sep.ambiguous))
    if "b_after" in result:
        before, after = b_stats(result["b_before"]), b_stats(result["b_after"])
        lines += ["", "## Caminho B: pares artigo–jogador, texto completo vs. corpo\n",
                  "| Medida | B fechado (sem chrome persistente) | Corpo (c′) |",
                  "| --- | ---: | ---: |",
                  *(f"| {k} | {before[k]} | {after[k]} |" for k in before)]
    lines.append("\nEstes valores são o resultado real desta execução, não uma estimativa.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_body",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--vocabulario", type=Path, default=None,
                        help="vocabulário do Caminho B, para comparar os pares artigo–jogador")
    args = parser.parse_args(argv)
    result = run(vocabulary=args.vocabulario)
    sep = result["separation"]
    print(f"Capturas: {dict(result['status'])}")
    print(f"Separação limpa nos pares comparáveis: {'sim' if sep.clean else 'não'} "
          f"(mín. mesma versão {sep.min_same:.3f}, máx. texto alterado {sep.max_changed:.3f})")
    print("Resumo: output/corpus_body_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
