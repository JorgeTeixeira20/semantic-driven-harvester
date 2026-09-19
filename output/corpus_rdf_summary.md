# Grafo RDF do corpus do Caminho A (passo final)

Execução real sobre os 127 artigos classificados como `Artigo` em `output/corpus_classification.csv`. As capturas foram reconstruídas a partir do raw de `version_history` já preservado pela Fase 2 (`data/raw/version_history/`), sem pedidos novos; só o download dos textos extraídos fez pedidos reais à API. A execução é retomável por artigo (`output/corpus_rdf_report.csv`); estes números agregam todas as sessões até à conclusão, não só a última.

## Resumo

- Artigos mapeados com sucesso: 127 de 127
- Artigos com falha (raw em falta ou manifesto inválido): 0
- Total de capturas incluídas no grafo: 941
- Textos descarregados (soma de todas as sessões): 281
- Textos reutilizados (já existentes em `data/raw/texts/`): 259
- Textos indisponíveis (falha ou 404): 401
- Triplos no grafo final (`output/corpus_articles.ttl`): 12735
- Capturas com `originalURL` normalizado (variante de esquema ou barras da mesma página): 189, em 32 artigos
- Capturas descartadas por `originalURL` não ser variante cosmética do URL canónico: 0

Estes valores são o resultado real desta execução, não uma estimativa. Detalhe por artigo em `output/corpus_rdf_report.csv`.
