"""Corpus `completo` = `por_ano` + `xl`, sem duplicados (extensão a 2010–2016).

Junta, sem rede e sem alterar nenhum ficheiro dos dois corpora de origem, os
artefactos que os Caminhos B e o painel leem por etiqueta:

- `data/processed/corpus_articles_completo_triples.nt`: os N-Triples dos dois;
- `output/corpus_phase1_completo_captures.csv`: os CSV de capturas dos dois (o
  painel usa-o para a modalidade pelo termo de pesquisa);
- `output/corpus_classification_completo.csv`: a classificação dos dois.

Um artigo que está nos dois (mesma `canonical_key`, isto é, o mesmo
`interior.aspx?content_id=N` em `record.pt` e em `record.xl.pt`) fica **uma
vez**, com o grafo da captura mais antiga; em caso de empate fica o do
`por_ano`. Os triplos do outro são retirados pelo hash do seu `originalURL`
canónico, que aparece em todos os URIs do artigo (`article/`, `resource-web/`,
`capture/` e `extracted-text/`).
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from .corpus_classification import ClassificationResult, canonical_key, write_csv
from .corpus_rdf import rdf_paths
from .rdf_mapper import stable_hash

SOURCES = ("por_ano", "xl")
OUT_LABEL = "completo"

HASH = re.compile(r"/([0-9a-f]{64})[/>]")
CAPTURE = re.compile(r"capture/([0-9a-f]{64})/(\d{14})>")

csv.field_size_limit(1 << 30)


def load_classification(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def oldest_tstamps(triples: Path, hashes: set[str]) -> dict[str, str]:
    """Menor `tstamp` de captura de cada hash pedido, lendo o N-Triples uma vez."""

    oldest: dict[str, str] = {}
    if not hashes or not triples.is_file():
        return oldest
    with triples.open(encoding="utf-8") as handle:
        for line in handle:
            if "/capture/" not in line and ":capture/" not in line:
                continue
            for article_hash, tstamp in CAPTURE.findall(line):
                if article_hash in hashes and (
                    article_hash not in oldest or tstamp < oldest[article_hash]
                ):
                    oldest[article_hash] = tstamp
    return oldest


def resolve_overlap(
    keys: dict[str, dict[str, str]],
    tstamps: dict[str, dict[str, str]],
) -> tuple[dict[str, set[str]], Counter]:
    """Para cada artigo nos dois corpora, escolhe a origem da captura mais antiga.

    `keys`: origem → {chave → hash do `originalURL` canónico} dos Artigos;
    `tstamps`: origem → {hash → menor tstamp no N-Triples}. Devolve os hashes
    a retirar por origem e o número de empates (mesmo tstamp ou nenhum dos dois com captura).
    """

    first, second = SOURCES
    drop: dict[str, set[str]] = {first: set(), second: set()}
    tally: Counter = Counter()
    for key in set(keys[first]) & set(keys[second]):
        hash_first, hash_second = keys[first][key], keys[second][key]
        ts_first = tstamps[first].get(hash_first)
        ts_second = tstamps[second].get(hash_second)
        # Sem captura num dos grafos (erro de mapeamento): fica o que tem grafo.
        if ts_first is None and ts_second is None:
            winner = first
        elif ts_second is None:
            winner = first
        elif ts_first is None:
            winner = second
        elif ts_second < ts_first:
            winner = second
        else:
            winner = first
        loser = second if winner == first else first
        drop[loser].add(keys[loser][key])
        if ts_first == ts_second:
            tally["empate"] += 1
    return drop, tally


def copy_triples(source: Path, target_handle, drop: set[str]) -> tuple[int, int]:
    """Acrescenta o N-Triples sem as linhas dos artigos retirados; devolve (escritas, retiradas)."""

    written = removed = 0
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if drop and any(token in drop for token in HASH.findall(line)):
                removed += 1
                continue
            target_handle.write(line)
            written += 1
    return written, removed


def concat_csv(sources: Iterable[Path], target: Path) -> int:
    rows = 0
    header: list[str] | None = None
    with target.open("w", encoding="utf-8", newline="") as out:
        writer = None
        for path in sources:
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                first = next(reader)
                if header is None:
                    header = first
                    writer = csv.writer(out, lineterminator="\n")
                    writer.writerow(header)
                elif first != header:
                    raise ValueError(f"Cabeçalho diferente em {path}")
                for row in reader:
                    writer.writerow(row)
                    rows += 1
    return rows


def build(root: Path) -> dict[str, int]:
    paths = {label: rdf_paths(root, label) for label in SOURCES}
    out = rdf_paths(root, OUT_LABEL)

    classification = {label: load_classification(paths[label]["classification"]) for label in SOURCES}
    keys: dict[str, dict[str, str]] = {}
    for label in SOURCES:
        keys[label] = {
            canonical_key(row["original_url"]): stable_hash(row["original_url"])
            for row in classification[label] if row["is_artigo"] == "True"
        }
    overlap = set(keys[SOURCES[0]]) & set(keys[SOURCES[1]])
    tstamps = {
        label: oldest_tstamps(paths[label]["triples"], {keys[label][k] for k in overlap})
        for label in SOURCES
    }
    drop, tally = resolve_overlap(keys, tstamps)

    out["triples"].parent.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {"sobreposicao": len(overlap)}
    with out["triples"].open("w", encoding="utf-8") as handle:
        for label in SOURCES:
            written, removed = copy_triples(paths[label]["triples"], handle, drop[label])
            stats[f"triplos_{label}"] = written
            stats[f"triplos_retirados_{label}"] = removed
    stats["fica_por_ano"] = len(drop["xl"])
    stats["fica_xl"] = len(drop["por_ano"])
    stats["empates"] = tally["empate"]

    # Classificação: primeiro os Artigos dos dois (sem os que perderam a sobreposição),
    # depois as outras linhas cuja chave ainda não aparece.
    seen: set[str] = set()
    merged: list[ClassificationResult] = []
    for want_artigo in (True, False):
        for label in SOURCES:
            for row in classification[label]:
                is_artigo = row["is_artigo"] == "True"
                if is_artigo != want_artigo:
                    continue
                key = canonical_key(row["original_url"])
                if key in seen or (is_artigo and stable_hash(row["original_url"]) in drop[label]):
                    continue
                seen.add(key)
                merged.append(ClassificationResult(
                    original_url=row["original_url"], title=row["title"],
                    captures=int(row["captures"]), is_artigo=is_artigo,
                    reason=row["reason"], variantes=row["variantes"],
                ))
    merged.sort(key=lambda result: result.original_url)
    write_csv(merged, out["classification"])
    stats["artigos"] = sum(1 for r in merged if r.is_artigo)

    stats["linhas_captures"] = concat_csv(
        [root / "output" / f"corpus_phase1_{label}_captures.csv" for label in SOURCES],
        root / "output" / f"corpus_phase1_{OUT_LABEL}_captures.csv",
    )
    return stats


def write_summary(stats: dict[str, int], path: Path) -> None:
    lines = [
        "# Corpus `completo` = `por_ano` + `xl`\n",
        f"- Artigos em `completo`: {stats['artigos']}",
        f"- Artigos nos dois corpora: {stats['sobreposicao']} "
        f"(ficam com a captura mais antiga: {stats['fica_xl']} do `xl`, "
        f"{stats['fica_por_ano']} do `por_ano`, {stats['empates']} empates)",
        f"- Triplos do `por_ano`: {stats['triplos_por_ano']} (retirados {stats['triplos_retirados_por_ano']})",
        f"- Triplos do `xl`: {stats['triplos_xl']} (retirados {stats['triplos_retirados_xl']})",
        f"- Linhas de capturas (Fase 1): {stats['linhas_captures']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_completo")
    parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    stats = build(root)
    write_summary(stats, root / "output" / "corpus_completo_summary.md")
    for name, value in stats.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
