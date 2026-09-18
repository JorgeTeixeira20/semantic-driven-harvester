# Fase 2 — profundidade temporal via version_history

Execução real sobre os 159 artigos únicos descobertos na Fase 1 (`output/corpus_phase1_captures.csv`). Sem restrição de datas por artigo (como o M3); paginação por offset só quando a página anterior veio cheia; `estimated_nr_results` não é usado como condição de paragem (correção de 2026-09-18).

## Resumo

- Artigos processados: 159
- Sucessos: 159
- Falhas (após 3 tentativas cada): 0
- Pedidos reais efetuados (todos os artigos, incluindo paginação): 287
- Total de capturas encontradas (artigos com sucesso): 7572
- Artigos com mais do que uma captura: 125 de 159 bem-sucedidos

## Distribuição de capturas por artigo

| Nº de capturas | Nº de artigos |
| ---: | ---: |
| 1 | 34 |
| 2 | 31 |
| 3 | 16 |
| 4 | 22 |
| 5 | 6 |
| 6 | 3 |
| 7 | 6 |
| 8 | 2 |
| 9 | 1 |
| 10 | 3 |
| 11 | 1 |
| 12 | 2 |
| 13 | 2 |
| 14 | 2 |
| 15 | 1 |
| 16 | 1 |
| 17 | 1 |
| 18 | 1 |
| 26 | 1 |
| 27 | 1 |
| 31 | 2 |
| 43 | 2 |
| 45 | 1 |
| 48 | 1 |
| 51 | 1 |
| 72 | 1 |
| 73 | 1 |
| 118 | 1 |
| 119 | 1 |
| 135 | 1 |
| 143 | 1 |
| 162 | 2 |
| 306 | 1 |
| 472 | 1 |
| 822 | 1 |
| 829 | 1 |
| 916 | 1 |
| 1084 | 1 |
| 1282 | 1 |

Estes valores são o resultado real desta execução, não uma estimativa. Detalhe por artigo em `output/corpus_phase2_history.csv`.
