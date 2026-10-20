"""Fase 1 do protocolo de queries do Caminho A — descoberta via TextSearch.

Começou como a Opção 2 (Moderada) decidida em `docs/experiments.md`
("Protocolo de queries para o corpus do Caminho A"): 13 termos (4
modalidades, 4 clubes, 5 atletas), `from=2015`/`to=2020`, explicitamente uma
amostra pequena. Essa execução deu o corpus atual de 125 artigos; o seu raw
(`data/raw/corpus_queries/`) e os seus relatórios (`output/corpus_phase1_*`)
são preservados e não são reescritos por este módulo.

**Âmbito atual (2026-10-19): decisão de âmbito explícita e muito mais
ampla**, já não uma amostra moderada. As facetas de modalidade, clube e
competição passam a enumerar todos os valores reais encontrados nos URLs do
`record.pt` (`docs/experiments.md`, enumeração de 2026-10-19 com
`themes_from_url()`, raw em
`data/raw/api_diagnostics/enumeracao_2026-10-19/`), com as decisões do autor
sobre os casos ambíguos: 39 modalidades (sem as secções editoriais `outras`,
`record-pela-patagonia` e `aventura-em-mocambique`), 57 clubes (variantes de
slug fundidas; `campeao` excluído; equipas B incluídas por terem ≥ 20 URLs)
e as 7 competições. Os 5 atletas ficam deliberadamente como estavam: são uma
faceta de descoberta, não vocabulário de entidades (decisão do Caminho B
sobre circularidade). Total: 108 termos, `from=1999`/`to=2026` (não há
limite de 2000 resultados que justifique dividir por datas).

**Recolha ano a ano (2026-10-19, `docs/experiments.md`, teste de blocos de
data).** Cada termo é pedido um ano de cada vez, de 1999 a 2026 (28
intervalos), com datas de 14 dígitos (`AAAA0101000000`–`AAAA1231235959`): a
API lê um ano sozinho como o início desse ano, pelo que `to=2020` excluía o
ano de 2020 inteiro. Um intervalo largo concentrava os 300 resultados
alcançáveis em 2–3 anos; o intervalo de um ano reparte-os. Em cada ano
pagina-se por `offset` até à primeira página vazia (uma página com menos de
`maxItems` resultados não é o fim) ou até 6 páginas. 1 repetição por termo
(decisão de âmbito do autor). Parâmetros mantidos: `siteSearch=record.pt`,
`maxItems=50`, `dedupField=url`/`dedupValue=1` explícitos; a paragem não
depende de `next_page`. Esta execução escreve o raw em
`data/raw/corpus_queries/por_ano/` e os relatórios em
`output/corpus_phase1_por_ano_*`; as execuções anteriores (original e
`alargada`) ficam intactas. Se for interrompida, retoma a partir do raw já
gravado, sem repetir pedidos.

Preserva o raw de cada pedido, depois agrega/deduplica os `response_items`
de todos os pedidos por `(originalURL, tstamp)` (captura) e por
`originalURL` (artigo), seguindo exatamente o método descrito em
`docs/experiments.md`. Não avança para a Fase 2 (`version_history`); esse é
um passo manual seguinte, condicional à confirmação do valor de `N`.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import requests

from .arquivo_client import ArquivoClient, SearchResponse
from .url_identity import has_tracking_params, normalize_for_grouping, strip_scheme

LOGGER = logging.getLogger(__name__)

SITE_SEARCH = "record.pt"
FIRST_YEAR = 1999
LAST_YEAR = 2026
YEARS = tuple(range(FIRST_YEAR, LAST_YEAR + 1))
MAX_ITEMS = 50
REPETITIONS = 1
MAX_PAGES_PER_TERM = 6
RETRY_ATTEMPTS = 3
RETRY_SLEEP_SECONDS = 10.0

RUN_LABEL = "por_ano"

# Valores reais da enumeração de 2026-10-19 (docs/experiments.md), com as
# decisões do autor sobre os casos ambíguos.
MODALIDADES = (
    "futebol", "basquetebol", "andebol", "voleibol", "atletismo", "ciclismo",
    "judo", "motores", "natação", "desporto-universitario", "jogos-europeus",
    "ténis", "hóquei em patins", "surf", "jogos olímpicos", "golfe",
    "desportos de combate", "rugby", "canoagem", "ténis de mesa", "triatlo",
    "ginástica", "padel", "NFL", "orientação", "desportos radicais", "vela",
    "remo", "desporto escolar", "badminton", "snooker", "MMA", "aventura",
    "tiro", "esgrima", "desportos de inverno", "desporto adaptado",
    "pólo aquático", "xadrez",
)
CLUBES = (
    "Benfica", "Sporting", "Porto", "SC Braga", "Vitória de Guimarães",
    "Rio Ave", "Vitória de Setúbal", "Marítimo", "Portimonense", "Boavista",
    "Tondela", "Chaves", "Aves", "Feirense", "Famalicão", "Belenenses",
    "Paços de Ferreira", "Moreirense", "Santa Clara", "Estoril Praia",
    "Gil Vicente", "Nacional", "Leixões", "Académica", "Farense",
    "Belenenses SAD", "Arouca", "Varzim", "União da Madeira",
    "Cova da Piedade", "Sporting da Covilhã", "Académico de Viseu",
    "Vilafranquense", "Oliveirense", "Benfica B", "Casa Pia", "Vizela",
    "Penafiel", "Estrela da Amadora", "Mafra", "Olhanense", "FC Porto B",
    "Sporting B", "Fafe", "Real Sport Clube", "SC Braga B", "AVS",
    "Vitória de Guimarães B", "Freamunde", "Trofense", "Torreense",
    "União de Leiria", "Lank Vilaverdense", "Sporting Clube Oriental",
    "Felgueiras", "Atlético Clube de Portugal", "Alverca",
)
# Faceta de descoberta, não vocabulário de entidades: não alargar.
ATLETAS = (
    "Cristiano Ronaldo",
    "Bruno Fernandes",
    "Telma Monteiro",
    "João Félix",
    "Nelson Évora",
)
COMPETICOES = (
    "2.ª Liga", "CAN", "Europeu", "Liga Jovem da UEFA",
    "Taça das Confederações", "Taça de Portugal", "Liga NOS",
)

TERMS: tuple[tuple[str, str], ...] = (
    tuple(("modalidade", termo) for termo in MODALIDADES)
    + tuple(("clube", termo) for termo in CLUBES)
    + tuple(("atleta", termo) for termo in ATLETAS)
    + tuple(("competicao", termo) for termo in COMPETICOES)
)


def year_bounds(year: int) -> tuple[str, str]:
    """`from`/`to` de um ano inteiro, em 14 dígitos (formato do `tstamp`).

    Um ano sozinho é lido pela API como o início desse ano (`to=2020` →
    `20200000000000`), excluindo-o; por isso nunca se envia só o ano.
    """

    return f"{year}0101000000", f"{year}1231235959"


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()


@dataclass(frozen=True)
class TermRunStats:
    facet: str
    query: str
    year: int
    repetition: int
    requests_made: int
    results_received: int


def _search_with_retries(client: ArquivoClient, **kwargs: Any) -> SearchResponse:
    last_exc: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return client.search(**kwargs)
        except requests.RequestException as exc:
            last_exc = exc
            LOGGER.warning(
                "Pedido falhou (tentativa %d/%d): %s", attempt, RETRY_ATTEMPTS, exc
            )
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_SLEEP_SECONDS)
    assert last_exc is not None
    raise last_exc


def collect_term_year(
    client: ArquivoClient,
    facet: str,
    query: str,
    year: int,
    raw_dir: Path,
    repetition: int = 1,
) -> tuple[list[dict[str, Any]], list[Path]]:
    """Pede as páginas de um termo num único ano, até à primeira página vazia.

    Uma página com menos de `MAX_ITEMS` resultados não pára a recolha: na
    enumeração de 2026-10-19 houve páginas assim a meio da paginação,
    seguidas de páginas cheias. Também não depende de `next_page`. O raw de
    cada página inclui o ano no nome; se já existir, é lido em vez de pedido
    de novo (retoma de uma execução interrompida).
    """

    items: list[dict[str, Any]] = []
    raw_paths: list[Path] = []
    offset = 0
    slug = slugify(query)
    from_date, to_date = year_bounds(year)

    for _ in range(MAX_PAGES_PER_TERM):
        raw_path = raw_dir / (
            f"{facet}_{slug}_{year}_rep{repetition}_offset-{offset:04d}.json"
        )
        if raw_path.is_file():
            results = json.loads(raw_path.read_bytes()).get("response_items") or []
        else:
            results = _search_with_retries(
                client,
                query=query,
                site_search=SITE_SEARCH,
                from_date=from_date,
                to_date=to_date,
                max_items=MAX_ITEMS,
                offset=offset,
                dedup_field="url",
                dedup_value=1,
                raw_path=raw_path,
            ).results
        raw_paths.append(raw_path)
        if not results:
            break
        items.extend(results)
        offset += MAX_ITEMS
    else:
        LOGGER.warning(
            "Atingido o limite de %d páginas para %s/%s em %d; a parar.",
            MAX_PAGES_PER_TERM,
            facet,
            query,
            year,
        )

    return items, raw_paths


@dataclass
class CaptureRecord:
    original_url: str
    tstamp: str
    title: str | None
    item: dict[str, Any]
    facets: set[str]
    queries: set[str]
    divergent: bool = False
    variants: set[str] = field(default_factory=set)


def representative_urls(records: list[tuple[str, str, dict[str, Any]]]) -> dict[str, str]:
    """Cada `originalURL` → representante do seu grupo de variantes.

    Grupo: o mesmo `normalize_for_grouping()` (`url_identity.py`: esquema,
    barras repetidas, barra final, `ref`/`utm_*`/`act`/`est`), a mesma regra
    da classificação e do RDF. Representante: sem parâmetros de rastreio,
    depois sem `//` no caminho, depois `https`, depois o que tem mais
    capturas distintas, depois a ordem alfabética (determinístico).
    """

    tstamps: dict[str, set[str]] = defaultdict(set)
    for _, _, item in records:
        tstamps[str(item.get("originalURL"))].add(str(item.get("tstamp")))
    groups: dict[str, list[str]] = defaultdict(list)
    for url in tstamps:
        groups[normalize_for_grouping(url)].append(url)
    mapping: dict[str, str] = {}
    for urls in groups.values():
        best = min(urls, key=lambda url: (
            has_tracking_params(url),
            "//" in strip_scheme(url),
            not url.startswith("https://"),
            -len(tstamps[url]),
            url,
        ))
        for url in urls:
            mapping[url] = best
    return mapping


def aggregate(
    records: list[tuple[str, str, dict[str, Any]]],
    url_map: dict[str, str] | None = None,
) -> tuple[dict[tuple[str, str], CaptureRecord], list[tuple[str, str]]]:
    """Deduplica por (originalURL, tstamp); sinaliza divergências de metadados.

    Com `url_map` (de `representative_urls()`), as variantes do mesmo URL
    juntam-se no representante e o `originalURL` real fica em `variants`; a
    divergência só se compara entre itens com o mesmo `originalURL` real
    (entre variantes os campos com o URL diferem por construção).
    """

    captures: dict[tuple[str, str], CaptureRecord] = {}
    divergent_keys: list[tuple[str, str]] = []

    for facet, query, item in records:
        real_url = str(item.get("originalURL"))
        original_url = url_map.get(real_url, real_url) if url_map else real_url
        tstamp = str(item.get("tstamp"))
        key = (original_url, tstamp)

        if key not in captures:
            captures[key] = CaptureRecord(
                original_url=original_url,
                tstamp=tstamp,
                title=item.get("title"),
                item=item,
                facets={facet},
                queries={query},
                variants={real_url},
            )
            continue

        existing = captures[key]
        existing.facets.add(facet)
        existing.queries.add(query)
        existing.variants.add(real_url)
        same_real_url = str(existing.item.get("originalURL")) == real_url
        if same_real_url and existing.item != item and not existing.divergent:
            existing.divergent = True
            divergent_keys.append(key)

    return captures, divergent_keys


def write_term_stats_csv(stats: list[TermRunStats], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(asdict(stats[0])), lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(row) for row in stats)


def write_captures_csv(
    captures: dict[tuple[str, str], CaptureRecord], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "original_url",
                "tstamp",
                "title",
                "facets",
                "queries",
                "num_queries_matched",
                "divergent",
                "url_variants",
            ]
        )
        for record in captures.values():
            writer.writerow(
                [
                    record.original_url,
                    record.tstamp,
                    record.title or "",
                    ";".join(sorted(record.facets)),
                    ";".join(sorted(record.queries)),
                    len(record.queries),
                    record.divergent,
                    ";".join(sorted(record.variants - {record.original_url})),
                ]
            )


def write_aggregation_markdown(
    stats: list[TermRunStats],
    captures: dict[tuple[str, str], CaptureRecord],
    divergent_keys: list[tuple[str, str]],
    path: Path,
) -> None:
    exact_urls = len({variant for record in captures.values() for variant in record.variants})
    total_requests = sum(row.requests_made for row in stats)
    total_raw_items = sum(row.results_received for row in stats)
    total_captures = len(captures)
    articles: dict[str, set[str]] = defaultdict(set)
    for record in captures.values():
        articles[record.original_url].add(record.tstamp)
    n_articles = len(articles)
    multi_query_articles = sum(
        1
        for record in captures.values()
        if len(record.queries) > 1
    )

    lines = [
        "# Fase 1 ano a ano — descoberta via TextSearch (corpus do Caminho A)\n",
        f"Execução real. Parâmetros comuns: `siteSearch=record.pt`, "
        f"`maxItems={MAX_ITEMS}`, `dedupField=url`/`dedupValue=1` explícitos. "
        f"{len(TERMS)} termos ({len(MODALIDADES)} modalidades, "
        f"{len(CLUBES)} clubes, {len(ATLETAS)} atletas, "
        f"{len(COMPETICOES)} competições), um intervalo por ano de "
        f"{FIRST_YEAR} a {LAST_YEAR} (`AAAA0101000000`–`AAAA1231235959`), "
        f"{REPETITIONS} repetição por termo, até {MAX_PAGES_PER_TERM} páginas "
        "por ano, paragem na primeira página vazia.\n",
        "## Resumo\n",
        f"- Pedidos reais efetuados: {total_requests}",
        f"- Itens brutos recebidos (antes de deduplicar): {total_raw_items}",
        f"- Capturas únicas por `(originalURL, tstamp)`: {total_captures}",
        f"- `originalURL` distintos tal como vieram da API: {exact_urls}",
        f"- **N (artigos únicos, `originalURL` normalizado — esquema, barras, "
        f"barra final, `ref`/`utm_*`/`act`/`est`): {n_articles}** "
        f"({exact_urls - n_articles} variantes juntadas)",
        f"- Capturas encontradas por mais do que uma query: {multi_query_articles}",
        f"- Divergências de metadados para a mesma `(originalURL, tstamp)`: "
        f"{len(divergent_keys)}",
        "\n## Por ano\n",
        "Pedidos e resultados por intervalo pedido; capturas únicas pelo ano "
        "do seu `tstamp`.\n",
        "| Ano | Pedidos | Resultados | Termos no teto de páginas | Capturas únicas |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    captures_per_year: dict[str, int] = defaultdict(int)
    for record in captures.values():
        captures_per_year[record.tstamp[:4]] += 1
    for year in YEARS:
        rows = [row for row in stats if row.year == year]
        capped = sum(1 for row in rows if row.results_received == MAX_ITEMS * MAX_PAGES_PER_TERM)
        lines.append(
            f"| {year} | {sum(row.requests_made for row in rows)} | "
            f"{sum(row.results_received for row in rows)} | {capped} | "
            f"{captures_per_year.get(str(year), 0)} |"
        )
    outside = sum(n for y, n in captures_per_year.items() if not y.isdigit() or int(y) not in YEARS)
    if outside:
        lines.append(f"\nCapturas com `tstamp` fora de {FIRST_YEAR}–{LAST_YEAR}: {outside}")

    lines.extend([
        "\n## Pedidos e resultados por termo (soma dos anos)\n",
        "| Faceta | Termo | Pedidos | Resultados | Anos com resultados | Anos no teto |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ])
    for facet, query in dict.fromkeys((row.facet, row.query) for row in stats):
        rows = [row for row in stats if (row.facet, row.query) == (facet, query)]
        lines.append(
            f"| {facet} | {query} | {sum(row.requests_made for row in rows)} | "
            f"{sum(row.results_received for row in rows)} | "
            f"{sum(1 for row in rows if row.results_received)} | "
            f"{sum(1 for row in rows if row.results_received == MAX_ITEMS * MAX_PAGES_PER_TERM)} |"
        )

    if divergent_keys:
        lines.extend(
            [
                "\n## Divergências de metadados\n",
                "| originalURL | tstamp |",
                "| --- | --- |",
            ]
        )
        for url, tstamp in divergent_keys:
            lines.append(f"| {url} | {tstamp} |")
        lines.append(
            "\nAmbas as versões do item ficam preservadas no raw de origem; "
            "esta tabela só sinaliza a divergência, não a resolve."
        )

    lines.append(
        "\nEstes valores são o resultado real desta execução, não uma "
        "estimativa. Corpus agregado em "
        f"`output/corpus_phase1_{RUN_LABEL}_captures.csv` "
        "(uma linha por captura única, com proveniência de faceta/termo)."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase1(project_root: Path | None = None) -> tuple[
    list[TermRunStats], dict[tuple[str, str], CaptureRecord], list[tuple[str, str]]
]:
    root = project_root or Path(__file__).resolve().parents[2]
    raw_dir = root / "data" / "raw" / "corpus_queries" / RUN_LABEL
    client = ArquivoClient(data_dir=root / "data" / "raw", timeout=(15.0, 120.0))

    stats: list[TermRunStats] = []
    records: list[tuple[str, str, dict[str, Any]]] = []

    for index, (facet, query) in enumerate(TERMS, start=1):
        for year in YEARS:
            for repetition in range(1, REPETITIONS + 1):
                items, raw_paths = collect_term_year(
                    client, facet, query, year, raw_dir, repetition
                )
                stats.append(
                    TermRunStats(
                        facet=facet,
                        query=query,
                        year=year,
                        repetition=repetition,
                        requests_made=len(raw_paths),
                        results_received=len(items),
                    )
                )
                for item in items:
                    records.append((facet, query, item))
        LOGGER.info("Termo %d/%d concluído: %s/%s", index, len(TERMS), facet, query)

    return write_outputs(root, stats, records)


def write_outputs(
    root: Path,
    stats: list[TermRunStats],
    records: list[tuple[str, str, dict[str, Any]]],
) -> tuple[list[TermRunStats], dict[tuple[str, str], CaptureRecord], list[tuple[str, str]]]:
    captures, divergent_keys = aggregate(records, representative_urls(records))

    write_term_stats_csv(stats, root / "output" / f"corpus_phase1_{RUN_LABEL}_per_term.csv")
    write_captures_csv(captures, root / "output" / f"corpus_phase1_{RUN_LABEL}_captures.csv")
    write_aggregation_markdown(
        stats, captures, divergent_keys, root / "output" / f"corpus_phase1_{RUN_LABEL}_aggregation.md"
    )
    return stats, captures, divergent_keys


RAW_NAME = re.compile(
    r"^(?P<facet>[a-z]+)_(?P<slug>[a-z0-9-]+)_(?P<year>\d{4})_rep(?P<rep>\d+)"
    r"_offset-(?P<offset>\d+)\.json$"
)


def records_from_raw(
    raw_dir: Path,
) -> tuple[list[TermRunStats], list[tuple[str, str, dict[str, Any]]]]:
    """Reconstrói estatísticas e registos a partir do raw já em disco, sem rede.

    Segue a ordem de `TERMS`/`YEARS`/offset, a mesma da execução, para que a
    primeira ocorrência de cada captura seja a mesma.
    """

    query_of = {(facet, slugify(query)): query for facet, query in TERMS}
    order = {term: index for index, term in enumerate(TERMS)}
    pages: dict[tuple[str, str, int, int], list[tuple[int, Path]]] = defaultdict(list)
    for path in raw_dir.iterdir():
        match = RAW_NAME.match(path.name)
        if not match:
            continue
        query = query_of.get((match["facet"], match["slug"]))
        if query is None:
            raise ValueError(f"Ficheiro de raw de um termo desconhecido: {path.name}")
        key = (match["facet"], query, int(match["year"]), int(match["rep"]))
        pages[key].append((int(match["offset"]), path))

    stats: list[TermRunStats] = []
    records: list[tuple[str, str, dict[str, Any]]] = []
    for facet, query, year, repetition in sorted(
        pages, key=lambda key: (order[(key[0], key[1])], key[2], key[3])
    ):
        received = 0
        for _, path in sorted(pages[(facet, query, year, repetition)]):
            items = json.loads(path.read_bytes()).get("response_items") or []
            received += len(items)
            records.extend((facet, query, item) for item in items)
        stats.append(TermRunStats(
            facet=facet, query=query, year=year, repetition=repetition,
            requests_made=len(pages[(facet, query, year, repetition)]),
            results_received=received,
        ))
    return stats, records


def rebuild_offline(project_root: Path | None = None) -> tuple[
    list[TermRunStats], dict[tuple[str, str], CaptureRecord], list[tuple[str, str]]
]:
    """Refaz os relatórios desta execução a partir do raw, com URLs normalizados.

    O CSV de capturas anterior é preservado como `.pre-normalizacao.csv`
    (uma vez; não é reescrito em reconstruções seguintes).
    """

    root = project_root or Path(__file__).resolve().parents[2]
    captures_csv = root / "output" / f"corpus_phase1_{RUN_LABEL}_captures.csv"
    backup = captures_csv.with_suffix(".pre-normalizacao.csv")
    if captures_csv.is_file() and not backup.exists():
        captures_csv.rename(backup)
    stats, records = records_from_raw(root / "data" / "raw" / "corpus_queries" / RUN_LABEL)
    return write_outputs(root, stats, records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.corpus_phase1")
    parser.add_argument(
        "--rebuild-offline", action="store_true",
        help="refaz os relatórios a partir do raw já em disco, sem pedidos à API",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        stats, captures, divergent_keys = rebuild_offline() if args.rebuild_offline else run_phase1()
    except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
        LOGGER.error("A Fase 1 falhou: %s", exc)
        return 1

    articles = {record.original_url for record in captures.values()}
    print(f"Pedidos efetuados: {sum(row.requests_made for row in stats)}")
    print(f"Capturas únicas: {len(captures)}")
    exact = {variant for record in captures.values() for variant in record.variants}
    print(f"originalURL distintos (exatos): {len(exact)}")
    print(f"N (artigos únicos, URL normalizado): {len(articles)} "
          f"({len(exact) - len(articles)} variantes juntadas)")
    print(f"Divergências: {len(divergent_keys)}")
    print(f"Relatórios: output/corpus_phase1_{RUN_LABEL}_per_term.csv, "
          f"output/corpus_phase1_{RUN_LABEL}_captures.csv, "
          f"output/corpus_phase1_{RUN_LABEL}_aggregation.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
