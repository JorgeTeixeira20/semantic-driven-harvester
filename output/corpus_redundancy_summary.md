# Caminho D — anotação de redundância entre capturas

Execução real, sem pedidos à API, sobre `output/corpus_articles.ttl` e os textos em `data/raw/texts/`. Nada foi removido do grafo nem do raw: o resultado é uma anotação por captura em `output/corpus_redundancy.csv`. Similaridade: Jaccard de conjuntos de palavras (`\w+`) do texto normalizado (NFC, minúsculas, espaços), sem remover o chrome do site.

**Limiar aplicado no CSV: 0,800.**

## Limiar e validação contra a amostra rotulada

Contra os 60 pares rotulados manualmente em `output/corpus_redundancy_label_sample.csv`, com este limiar:

- "texto alterado" com similaridade ≥ limiar (seriam tratados como a mesma versão — erro grave): **0 de 2**.
- "mesma versão" com similaridade < limiar (ficam como versões distintas — erro conservador): **28 de 58**. A anotação é não destrutiva: este erro não apaga nada, só aumenta o número de "versões distintas".
- Limiares da grelha que separam os rótulos sem erros: **nenhum**. O limiar é uma escolha pragmática dos autores, não uma calibração limpa; critério e limitações em `docs/experiments.md`.

## Estrutura do corpus

- Artigos: 125; capturas: 941; capturas com texto: 793

| Situação | Artigos |
| --- | ---: |
| Só 1 captura | 29 |
| Nenhuma captura com texto (não avaliáveis) | 2 |
| Exatamente 1 captura com texto | 38 |
| 2 ou mais capturas com texto (comparáveis) | 85 |

## Contagens por camada

| Camada | Capturas |
| --- | ---: |
| Camada 1 — com texto e `statusCode` 200 | 793 |
| Camada 2 — sem texto, em artigos com algum texto | 146 |
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
| 670 | 0,434 | 0,562 | 0,655 | 0,996 | 1,000 |

| Faixa | Pares |
| --- | ---: |
| [0,400; 0,450) | 2 |
| [0,450; 0,500) | 14 |
| [0,500; 0,550) | 40 |
| [0,550; 0,600) | 69 |
| [0,600; 0,650) | 189 |
| [0,650; 0,700) | 140 |
| [0,700; 0,750) | 44 |
| [0,750; 0,800) | 40 |
| [0,800; 0,850) | 42 |
| [0,850; 0,900) | 7 |
| [0,900; 0,950) | 5 |
| [0,950; 1,000) | 13 |
| = 1,000 | 65 |

## Sensibilidade ao limiar (Camada 1)

Redundantes = capturas com similaridade ≥ limiar face ao termo de comparação; versões = capturas da Camada 1 que ficam como representantes (versões textuais distintas). "Último rep." é a estratégia do desenho; "consecutiva" é a análise de sensibilidade. Divergências = capturas com classificação ou representante diferente entre as duas.

| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | Versões (último rep.) | Versões (consecutiva) | Divergências | Artigos com redundantes (último rep.) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0,500 | 630 | 654 | 163 | 139 | 108 | 85 |
| 0,600 | 522 | 545 | 271 | 248 | 78 | 73 |
| 0,700 | 214 | 216 | 579 | 577 | 5 | 58 |
| 0,800 | 127 | 132 | 666 | 661 | 34 | 36 |
| 0,850 | 90 | 90 | 703 | 703 | 0 | 24 |
| 0,900 | 83 | 83 | 710 | 710 | 0 | 17 |
| 0,950 | 77 | 78 | 716 | 715 | 3 | 14 |
| 0,990 | 71 | 71 | 722 | 722 | 0 | 13 |
| 1,000 | 65 | 65 | 728 | 728 | 0 | 13 |

## Versões textuais distintas por artigo (Camada 1)

- Artigos com texto: 123; capturas da Camada 1: 793; versões textuais distintas: **666**; capturas redundantes: 127.
- Detalhe por artigo em `output/corpus_redundancy_versions.csv`.

| Versões distintas | Artigos |
| --- | ---: |
| 1 | 52 |
| 2 | 22 |
| 3–5 | 28 |
| 6–10 | 7 |
| ≥ 11 | 14 |
| Artigos sem texto (não avaliáveis) | 2 |

## Amostra para rotulagem manual

`output/corpus_redundancy_label_sample.csv`: pares consecutivos com texto, até 20 por faixa (semente 0), repartidos em rotação pelas sub-faixas de 0,05 (1,0 exato numa sub-faixa própria). As faixas servem só para espalhar a amostra; não são limiares propostos. Já rotulada manualmente (colunas `rotulo_manual` e `notas`); não é reescrita por novas execuções.

| Faixa | Intervalo | Pares na amostra | Pares disponíveis |
| --- | --- | ---: | ---: |
| baixa | [0,000; 0,700) | 20 | 454 |
| media | [0,700; 0,900) | 20 | 133 |
| alta | [0,900; 1,000] | 20 | 83 |

Estes valores são o resultado real desta execução, não uma estimativa.
