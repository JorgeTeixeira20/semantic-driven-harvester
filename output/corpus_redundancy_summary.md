# Caminho D — anotação de redundância entre capturas

Execução real, sem pedidos à API, sobre `output/corpus_articles.ttl` e os textos em `data/raw/texts/`. Nada foi removido do grafo nem do raw: o resultado é uma anotação por captura em `output/corpus_redundancy.csv`. Similaridade: Jaccard de conjuntos de palavras (`\w+`) do texto normalizado (NFC, minúsculas, espaços), sem remover o chrome do site.

**Limiar aplicado no CSV: 0,800.**

## Limiar e validação contra a amostra rotulada

Contra os 60 pares rotulados manualmente em `output/corpus_redundancy_label_sample.csv`, com este limiar:

- "texto alterado" com similaridade ≥ limiar (seriam tratados como a mesma versão — erro grave): **0 de 2**.
- "mesma versão" com similaridade < limiar (ficam como versões distintas — erro conservador): **28 de 58**. A anotação é não destrutiva: este erro não apaga nada, só aumenta o número de "versões distintas".
- Limiares da grelha que separam os rótulos sem erros: **nenhum**. O limiar é uma escolha pragmática dos autores, não uma calibração limpa; critério e limitações em `docs/experiments.md`.

## Estrutura do corpus

- Artigos: 127; capturas: 941; capturas com texto: 789

| Situação | Artigos |
| --- | ---: |
| Só 1 captura | 31 |
| Nenhuma captura com texto (não avaliáveis) | 2 |
| Exatamente 1 captura com texto | 41 |
| 2 ou mais capturas com texto (comparáveis) | 84 |

## Contagens por camada

| Camada | Capturas |
| --- | ---: |
| Camada 1 — com texto e `statusCode` 200 | 789 |
| Camada 2 — sem texto, em artigos com algum texto | 150 |
| Não avaliáveis — artigos sem nenhum texto | 2 |
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
| 664 | 0,434 | 0,561 | 0,655 | 0,995 | 1,000 |

| Faixa | Pares |
| --- | ---: |
| [0,400; 0,450) | 2 |
| [0,450; 0,500) | 14 |
| [0,500; 0,550) | 40 |
| [0,550; 0,600) | 68 |
| [0,600; 0,650) | 188 |
| [0,650; 0,700) | 140 |
| [0,700; 0,750) | 44 |
| [0,750; 0,800) | 39 |
| [0,800; 0,850) | 41 |
| [0,850; 0,900) | 7 |
| [0,900; 0,950) | 5 |
| [0,950; 1,000) | 12 |
| = 1,000 | 64 |

## Sensibilidade ao limiar (Camada 1)

Redundantes = capturas com similaridade ≥ limiar face ao termo de comparação; versões = capturas da Camada 1 que ficam como representantes (versões textuais distintas). "Último rep." é a estratégia do desenho; "consecutiva" é a análise de sensibilidade. Divergências = capturas com classificação ou representante diferente entre as duas.

| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | Versões (último rep.) | Versões (consecutiva) | Divergências | Artigos com redundantes (último rep.) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0,500 | 624 | 648 | 165 | 141 | 108 | 84 |
| 0,600 | 518 | 540 | 271 | 249 | 72 | 72 |
| 0,700 | 210 | 212 | 579 | 577 | 5 | 57 |
| 0,800 | 124 | 129 | 665 | 660 | 34 | 34 |
| 0,850 | 88 | 88 | 701 | 701 | 0 | 22 |
| 0,900 | 81 | 81 | 708 | 708 | 0 | 15 |
| 0,950 | 75 | 76 | 714 | 713 | 3 | 12 |
| 0,990 | 70 | 70 | 719 | 719 | 0 | 12 |
| 1,000 | 64 | 64 | 725 | 725 | 0 | 12 |

## Versões textuais distintas por artigo (Camada 1)

- Artigos com texto: 125; capturas da Camada 1: 789; versões textuais distintas: **665**; capturas redundantes: 124.
- Detalhe por artigo em `output/corpus_redundancy_versions.csv`.

| Versões distintas | Artigos |
| --- | ---: |
| 1 | 55 |
| 2 | 21 |
| 3–5 | 28 |
| 6–10 | 7 |
| ≥ 11 | 14 |
| Artigos sem texto (não avaliáveis) | 2 |

## Amostra para rotulagem manual

`output/corpus_redundancy_label_sample.csv`: pares consecutivos com texto, até 20 por faixa (semente 0), repartidos em rotação pelas sub-faixas de 0,05 (1,0 exato numa sub-faixa própria). As faixas servem só para espalhar a amostra; não são limiares propostos. Já rotulada manualmente (colunas `rotulo_manual` e `notas`); não é reescrita por novas execuções.

| Faixa | Intervalo | Pares na amostra | Pares disponíveis |
| --- | --- | ---: | ---: |
| baixa | [0,000; 0,700) | 20 | 452 |
| media | [0,700; 0,900) | 20 | 131 |
| alta | [0,900; 1,000] | 20 | 81 |

Estes valores são o resultado real desta execução, não uma estimativa.
