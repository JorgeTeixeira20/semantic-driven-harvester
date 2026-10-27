"""Amostra de 50 entidades aceites novas do vocabulário híbrido do `completo` (passo 9).

Novas = origem `candidato` no híbrido do `completo` e QID ausente do híbrido do `por_ano`.
25 com >= 50 artigos e 25 com 10-49 (artigos com a entidade no texto, passagem 2).
Para cada uma, um artigo de exemplo ao acaso e o trecho em volta da primeira variante
encontrada no corpo. Só leitura; escreve `data/processed/amostra_entidades_novas_completo.csv`.

    python scripts/avaliacao_cobertura/amostra_entidades_novas.py [semente]
"""

import csv
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
csv.field_size_limit(1 << 30)

from semantic_harvester.arquivo_client import ArquivoClient  # noqa: E402
from semantic_harvester.corpus_redundancy import Capture, _body_with_html  # noqa: E402

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261031


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def vocabulary(label: str) -> list[dict[str, str]]:
    path = ROOT / f"data/processed/caminho_b_vocabulario_hibrido_{label}.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def body_of(url: str, tstamp: str) -> str:
    name = ArquivoClient._text_filename({"originalURL": url, "tstamp": tstamp})
    text_path = ROOT / "data/raw/texts" / name
    if not text_path.is_file():
        return ""
    html_path = ROOT / "data/raw/original_html" / (text_path.stem + ".html")
    capture = Capture(article=url, tstamp=tstamp, digest=None, content_length=None, status_code=None,
                      text=text_path.read_text(encoding="utf-8"),
                      html_path=html_path if html_path.is_file() else None)
    return _body_with_html(capture).text or ""


def main() -> None:
    old_qids = {r["wikidata"] for r in vocabulary("por_ano")}
    new = {r["rotulo"]: r for r in vocabulary("completo")
           if r["origem"] == "candidato" and r["wikidata"] not in old_qids}
    articles_of: dict[str, set[str]] = defaultdict(set)
    with (ROOT / "output/corpus_entities_completo.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["tipo"] == "entidade" and row["origem"] == "texto" and row["rotulo"] in new:
                articles_of[row["rotulo"]].add(row["artigo"])
    data = (ROOT / "output/prototipo_completo/data.js").read_text(encoding="utf-8")
    articles = json.loads(data.removeprefix("window.SDH_DATA = ").rstrip().rstrip(";"))["articles"]
    info = {a[2]: (a[0], a[1]) for a in articles}

    big = sorted(r for r, urls in articles_of.items() if len(urls) >= 50)
    small = sorted(r for r, urls in articles_of.items() if 10 <= len(urls) < 50)
    print(f"novas: {len(new)}; com artigos no texto: {len(articles_of)}; >=50: {len(big)}; 10-49: {len(small)}")
    rng = random.Random(SEED)
    chosen = [("≥50", r) for r in rng.sample(big, 25)] + [("10–49", r) for r in rng.sample(small, 25)]

    out = ROOT / "data/processed/amostra_entidades_novas_completo.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["n", "estrato", "rotulo", "categoria", "qid", "modalidade", "variantes", "artigos",
                         "url_exemplo", "titulo_exemplo", "trecho"])
        for n, (stratum, rotulo) in enumerate(chosen, 1):
            row = new[rotulo]
            urls = sorted(articles_of[rotulo])
            names = [rotulo] + [v for v in row["variantes"].split("|") if v]
            snippet, example = "", urls[0]
            for url in rng.sample(urls, min(len(urls), 8)):
                body = body_of(url, info[url][0]) if url in info else ""
                folded = fold(body)
                for name in names:
                    m = re.search(r"(?<!\w)" + re.escape(fold(name)) + r"(?!\w)", folded)
                    if m:
                        snippet = body[max(0, m.start() - 160): m.end() + 160].replace("\n", " ")
                        example = url
                        break
                if snippet:
                    break
            writer.writerow([n, stratum, rotulo, row["categoria"], row["wikidata"], row["modalidade"],
                             row["variantes"], len(urls), example, info.get(example, ("", ""))[1], snippet])
    print("escrito", out)


if __name__ == "__main__":
    main()
