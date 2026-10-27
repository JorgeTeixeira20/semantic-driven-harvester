"""Reconstrói a cache da Wikidata de um corpus a partir da de outro, pelo conteúdo da consulta.

Problema: `wikidata_candidates` guarda as respostas por **posição** na lista de candidatos
(`candidato_00046.json`, `candidato_00046_pesquisa.json`). Com um corpus diferente a lista
tem outra ordem (os candidatos vêm ordenados por número de artigos), por isso o ficheiro de
cada posição já não corresponde ao mesmo candidato e `--reutilizar` repete pedidos que já
estavam feitos. O `.rq` ao lado de cada resposta tem a consulta, que depende só do candidato.

Uso (sem rede; o destino é apagado e reconstruído):

    python scripts/wikidata_cache_por_conteudo.py [ORIGEM [DESTINO [MIN_ARTIGOS]]]

por omissão `por_ano` → `completo`, com 10 artigos. Lê `output/corpus_candidate_entities_<DESTINO>.csv`
(tem de existir), procura cada consulta do destino nas respostas de
`data/raw/wikidata/candidatos_<ORIGEM>/` e copia as que existem para a posição certa de
`candidatos_<DESTINO>/`. Depois corre-se `wikidata_candidates --corpus <DESTINO> --reutilizar`,
que só faz os pedidos que faltam. Não altera a origem.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from semantic_harvester.wikidata_candidates import candidate_query, form_problem, load_candidates  # noqa: E402


def main(origem: str = "por_ano", destino: str = "completo", minimo: int = 10) -> None:
    src = ROOT / "data" / "raw" / "wikidata" / f"candidatos_{origem}"
    dst = ROOT / "data" / "raw" / "wikidata" / f"candidatos_{destino}"
    by = {}
    for rq in src.glob("candidato_*.rq"):
        raw = rq.with_suffix(".json")
        if raw.exists():
            by[rq.read_text(encoding="utf-8")] = (rq, raw)
    print("respostas em cache (por conteúdo da consulta):", len(by))
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    cands = load_candidates(ROOT / "output" / f"corpus_candidate_entities_{destino}.csv", minimo)
    reused = total = bad_form = 0
    for i, (candidate, _articles) in enumerate(cands, start=1):
        if form_problem(candidate):
            bad_form += 1
            continue
        for suffix, search in (("", False), ("_pesquisa", True)):
            total += 1
            hit = by.get(candidate_query(candidate, search) + "\n")
            if hit:
                shutil.copy2(hit[0], dst / f"candidato_{i:05d}{suffix}.rq")
                shutil.copy2(hit[1], dst / f"candidato_{i:05d}{suffix}.json")
                reused += 1
    new = sum(1 for i, (c, _n) in enumerate(cands, start=1)
              if not form_problem(c) and not (dst / f"candidato_{i:05d}.json").exists())
    print(f"candidatos com {minimo}+ artigos: {len(cands)} | sem consulta (forma inválida): {bad_form}"
          f" | consultas possíveis: {total} | reaproveitadas: {reused}")
    print("candidatos que precisam de pedidos novos (consulta exata):", new)


if __name__ == "__main__":
    main(*(sys.argv[1:3] + [int(sys.argv[3])] if len(sys.argv) > 3 else sys.argv[1:3]))
