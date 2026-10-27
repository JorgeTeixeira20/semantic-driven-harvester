"""Compara a anotação de 2010–2016 com as passagens 1 e 2 do `completo` (amostra B).

Lê `data/processed/amostra_cobertura_2010_2016.csv` e `anotacao_cobertura_2010_2016.csv` (só os
artigos anotados) e os CSV de entidades das duas passagens. Para cada entidade anotada:
`certa` (o sistema encontrou-a), `falhada` (com motivo) e, para cada entidade do sistema sem
anotação, `errada`. Motivos e equivalências manuais ficam em `MANUAL` (lido no fim da execução
de diagnóstico, depois de ver as falhas). Escreve `data/processed/avaliacao_cobertura_2010_2016.csv`.

    python scripts/avaliacao_cobertura/comparar_2010_2016.py
"""

import collections
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
csv.field_size_limit(1 << 30)

from amostra_entidades_novas import body_of, fold, vocabulary  # noqa: E402

PASSES = {
    1: (ROOT / "output/caminho_b_completo_passagem1/corpus_entities_completo.csv",
        ROOT / "data/processed/caminho_b_vocabulario_wikidata_alargado.csv"),
    2: (ROOT / "output/corpus_entities_completo.csv",
        ROOT / "data/processed/caminho_b_vocabulario_hibrido_completo.csv"),
}
# (artigo, entidade anotada) -> rótulo do vocabulário (mesma entidade com outro nome) / motivo e nota.
EQUIV: dict[tuple[int, str], str] = {}
FAIL: dict[tuple[int, str], tuple[str, str, str]] = {}   # -> (alvo no vocabulário ou "", motivo, nota)
WRONG: dict[tuple[int, str], tuple[str, str]] = {}       # (artigo, rótulo do sistema) -> (motivo, nota)
MANUAL = Path(__file__).with_name("comparar_2010_2016_manual.json")


def nf(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", fold(text))).strip()


def load_manual() -> None:
    if not MANUAL.is_file():
        return
    data = json.loads(MANUAL.read_text(encoding="utf-8"))
    for key, value in data.get("equiv", {}).items():
        n, name = key.split("|", 1)
        EQUIV[(int(n), name)] = value
    for key, value in data.get("falhada", {}).items():
        n, name = key.split("|", 1)
        FAIL[(int(n), name)] = tuple(value)
    for key, value in data.get("errada", {}).items():
        n, name = key.split("|", 1)
        WRONG[(int(n), name)] = tuple(value)


def main() -> None:
    load_manual()
    sample = {int(r["n"]): r for r in csv.DictReader(
        (ROOT / "data/processed/amostra_cobertura_2010_2016.csv").open(encoding="utf-8"))}
    annotation = [r for r in csv.DictReader(
        (ROOT / "data/processed/anotacao_cobertura_2010_2016.csv").open(encoding="utf-8"))]
    done = {int(r["n"]) for r in annotation}
    data = (ROOT / "output/prototipo_completo/data.js").read_text(encoding="utf-8")
    d = json.loads(data.removeprefix("window.SDH_DATA = ").rstrip().rstrip(";"))
    body_origin = {a[2]: d["bodies"][a[9]] for a in d["articles"]}
    out, rows, names, by_label = [], {}, {}, {}
    for number, (path, vocab_path) in PASSES.items():
        voc = list(csv.DictReader(vocab_path.open(encoding="utf-8")))
        by_label[number] = {r["rotulo"]: r for r in voc}
        names[number] = collections.defaultdict(list)
        for r in voc:
            for form in [r["rotulo"]] + [v for v in r["variantes"].split("|") if v]:
                names[number][nf(form)].append(r["rotulo"])
        urls = {sample[n]["url"] for n in done}
        found: dict[str, set[str]] = collections.defaultdict(set)
        for r in csv.DictReader(path.open(encoding="utf-8")):
            if r["tipo"] == "entidade" and r["origem"] == "texto" and r["artigo"] in urls:
                found[r["artigo"]].add(r["rotulo"])
        rows[number] = found
    for n in sorted(done):
        s = sample[n]
        body = body_of(s["url"], s["tstamp"])
        origin = body_origin.get(s["url"], "")
        for number in (2, 1):
            system = rows[number].get(s["url"], set())
            used = set()
            for a in (r for r in annotation if int(r["n"]) == n):
                key = (n, a["entidade"])
                hit = [x for x in names[number].get(nf(a["entidade"]), []) if x in system]
                if not hit and key in EQUIV and EQUIV[key] in system:
                    hit = [EQUIV[key]]
                base = dict(artigo=n, esquema=s["esquema"], entidade=a["entidade"], categoria=a["categoria"],
                            qid=a["qid"], passagem=number)
                if hit:
                    used.add(hit[0])
                    out.append({**base, "resultado": "certa", "motivo": "", "sistema": hit[0], "nota": ""})
                    continue
                if not body:
                    reason, note, target = "sem_corpo", f"origem do corpo: {origin or 'sem corpo'}", ""
                elif key in FAIL:
                    target, reason, note = FAIL[key]
                    if reason == "forma_nao_prevista" and target and target not in by_label[number]:
                        reason, note = "fora_do_vocabulario", f"{target} só existe na híbrida"
                else:
                    target, reason, note = "", "fora_do_vocabulario", ""
                    if names[number].get(nf(a["entidade"])):
                        print("ATENÇÃO existe no vocabulário e não foi marcada:", number, key, names[number][nf(a["entidade"])])
                out.append({**base, "resultado": "falhada", "motivo": reason, "sistema": "", "nota": note})
            for label in sorted(system - used):
                reason, note = WRONG.get((n, label), ("?", ""))
                if reason == "?":
                    print("ERRADA sem motivo:", number, n, label)
                row = by_label[number].get(label, {})
                out.append(dict(artigo=n, esquema=s["esquema"], entidade="", categoria=row.get("categoria", ""),
                                qid=row.get("wikidata", ""), passagem=number, resultado="errada",
                                motivo=reason, sistema=label, nota=note))
    out.sort(key=lambda o: (o["passagem"], o["artigo"]))
    fields = ["artigo", "esquema", "entidade", "categoria", "qid", "passagem", "resultado", "motivo", "sistema", "nota"]
    target = ROOT / "data/processed/avaliacao_cobertura_2010_2016.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    print(len(out), sorted(collections.Counter((o["passagem"], o["resultado"]) for o in out).items()))


if __name__ == "__main__":
    main()
