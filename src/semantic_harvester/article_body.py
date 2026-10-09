"""Corpo do artigo delimitado por âncoras literais (variante c′).

Adotado nos Caminhos D e B (`docs/experiments.md`, "Variante (c′)"). Sem
dependências do resto do pacote, para poder ser usado por `corpus_redundancy`
e `corpus_entities`.

- **Início:** o título do artigo dentro do texto, a seguir ao título da
  página (páginas normais: o que vem antes do primeiro " - "; páginas AMP,
  sem esse sufixo: o que vem antes de " Home ", procurado depois de
  "Home"). Uma ocorrência do título seguida logo de um marcador é uma
  listagem do menu e é ignorada.
- **Fim:** o primeiro dos 14 marcadores de bloco de chrome depois do início.
  Comparação sem acentos e sem distinguir o resto da capitalização, mas com
  limites de palavra e com a **primeira letra maiúscula no texto original**
  (os cabeçalhos de bloco começam sempre com maiúscula; "os mais recentes
  rumores", a meio de uma frase, não corta).
- **Sem início localizável:** corpo vazio, captura "sem corpo".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MARKERS = (
    "Mais notícias", "O Record recomenda para si", "Mais Fotos", "Mais Hora Record",
    "Últimas Notícias", "Mais Recentes", "Mais Vistas", "Mais Comentadas",
    "Notícias MAIS", "Veja também", "Mais Vídeos", "Enviar artigo por email",
    "Leia este artigo na íntegra", "Mais Premium",
)
TITLE_WINDOW = 300
NO_BODY = "sem_corpo"

_SPACES = re.compile(r"\s+")


def fold_same_length(text: str) -> str:
    """Minúsculas e sem acentos, um carácter por carácter (mesmas posições)."""

    return "".join(unicodedata.normalize("NFD", ch)[0].lower() for ch in text)


_MARKER_PATTERNS = [
    re.compile(r"(?<!\w)" + re.escape(fold_same_length(m)) + r"(?!\w)") for m in MARKERS
]


def find_marker(text: str, folded: str, start: int) -> tuple[int, str] | None:
    """Primeiro marcador a partir de `start` cuja primeira letra é maiúscula no original."""

    best: tuple[int, str] | None = None
    for marker, pattern in zip(MARKERS, _MARKER_PATTERNS):
        for hit in pattern.finditer(folded, start):
            if text[hit.start()].isupper():
                if best is None or hit.start() < best[0]:
                    best = (hit.start(), marker)
                break
    return best


@dataclass(frozen=True)
class Body:
    text: str
    found: bool
    end_marker: str | None


def page_title(text: str) -> tuple[str, int] | None:
    """(título, posição a partir da qual procurar o corpo), ou None."""

    head = text[:TITLE_WINDOW]
    dash, home = head.find(" - "), head.find(" Home ")
    if dash > 0 and (home < 0 or dash < home):
        return text[:dash].strip(), 1
    if home > 0:
        return text[:home].strip(), home + len(" Home ")
    return None


def extract_body(raw: str) -> Body:
    text = unicodedata.normalize("NFC", _SPACES.sub(" ", raw)).strip()
    folded = fold_same_length(text)
    located = page_title(text)
    if located is None or not located[0]:
        return Body("", False, None)
    title, search_from = located
    title_folded = fold_same_length(title)
    start = None
    position = folded.find(title_folded, search_from)
    while position >= 0:
        after = position + len(title_folded)
        following = find_marker(text, folded, after)
        # Título seguido logo de um marcador: listagem do menu, não o artigo.
        if following is None or folded[after:following[0]].strip():
            start = position
            break
        position = folded.find(title_folded, after)
    if start is None:
        return Body("", False, None)
    end = find_marker(text, folded, start + len(title_folded))
    stop = end[0] if end else len(text)
    return Body(text[start:stop].strip(), True, end[1] if end else None)
