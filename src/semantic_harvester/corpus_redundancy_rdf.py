"""Caminho D em RDF: `sdh:versaoDe` e `sdh:similaridade` para as capturas redundantes.

Lê `output/corpus_redundancy.csv` (variante c′, limiar 0,90) e escreve
`output/corpus_redundancy.ttl`, separado de `output/corpus_articles.ttl`, que
não é alterado (checksum verificado antes e depois). Sem pedidos à API.

Só a Camada 1 (capturas com corpo e `statusCode` 200) recebe triplos, e só as
capturas **redundantes**: `versaoDe` aponta para a representante e
`similaridade` é a Jaccard do corpo face a ela. A representante não recebe
triplos (não tem nada anterior para apontar). As capturas `sem_corpo` e a
Camada 2 (sem texto) não recebem nenhum triplo: não têm comparação nem
representante calculados; `sdh:digest`/`sdh:contentLength`, já no grafo,
permitem reconstituir a Camada 2 por SPARQL. Os URIs das capturas são os de
`rdf_mapper.capture_uri`, os mesmos de `corpus_articles.ttl`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal

from .corpus_redundancy import LABEL_REDUNDANT, LAYER_TEXT
from .rdf_mapper import SDH, capture_uri

EXPECTED_THRESHOLD = "0.9"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_graph(rows: list[dict[str, str]], captures_in_graph: set) -> tuple[Graph, Counter]:
    graph = Graph()
    graph.bind("sdh", SDH)
    graph.bind("xsd", XSD)
    stats: Counter = Counter()
    for row in rows:
        stats[f"camada:{row['camada']}"] += 1
        if row["camada"] != LAYER_TEXT:
            continue
        if row["limiar"] != EXPECTED_THRESHOLD:
            raise ValueError(f"Camada 1 com limiar {row['limiar']!r}, esperado {EXPECTED_THRESHOLD}")
        if row["rotulo"] != LABEL_REDUNDANT:
            stats["representantes_sem_triplos"] += 1
            continue
        capture = capture_uri(row["artigo"], row["tstamp"])
        representative = capture_uri(row["artigo"], row["representante"])
        for node in (capture, representative):
            if node not in captures_in_graph:
                raise ValueError(f"Captura ausente de corpus_articles.ttl: {node}")
        graph.add((capture, SDH.versaoDe, representative))
        graph.add((capture, SDH.similaridade, Literal(float(row["similaridade"]), datatype=XSD.float)))
        stats["redundantes_com_triplos"] += 1
    return graph, stats


def run(project_root: Path | None = None) -> tuple[Graph, Counter]:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    articles_ttl = output / "corpus_articles.ttl"
    before = file_sha256(articles_ttl)

    captures_in_graph = set(
        Graph().parse(articles_ttl, format="turtle").subjects(RDF.type, SDH.CapturaArquivada)
    )
    with (output / "corpus_redundancy.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    graph, stats = build_graph(rows, captures_in_graph)
    graph.serialize(destination=output / "corpus_redundancy.ttl", format="turtle")
    stats["triplos"] = len(graph)

    if file_sha256(articles_ttl) != before:
        raise RuntimeError("output/corpus_articles.ttl foi alterado durante a execução")
    write_summary(stats, output / "corpus_redundancy_rdf_summary.md")
    return graph, stats


def write_summary(stats: Counter, path: Path) -> None:
    lines = [
        "# Caminho D em RDF (`output/corpus_redundancy.ttl`)\n",
        "Gerado de `output/corpus_redundancy.csv` (variante c′, limiar 0,90), sem pedidos "
        "à API; `output/corpus_articles.ttl` não foi alterado (checksum igual antes e "
        "depois).\n",
        f"- Triplos: {stats['triplos']}",
        f"- Capturas redundantes com `sdh:versaoDe` + `sdh:similaridade`: "
        f"{stats['redundantes_com_triplos']}",
        f"- Representantes da Camada 1 (sem triplos novos): {stats['representantes_sem_triplos']}",
        "",
        "| Camada no CSV | Capturas | Triplos novos |",
        "| --- | ---: | --- |",
    ]
    for key, count in sorted(stats.items()):
        if key.startswith("camada:"):
            layer = key.split(":", 1)[1]
            lines.append(f"| {layer} | {count} | {'só as redundantes' if layer == LAYER_TEXT else 'nenhum'} |")
    lines.append("\nEstes valores são o resultado real desta execução, não uma estimativa.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_redundancy_rdf",
                                     description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    _, stats = run()
    print(f"Triplos: {stats['triplos']}; capturas redundantes: {stats['redundantes_com_triplos']}")
    print("Saídas: output/corpus_redundancy.ttl, output/corpus_redundancy_rdf_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
