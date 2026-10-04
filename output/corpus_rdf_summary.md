# Grafo RDF do corpus do Caminho A (passo final)

Reconstrução **offline** sobre os 125 artigos classificados como `Artigo` em `output/corpus_classification.csv`, a partir do raw de `version_history` (`data/raw/version_history/`) e da cache de textos (`data/raw/texts/`), **sem qualquer pedido à API**. Um texto conta como disponível se o ficheiro existir na cache. Inclui os textos recuperados pela retentativa (`output/corpus_text_retry_report.csv`).

## Resumo

- Artigos mapeados com sucesso: 125 de 125
- Artigos com falha (raw em falta ou manifesto inválido): 0
- Total de capturas incluídas no grafo: 941
- Textos disponíveis (ficheiro na cache): 793
- Textos indisponíveis (sem ficheiro na cache): 148
- A divisão histórica descarregados/reutilizados não é preservada numa reconstrução offline (todos contam como reutilizados); só o total disponível é informativo.
- Triplos no grafo final (`output/corpus_articles.ttl`): 13482
- Capturas com `originalURL` normalizado (variante de esquema ou barras da mesma página): 191, em 34 artigos
- Capturas descartadas por `originalURL` não ser variante cosmética do URL canónico: 0

Estes valores são o resultado real desta execução, não uma estimativa. Detalhe por artigo em `output/corpus_rdf_report.csv`.
