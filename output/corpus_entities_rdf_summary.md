# Caminho B em RDF (`output/corpus_entities.ttl`)

Gerado de `output/corpus_entities.csv` (variante c′) e do vocabulário da Wikidata, sem pedidos à API; `output/corpus_articles.ttl` não foi alterado (checksum igual antes e depois).

- Triplos: 1701
- Linhas de tema / de menção no CSV: 308 / 115
- Nós `Tema` (partilhados por categoria e valor): 40
- Nós `EntidadeMencionada`: 79 — 78 com URI da Wikidata, 1 com URI próprio (homónimos)
- Nós `Mencao`: 115

## Exceção: rótulos homónimos

Rótulos do vocabulário com mais de um QID (3): André Silva, Chico, Pedro Mendes. Para eles não se atribui um QID, porque a deteção por vocabulário fechado não distingue qual das pessoas é mencionada; usa-se `sdh:entity/<sha256(rotulo)>`.

Linhas de menção com rótulo homónimo no CSV atual: 1 — Pedro Mendes em https://www.record.pt/modalidades/desporto-universitario/detalhe/AMP/universidade-do-porto-vence-no-xadrez.html

Estes valores são o resultado real desta execução, não uma estimativa.
