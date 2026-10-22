"""Caminho D — anotação de redundância entre capturas do mesmo artigo.

Implementa o desenho de `docs/experiments.md` ("Caminho D — redução de
redundância entre capturas"). Não faz pedidos à API e não altera o grafo nem
o raw: lê `output/corpus_articles.ttl` e os textos referenciados por
`sdh:filePath` e escreve uma **anotação** por captura.

- **Camada 1** (captura com texto e `statusCode` 200): por artigo, em ordem
  temporal, cada captura é comparada com o **último representante retido**;
  é redundante se a similaridade for ≥ limiar, senão passa a representante.
  Em paralelo, como análise de sensibilidade, a variante que compara só com a
  captura com texto consecutiva.
- **Camada 2** (sem texto, ou `statusCode` ≠ 200): todas mantidas. Anotam-se
  à parte, nunca somados à Camada 1, os grupos com `digest` e
  `contentLength` iguais dentro do artigo, como candidatas não verificadas
  por texto.
- **Não avaliáveis**: capturas de artigos sem nenhum texto utilizável.

Similaridade: Jaccard sobre conjuntos de palavras (`\\w+`) do texto
normalizado (Unicode NFC, minúsculas, espaços colapsados). Por omissão na
linha de comandos, só sobre o corpo do artigo (variante c′, `article_body.py`;
capturas sem corpo ficam na camada `sem_corpo`); `--texto completo` repõe a
variante (a), com o "chrome" do site. É a medida da exploração documentada; esta tokenização
reproduz os números aí publicados.

O limiar **não** é fixado aqui: sem `--limiar`, a Camada 1 fica
`pendente_limiar` no CSV, o resumo publica a tabela de sensibilidade para uma
grelha de limiares e é gerada uma amostra de pares, espalhada por faixas de
similaridade, para rotulagem manual.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import statistics
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from rdflib import RDF, Graph
from rdflib.plugins.parsers.ntriples import W3CNTriplesParser

from .article_body import extract_body
from .html_body import extract_html_body

from .rdf_mapper import SDH

SENSITIVITY_THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.99, 1.00)

# Faixas só para espalhar a amostra de rotulagem; não são limiares propostos.
SAMPLE_BANDS = (("baixa", 0.0, 0.70), ("media", 0.70, 0.90), ("alta", 0.90, 1.0))
SAMPLE_SUBBIN_WIDTH = 0.05
SAMPLE_PER_BAND = 20
SAMPLE_SEED = 0
SAMPLE_DIFF_WORDS = 25

LAYER_TEXT = "1_texto"
LAYER_NO_TEXT = "2_sem_texto"
LAYER_NOT_EVALUABLE = "nao_avaliavel"
LAYER_NO_BODY = "sem_corpo"

LABEL_REPRESENTATIVE = "representante"
LABEL_REDUNDANT = "redundante"
LABEL_PENDING = "pendente_limiar"
LABEL_KEPT_NO_TEXT = "mantida_sem_texto"
LABEL_KEPT_NO_BODY = "mantida_sem_corpo"
LABEL_DIGEST_CANDIDATE = "candidata_digest_nao_verificada"
LABEL_DIGEST_CANDIDATE_MIXED = "candidata_digest_nao_verificada_grupo_misto"

CSV_FIELDS = (
    "artigo",
    "tstamp",
    "tem_texto",
    "status_code",
    "camada",
    "representante",
    "similaridade",
    "rotulo",
    "limiar",
    "sim_consecutiva",
    "digest",
    "content_length",
    "grupo_digest",
)

_WORD_RE = re.compile(r"\w+")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Capture:
    article: str
    tstamp: str
    # Ausentes no grafo do corpus da Fase 1: a TextSearch não devolve
    # `digest` fiável, `contentLength` nem `statusCode`.
    digest: str | None
    content_length: int | None
    status_code: int | None
    text: str | None
    # Variante (c′): tem texto, mas sem corpo de artigo localizável.
    body_missing: bool = False
    # HTML em bruto da mesma captura, se existir no disco.
    html_path: Path | None = None
    # Com o HTML ligado: de onde veio o corpo (`c′`, `html:<contentor>`) ou
    # porque não há (`premium`, `sem_corpo`).
    body_source: str | None = None

    @property
    def has_text(self) -> bool:
        return self.text is not None

    @property
    def in_layer1(self) -> bool:
        # `statusCode` desconhecido (corpus da Fase 1) não exclui a captura;
        # no corpus de 125 artigos todas as capturas o têm.
        return self.text is not None and self.status_code in (200, None) and not self.body_missing


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    return _SPACE_RE.sub(" ", text).strip()


def word_set(text: str) -> frozenset[str]:
    return frozenset(_WORD_RE.findall(normalize_text(text)))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


# --- Camada 1 ---------------------------------------------------------------


@dataclass(frozen=True)
class Assignment:
    representative: int
    similarity: float | None
    redundant: bool


def assign_last_representative(
    words: list[frozenset[str]], threshold: float
) -> list[Assignment]:
    """Compara cada captura com o último representante retido (ponto 5 do desenho)."""

    result: list[Assignment] = []
    current = None
    for index, tokens in enumerate(words):
        if current is None:
            result.append(Assignment(index, None, False))
            current = index
            continue
        similarity = jaccard(words[current], tokens)
        if similarity >= threshold:
            result.append(Assignment(current, similarity, True))
        else:
            result.append(Assignment(index, similarity, False))
            current = index
    return result


def assign_consecutive(
    words: list[frozenset[str]], threshold: float
) -> list[Assignment]:
    """Variante de sensibilidade: compara só com a captura com texto anterior.

    O representante de uma redundante é o início da cadeia, o que permite a
    fusão A≈B, B≈C, A≉C que a estratégia principal evita.
    """

    result: list[Assignment] = []
    for index, tokens in enumerate(words):
        if index == 0:
            result.append(Assignment(0, None, False))
            continue
        similarity = jaccard(words[index - 1], tokens)
        if similarity >= threshold:
            result.append(Assignment(result[index - 1].representative, similarity, True))
        else:
            result.append(Assignment(index, similarity, False))
    return result


def consecutive_similarities(words: list[frozenset[str]]) -> list[float | None]:
    return [None] + [jaccard(a, b) for a, b in zip(words, words[1:])]


# --- Camada 2 ---------------------------------------------------------------


def digest_annotations(captures: list[Capture]) -> dict[int, tuple[str, str]]:
    """Grupos (`digest`, `contentLength`) iguais no artigo que incluem capturas da Camada 2.

    Devolve, por índice de captura da Camada 2 num grupo com 2+ membros,
    `(grupo, rótulo)`. Num grupo só da Camada 2 a primeira (em ordem
    temporal) fica como referência e as restantes são candidatas; num grupo
    misto (com uma captura da Camada 1) todas as da Camada 2 são candidatas.
    Nada é removido: é só uma anotação.
    """

    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, capture in enumerate(captures):
        groups[(capture.digest, capture.content_length)].append(index)

    annotations: dict[int, tuple[str, str]] = {}
    for (digest, length), members in groups.items():
        if len(members) < 2:
            continue
        no_text = [i for i in members
                   if not captures[i].in_layer1 and not captures[i].body_missing]
        if not no_text:
            continue
        group_id = f"{digest}|{length}"
        mixed = len(no_text) < len(members)
        for position, index in enumerate(no_text):
            if mixed:
                label = LABEL_DIGEST_CANDIDATE_MIXED
            elif position == 0:
                label = LABEL_KEPT_NO_TEXT
            else:
                label = LABEL_DIGEST_CANDIDATE
            annotations[index] = (group_id, label)
    return annotations


# --- Anotação por captura ---------------------------------------------------


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def annotate_article(
    captures: list[Capture], threshold: float | None
) -> list[dict[str, str]]:
    """Uma linha por captura do artigo (capturas já em ordem temporal)."""

    layer1 = [i for i, c in enumerate(captures) if c.in_layer1]
    words = [word_set(captures[i].text or "") for i in layer1]
    consecutive = consecutive_similarities(words)
    assignments = (
        assign_last_representative(words, threshold) if threshold is not None else None
    )
    digest = digest_annotations(captures)
    position_in_layer1 = {index: pos for pos, index in enumerate(layer1)}

    rows: list[dict[str, str]] = []
    for index, capture in enumerate(captures):
        row = {
            "artigo": capture.article,
            "tstamp": capture.tstamp,
            "tem_texto": str(capture.has_text),
            "status_code": "" if capture.status_code is None else str(capture.status_code),
            "camada": "",
            "representante": "",
            "similaridade": "",
            "rotulo": "",
            "limiar": "" if threshold is None else f"{threshold:g}",
            "sim_consecutiva": "",
            "digest": capture.digest or "",
            "content_length": "" if capture.content_length is None else str(capture.content_length),
            "grupo_digest": "",
        }
        if index in position_in_layer1:
            pos = position_in_layer1[index]
            row["camada"] = LAYER_TEXT
            row["sim_consecutiva"] = _fmt(consecutive[pos])
            if assignments is not None:
                assignment = assignments[pos]
                row["representante"] = captures[layer1[assignment.representative]].tstamp
                row["similaridade"] = _fmt(assignment.similarity)
                row["rotulo"] = LABEL_REDUNDANT if assignment.redundant else LABEL_REPRESENTATIVE
            elif pos == 0:
                # A primeira captura com texto é representante para qualquer limiar.
                row["representante"] = capture.tstamp
                row["rotulo"] = LABEL_REPRESENTATIVE
            else:
                row["rotulo"] = LABEL_PENDING
        elif capture.body_missing:
            row["camada"] = LAYER_NO_BODY
            row["rotulo"] = LABEL_KEPT_NO_BODY
        else:
            row["camada"] = LAYER_NO_TEXT if layer1 else LAYER_NOT_EVALUABLE
            group_id, label = digest.get(index, ("", LABEL_KEPT_NO_TEXT))
            row["grupo_digest"] = group_id
            row["rotulo"] = label
        rows.append(row)
    return rows


# --- Leitura do corpus ------------------------------------------------------


HTML_DIR = Path("data") / "raw" / "original_html"

_CAPTURE_PREDICATES = {
    SDH.tstamp: "tstamp",
    SDH.digest: "digest",
    SDH.contentLength: "content_length",
    SDH.statusCode: "status_code",
    SDH.temTextoExtraido: "text_node",
}


def corpus_graph_path(project_root: Path, label: str | None = None) -> Path:
    """Grafo de entrada: o Turtle dos 125 artigos, ou o N-Triples de um corpus
    etiquetado da Fase 1 (o mesmo caminho de `corpus_rdf.rdf_paths`)."""

    if label is None:
        return project_root / "output" / "corpus_articles.ttl"
    return project_root / "data" / "processed" / f"corpus_articles_{label}_triples.nt"


class _GraphIndex:
    """Só os triplos que a leitura do corpus usa; serve de sink ao parser
    N-Triples, que assim não guarda o grafo inteiro em memória."""

    def __init__(self) -> None:
        self.resources: set = set()
        self.articles: set = set()
        self.original_url: dict = {}
        self.captures: dict[object, set] = defaultdict(set)
        self.capture_fields: dict[object, dict[str, object]] = defaultdict(dict)
        self.file_path: dict = {}

    def triple(self, s, p, o) -> None:
        if p == RDF.type:
            if o == SDH.RecursoWeb:
                self.resources.add(s)
            elif o == SDH.Artigo:
                self.articles.add(s)
        elif p == SDH.originalURL:
            self.original_url[s] = o
        elif p == SDH.temCaptura:
            # Um artigo refeito numa repetição aparece duas vezes no .nt
            # apendável: as capturas juntam-se, não se duplicam.
            self.captures[s].add(o)
        elif p in _CAPTURE_PREDICATES:
            self.capture_fields[s][_CAPTURE_PREDICATES[p]] = o
        elif p == SDH.filePath:
            self.file_path[s] = o


def read_graph_index(graph_path: Path) -> _GraphIndex:
    index = _GraphIndex()
    if graph_path.suffix == ".nt":
        with graph_path.open("rb") as handle:
            W3CNTriplesParser(sink=index).parse(handle)
    else:
        for triple in Graph().parse(graph_path, format="turtle"):
            index.triple(*triple)
    return index


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def load_corpus(graph_path: Path, project_root: Path) -> dict[str, list[Capture]]:
    """Capturas por artigo (`originalURL`), em ordem temporal.

    Lê o Turtle do corpus de 125 artigos ou, se o caminho acabar em `.nt`, o
    N-Triples de um corpus da Fase 1, em streaming. O HTML em bruto de uma
    captura com texto é procurado em `data/raw/original_html/` com o nome do
    ficheiro de texto (a mesma convenção do `ArquivoClient`).
    """

    index = read_graph_index(graph_path)
    corpus: dict[str, list[Capture]] = {}
    for web_resource in index.resources:
        article = str(index.original_url[web_resource])
        captures = []
        for capture in index.captures.get(web_resource, ()):
            fields = index.capture_fields[capture]
            text = html_path = None
            text_node = fields.get("text_node")
            if text_node is not None:
                file_path = project_root / str(index.file_path[text_node])
                if not file_path.is_file():
                    raise FileNotFoundError(f"Texto referenciado no grafo em falta: {file_path}")
                text = file_path.read_text(encoding="utf-8")
                candidate = project_root / HTML_DIR / f"{file_path.stem}.html"
                html_path = candidate if candidate.is_file() else None
            digest = fields.get("digest")
            captures.append(
                Capture(
                    article=article,
                    tstamp=str(fields["tstamp"]),
                    digest=None if digest is None else str(digest),
                    content_length=_optional_int(fields.get("content_length")),
                    status_code=_optional_int(fields.get("status_code")),
                    text=text,
                    html_path=html_path,
                )
            )
        corpus[article] = sorted(captures, key=lambda c: c.tstamp)
    return dict(sorted(corpus.items()))


# --- Sensibilidade, distribuição e amostra ----------------------------------


@dataclass(frozen=True)
class SensitivityRow:
    threshold: float
    redundant_last_rep: int
    redundant_consecutive: int
    versions_last_rep: int
    versions_consecutive: int
    disagreements: int
    articles_with_redundant: int


def to_body_corpus(
    corpus: dict[str, list[Capture]], use_html: bool = False
) -> dict[str, list[Capture]]:
    """Variante (c′): o texto de cada captura passa a ser só o corpo do artigo.

    Capturas com texto mas sem corpo localizável ficam `body_missing` (fora da
    Camada 1, sem deixarem de ter texto). Com `use_html` (decisão de
    2026-10-19): uma captura cujo HTML marca Premium fica sem corpo; se a c′
    não encontrar corpo, usa-se o contentor do HTML (`html_body.py`).
    """

    result = {}
    for article, captures in corpus.items():
        converted = []
        for capture in captures:
            if capture.text is None:
                converted.append(capture)
                continue
            if use_html:
                converted.append(_body_with_html(capture))
                continue
            body = extract_body(capture.text)
            converted.append(replace(capture, text=body.text, body_missing=not body.found))
        result[article] = converted
    return result


def _body_with_html(capture: Capture) -> Capture:
    html = extract_html_body(capture.html_path.read_bytes()) if capture.html_path else None
    if html is not None and html.premium:
        return replace(capture, text="", body_missing=True, body_source="premium")
    body = extract_body(capture.text or "")
    if body.found:
        return replace(capture, text=body.text, body_missing=False, body_source="c′")
    if html is not None and html.found:
        return replace(capture, text=html.text, body_missing=False,
                       body_source=f"html:{html.container}")
    return replace(capture, text="", body_missing=True, body_source="sem_corpo")


def sensitivity_table(
    layer1_words: dict[str, list[frozenset[str]]],
    thresholds: tuple[float, ...] = SENSITIVITY_THRESHOLDS,
) -> list[SensitivityRow]:
    rows = []
    for threshold in thresholds:
        red_last = red_cons = disagree = articles = 0
        versions_last = versions_cons = 0
        for words in layer1_words.values():
            last = assign_last_representative(words, threshold)
            cons = assign_consecutive(words, threshold)
            n_last = sum(a.redundant for a in last)
            red_last += n_last
            red_cons += sum(a.redundant for a in cons)
            versions_last += len(words) - n_last
            versions_cons += sum(not a.redundant for a in cons)
            disagree += sum(
                a.redundant != b.redundant or a.representative != b.representative
                for a, b in zip(last, cons)
            )
            articles += n_last > 0
        rows.append(
            SensitivityRow(
                threshold, red_last, red_cons, versions_last, versions_cons,
                disagree, articles,
            )
        )
    return rows


@dataclass(frozen=True)
class Pair:
    article: str
    tstamp_a: str
    tstamp_b: str
    similarity: float
    only_a: list[str]
    only_b: list[str]


def _ordered_difference(text: str, other: frozenset[str]) -> list[str]:
    seen: dict[str, None] = {}
    for word in _WORD_RE.findall(normalize_text(text)):
        if word not in other:
            seen.setdefault(word, None)
    return list(seen)


def consecutive_pairs(corpus: dict[str, list[Capture]]) -> list[Pair]:
    pairs = []
    for article, captures in corpus.items():
        layer1 = [c for c in captures if c.in_layer1]
        for a, b in zip(layer1, layer1[1:]):
            words_a, words_b = word_set(a.text or ""), word_set(b.text or "")
            pairs.append(
                Pair(
                    article, a.tstamp, b.tstamp, jaccard(words_a, words_b),
                    _ordered_difference(a.text or "", words_b),
                    _ordered_difference(b.text or "", words_a),
                )
            )
    return pairs


def _band_of(similarity: float) -> str:
    for name, low, high in SAMPLE_BANDS:
        if low <= similarity < high or (high == 1.0 and similarity == 1.0):
            return name
    raise ValueError(similarity)


def _subbin_of(similarity: float) -> float:
    # 1,0 exato fica numa sub-faixa própria para não dominar a faixa alta.
    if similarity == 1.0:
        return 1.0
    return int(similarity / SAMPLE_SUBBIN_WIDTH + 1e-9) * SAMPLE_SUBBIN_WIDTH


def label_sample(
    pairs: list[Pair], per_band: int = SAMPLE_PER_BAND, seed: int = SAMPLE_SEED
) -> list[tuple[str, Pair]]:
    """Amostra estratificada por faixa, repartida em rotação pelas sub-faixas de 0,05."""

    rng = random.Random(seed)
    sample: list[tuple[str, Pair]] = []
    for band, _low, _high in SAMPLE_BANDS:
        subbins: dict[float, list[Pair]] = defaultdict(list)
        for pair in pairs:
            if _band_of(pair.similarity) == band:
                subbins[_subbin_of(pair.similarity)].append(pair)
        pools = []
        for key in sorted(subbins):
            pool = sorted(subbins[key], key=lambda p: (p.article, p.tstamp_b))
            rng.shuffle(pool)
            pools.append(pool)
        chosen: list[Pair] = []
        while len(chosen) < per_band and any(pools):
            for pool in pools:
                if pool and len(chosen) < per_band:
                    chosen.append(pool.pop())
        chosen.sort(key=lambda p: p.similarity)
        sample.extend((band, pair) for pair in chosen)
    return sample


def describe(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)
    return {
        "n": n,
        "min": ordered[0],
        "p10": ordered[int(0.1 * n)],
        "mediana": statistics.median(ordered),
        "p90": ordered[int(0.9 * n)],
        "max": ordered[-1],
    }


# --- Saídas -----------------------------------------------------------------


def write_redundancy_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_sample_csv(sample: list[tuple[str, Pair]], path: Path) -> None:
    fields = (
        "par_id", "faixa", "artigo", "tstamp_a", "tstamp_b", "similaridade",
        "n_palavras_so_a", "n_palavras_so_b", "palavras_so_a", "palavras_so_b",
        "rotulo_manual", "notas",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for number, (band, pair) in enumerate(sample, start=1):
            writer.writerow({
                "par_id": number,
                "faixa": band,
                "artigo": pair.article,
                "tstamp_a": pair.tstamp_a,
                "tstamp_b": pair.tstamp_b,
                "similaridade": _fmt(pair.similarity),
                "n_palavras_so_a": len(pair.only_a),
                "n_palavras_so_b": len(pair.only_b),
                "palavras_so_a": " ".join(pair.only_a[:SAMPLE_DIFF_WORDS]),
                "palavras_so_b": " ".join(pair.only_b[:SAMPLE_DIFF_WORDS]),
                "rotulo_manual": "",
                "notas": "",
            })


LABEL_SAME = "mesma versão"
LABEL_CHANGED = "texto alterado"


def read_labelled_sample(path: Path) -> list[dict[str, str]] | None:
    """Devolve as linhas da amostra se já tiver rótulos manuais; senão `None`."""

    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows if any(row.get("rotulo_manual") for row in rows) else None


@dataclass(frozen=True)
class LabelValidation:
    same_total: int
    changed_total: int
    same_below: int
    changed_above: int
    separating_thresholds: list[float]


def validate_against_labels(
    labels: list[dict[str, str]],
    threshold: float,
    grid: tuple[float, ...] = SENSITIVITY_THRESHOLDS,
) -> LabelValidation:
    """Erros do limiar contra os rótulos: iguais abaixo e alterados acima."""

    same = [float(r["similaridade"]) for r in labels if r["rotulo_manual"] == LABEL_SAME]
    changed = [float(r["similaridade"]) for r in labels if r["rotulo_manual"] == LABEL_CHANGED]

    def errors(t: float) -> tuple[int, int]:
        return sum(s < t for s in same), sum(s >= t for s in changed)

    below, above = errors(threshold)
    separating = [t for t in grid if errors(t) == (0, 0)]
    return LabelValidation(len(same), len(changed), below, above, separating)


def versions_per_article(
    corpus: dict[str, list[Capture]], rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Por artigo: capturas, capturas da Camada 1 e versões textuais distintas."""

    versions: dict[str, int] = defaultdict(int)
    layer1: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["camada"] == LAYER_TEXT:
            layer1[row["artigo"]] += 1
            versions[row["artigo"]] += row["rotulo"] == LABEL_REPRESENTATIVE
    return [
        {
            "artigo": article,
            "capturas": str(len(captures)),
            "capturas_camada1": str(layer1[article]),
            "versoes_distintas": str(versions[article]),
        }
        for article, captures in corpus.items()
    ]


def write_versions_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["artigo", "capturas", "capturas_camada1", "versoes_distintas"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _num(value: float) -> str:
    return f"{value:.3f}".replace(".", ",")


def write_summary_markdown(
    corpus: dict[str, list[Capture]],
    rows: list[dict[str, str]],
    pairs: list[Pair],
    sensitivity: list[SensitivityRow],
    sample: list[tuple[str, Pair]],
    threshold: float | None,
    path: Path,
    labels: list[dict[str, str]] | None = None,
    versions: list[dict[str, str]] | None = None,
    use_body: bool = False,
    labels_without_body: list[dict[str, str]] | None = None,
) -> None:
    captures = [c for cs in corpus.values() for c in cs]
    layer1 = [r for r in rows if r["camada"] == LAYER_TEXT]
    layer2 = [r for r in rows if r["camada"] == LAYER_NO_TEXT]
    not_evaluable = [r for r in rows if r["camada"] == LAYER_NOT_EVALUABLE]
    no_body = [r for r in rows if r["camada"] == LAYER_NO_BODY]
    no_text_rows = layer2 + not_evaluable

    layer1_counts = {a: sum(c.in_layer1 for c in cs) for a, cs in corpus.items()}
    situations = [
        ("Só 1 captura", sum(len(cs) == 1 for cs in corpus.values())),
        ("Nenhuma captura com texto (não avaliáveis)",
         sum(n == 0 for n in layer1_counts.values())),
        ("Exatamente 1 captura com texto", sum(n == 1 for n in layer1_counts.values())),
        ("2 ou mais capturas com texto (comparáveis)",
         sum(n >= 2 for n in layer1_counts.values())),
    ]

    def groups(label: str) -> tuple[int, int]:
        members = [r for r in no_text_rows if r["rotulo"] == label]
        return len({(r["artigo"], r["grupo_digest"]) for r in members}), len(members)

    pure_groups, pure_candidates = groups(LABEL_DIGEST_CANDIDATE)
    mixed_groups, mixed_candidates = groups(LABEL_DIGEST_CANDIDATE_MIXED)
    status_not_200 = [c for c in captures if c.status_code != 200]

    lines = [
        "# Caminho D — anotação de redundância entre capturas\n",
        "Execução real, sem pedidos à API, sobre `output/corpus_articles.ttl` e os "
        "textos em `data/raw/texts/`. Nada foi removido do grafo nem do raw: o "
        "resultado é uma anotação por captura em `output/corpus_redundancy.csv`. "
        "Similaridade: Jaccard de conjuntos de palavras (`\\w+`) do texto "
        "normalizado (NFC, minúsculas, espaços), "
        + ("calculada só sobre o **corpo do artigo** (variante c′: entre o título e o "
           "primeiro marcador de bloco de chrome; `article_body.py`).\n" if use_body else
           "sobre o texto completo, sem remover o chrome do site (variante a).\n"),
    ]
    if threshold is None:
        lines.append(
            "**Limiar: não fixado, pendente de rotulagem manual.** As capturas da "
            "Camada 1 que dependem do limiar estão marcadas `pendente_limiar` no CSV; "
            "a tabela de sensibilidade abaixo mostra o efeito de cada limiar "
            "candidato. Depois da rotulagem, `--limiar X` preenche o CSV.\n"
        )
    else:
        lines.append(f"**Limiar aplicado no CSV: {_num(threshold)}.**\n")
        if labels:
            check = validate_against_labels(labels, threshold)
            lines += [
                "## Limiar e validação contra a amostra rotulada\n",
                f"Contra os {check.same_total + check.changed_total} pares rotulados "
                "manualmente em `output/corpus_redundancy_label_sample.csv`, com este "
                "limiar:\n",
                f"- \"texto alterado\" com similaridade ≥ limiar (seriam tratados como a "
                f"mesma versão — erro grave): **{check.changed_above} de "
                f"{check.changed_total}**.",
                f"- \"mesma versão\" com similaridade < limiar (ficam como versões "
                f"distintas — erro conservador): **{check.same_below} de "
                f"{check.same_total}**. A anotação é não destrutiva: este erro não "
                "apaga nada, só aumenta o número de \"versões distintas\".",
                "- Limiares da grelha que separam os rótulos sem erros: "
                + (", ".join(_num(t) for t in check.separating_thresholds)
                   if check.separating_thresholds else "**nenhum**")
                + (". O lado \"texto alterado\" assenta em muito poucos pares; "
                   "critério e limitações em `docs/experiments.md`."
                   if check.separating_thresholds else
                   ". O limiar é uma escolha pragmática dos autores, não uma "
                   "calibração limpa; critério e limitações em `docs/experiments.md`."),
            ]
            if labels_without_body:
                lines.append(
                    f"- Pares rotulados com alguma captura sem corpo (fora desta "
                    f"validação): {len(labels_without_body)} — "
                    + ", ".join(f"par {r['par_id']} ({r['rotulo_manual']})"
                                for r in labels_without_body) + "."
                )
            lines.append("")

    lines += [
        "## Estrutura do corpus\n",
        f"- Artigos: {len(corpus)}; capturas: {len(captures)}; capturas com texto: "
        f"{sum(c.has_text for c in captures)}",
        "",
        "| Situação | Artigos |",
        "| --- | ---: |",
        *(f"| {name} | {count} |" for name, count in situations),
        "",
        "## Contagens por camada\n",
        "| Camada | Capturas |",
        "| --- | ---: |",
        f"| Camada 1 — com texto{' e corpo' if use_body else ''} e `statusCode` 200 "
        f"| {len(layer1)} |",
        *([f"| Sem corpo — com texto, mas sem corpo de artigo localizável | {len(no_body)} |"]
          if use_body else []),
        f"| Camada 2 — sem texto, em artigos com algum texto | {len(layer2)} |",
        f"| Não avaliáveis — artigos sem nenhuma captura na Camada 1"
        f"{' (sem texto ou sem corpo)' if use_body else ' (sem texto)'} | {len(not_evaluable)} |",
        f"| Total | {len(rows)} |",
        "",
        f"- Capturas com `statusCode` ≠ 200: {len(status_not_200)}, das quais "
        f"{sum(c.has_text for c in status_not_200)} com texto; todas fora da "
        "Camada 1 (contabilizadas à parte, não são redundância).",
        "",
        "### Camada 2 — candidatas por `digest` + `contentLength` (não verificadas por texto)\n",
        "Todas as capturas sem texto são mantidas. Estas contagens são apenas um "
        "limite superior do que um critério fraco deduziria e **nunca são somadas "
        "à Camada 1**.\n",
        "| Tipo de grupo (dentro do artigo) | Grupos | Candidatas |",
        "| --- | ---: | ---: |",
        f"| Só capturas sem texto (n−1 por grupo) | {pure_groups} | {pure_candidates} |",
        f"| Misto (mesmo `digest`/`contentLength` de uma captura com texto) | "
        f"{mixed_groups} | {mixed_candidates} |",
        "",
        "## Distribuição de similaridades (pares consecutivos com texto)\n",
    ]

    similarities = [p.similarity for p in pairs]
    if similarities:
        stats = describe(similarities)
        lines += [
            "| n | mín. | p10 | mediana | p90 | máx. |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| {stats['n']} | {_num(stats['min'])} | {_num(stats['p10'])} | "
            f"{_num(stats['mediana'])} | {_num(stats['p90'])} | {_num(stats['max'])} |",
            "",
            "| Faixa | Pares |",
            "| --- | ---: |",
        ]
        bins: dict[float, int] = defaultdict(int)
        for value in similarities:
            bins[_subbin_of(value)] += 1
        for key in sorted(bins):
            label = "= 1,000" if key == 1.0 else (
                f"[{_num(key)}; {_num(key + SAMPLE_SUBBIN_WIDTH)})"
            )
            lines.append(f"| {label} | {bins[key]} |")
        lines.append("")

    lines += [
        "## Sensibilidade ao limiar (Camada 1)\n",
        "Redundantes = capturas com similaridade ≥ limiar face ao termo de "
        "comparação; versões = capturas da Camada 1 que ficam como "
        "representantes (versões textuais distintas). \"Último rep.\" é a "
        "estratégia do desenho; \"consecutiva\" é a análise de sensibilidade. "
        "Divergências = capturas com classificação ou representante diferente "
        "entre as duas.\n",
        "| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | "
        "Versões (último rep.) | Versões (consecutiva) | Divergências | "
        "Artigos com redundantes (último rep.) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in sensitivity:
        lines.append(
            f"| {_num(s.threshold)} | {s.redundant_last_rep} | {s.redundant_consecutive} | "
            f"{s.versions_last_rep} | {s.versions_consecutive} | {s.disagreements} | "
            f"{s.articles_with_redundant} |"
        )

    if versions is not None:
        evaluable = [v for v in versions if int(v["capturas_camada1"]) > 0]
        total_versions = sum(int(v["versoes_distintas"]) for v in evaluable)
        total_layer1 = sum(int(v["capturas_camada1"]) for v in evaluable)
        buckets = ((1, 1), (2, 2), (3, 5), (6, 10), (11, 10**9))
        lines += [
            "",
            "## Versões textuais distintas por artigo (Camada 1)\n",
            f"- Artigos com texto: {len(evaluable)}; capturas da Camada 1: "
            f"{total_layer1}; versões textuais distintas: **{total_versions}**; "
            f"capturas redundantes: {total_layer1 - total_versions}.",
            "- Detalhe por artigo em `output/corpus_redundancy_versions.csv`.",
            "",
            "| Versões distintas | Artigos |",
            "| --- | ---: |",
        ]
        for low, high in buckets:
            count = sum(low <= int(v["versoes_distintas"]) <= high for v in evaluable)
            label = str(low) if low == high else (f"{low}–{high}" if high < 10**9 else f"≥ {low}")
            lines.append(f"| {label} | {count} |")
        lines.append(
            f"| Artigos sem texto (não avaliáveis) | {len(versions) - len(evaluable)} |"
        )

    band_counts = defaultdict(int)
    if labels:
        for row in labels + (labels_without_body or []):
            band_counts[row["faixa"]] += 1
    else:
        for band, _pair in sample:
            band_counts[band] += 1
    lines += [
        "",
        "## Amostra para rotulagem manual\n",
        "`output/corpus_redundancy_label_sample.csv`: pares consecutivos com texto, "
        f"até {SAMPLE_PER_BAND} por faixa (semente {SAMPLE_SEED}), repartidos em "
        "rotação pelas sub-faixas de 0,05 (1,0 exato numa sub-faixa própria). As "
        "faixas servem só para espalhar a amostra; não são limiares propostos. "
        + ("Já rotulada manualmente (colunas `rotulo_manual` e `notas`); não é "
           "reescrita por novas execuções.\n" if labels else
           "Colunas `rotulo_manual` (\"mesma versão\" / \"texto alterado\") e "
           "`notas` por preencher.\n"),
        "| Faixa | Intervalo | Pares na amostra | Pares disponíveis |",
        "| --- | --- | ---: | ---: |",
    ]
    for band, low, high in SAMPLE_BANDS:
        available = sum(_band_of(v) == band for v in similarities)
        interval = f"[{_num(low)}; {_num(high)}]" if high == 1.0 else f"[{_num(low)}; {_num(high)})"
        lines.append(f"| {band} | {interval} | {band_counts[band]} | {available} |")

    lines.append(
        "\nEstes valores são o resultado real desta execução, não uma estimativa."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def labels_on_body(
    labels: list[dict[str, str]], corpus: dict[str, list[Capture]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Recalcula a similaridade dos pares rotulados sobre o corpo (variante c′).

    Devolve `(pares com corpo, com a similaridade nova; pares com alguma
    captura sem corpo, à parte)`.
    """

    by_key = {(c.article, c.tstamp): c for caps in corpus.values() for c in caps}
    with_body, without_body = [], []
    for row in labels:
        a, b = by_key[(row["artigo"], row["tstamp_a"])], by_key[(row["artigo"], row["tstamp_b"])]
        if a.body_missing or b.body_missing:
            without_body.append(row)
        else:
            sim = jaccard(word_set(a.text or ""), word_set(b.text or ""))
            with_body.append({**row, "similaridade": f"{sim:.6f}"})
    return with_body, without_body


def run(
    project_root: Path | None = None, threshold: float | None = None, use_body: bool = False,
) -> tuple[list[dict[str, str]], list[SensitivityRow], list[tuple[str, Pair]]]:
    root = project_root or Path(__file__).resolve().parents[2]
    output = root / "output"
    corpus = load_corpus(output / "corpus_articles.ttl", root)
    if use_body:
        corpus = to_body_corpus(corpus)

    rows = [row for captures in corpus.values() for row in annotate_article(captures, threshold)]
    layer1_words = {
        article: [word_set(c.text or "") for c in captures if c.in_layer1]
        for article, captures in corpus.items()
    }
    sensitivity = sensitivity_table(layer1_words)
    pairs = consecutive_pairs(corpus)
    sample = label_sample(pairs)

    sample_path = output / "corpus_redundancy_label_sample.csv"
    # Uma amostra já rotulada à mão nunca é reescrita (os rótulos perder-se-iam).
    labels = read_labelled_sample(sample_path)
    labels_without_body: list[dict[str, str]] = []
    if labels and use_body:
        labels, labels_without_body = labels_on_body(labels, corpus)
    versions = versions_per_article(corpus, rows) if threshold is not None else None

    write_redundancy_csv(rows, output / "corpus_redundancy.csv")
    if labels is None and not labels_without_body:
        write_sample_csv(sample, sample_path)
    if versions is not None:
        write_versions_csv(versions, output / "corpus_redundancy_versions.csv")
    write_summary_markdown(
        corpus, rows, pairs, sensitivity, sample, threshold,
        output / "corpus_redundancy_summary.md", labels, versions, use_body,
        labels_without_body,
    )
    return rows, sensitivity, sample


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.corpus_redundancy",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument(
        "--limiar",
        type=float,
        default=None,
        help="limiar de Jaccard para a Camada 1; omitido enquanto não houver "
        "calibração por rotulagem manual (Camada 1 fica pendente_limiar)",
    )
    parser.add_argument(
        "--texto", choices=("corpo", "completo"), default="corpo",
        help="corpo do artigo (variante c′, adotada; por omissão) ou texto completo "
        "com chrome (variante a, histórica)",
    )
    args = parser.parse_args(argv)
    if args.limiar is not None and not 0.0 <= args.limiar <= 1.0:
        parser.error("--limiar tem de estar entre 0 e 1")

    rows, sensitivity, sample = run(threshold=args.limiar, use_body=args.texto == "corpo")
    print(f"Capturas anotadas: {len(rows)}")
    sample_path = Path(__file__).resolve().parents[2] / "output" / "corpus_redundancy_label_sample.csv"
    if read_labelled_sample(sample_path) is not None:
        print("Amostra de rotulagem: já rotulada, mantida (não reescrita)")
    else:
        print(f"Pares na amostra de rotulagem: {len(sample)}")
    print(
        "Saídas: output/corpus_redundancy.csv, output/corpus_redundancy_summary.md, "
        "output/corpus_redundancy_label_sample.csv"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
