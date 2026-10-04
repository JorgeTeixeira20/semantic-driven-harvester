"""Classificação Artigo vs. redirecionamento/não-artigo (Caminho A, passo 6).

Implementa a regra proposta e justificada em `docs/experiments.md`
("Classificação Artigo vs. redirecionamento/não-artigo"), com base apenas
em evidência já recolhida nas Fases 1–2 do protocolo de queries — não faz
pedidos novos à API.

Antes de classificar, agrupa `originalURL` que só diferem no esquema
(`http://`/`https://`) ou em parâmetros de rastreio (`ref`, `utm_*`, `act`,
`est`; ver `url_identity.py`) num único recurso. O URL canónico guardado é um
dos URLs reais do grupo: prefere `https://`, depois o URL sem parâmetros de
rastreio, depois o de mais capturas. Variantes só de esquema devolveram os
mesmos `tstamp` na Fase 2 (não se somam); variantes de rastreio devolveram
capturas distintas (somam-se). As outras formas ficam na coluna `variantes`,
para `corpus_rdf` juntar o raw de todas.

Um recurso é classificado como `Artigo` só se nenhuma das três condições
seguintes se verificar:

1. `/sabermais/` no caminho do URL — página de referência/perfil.
2. `title` igual a ou começado por "Object moved" — página de
   redirecionamento arquivada.
3. Número de capturas (Fase 2) superior a `CAPTURES_THRESHOLD` — página
   persistente/reutilizada, não uma publicação editorial pontual.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from .url_identity import has_tracking_params, strip_scheme, without_tracking

CAPTURES_THRESHOLD = 100

REASON_ARTIGO = "artigo"
REASON_SABERMAIS = "sabermais"
REASON_OBJECT_MOVED = "object_moved"
REASON_CAPTURES_OUTLIER = "captures_outlier"


@dataclass(frozen=True)
class ClassificationResult:
    original_url: str
    title: str
    captures: int
    is_artigo: bool
    reason: str
    variantes: str = ""


def canonical_key(url: str) -> str:
    """Chave de agrupamento: sem esquema e sem parâmetros de rastreio."""

    return strip_scheme(without_tracking(url))


def choose_canonical_url(urls: list[str], captures_by_url: dict[str, int] | None = None) -> str:
    """Prefere https, depois sem parâmetros de rastreio, depois mais capturas."""

    captures_by_url = captures_by_url or {}
    return min(urls, key=lambda url: (
        not url.startswith("https://"),
        has_tracking_params(url),
        -captures_by_url.get(url, 0),
        url,
    ))


def group_captures(urls: list[str], captures_by_url: dict[str, int]) -> int:
    """Capturas do grupo: variantes só de esquema contam uma vez; as de rastreio somam-se."""

    by_scheme_free: dict[str, int] = {}
    for url in urls:
        key = strip_scheme(url)
        by_scheme_free[key] = max(by_scheme_free.get(key, 0), captures_by_url.get(url, 0))
    return sum(by_scheme_free.values())


def classify(original_url: str, title: str | None, captures: int) -> ClassificationResult:
    path = urlsplit(original_url).path
    normalized_title = (title or "").strip().lower()

    if "/sabermais/" in path:
        reason = REASON_SABERMAIS
    elif normalized_title.startswith("object moved"):
        reason = REASON_OBJECT_MOVED
    elif captures > CAPTURES_THRESHOLD:
        reason = REASON_CAPTURES_OUTLIER
    else:
        reason = REASON_ARTIGO

    return ClassificationResult(
        original_url=original_url,
        title=title or "",
        captures=captures,
        is_artigo=(reason == REASON_ARTIGO),
        reason=reason,
    )


def load_phase1_titles(captures_csv: Path) -> dict[str, dict[str, str]]:
    """Um registo por `originalURL`, mantendo o de maior `num_queries_matched`."""

    by_url: dict[str, dict[str, str]] = {}
    with captures_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            url = row["original_url"]
            existing = by_url.get(url)
            if existing is None or int(row["num_queries_matched"]) > int(
                existing["num_queries_matched"]
            ):
                by_url[url] = row
    return by_url


def load_phase2_captures(history_csv: Path) -> dict[str, int]:
    captures_by_url: dict[str, int] = {}
    with history_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            captures_by_url[row["original_url"]] = int(row["captures"])
    return captures_by_url


def classify_corpus(
    captures_csv: Path, history_csv: Path
) -> list[ClassificationResult]:
    phase1 = load_phase1_titles(captures_csv)
    captures_by_url = load_phase2_captures(history_csv)

    groups: dict[str, list[str]] = {}
    for url in phase1:
        groups.setdefault(canonical_key(url), []).append(url)

    results: list[ClassificationResult] = []
    for urls in groups.values():
        chosen = choose_canonical_url(urls, captures_by_url)
        title = phase1[chosen]["title"]
        result = classify(chosen, title, group_captures(urls, captures_by_url))
        variants = "|".join(sorted(url for url in urls if url != chosen))
        results.append(replace(result, variantes=variants))

    results.sort(key=lambda result: result.original_url)
    return results


def write_csv(results: list[ClassificationResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0])), lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


def write_summary_markdown(results: list[ClassificationResult], path: Path) -> None:
    by_reason: dict[str, list[ClassificationResult]] = {}
    for result in results:
        by_reason.setdefault(result.reason, []).append(result)

    artigos = by_reason.get(REASON_ARTIGO, [])
    sabermais = by_reason.get(REASON_SABERMAIS, [])
    moved = by_reason.get(REASON_OBJECT_MOVED, [])
    outliers = by_reason.get(REASON_CAPTURES_OUTLIER, [])

    lines = [
        "# Classificação Artigo vs. redirecionamento/não-artigo (passo 6)\n",
        "Regra e justificação em `docs/experiments.md`. Execução real sobre "
        "os dados já recolhidos nas Fases 1–2, sem pedidos novos à API.\n",
        "## Resumo\n",
        f"- Recursos distintos (depois de agrupar variantes de esquema http/https "
        f"e de parâmetros de rastreio): {len(results)}",
        f"- Recursos com variantes de URL agrupadas: "
        f"{sum(1 for r in results if r.variantes)}",
        f"- Classificados como Artigo: {len(artigos)}",
        f"- Excluídos — `/sabermais/`: {len(sabermais)}",
        f"- Excluídos — `Object moved`: {len(moved)}",
        f"- Excluídos — capturas > {CAPTURES_THRESHOLD}: {len(outliers)}",
        "\n## Excluídos — /sabermais/\n",
        "| originalURL | title | capturas |",
        "| --- | --- | ---: |",
    ]
    for result in sabermais:
        lines.append(f"| {result.original_url} | {result.title} | {result.captures} |")

    lines.extend(
        [
            "\n## Excluídos — Object moved\n",
            "| originalURL | capturas |",
            "| --- | ---: |",
        ]
    )
    for result in moved:
        lines.append(f"| {result.original_url} | {result.captures} |")

    lines.extend(
        [
            "\n## Excluídos — capturas acima do limiar\n",
            "| originalURL | title | capturas |",
            "| --- | --- | ---: |",
        ]
    )
    for result in sorted(outliers, key=lambda r: -r.captures):
        lines.append(f"| {result.original_url} | {result.title} | {result.captures} |")

    lines.append(
        "\nLista completa (incluindo os classificados como Artigo) em "
        "`output/corpus_classification.csv`."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_classification(project_root: Path | None = None) -> list[ClassificationResult]:
    root = project_root or Path(__file__).resolve().parents[2]
    captures_csv = root / "output" / "corpus_phase1_captures.csv"
    history_csv = root / "output" / "corpus_phase2_history.csv"

    results = classify_corpus(captures_csv, history_csv)

    write_csv(results, root / "output" / "corpus_classification.csv")
    write_summary_markdown(results, root / "output" / "corpus_classification_summary.md")
    return results


def main() -> int:
    results = run_classification()
    artigos = [r for r in results if r.is_artigo]
    print(f"Recursos distintos: {len(results)}")
    print(f"Classificados como Artigo: {len(artigos)}")
    print(
        "Relatórios: output/corpus_classification.csv, "
        "output/corpus_classification_summary.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
