# Retentativa dos textos que falharam por timeout ou ligação cortada

Candidatas em `output/corpus_text_retry_candidates.csv`; resultado por captura em `output/corpus_text_retry_report.csv`. Não altera `output/corpus_rdf_report.csv` nem o grafo: os textos recuperados só ficam em `data/raw/texts/` até o grafo ser reconstruído.

## Resumo

- Candidatas: 324
- Já tentadas (com resultado definitivo): 324
- Por tentar: 0
- Recuperadas: 249 (249 descarregadas, 0 já existiam em cache)
- Falhas definitivas: 75
  - http_404: 51
  - timeout_de_leitura: 24

Estes valores são o resultado real desta execução, não uma estimativa.
