"""Consultas SPARQL sobre o grafo RDF completo de um corpus da Fase 1.

Responde, sobre o grafo e não sobre os CSV, às perguntas do painel
(`navigation_corpus.py`): artigos por ano, artigos de uma entidade por ano,
entidades mais mencionadas, co-ocorrências e entidades por origem no
vocabulário. Serve para mostrar que o grafo suporta estas consultas à escala do
corpus e que o painel é uma vista pré-calculada com os mesmos números.

Dados, sem rede e sem alterar nada:

- o grafo dos artigos (`data/processed/corpus_articles_<etiqueta>_triples.nt`);
- o grafo do Caminho B (`output/corpus_entities_<etiqueta>.ttl`,
  `corpus_entities_rdf.py`), que partilha os URIs de `Artigo`;
- as queries versionadas em `queries/corpus/*.rq`;
- para a comparação, o resumo do painel (`output/prototipo_<etiqueta>/resumo.md`).

Motor: `pyoxigraph` (dependência opcional, `pip install -e ".[sparql]"`), um
store em disco com carga em massa; o RDFLib é demasiado lento para ~10 M de
triplos. O store fica em `output/sparql_<etiqueta>/store/` e é reutilizado
(`--recarregar` refaz a carga). Escreve `output/sparql_<etiqueta>/relatorio.md`
com os tempos, as tabelas e a comparação com o painel.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .corpus_entities_rdf import WIKIDATA_ENTITY
from .corpus_redundancy import corpus_graph_path
from .rdf_mapper import SDH

DEFAULT_LABEL = "por_ano"
DEFAULT_ENTITY = "Q131499"  # Sport Lisboa e Benfica, o exemplo do painel
DEFAULT_TOP = 20
QID_PATTERN = re.compile(r"^Q[0-9]+$")
QUERIES_DIR = Path(__file__).resolve().parents[2] / "queries" / "corpus"
QUERY_NAMES = ("artigos_por_ano", "entidade_por_ano", "entidades_mais_mencionadas",
               "coocorrencias", "entidades_por_origem")
NO_ORIGIN = "(sem origem)"
SDH_IRI = str(SDH)


class MissingDependencyError(RuntimeError):
    pass


def require_pyoxigraph():
    try:
        import pyoxigraph
    except ImportError as error:
        raise MissingDependencyError(
            "O pyoxigraph não está instalado (dependência opcional das consultas SPARQL "
            "ao corpus). Instalar com: python -m pip install -e \".[sparql]\" "
            "(ou python -m pip install pyoxigraph)."
        ) from error
    return pyoxigraph


def entity_iri(qid: str) -> str:
    if not QID_PATTERN.fullmatch(qid or ""):
        raise ValueError(f"QID inválido: {qid!r} (esperado Q seguido de algarismos, ex. Q131499)")
    return WIKIDATA_ENTITY + qid


def input_paths(root: Path, label: str) -> list[Path]:
    return [corpus_graph_path(root, label), root / "output" / f"corpus_entities_{label}.ttl"]


def _fingerprint(paths: list[Path]) -> dict[str, dict[str, int]]:
    return {p.as_posix(): {"bytes": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns} for p in paths}


@dataclass
class LoadInfo:
    triples: int
    seconds: float
    reused: bool
    loaded_at: str


def open_store(root: Path, label: str, reload: bool = False):
    """Store em disco com os dois grafos; carrega-o se não existir (ou com `reload`)."""

    ox = require_pyoxigraph()
    sources = input_paths(root, label)
    missing = [p for p in sources if not p.is_file()]
    if missing:
        raise FileNotFoundError("Grafo em falta: " + ", ".join(str(p) for p in missing))
    target = root / "output" / f"sparql_{label}"
    store_dir, marker = target / "store", target / "carga.json"
    fingerprint = _fingerprint(sources)
    if marker.is_file() and store_dir.is_dir() and not reload:
        info = json.loads(marker.read_text(encoding="utf-8"))
        if info["fontes"] != fingerprint:
            raise RuntimeError(f"Os grafos mudaram desde a carga de {store_dir}; "
                               "correr de novo com --recarregar.")
        return ox.Store(str(store_dir)), LoadInfo(info["triplos"], info["segundos"], True, info["data"])

    if store_dir.exists():
        shutil.rmtree(store_dir)
    marker.unlink(missing_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    store = ox.Store(str(store_dir))
    start = time.perf_counter()
    for path in sources:
        fmt = ox.RdfFormat.N_TRIPLES if path.suffix == ".nt" else ox.RdfFormat.TURTLE
        store.bulk_load(path=str(path), format=fmt)
    store.flush()
    seconds = time.perf_counter() - start
    info = LoadInfo(len(store), seconds, False, time.strftime("%Y-%m-%d %H:%M:%S"))
    marker.write_text(json.dumps({"fontes": fingerprint, "triplos": info.triples, "segundos": seconds,
                                  "data": info.loaded_at}, indent=2) + "\n", encoding="utf-8")
    return store, info


def _term_value(term):
    if term is None:
        return None
    value = term.value
    datatype = getattr(term, "datatype", None)
    if datatype is not None and datatype.value.startswith("http://www.w3.org/2001/XMLSchema#") and \
            datatype.value.rsplit("#", 1)[1] in ("integer", "long", "int", "nonNegativeInteger", "decimal"):
        return int(value) if "." not in value else float(value)
    return value


@dataclass
class QueryResult:
    name: str
    columns: list[str]
    rows: list[dict]
    seconds: float


def run_query(store, name: str, entity: str | None = None) -> QueryResult:
    ox = require_pyoxigraph()
    text = (QUERIES_DIR / f"{name}.rq").read_text(encoding="utf-8")
    substitutions = {ox.Variable("entidade"): ox.NamedNode(entity)} if entity else None
    start = time.perf_counter()
    solutions = store.query(text, substitutions=substitutions)
    columns = [v.value for v in solutions.variables]
    rows = [{c: _term_value(s[c]) for c in columns} for s in solutions]
    return QueryResult(name, columns, rows, time.perf_counter() - start)


def run_queries(store, qid: str) -> dict[str, QueryResult]:
    iri = entity_iri(qid)
    return {name: run_query(store, name, iri if name in ("entidade_por_ano", "coocorrencias") else None)
            for name in QUERY_NAMES}


# --- Comparação com o resumo do painel -------------------------------------


@dataclass
class DashboardSummary:
    totals: dict[str, int] = field(default_factory=dict)
    sections: dict[str, list[list[str]]] = field(default_factory=dict)


def parse_dashboard_summary(path: Path) -> DashboardSummary:
    """Linhas `- Nome: N` e tabelas de `resumo.md`, por título de secção."""

    summary, section = DashboardSummary(), ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            summary.sections[section] = []
        elif line.startswith("- ") and ":" in line and not section:
            name, _, value = line[2:].partition(":")
            if value.strip().isdigit():
                summary.totals[name.strip()] = int(value.strip())
        elif line.startswith("|") and section:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and not set(cells[0]) <= {"-", ":"}:
                summary.sections[section].append(cells)
    for name in summary.sections:  # tira o cabeçalho de cada tabela
        summary.sections[name] = summary.sections[name][1:]
    return summary


def verdict(dashboard, sparql) -> str:
    if dashboard is None or sparql is None:
        return "sem correspondência"
    return "igual" if dashboard == sparql else f"diferente ({dashboard} vs {sparql})"


def compare(summary: DashboardSummary, results: dict[str, QueryResult]) -> list[str]:
    lines: list[str] = []
    years = {r["ano"]: r for r in results["artigos_por_ano"].rows}
    rows = summary.sections.get("Artigos por ano", [])
    if rows:
        lines += ["### Artigos por ano\n", "| Ano | Painel | SPARQL | Resultado | Com entidade (painel) "
                  "| Com entidade (SPARQL) | Resultado |", "| --- | ---: | ---: | --- | ---: | ---: | --- |"]
        all_years = sorted({r[0] for r in rows} | set(years))
        dash = {r[0]: r for r in rows}
        for year in all_years:
            d, s = dash.get(year), years.get(year)
            d_art, d_ent = (int(d[1]), int(d[2])) if d else (None, None)
            s_art, s_ent = (s["artigos"], s["comEntidade"]) if s else (None, None)
            lines.append(f"| {year} | {d_art} | {s_art} | {verdict(d_art, s_art)} | {d_ent} | {s_ent} "
                         f"| {verdict(d_ent, s_ent)} |")
        lines.append("")
    total_articles = sum(r["artigos"] for r in years.values())
    total_entity = sum(r["comEntidade"] for r in years.values())
    for name, value in (("Artigos", total_articles), ("Com pelo menos uma entidade", total_entity)):
        if name in summary.totals:
            lines.append(f"- {name}: painel {summary.totals[name]}, SPARQL {value} — "
                         f"{verdict(summary.totals[name], value)}")
    lines.append("")

    by_label: dict[str, list[dict]] = {}
    for row in results["entidades_mais_mencionadas"].rows:
        for label in (row["rotulo"] or "").split(" | "):
            by_label.setdefault(label, []).append(row)
    for section in ("Clubes mais mencionados no texto", "Atletas mais mencionados no texto",
                    "Treinadores, estádios e competições mais mencionados"):
        rows = summary.sections.get(section, [])
        if not rows:
            continue
        lines += [f"### {section}\n", "| Entidade | Painel | SPARQL | Resultado |", "| --- | ---: | ---: | --- |"]
        for cells in rows:
            name, dashboard = cells[0], int(cells[-1])
            found = by_label.get(name, [])
            if len(found) == 1:
                lines.append(f"| {name} | {dashboard} | {found[0]['artigos']} "
                             f"| {verdict(dashboard, found[0]['artigos'])} |")
            else:
                note = "rótulo ausente do grafo" if not found else f"rótulo em {len(found)} nós"
                lines.append(f"| {name} | {dashboard} | — | sem correspondência ({note}) |")
        lines.append("")

    rows = summary.sections.get("Origem das entidades mencionadas no vocabulário", [])
    if rows:
        sparql = {(r["origem"] or NO_ORIGIN): r["entidades"] for r in results["entidades_por_origem"].rows}
        dash = {(r[0] or NO_ORIGIN): int(r[-1]) for r in rows}
        lines += ["### Entidades distintas por origem no vocabulário\n",
                  "| Origem | Painel | SPARQL | Resultado |", "| --- | ---: | ---: | --- |"]
        for origin in sorted(set(dash) | set(sparql), key=lambda o: -max(dash.get(o, 0), sparql.get(o, 0))):
            lines.append(f"| {origin} | {dash.get(origin)} | {sparql.get(origin)} "
                         f"| {verdict(dash.get(origin), sparql.get(origin))} |")
        lines.append("")
    return lines


# --- Relatório ---------------------------------------------------------------


def _table(header: tuple[str, ...], rows: list[tuple]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    lines += ["| " + " | ".join("" if v is None else str(v).replace("|", "\\|") for v in row) + " |"
              for row in rows]
    return lines + [""]


def _short(iri: str | None) -> str:
    return (iri or "").replace(WIKIDATA_ENTITY, "wd:").replace(SDH_IRI, "sdh:")


def write_report(path: Path, label: str, load: LoadInfo, results: dict[str, QueryResult], qid: str,
                 top: int, summary_path: Path, sources: list[str]) -> None:
    entities = results["entidades_mais_mencionadas"].rows
    entity_name = next((r["rotulo"] for r in entities if r["entidade"] == WIKIDATA_ENTITY + qid), None)
    load_text = (f"store reutilizado (carregado em {load.loaded_at}; a carga demorou {load.seconds:.1f} s)"
                 if load.reused else f"nesta execução ({load.loaded_at}): {load.seconds:.1f} s")
    lines = [
        f"# Consultas SPARQL sobre o grafo do corpus `{label}`\n",
        "Gerado por `python -m semantic_harvester.sparql_corpus`, sem rede, com `pyoxigraph` "
        "(store em disco) e as queries de `queries/corpus/`. A data de cada artigo é a da "
        "captura mais antiga conhecida (menor `sdh:tstamp`), como no painel.\n",
        f"- Grafos: {', '.join(f'`{s}`' for s in sources)}",
        f"- Triplos no store (distintos): {load.triples}",
        f"- Carga: {load_text}",
        "",
        "## Tempo de cada consulta\n",
        *_table(("Consulta", "Linhas", "Tempo (s)"),
                [(f"`{r.name}.rq`", len(r.rows), f"{r.seconds:.3f}") for r in results.values()]),
        "## Artigos por ano\n",
        *_table(("Ano", "Artigos", "Com entidade"),
                [(r["ano"], r["artigos"], r["comEntidade"]) for r in results["artigos_por_ano"].rows]),
        f"## Artigos que mencionam {entity_name or qid} (`wd:{qid}`), por ano\n",
        *_table(("Ano", "Artigos"), [(r["ano"], r["artigos"]) for r in results["entidade_por_ano"].rows]),
        f"Total: {sum(r['artigos'] for r in results['entidade_por_ano'].rows)}.\n",
        f"## Entidades mais mencionadas ({min(top, len(entities))} primeiras de {len(entities)})\n",
        "A categoria (clube, jogador, …) não está no grafo de entidades, só no vocabulário CSV.\n",
        *_table(("Entidade", "Rótulo", "Origem", "Artigos"),
                [(_short(r["entidade"]), r["rotulo"], r["origem"], r["artigos"]) for r in entities[:top]]),
        f"## Entidades que co-ocorrem com {entity_name or qid} "
        f"({min(top, len(results['coocorrencias'].rows))} primeiras)\n",
        *_table(("Entidade", "Rótulo", "Artigos em comum"),
                [(_short(r["outra"]), r["rotulo"], r["artigos"]) for r in results["coocorrencias"].rows[:top]]),
        "## Entidades distintas por origem no vocabulário\n",
        *_table(("Origem", "Entidades"),
                [(r["origem"] or NO_ORIGIN, r["entidades"]) for r in results["entidades_por_origem"].rows]),
        "## Comparação com o painel\n",
    ]
    if summary_path.is_file():
        lines += [
            f"Contra `{summary_path.name}` do painel (`output/prototipo_{label}/`), calculado dos CSV. "
            "\"igual\"/\"diferente\" resultam da comparação feita nesta execução. Diferenças "
            "legítimas possíveis: (1) o painel e o grafo de entidades têm de vir do mesmo "
            f"`corpus_entities_{label}.csv` e do mesmo vocabulário (o painel usa por omissão o "
            "alargado e o `corpus_entities_rdf` o original); (2) o painel conta um artigo sem "
            "captura num ano vazio, a consulta deixa-o de fora; (3) as entidades comparam-se pelo "
            "rótulo do painel, e um rótulo em mais de um nó do grafo não se compara; (4) na origem, "
            "o painel dá a cada entidade a origem de um só rótulo do vocabulário, o grafo guarda a "
            "de todos os rótulos com o mesmo QID (a entidade conta em cada origem).\n",
            *compare(parse_dashboard_summary(summary_path), results),
        ]
    else:
        lines.append(f"Sem `output/prototipo_{label}/resumo.md`: comparação não feita.")
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def run(project_root: Path | None = None, label: str = DEFAULT_LABEL, qid: str = DEFAULT_ENTITY,
        top: int = DEFAULT_TOP, reload: bool = False) -> Path:
    root = project_root or Path(__file__).resolve().parents[2]
    entity_iri(qid)  # valida antes de carregar
    store, load = open_store(root, label, reload)
    results = run_queries(store, qid)
    target = root / "output" / f"sparql_{label}"
    report = target / "relatorio.md"
    write_report(report, label, load, results, qid, top, root / "output" / f"prototipo_{label}" / "resumo.md",
                 [p.relative_to(root).as_posix() for p in input_paths(root, label)])
    del store
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m semantic_harvester.sparql_corpus",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", default=DEFAULT_LABEL, metavar="ETIQUETA",
                        help="corpus da Fase 1 (por omissão por_ano)")
    parser.add_argument("--entidade", default=DEFAULT_ENTITY, metavar="QID",
                        help=f"entidade das consultas por ano e de co-ocorrência (por omissão {DEFAULT_ENTITY})")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help="linhas das tabelas de entidades")
    parser.add_argument("--recarregar", action="store_true", help="refaz a carga do store")
    args = parser.parse_args(argv)
    try:
        report = run(label=args.corpus, qid=args.entidade, top=args.top, reload=args.recarregar)
    except (MissingDependencyError, ValueError, FileNotFoundError, RuntimeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    print(f"Relatório: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
