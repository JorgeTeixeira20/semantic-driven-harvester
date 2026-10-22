"""Corpo do artigo a partir do contentor do HTML em bruto.

Complemento da variante c′ (`article_body.py`), segundo a decisão de
2026-10-19 (`docs/experiments.md`, "Decisão de design (híbrido...)"): o
HTML serve para detetar Premium e para recuperar o corpo quando a c′ não o
encontra (por exemplo, todas as páginas `noticia.asp` de 2000–2009 medidas).

Contentores medidos sobre o HTML em disco (2026-10-22), por ordem de
tentativa — o template depende da página, não só do esquema de URL:
`div#readerBody` (2017), `div.text_container` (2018–2024), `div.bodybox`
(AMP), a tag `<aux>` (`noticia.asp`; a classe do `span` à volta muda com a
época) e, em `noticia.aspx` (2009), o `span.apreto12n` dentro da coluna
`td[width=600]`; nas `tn0cs`/`tn1cs.asp` (1999–2000), a coluna `td[width=480]`
sem título, data e antetítulo, e sem a assinatura final. Dentro deles
retiram-se os blocos medidos que não são corpo, e
sobre o texto aplicam-se os 14 marcadores de chrome da c′ mais
"Relacionadas" (blocos de chrome dentro do `bodybox` das AMP em `/detalhe/`).

Codificação: UTF-8 estrito, depois cp1252 e, por fim, latin-1 — a
declaração na página nem sempre é fiável (2002: declarada iso-8859-1, UTF-8
em 3 de 4).
Sem dependências fora da biblioteca padrão.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser

from .article_body import find_marker, fold_same_length

# (nome, teste sobre a tag, ids, classes, atributos e se está dentro da coluna principal)
CONTAINERS = (
    ("readerBody", lambda tag, ids, classes, attrs, main: tag == "div" and "readerBody" in ids),
    ("text_container", lambda tag, ids, classes, attrs, main: tag == "div" and "text_container" in classes),
    ("bodybox", lambda tag, ids, classes, attrs, main: tag == "div" and "bodybox" in classes),
    ("aux", lambda tag, ids, classes, attrs, main: tag == "aux"),
    # noticia.aspx (2009): `apreto12n` é só uma classe de tipo de letra (9 a 16 por
    # página); o corpo é o que está dentro da coluna `td[width=600]` (a votação fica fora).
    ("apreto12n", lambda tag, ids, classes, attrs, main: tag == "span" and "apreto12n" in classes and main),
    # tn0cs/tn1cs.asp (1999–2000): só tabelas e <font>, sem classes; a coluna
    # td[width=480] tem antetítulo, título, lead, corpo e data (ver OLD_SITE_SKIP).
    ("td480", lambda tag, ids, classes, attrs, main: tag == "td" and _attr(attrs, "width") == "480"),
)
MAIN_COLUMN_WIDTH = "600"
# Dentro do td480: título (size 6), data (size 0) e antetítulo (size 2 com cor)
# não são corpo; ficam o lead (size 3, itálico) e o corpo (size 2 sem cor).
OLD_SITE_SKIP_SIZES = frozenset({"6", "0"})
# Assinatura no fim do corpo do site de 1999–2000 ("CARLOS OLIVEIRA"): 2 a 4
# palavras só em maiúsculas depois do fim de uma frase.
_SIGNATURE = re.compile(r"(?<=[.!?»”\"')])\s+(?:[A-ZÀ-Ý][A-ZÀ-Ý'.-]*\s+){1,3}[A-ZÀ-Ý][A-ZÀ-Ý'.-]*\s*$")


def _attr(attrs: dict[str, str | None], name: str) -> str:
    return (attrs.get(name) or "").strip()
SKIP_TAGS = frozenset({
    "script", "style", "noscript", "template", "iframe", "button", "figure", "h1",
    "amp-analytics", "amp-ad",
})
SKIP_CLASSES = frozenset({
    "lerMaisCont", "lerMais", "btLerMais", "autorDetalhe", "pub_inside_text",
    "texto_socialShare", "adbox", "texto_autor", "container_assinatura",
    "relacionadas", "comentarBtn", "detalheAds", "pub",
})
SKIP_IDS = frozenset({"escondec", "relacContainer", "incontent"})
PREMIUM_CLASSES = frozenset({"container_assinatura", "article-premium"})
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
})
EXTRA_MARKER = re.compile(r"(?<!\w)relacionadas(?!\w)")

_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class HtmlBody:
    text: str
    found: bool
    container: str | None
    premium: bool


def decode_html(raw: bytes) -> str:
    # cp1252 antes de latin-1: as aspas e travessões “ ” ’ – do site antigo
    # (0x80–0x9F) seriam caracteres de controlo em latin-1.
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


class _ContainerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # (tag, este elemento é ignorado, é a coluna principal td[width=600])
        self.stack: list[tuple[str, bool, bool]] = []
        self.active: list[tuple[str, int]] = []  # (contentor, profundidade de abertura)
        self.parts: dict[str, list[list[str]]] = {name: [] for name, _ in CONTAINERS}
        self.premium = False

    def _skipping(self) -> bool:
        return any(skip for _, skip, _ in self.stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        ids = {values.get("id") or ""}
        if classes & PREMIUM_CLASSES:
            self.premium = True
        if tag in VOID_TAGS:
            if tag == "br":
                self._write(" ")
            return
        main_column = tag == "td" and _attr(values, "width") == MAIN_COLUMN_WIDTH
        in_main = main_column or any(main for _, _, main in self.stack)
        if not self._skipping():
            for name, matches in CONTAINERS:
                if matches(tag, ids, classes, values, in_main) and not any(n == name for n, _ in self.active):
                    self.parts[name].append([])
                    self.active.append((name, len(self.stack)))
        skip = tag in SKIP_TAGS or bool(classes & SKIP_CLASSES) or bool(ids & SKIP_IDS)
        if tag == "font" and any(n == "td480" for n, _ in self.active):
            size = _attr(values, "size")
            skip = skip or size in OLD_SITE_SKIP_SIZES or (size == "2" and bool(_attr(values, "color")))
        self.stack.append((tag, skip, main_column))
        self._write(" ")

    def handle_endtag(self, tag: str) -> None:
        # HTML antigo fecha mal as tags: fecha até à correspondente, se aberta.
        if not any(open_tag == tag for open_tag, _, _ in self.stack):
            return
        while self.stack:
            open_tag, _, _ = self.stack.pop()
            self.active = [(n, depth) for n, depth in self.active if depth < len(self.stack)]
            if open_tag == tag:
                break
        self._write(" ")

    def handle_data(self, data: str) -> None:
        if not self._skipping():
            self._write(data)

    def _write(self, data: str) -> None:
        for name, _ in self.active:
            self.parts[name][-1].append(data)


def _cut_chrome(text: str) -> str:
    folded = fold_same_length(text)
    stops = []
    marker = find_marker(text, folded, 0)
    if marker is not None:
        stops.append(marker[0])
    for hit in EXTRA_MARKER.finditer(folded):
        if text[hit.start()].isupper():
            stops.append(hit.start())
            break
    return text[:min(stops)] if stops else text


def _clean(parts: list[str]) -> str:
    text = unicodedata.normalize("NFC", _SPACES.sub(" ", "".join(parts)).strip())
    return _cut_chrome(text).strip()


def extract_html_body(raw: bytes) -> HtmlBody:
    parser = _ContainerParser()
    parser.feed(decode_html(raw))
    parser.close()
    for name, _ in CONTAINERS:
        occurrences = [_clean(part) for part in parser.parts[name]]
        if name == "aux":
            text = " ".join(t for t in occurrences if t)
        elif name == "td480":
            text = _SIGNATURE.sub("", max(occurrences, key=len, default="")).strip()
        else:
            # Uma página pode ter mais de um contentor igual (em 2024, o
            # primeiro `text_container` é um destaque promocional): o mais longo.
            text = max(occurrences, key=len, default="")
        if text:
            return HtmlBody(text, True, name, parser.premium)
    return HtmlBody("", False, None, parser.premium)


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog="python -m semantic_harvester.html_body",
        description="Mostra o corpo extraído de ficheiros HTML (validação manual; sem rede).",
    )
    parser.add_argument("ficheiros", nargs="+", type=Path)
    args = parser.parse_args(argv)
    print("ficheiro\tcontentor\tpremium\tpalavras\tinicio")
    for path in args.ficheiros:
        body = extract_html_body(path.read_bytes())
        print(f"{path.name}\t{body.container or '-'}\t{body.premium}\t"
              f"{len(body.text.split())}\t{body.text[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
