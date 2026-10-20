"""Identidade de `originalURL`: o que conta como a mesma página do Record.

Partilhado por `corpus_classification` (agrupar recursos) e `corpus_rdf`
(aceitar capturas de variantes do mesmo URL), para que as duas fases usem a
mesma regra. Só serve para **comparar**: o `originalURL` guardado continua a
ser o URL real.

Parâmetros de rastreio da origem do clique (`ref`, `utm_*`, `act`, `est`)
não identificam conteúdo e são ignorados na comparação; qualquer outro
parâmetro é mantido. No site antigo do Record a query string **é** o
identificador do artigo (`interior.aspx?content_id/x3d730429`), por isso a
query nunca é descartada por inteiro (`docs/experiments.md`).
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

TRACKING_PARAMS = frozenset({"ref", "act", "est"})
TRACKING_PREFIXES = ("utm_",)


def is_tracking_param(name: str) -> bool:
    name = name.lower()
    return name in TRACKING_PARAMS or name.startswith(TRACKING_PREFIXES)


def strip_tracking_params(query: str) -> str:
    """Remove só os parâmetros de rastreio, preservando os outros tal como estão."""

    kept = [part for part in query.split("&") if part and not is_tracking_param(part.split("=", 1)[0])]
    return "&".join(kept)


def has_tracking_params(url: str) -> bool:
    query = urlsplit(url).query
    return strip_tracking_params(query) != query


def without_tracking(url: str) -> str:
    """O URL sem parâmetros de rastreio (o resto, incluindo o esquema, intacto)."""

    head, sep, query = url.partition("?")
    if not sep:
        return url
    kept = strip_tracking_params(query)
    return f"{head}?{kept}" if kept else head


def strip_scheme(url: str) -> str:
    return url.split("://", 1)[-1]


def normalize_for_grouping(url: str) -> str:
    """Remove esquema, parâmetros de rastreio, barras repetidas e uma barra final.

    Usado só para decidir se dois URLs são a mesma página modulo variação
    cosmética — nunca para gerar identificadores (esses continuam a usar o
    `originalURL` canónico tal como veio da descoberta/classificação).
    """

    head, _, query = strip_scheme(url).partition("?")
    collapsed = re.sub(r"/{2,}", "/", head).rstrip("/")
    query = strip_tracking_params(query)
    return f"{collapsed}?{query}" if query else collapsed
