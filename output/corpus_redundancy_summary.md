# Caminho D — anotação de redundância entre capturas

Execução real, sem pedidos à API, sobre `output/corpus_articles.ttl` e os textos em `data/raw/texts/`. Nada foi removido do grafo nem do raw: o resultado é uma anotação por captura em `output/corpus_redundancy.csv`. Similaridade: Jaccard de conjuntos de palavras (`\w+`) do texto normalizado (NFC, minúsculas, espaços), calculada só sobre o **corpo do artigo** (variante c′: entre o título e o primeiro marcador de bloco de chrome; `article_body.py`).

**Limiar aplicado no CSV: 0,900.**

## Limiar e validação contra a amostra rotulada

Contra os 57 pares rotulados manualmente em `output/corpus_redundancy_label_sample.csv`, com este limiar:

- "texto alterado" com similaridade ≥ limiar (seriam tratados como a mesma versão — erro grave): **0 de 1**.
- "mesma versão" com similaridade < limiar (ficam como versões distintas — erro conservador): **0 de 56**. A anotação é não destrutiva: este erro não apaga nada, só aumenta o número de "versões distintas".
- Limiares da grelha que separam os rótulos sem erros: 0,850, 0,900, 0,950. O lado "texto alterado" assenta em muito poucos pares; critério e limitações em `docs/experiments.md`.
- Pares rotulados com alguma captura sem corpo (fora desta validação): 3 — par 1 (texto alterado), par 50 (mesma versão), par 60 (mesma versão).

## Estrutura do corpus

- Artigos: 125; capturas: 941; capturas com texto: 793

| Situação | Artigos |
| --- | ---: |
| Só 1 captura | 29 |
| Nenhuma captura com texto (não avaliáveis) | 4 |
| Exatamente 1 captura com texto | 37 |
| 2 ou mais capturas com texto (comparáveis) | 84 |

## Contagens por camada

| Camada | Capturas |
| --- | ---: |
| Camada 1 — com texto e corpo e `statusCode` 200 | 775 |
| Sem corpo — com texto, mas sem corpo de artigo localizável | 18 |
| Camada 2 — sem texto, em artigos com algum texto | 144 |
| Não avaliáveis — artigos sem nenhuma captura na Camada 1 (sem texto ou sem corpo) | 4 |
| Total | 941 |

- Capturas com `statusCode` ≠ 200: 35, das quais 0 com texto; todas fora da Camada 1 (contabilizadas à parte, não são redundância).

### Camada 2 — candidatas por `digest` + `contentLength` (não verificadas por texto)

Todas as capturas sem texto são mantidas. Estas contagens são apenas um limite superior do que um critério fraco deduziria e **nunca são somadas à Camada 1**.

| Tipo de grupo (dentro do artigo) | Grupos | Candidatas |
| --- | ---: | ---: |
| Só capturas sem texto (n−1 por grupo) | 9 | 14 |
| Misto (mesmo `digest`/`contentLength` de uma captura com texto) | 0 | 0 |

## Distribuição de similaridades (pares consecutivos com texto)

| n | mín. | p10 | mediana | p90 | máx. |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 654 | 0,125 | 1,000 | 1,000 | 1,000 | 1,000 |

| Faixa | Pares |
| --- | ---: |
| [0,100; 0,150) | 4 |
| [0,400; 0,450) | 1 |
| [0,550; 0,600) | 1 |
| [0,600; 0,650) | 2 |
| [0,650; 0,700) | 1 |
| [0,800; 0,850) | 2 |
| [0,850; 0,900) | 1 |
| [0,900; 0,950) | 2 |
| [0,950; 1,000) | 26 |
| = 1,000 | 614 |

## Sensibilidade ao limiar (Camada 1)

Redundantes = capturas com similaridade ≥ limiar face ao termo de comparação; versões = capturas da Camada 1 que ficam como representantes (versões textuais distintas). "Último rep." é a estratégia do desenho; "consecutiva" é a análise de sensibilidade. Divergências = capturas com classificação ou representante diferente entre as duas.

| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | Versões (último rep.) | Versões (consecutiva) | Divergências | Artigos com redundantes (último rep.) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0,500 | 649 | 649 | 126 | 126 | 0 | 84 |
| 0,600 | 648 | 648 | 127 | 127 | 0 | 84 |
| 0,700 | 645 | 645 | 130 | 130 | 0 | 84 |
| 0,800 | 645 | 645 | 130 | 130 | 0 | 84 |
| 0,850 | 643 | 643 | 132 | 132 | 0 | 83 |
| 0,900 | 642 | 642 | 133 | 133 | 0 | 82 |
| 0,950 | 640 | 640 | 135 | 135 | 0 | 81 |
| 0,990 | 623 | 623 | 152 | 152 | 0 | 73 |
| 1,000 | 614 | 614 | 161 | 161 | 0 | 72 |

## Versões textuais distintas por artigo (Camada 1)

- Artigos com texto: 121; capturas da Camada 1: 775; versões textuais distintas: **133**; capturas redundantes: 642.
- Detalhe por artigo em `output/corpus_redundancy_versions.csv`.

| Versões distintas | Artigos |
| --- | ---: |
| 1 | 112 |
| 2 | 8 |
| 3–5 | 1 |
| 6–10 | 0 |
| ≥ 11 | 0 |
| Artigos sem texto (não avaliáveis) | 4 |

## Amostra para rotulagem manual

`output/corpus_redundancy_label_sample.csv`: pares consecutivos com texto, até 20 por faixa (semente 0), repartidos em rotação pelas sub-faixas de 0,05 (1,0 exato numa sub-faixa própria). As faixas servem só para espalhar a amostra; não são limiares propostos. Já rotulada manualmente (colunas `rotulo_manual` e `notas`); não é reescrita por novas execuções.

| Faixa | Intervalo | Pares na amostra | Pares disponíveis |
| --- | --- | ---: | ---: |
| baixa | [0,000; 0,700) | 20 | 9 |
| media | [0,700; 0,900) | 20 | 3 |
| alta | [0,900; 1,000] | 20 | 642 |

Estes valores são o resultado real desta execução, não uma estimativa.
