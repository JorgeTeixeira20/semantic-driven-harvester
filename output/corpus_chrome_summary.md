# Caminho D — variante (b): remoção do chrome

Execução real, sem pedidos à API, sobre `output/corpus_articles.ttl` e `data/raw/texts/`. Não altera o grafo, o raw nem as saídas da variante (a). Chrome = n-gramas de palavras presentes numa fração alta dos artigos distintos (critério derivado do corpus).

## Distribuição das frequências dos 5-gramas

Base: 789 capturas da Camada 1 de 125 artigos com texto; frequência = nº de artigos distintos em que o 5-grama aparece. 223142 5-gramas distintos.

| Artigos em que aparece | 5-gramas distintos |
| --- | ---: |
| 1 | 166085 |
| 2 | 40272 |
| 3–5 | 13047 |
| 6–10 | 1850 |
| 11–20 | 595 |
| 21–30 | 194 |
| 31–50 | 567 |
| 51–75 | 495 |
| 76–100 | 22 |
| 101–125 | 15 |

Efeito de cada fração de corte (chrome = presente em ≥ fração dos artigos e em ≥ 2 artigos):

| Fração | Mín. artigos | n-gramas de chrome | Palavras removidas (todas as capturas) |
| ---: | ---: | ---: | ---: |
| 0,02 | 3 | 16785 | 58,0% |
| 0,03 | 4 | 9026 | 54,0% |
| 0,05 | 7 | 3182 | 47,5% |
| 0,10 | 13 | 1714 | 43,2% |
| 0,15 | 19 | 1337 | 42,0% |
| 0,20 | 25 | 1143 | 40,9% |
| 0,30 | 38 | 933 | 39,2% |
| 0,40 | 50 | 550 | 29,9% |
| 0,50 | 63 | 138 | 15,5% |
| 0,75 | 94 | 16 | 3,8% |

## Avaliação com n = 5 e fração = 0,10

- n-gramas de chrome: 1714
- Capturas da Camada 1 que ficam sem nenhuma palavra: 0 (de 789; Jaccard de dois conjuntos vazios = 1)

### Pares consecutivos da Camada 1, texto sem chrome

| n | mín. | p10 | mediana | p90 | máx. |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 664 | 0,225 | 0,340 | 0,457 | 0,995 | 1,000 |

### Sensibilidade ao limiar (Camada 1, texto sem chrome)

| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | Versões (último rep.) | Divergências |
| ---: | ---: | ---: | ---: | ---: |
| 0,500 | 253 | 267 | 536 | 22 |
| 0,600 | 142 | 148 | 647 | 29 |
| 0,700 | 99 | 101 | 690 | 3 |
| 0,800 | 82 | 82 | 707 | 0 |
| 0,850 | 78 | 79 | 711 | 3 |
| 0,900 | 75 | 76 | 714 | 1 |
| 0,950 | 73 | 73 | 716 | 0 |
| 0,990 | 70 | 70 | 719 | 0 |
| 1,000 | 66 | 66 | 723 | 0 |

### Os 60 pares rotulados, texto sem chrome

| Limiar | "mesma versão" abaixo do limiar (de 58) | "texto alterado" acima do limiar (de 2) |
| ---: | ---: | ---: |
| 0,50 | 18 | 1 |
| 0,60 | 27 | 1 |
| 0,70 | 33 | 1 |
| 0,80 | 37 | 0 |
| 0,85 | 40 | 0 |
| 0,90 | 43 | 0 |
| 0,95 | 46 | 0 |
| 0,99 | 48 | 0 |
| 1,00 | 50 | 0 |

- Mínimo "mesma versão": 0,240; máximo "texto alterado": 0,713.
- Separação limpa: **não**.
- Pares ambíguos (34):
  - par 2 (mesma versão): 0,240
  - par 9 (mesma versão): 0,251
  - par 6 (mesma versão): 0,261
  - par 3 (mesma versão): 0,271
  - par 4 (mesma versão): 0,280
  - par 5 (mesma versão): 0,312
  - par 15 (mesma versão): 0,337
  - par 7 (mesma versão): 0,354
  - par 10 (mesma versão): 0,369
  - par 16 (mesma versão): 0,376
  - par 8 (mesma versão): 0,379
  - par 17 (mesma versão): 0,404
  - par 11 (mesma versão): 0,408
  - par 13 (mesma versão): 0,410
  - par 14 (mesma versão): 0,428
  - par 12 (mesma versão): 0,438
  - par 18 (mesma versão): 0,457
  - par 20 (mesma versão): 0,481
  - par 28 (mesma versão): 0,512
  - par 30 (mesma versão): 0,536
  - par 24 (mesma versão): 0,554
  - par 23 (mesma versão): 0,555
  - par 19 (mesma versão): 0,555
  - par 25 (mesma versão): 0,559
  - par 22 (mesma versão): 0,579
  - par 21 (mesma versão): 0,589
  - par 26 (mesma versão): 0,590
  - par 27 (mesma versão): 0,611
  - par 32 (mesma versão): 0,647
  - par 33 (mesma versão): 0,660
  - par 31 (mesma versão): 0,674
  - par 36 (mesma versão): 0,676
  - par 40 (mesma versão): 0,689
  - par 29 (texto alterado): 0,713

Detalhe por par em `output/corpus_chrome_label_eval.csv`.

### Sensibilidade a n (mesma fração)

| n | n-gramas de chrome | mín. "mesma versão" | máx. "texto alterado" | separação limpa |
| ---: | ---: | ---: | ---: | --- |
| 3 | 1732 | 0,238 | 0,708 | não |
| 5 | 1714 | 0,240 | 0,713 | não |
| 8 | 1839 | 0,239 | 0,714 | não |

Estes valores são o resultado real desta execução, não uma estimativa.
