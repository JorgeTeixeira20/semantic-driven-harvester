"""Mapeamento de uma captura real do M1 para um pequeno grafo RDF."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

SDH = Namespace("urn:semantic-driven-harvester:prototype:")

# Esta captura foi escolhida deliberadamente: o título, o URL /detalhe/ e o
# texto extraído identificam-na claramente como um artigo editorial.
SAMPLE_ORIGINAL_URL = (
    "https://www.record.pt/futebol/futebol-nacional/liga-nos/benfica/"
    "detalhe/yony-gonzalez-e-reforco-para-o-benfica"
)
SAMPLE_TSTAMP = "20191120040251"

CAPTURE_FIELDS: dict[str, tuple[URIRef, URIRef]] = {
    "title": (SDH.title, XSD.string),
    "linkToArchive": (SDH.archiveURL, XSD.anyURI),
    "mimeType": (SDH.mimeType, XSD.string),
    "contentLength": (SDH.contentLength, XSD.nonNegativeInteger),
    "digest": (SDH.digest, XSD.string),
    "encoding": (SDH.encoding, XSD.string),
    "collection": (SDH.collection, XSD.string),
    "snippet": (SDH.snippet, XSD.string),
}


def stable_hash(value: str) -> str:
    """Devolve um SHA-256 hexadecimal determinístico."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def resource_uri(original_url: str) -> URIRef:
    return SDH[f"resource-web/{stable_hash(original_url)}"]


def capture_uri(original_url: str, tstamp: str) -> URIRef:
    return SDH[f"capture/{stable_hash(original_url)}/{tstamp}"]


def extracted_text_uri(original_url: str, tstamp: str) -> URIRef:
    return SDH[f"extracted-text/{stable_hash(original_url)}/{tstamp}"]


def article_uri(original_url: str) -> URIRef:
    return SDH[f"article/{stable_hash(original_url)}"]


def tstamp_as_xsd_datetime(tstamp: str) -> Literal:
    """Converte YYYYMMDDhhmmss para um literal xsd:dateTime em UTC."""

    parsed = datetime.strptime(tstamp, "%Y%m%d%H%M%S")
    return Literal(parsed.strftime("%Y-%m-%dT%H:%M:%SZ"), datatype=XSD.dateTime)


def load_sample_result(searches_dir: Path) -> tuple[dict[str, Any], Path]:
    """Localiza a captura editorial escolhida nas respostas reais do M1."""

    for json_path in reversed(sorted(searches_dir.glob("*.json"))):
        payload = json.loads(json_path.read_bytes())
        for result in payload.get("response_items", []):
            if (
                result.get("originalURL") == SAMPLE_ORIGINAL_URL
                and result.get("tstamp") == SAMPLE_TSTAMP
            ):
                return result, json_path
    raise FileNotFoundError(
        f"Captura {SAMPLE_TSTAMP} não encontrada em {searches_dir}"
    )


def text_path_for_result(result: dict[str, Any], project_root: Path) -> Path:
    """Obtém o caminho determinístico usado no M1 para o texto da captura."""

    original_url = str(result["originalURL"])
    tstamp = str(result["tstamp"])
    url_hash = stable_hash(original_url)[:16]
    return project_root / "data" / "raw" / "texts" / f"{tstamp}_{url_hash}.txt"


def build_sample_graph(
    result: dict[str, Any], text_path: Path, project_root: Path
) -> Graph:
    """Cria o grafo do sample apenas com dados reais ou valores derivados."""

    original_url = str(result["originalURL"])
    tstamp = str(result["tstamp"])
    if original_url != SAMPLE_ORIGINAL_URL or tstamp != SAMPLE_TSTAMP:
        raise ValueError("O resultado não é a captura editorial escolhida para o sample")
    if not text_path.is_file():
        raise FileNotFoundError(f"Texto extraído não encontrado: {text_path}")

    graph = Graph()
    graph.bind("sdh", SDH)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)

    newspaper = SDH["newspaper/record"]
    web_resource = resource_uri(original_url)
    capture = capture_uri(original_url, tstamp)
    extracted_text = extracted_text_uri(original_url, tstamp)
    article = article_uri(original_url)

    graph.add((newspaper, RDF.type, SDH.Jornal))
    graph.add((newspaper, RDFS.label, Literal("Record", lang="pt")))

    graph.add((article, RDF.type, SDH.Artigo))
    graph.add((article, RDFS.label, Literal(str(result["title"]))))
    graph.add((article, SDH.publicadoPor, newspaper))
    graph.add((article, SDH.temRecursoWeb, web_resource))

    graph.add((web_resource, RDF.type, SDH.RecursoWeb))
    graph.add(
        (web_resource, SDH.originalURL, Literal(original_url, datatype=XSD.anyURI))
    )
    graph.add((web_resource, SDH.temCaptura, capture))

    graph.add((capture, RDF.type, SDH.CapturaArquivada))
    graph.add((capture, SDH.tstamp, Literal(tstamp, datatype=XSD.string)))
    graph.add((capture, SDH.capturedAt, tstamp_as_xsd_datetime(tstamp)))
    graph.add((capture, SDH.temTextoExtraido, extracted_text))

    for source_field, (predicate, datatype) in CAPTURE_FIELDS.items():
        value = result.get(source_field)
        if value is None:
            continue
        if datatype == XSD.nonNegativeInteger:
            literal = Literal(int(value), datatype=datatype)
        else:
            literal = Literal(str(value), datatype=datatype)
        graph.add((capture, predicate, literal))

    relative_text_path = text_path.relative_to(project_root).as_posix()
    graph.add((extracted_text, RDF.type, SDH.TextoExtraido))
    graph.add(
        (extracted_text, SDH.filePath, Literal(relative_text_path, datatype=XSD.string))
    )

    return graph


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    """Carrega um manifesto JSONL produzido pelo histórico temporal."""

    records: list[dict[str, Any]] = []
    with manifest_path.open(encoding="utf-8") as manifest:
        for line in manifest:
            if line.strip():
                records.append(json.loads(line))
    return records


def build_article_history_graph(
    records: list[dict[str, Any]], article_title: str, project_root: Path
) -> Graph:
    """Mapeia todas as capturas do manifesto para um Artigo e um RecursoWeb."""

    if not records:
        raise ValueError("O manifesto de capturas está vazio")

    article_ids = {str(record["article_id"]) for record in records}
    original_urls = {str(record["original_url"]) for record in records}
    if len(article_ids) != 1 or len(original_urls) != 1:
        raise ValueError("O manifesto deve representar um único artigo lógico")

    original_url = original_urls.pop()
    graph = Graph()
    graph.bind("sdh", SDH)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)

    newspaper = SDH["newspaper/record"]
    article = article_uri(original_url)
    web_resource = resource_uri(original_url)

    graph.add((newspaper, RDF.type, SDH.Jornal))
    graph.add((newspaper, RDFS.label, Literal("Record", lang="pt")))
    graph.add((article, RDF.type, SDH.Artigo))
    graph.add((article, RDFS.label, Literal(article_title)))
    graph.add((article, SDH.publicadoPor, newspaper))
    graph.add((article, SDH.temRecursoWeb, web_resource))
    graph.add((web_resource, RDF.type, SDH.RecursoWeb))
    graph.add(
        (web_resource, SDH.originalURL, Literal(original_url, datatype=XSD.anyURI))
    )

    history_fields: dict[str, tuple[URIRef, URIRef]] = {
        "archive_url": (SDH.archiveURL, XSD.anyURI),
        "title": (SDH.title, XSD.string),
        "digest": (SDH.digest, XSD.string),
        "content_length": (SDH.contentLength, XSD.nonNegativeInteger),
        "mime_type": (SDH.mimeType, XSD.string),
        "encoding": (SDH.encoding, XSD.string),
        "collection": (SDH.collection, XSD.string),
        "status_code": (SDH.statusCode, XSD.integer),
    }

    for record in records:
        tstamp = str(record["tstamp"])
        capture = capture_uri(original_url, tstamp)
        graph.add((web_resource, SDH.temCaptura, capture))
        graph.add((capture, RDF.type, SDH.CapturaArquivada))
        graph.add((capture, SDH.tstamp, Literal(tstamp, datatype=XSD.string)))
        graph.add(
            (
                capture,
                SDH.capturedAt,
                Literal(str(record["captured_at"]), datatype=XSD.dateTime),
            )
        )

        for manifest_field, (predicate, datatype) in history_fields.items():
            value = record.get(manifest_field)
            if value is None:
                continue
            if datatype in (XSD.integer, XSD.nonNegativeInteger):
                literal = Literal(int(value), datatype=datatype)
            else:
                literal = Literal(str(value), datatype=datatype)
            graph.add((capture, predicate, literal))

        text_path_value = record.get("extracted_text_path")
        if not record.get("text_download_success") or not text_path_value:
            continue
        text_path = project_root / str(text_path_value)
        if not text_path.is_file():
            continue

        extracted_text = extracted_text_uri(original_url, tstamp)
        graph.add((capture, SDH.temTextoExtraido, extracted_text))
        graph.add((extracted_text, RDF.type, SDH.TextoExtraido))
        graph.add(
            (
                extracted_text,
                SDH.filePath,
                Literal(str(text_path_value), datatype=XSD.string),
            )
        )

    return graph


def generate_sample(project_root: Path | None = None) -> tuple[Path, Path]:
    """Carrega dados do M1 e grava output/sample_capture.ttl."""

    root = project_root or Path(__file__).resolve().parents[2]
    result, source_json = load_sample_result(root / "data" / "raw" / "searches")
    text_path = text_path_for_result(result, root)
    graph = build_sample_graph(result, text_path, root)

    output_path = root / "output" / "sample_capture.ttl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format="turtle")
    return output_path, source_json


def generate_article_history(project_root: Path | None = None) -> Path:
    """Gera output/article_history.ttl a partir do manifesto do M3."""

    root = project_root or Path(__file__).resolve().parents[2]
    manifest_path = root / "data" / "processed" / "captures_manifest.jsonl"
    records = load_manifest(manifest_path)
    sample_result, _ = load_sample_result(root / "data" / "raw" / "searches")
    graph = build_article_history_graph(records, str(sample_result["title"]), root)

    output_path = root / "output" / "article_history.ttl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format="turtle")
    return output_path


def main() -> int:
    output_path, source_json = generate_sample()
    print(f"Captura usada: {SAMPLE_TSTAMP}")
    print(f"JSON de origem: {source_json}")
    print(f"Turtle gerado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
