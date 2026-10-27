"""Amostra B: 15 notícias de 2010–2016 do `completo` para anotar (protocolo de cobertura).

Ao acaso (semente por omissão 20261029) entre **todos** os Artigos cuja captura mais antiga é
de 2010–2016, incluindo sem corpo e Premium (a medida é de ponta a ponta). Escreve
`data/processed/amostra_cobertura_2010_2016.csv` (n, estrato, url, tstamp, esquema) e
deve ser versionado **antes** de anotar (sem a origem do corpo, para não influenciar a anotação).

    python scripts/avaliacao_cobertura/amostra_cobertura_2010_2016.py [semente]
"""

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261029
SIZE = 15


def scheme(url: str) -> str:
    for marker in ("interior.aspx?content_id", "/detalhe/", "noticia.aspx?id", "noticia.asp?id", "shownews.asp?id"):
        if marker in url:
            return marker
    return "outro"


def main() -> None:
    data = (ROOT / "output/prototipo_completo/data.js").read_text(encoding="utf-8")
    d = json.loads(data.removeprefix("window.SDH_DATA = ").rstrip().rstrip(";"))
    pool = sorted((a[2], a[0]) for a in d["articles"] if "2010" <= a[0][:4] <= "2016")
    print(f"artigos de 2010–2016: {len(pool)}")
    chosen = random.Random(SEED).sample(pool, SIZE)
    with (ROOT / "data/processed/amostra_cobertura_2010_2016.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["n", "estrato", "url", "tstamp", "esquema"])
        for n, (url, tstamp) in enumerate(chosen, 1):
            writer.writerow([n, "2010-2016", url, tstamp, scheme(url)])


if __name__ == "__main__":
    main()
