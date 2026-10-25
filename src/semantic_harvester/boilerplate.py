"""Texto repetido entre artigos que não é notícia (antes de procurar entidades).

Diagnóstico de 2026-10-25 (`docs/experiments.md`, "Diagnóstico de falhas no
painel"): 15 de 40 menções ao acaso eram falsas, por tabelas laterais, por
manchetes de outras notícias dentro do corpo e por rodapés. Este módulo marca
dois tipos de trechos, que o Caminho B deixa de ler:

1. **Frases repetidas com sinais combinados**, não só pela frequência (uma
   citação, um resultado ou um comunicado também se repetem). Uma frase é
   retirada só se aparecer em pelo menos `MIN_ARTICLES` artigos **e** em
   pelo menos `MIN_MONTHS` meses diferentes: uma citação ou um resultado
   repetem-se em notícias do mesmo acontecimento, perto no tempo; um rodapé,
   um aviso de Premium ou um widget repetem-se ao longo de meses. Revisão de
   2026-10-25 (avaliação da terceira corrida): uma frase em pelo menos
   `MIN_ARTICLES_ANY_TIME` artigos sai mesmo em poucos meses (as tabelas de
   2001/02 foram capturadas numa janela curta); e as linhas de ficha de jogo
   ("Treinador: …", "Jogo disputado no Estádio …", "Assistência: …") nunca
   saem, porque são texto da notícia que se repete por o treinador ou o
   estádio serem os mesmos.
2. **Manchetes de outras notícias** dentro do corpo (listas de "mais
   notícias"): uma sequência de palavras igual ao título de *outro* artigo do
   corpus, com pelo menos `MIN_TITLE_WORDS` palavras, que **não continua**
   numa palavra minúscula (numa lista de manchetes, a seguinte começa por
   maiúscula; "Benfica vence o FC Porto por 2-1" numa frase da notícia não é
   retirado). O título do próprio artigo nunca conta, mesmo que outro artigo
   tenha o mesmo título; os títulos comparam-se **sem o sufixo do site**
   ("… - Futebol - Jornal Record"), e um trecho no início do corpo nunca sai
   (82 % dos trechos retirados na terceira corrida eram o título do próprio
   artigo, guardado com sufixo, repetido no início do corpo).

Os trechos retirados partem o texto: as palavras de um lado e do outro não se
juntam numa menção. Sem rede; tudo calculado sobre o corpo já extraído.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

MIN_ARTICLES = 20
MIN_MONTHS = 3
MIN_ARTICLES_ANY_TIME = 100
# Início (palavras normalizadas) das linhas de ficha de jogo, que nunca saem.
MATCH_SHEET_PREFIXES = (
    "treinador", "treinadores", "arbitro", "arbitros", "assistencia", "jogo disputado",
    "jogo no estadio", "jogo realizado", "estadio", "suplentes", "suplentes nao utilizados",
    "golos", "marcadores", "ao intervalo", "disciplina", "substituicoes", "cartoes",
)
MIN_SENTENCE_WORDS = 3
MIN_TITLE_WORDS = 6

_WORD_RE = re.compile(r"\w+")
# Fim de frase: pontuação final seguida de espaço e de maiúscula ou dígito (a
# mesma regra do diagnóstico; as abreviaturas "V. Setúbal" também cortam).
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÀ-Ý0-9«\"“])")


def _fold_word(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def words(text: str) -> list[str]:
    return [_fold_word(w) for w in _WORD_RE.findall(unicodedata.normalize("NFC", text))]


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """(início, fim) de cada frase no texto."""

    spans, start = [], 0
    for cut in _SENTENCE_END.finditer(text):
        spans.append((start, cut.start()))
        start = cut.end()
    spans.append((start, len(text)))
    return [(a, b) for a, b in spans if text[a:b].strip()]


def sentence_key(sentence: str) -> str | None:
    tokens = words(sentence)
    return " ".join(tokens) if len(tokens) >= MIN_SENTENCE_WORDS else None


def is_match_sheet(key: str) -> bool:
    return any(key == p or key.startswith(p + " ") for p in MATCH_SHEET_PREFIXES)


_TITLE_SUFFIX = re.compile(r"\s+[-–|]\s+.*\brecord\b.*$", re.IGNORECASE)


def title_words(title: str) -> tuple[str, ...]:
    """Palavras do título sem o sufixo do site ("… - Futebol - Jornal Record")."""

    return tuple(words(_TITLE_SUFFIX.sub("", unicodedata.normalize("NFC", title))))


def _continues_lowercase(text: str, matches: list[re.Match], after: int) -> bool:
    """A palavra a seguir ao trecho existe, vem logo a seguir (sem pontuação) e é minúscula."""

    if after >= len(matches):
        return False
    gap = text[matches[after - 1].end():matches[after].start()]
    return gap.strip() == "" and matches[after].group()[:1].islower()


@dataclass
class Boilerplate:
    repeated: set[str] = field(default_factory=set)
    # (primeiras duas palavras) → títulos (palavras) e os artigos com esse título
    titles: dict[tuple[str, str], list[tuple[tuple[str, ...], frozenset[str]]]] = field(default_factory=dict)
    sentence_stats: dict[str, tuple[int, int]] = field(default_factory=dict)

    def spans(self, text: str, article: str) -> list[tuple[int, int, str]]:
        """Trechos a retirar no texto em NFC: (início, fim, motivo), por ordem."""

        text = unicodedata.normalize("NFC", text)
        found = [(a, b, "frase_repetida") for a, b in sentence_spans(text)
                 if sentence_key(text[a:b]) in self.repeated]
        matches = list(_WORD_RE.finditer(text))
        folded = [_fold_word(m.group()) for m in matches]
        i = 1  # o início do corpo nunca sai (é onde o título do próprio artigo se repete)
        while i < len(folded) - 1:
            best = 0
            for title, owners in self.titles.get((folded[i], folded[i + 1]), ()):
                n = len(title)
                if (article not in owners and n > best and tuple(folded[i:i + n]) == title
                        and not _continues_lowercase(text, matches, i + n)):
                    best = n
            if best:
                found.append((matches[i].start(), matches[i + best - 1].end(), "manchete"))
                i += best
            else:
                i += 1
        return sorted(found)

    def split(self, text: str, article: str) -> tuple[list[str], list[str]]:
        """O texto partido nos trechos retirados, e o motivo de cada trecho."""

        text = unicodedata.normalize("NFC", text)
        spans = self.spans(text, article)
        out, pos = [], 0
        for start, end, _ in spans:
            if start > pos:
                out.append(text[pos:start])
            pos = max(pos, end)
        out.append(text[pos:])
        return [p for p in out if p.strip()], [reason for _, _, reason in spans]

    def pieces(self, text: str, article: str) -> list[str]:
        return self.split(text, article)[0]


def build(
    bodies: dict[str, list[tuple[str, str]]],
    titles: dict[str, str],
    min_articles: int = MIN_ARTICLES,
    min_months: int = MIN_MONTHS,
) -> Boilerplate:
    """`bodies`: artigo → [(tstamp, corpo)] das capturas; `titles`: título por artigo."""

    counts: Counter[str] = Counter()
    # Mês da primeira ocorrência; só as frases vistas em mais de um mês têm um conjunto
    # (poupa memória: a grande maioria das frases aparece num só artigo).
    first_month: dict[str, str] = {}
    months_of: dict[str, set[str]] = {}
    for captures in bodies.values():
        keys: dict[str, str] = {}
        for tstamp, text in captures:
            text = unicodedata.normalize("NFC", text)
            for a, b in sentence_spans(text):
                key = sentence_key(text[a:b])
                if key is not None:
                    keys.setdefault(key, tstamp[:6])
        counts.update(keys.keys())
        for key, month in keys.items():
            first = first_month.setdefault(key, month)
            if month != first:
                seen = months_of.setdefault(key, {first})
                if len(seen) < min_months:
                    seen.add(month)
    result = Boilerplate()
    for key, n in counts.items():
        if n >= min_articles:
            months = len(months_of.get(key, ())) or 1
            result.sentence_stats[key] = (n, months)
            if (months >= min_months or n >= MIN_ARTICLES_ANY_TIME) and not is_match_sheet(key):
                result.repeated.add(key)

    own: dict[tuple[str, ...], set[str]] = {}
    for article, title in titles.items():
        tokens = title_words(title)
        if len(tokens) >= MIN_TITLE_WORDS:
            own.setdefault(tokens, set()).add(article)
    for tokens, owners in own.items():
        result.titles.setdefault(tokens[:2], []).append((tokens, frozenset(owners)))
    return result
