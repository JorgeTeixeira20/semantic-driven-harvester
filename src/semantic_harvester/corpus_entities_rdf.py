"""Caminho B em RDF: temas, entidades mencionadas e menções.

Lê `output/corpus_entities.csv` (variante c′) e o vocabulário
`data/processed/caminho_b_vocabulario_wikidata.csv`, e escreve
`output/corpus_entities.ttl`, separado de `output/corpus_articles.ttl`, que
não é alterado (checksum verificado antes e depois). Sem pedidos à API.

Identidade dos nós (`docs/experiments.md`):

- `Artigo`: `rdf_mapper.article_uri(originalURL)`, o mesmo de `corpus_articles.ttl`.
- `EntidadeMencionada`: nó partilhado por entidade. Rótulo com um só QID no
  vocabulário (`homonimos == 1`) → URI da Wikidata
  `http://www.wikidata.org/entity/<QID>`; rótulo de homónimos (`homonimos > 1`)
  → `sdh:entity/<sha256(rotulo)>`, porque a deteção por vocabulário fechado
  não distingue qual das pessoas é mencionada.
- `Tema`: nó partilhado por (categoria, valor): `sdh:tema/<sha256(categoria|valor)>`.
- `Mencao`: um por par artigo–entidade: `sdh:mencao/<sha256(artigo|rotulo)>`.

O artigo liga-se à entidade em paralelo por `sdh:mencionaEntidade` (um salto)
e por `sdh:temMencao` → `sdh:Mencao` → `sdh:sobreEntidade` (com as métricas).
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, URIRef

from .corpus_redundancy_rdf import file_sha256
from .rdf_mapper import SDH, article_uri, stable_hash

WIKIDATA_ENTITY = "http://www.wikidata.org/entity/"


def load_vocabulary_identity(path: Path) -> dict[str, tuple[str, int]]:
    """rotulo → (QIDs separados por `|`, nº de homónimos)."""

    with path.open(encoding="utf-8", newline="") as handle:
        return {row["rotulo"]: (row["wikidata"], int(row["homonimos"]))
                for row in csv.DictReader(handle)}


def entity_uri(rotulo: str, vocabulary: dict[str, tuple[str, int]]) -> URIRef:
    if rotulo not in vocabulary:
        raise ValueError(f"Entidade {rotulo!r} ausente do vocabulário")
    qids, homonyms = vocabulary[rotulo]
    if homonyms == 1:
        return URIRef(WIKIDATA_ENTITY + qids)
    return SDH[f"entity/{stable_hash(rotulo)}"]


def tema_uri(categoria: str, valor: str) -> URIRef:
    return SDH[f"tema/{stable_hash(categoria + '|' + valor)}"]


def mencao_uri(artigo: str, rotulo: str) -> URIRef:
    return SDH[f"mencao/{stable_hash(artigo + '|' + rotulo)}"]


def build_graph(
    rows: list[dict[str, str]], vocabulary: dict[str, tuple[str, int]], articles_in_graph: set,
) -> tuple[Graph, Counter, list[str]]:
    graph = Graph()
    for prefix, namespace in (("sdh", SDH), ("rdfs", RDFS), ("xsd", XSD)):
        graph.bind(prefix, namespace)
    graph.bind("wd", WIKIDATA_ENTITY)
    stats: Counter = Counter()
    homonym_rows: list[str] = []

    for row in rows:
        article = article_uri(row["artigo"])
        if article not in articles_in_graph:
            raise ValueError(f"Artigo ausente de corpus_articles.ttl: {row['artigo']}")
        if row["origem"] == "url":
            tema = tema_uri(row["categoria"], row["rotulo"])
            graph.add((tema, RDF.type, SDH.Tema))
            graph.add((tema, SDH.categoriaTema, Literal(row["categoria"], datatype=XSD.string)))
            graph.add((tema, SDH.valorTema, Literal(row["rotulo"], datatype=XSD.string)))
            graph.add((tema, RDFS.label, Literal(f"{row['categoria']}: {row['rotulo']}")))
            graph.add((article, SDH.temTema, tema))
            stats["linhas_tema"] += 1
            continue

        entity = entity_uri(row["rotulo"], vocabulary)
        if vocabulary[row["rotulo"]][1] > 1:
            homonym_rows.append(f"{row['rotulo']} em {row['artigo']}")
        mencao = mencao_uri(row["artigo"], row["rotulo"])
        graph.add((entity, RDF.type, SDH.EntidadeMencionada))
        graph.add((entity, RDFS.label, Literal(row["rotulo"])))
        graph.add((article, SDH.mencionaEntidade, entity))
        graph.add((article, SDH.temMencao, mencao))
        graph.add((mencao, RDF.type, SDH.Mencao))
        graph.add((mencao, SDH.sobreEntidade, entity))
        for prop, column in ((SDH.capturasComMencao, "capturas_com_mencao"),
                             (SDH.capturasComTexto, "capturas_com_texto"),
                             (SDH.ocorrencias, "ocorrencias")):
            graph.add((mencao, prop, Literal(int(row[column]), datatype=XSD.nonNegativeInteger)))
        graph.add((mencao, SDH.persistente,
                   Literal(row["persistente"] == "True", datatype=XSD.boolean)))
        graph.add((mencao, SDH.clubeCoerente, Literal(row["clube_coerente"], datatype=XSD.string)))
        stats["linhas_mencao"] += 1

    stats["temas"] = len(set(graph.subjects(RDF.type, SDH.Tema)))
    entities = set(graph.subjects(RDF.type, SDH.EntidadeMencionada))
    stats["entidades"] = len(entities)
    stats["entidades_wikidata"] = sum(str(e).startswith(WIKIDATA_ENTITY) for e in entities)
    stats["entidades_fallback"] = stats["entidades"] - stats["entidades_wikidata"]
    stats["mencoes"] = len(set(graph.subjects(RDF.type, SDH.Mencao)))
    stats["triplos"] = len(graph)
    return graph, stats, homonym_rows


def run(project_root: Path | None = None) -> tuple[Graph, Counter, list[str]]:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    articles_ttl = output / "corpus_articles.ttl"
    before = file_sha256(articles_ttl)

    articles_in_graph = set(
        Graph().parse(articles_ttl, format="turtle").subjects(RDF.type, SDH.Artigo)
    )
    vocabulary = load_vocabulary_identity(root / "data" / "processed" / "caminho_b_vocabulario_wikidata.csv")
    with (output / "corpus_entities.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    graph, stats, homonym_rows = build_graph(rows, vocabulary, articles_in_graph)
    (output / "corpus_entities.ttl").write_text(graph.serialize(format="turtle").rstrip("\n") + "\n", encoding="utf-8")

    if file_sha256(articles_ttl) != before:
        raise RuntimeError("output/corpus_articles.ttl foi alterado durante a execução")
    homonym_labels = sorted(r for r, (_, n) in vocabulary.items() if n > 1)
    write_summary(stats, homonym_rows, homonym_labels, output / "corpus_entities_rdf_summary.md")
    return graph, stats, homonym_rows


def write_summary(stats: Counter, homonym_rows: list[str], homonym_labels: list[str], path: Path) -> None:
    lines = [
        "# Caminho B em RDF (`output/corpus_entities.ttl`)\n",
        "Gerado de `output/corpus_entities.csv` (variante c′) e do vocabulário da "
        "Wikidata, sem pedidos à API; `output/corpus_articles.ttl` não foi alterado "
        "(checksum igual antes e depois).\n",
        f"- Triplos: {stats['triplos']}",
        f"- Linhas de tema / de menção no CSV: {stats['linhas_tema']} / {stats['linhas_mencao']}",
        f"- Nós `Tema` (partilhados por categoria e valor): {stats['temas']}",
        f"- Nós `EntidadeMencionada`: {stats['entidades']} — {stats['entidades_wikidata']} com URI "
        f"da Wikidata, {stats['entidades_fallback']} com URI próprio (homónimos)",
        f"- Nós `Mencao`: {stats['mencoes']}",
        "",
        "## Exceção: rótulos homónimos\n",
        f"Rótulos do vocabulário com mais de um QID ({len(homonym_labels)}): "
        + ", ".join(homonym_labels) + ". Para eles não se atribui um QID, porque a "
        "deteção por vocabulário fechado não distingue qual das pessoas é mencionada; "
        "usa-se `sdh:entity/<sha256(rotulo)>`.",
        f"\nLinhas de menção com rótulo homónimo no CSV atual: {len(homonym_rows)}"
        + ("" if not homonym_rows else " — " + "; ".join(homonym_rows)),
        "\nEstes valores são o resultado real desta execução, não uma estimativa.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_entities_rdf",
                                     description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    _, stats, homonym_rows = run()
    print(f"Triplos: {stats['triplos']}; temas: {stats['temas']}; entidades: {stats['entidades']}; "
          f"menções: {stats['mencoes']}; linhas com homónimos: {len(homonym_rows)}")
    print("Saídas: output/corpus_entities.ttl, output/corpus_entities_rdf_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
