"""Amostra A: 40 pares artigo–entidade de artigos de 2010–2016 (passagem 2 do `completo`).

Só menções no texto (`tipo=entidade`, `origem=texto`) de Artigos cuja captura mais antiga é de
2010–2016 (a data de `output/prototipo_completo/data.js`). Os pares ordenam-se por (URL,
rótulo) antes do sorteio, para o resultado só depender da semente. Escreve a lista
`data/processed/amostra_pares_2010_2016.csv` (a avaliar depois de versionada) com o trecho
em volta da menção, para a leitura.

    python scripts/avaliacao_cobertura/amostra_pares_2010_2016.py [semente]
"""

import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
csv.field_size_limit(1 << 30)

from amostra_entidades_novas import body_of, fold, vocabulary  # noqa: E402

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261028
SIZE = 40


def main() -> None:
    data = (ROOT / "output/prototipo_completo/data.js").read_text(encoding="utf-8")
    articles = json.loads(data.removeprefix("window.SDH_DATA = ").rstrip().rstrip(";"))["articles"]
    info = {a[2]: (a[0], a[1]) for a in articles if "2010" <= a[0][:4] <= "2016"}
    variants = {r["rotulo"]: [r["rotulo"]] + [v for v in r["variantes"].split("|") if v]
                for r in vocabulary("completo")}
    pairs = set()
    with (ROOT / "output/corpus_entities_completo.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["tipo"] == "entidade" and row["origem"] == "texto" and row["artigo"] in info:
                pairs.add((row["artigo"], row["rotulo"], row["categoria"]))
    pairs = sorted(pairs)
    print(f"pares de 2010–2016 (menções no texto): {len(pairs)}; artigos: {len({p[0] for p in pairs})}")
    chosen = random.Random(SEED).sample(pairs, SIZE)
    out = ROOT / "data/processed/amostra_pares_2010_2016.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["n", "url", "tstamp", "titulo", "entidade", "categoria", "trecho"])
        for n, (url, rotulo, categoria) in enumerate(chosen, 1):
            tstamp, title = info[url]
            body = body_of(url, tstamp)
            folded = fold(body)
            snippet = ""
            for name in variants.get(rotulo, [rotulo]):
                m = re.search(r"(?<!\w)" + re.escape(fold(name)) + r"(?!\w)", folded)
                if m:
                    snippet = body[max(0, m.start() - 200): m.end() + 200].replace("\n", " ")
                    break
            writer.writerow([n, url, tstamp, title, rotulo, categoria, snippet])
    print("escrito", out)


if __name__ == "__main__":
    main()
