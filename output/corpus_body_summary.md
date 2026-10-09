# Variante (c′): corpo do artigo por âncoras literais

Sem pedidos à API; não altera o grafo, o raw nem as saídas fechadas de D e B.

## Delimitação do corpo nas capturas da Camada 1

| Resultado | Capturas |
| --- | ---: |
| corpo | 775 |
| sem_corpo | 18 |

| Marcador que fechou o corpo | Capturas |
| --- | ---: |
| Mais notícias | 216 |
| Veja também | 168 |
| O Record recomenda para si | 117 |
| Últimas Notícias | 84 |
| Mais Hora Record | 44 |
| (fim do texto) | 34 |
| Mais Fotos | 29 |
| Mais Vídeos | 20 |
| Mais Premium | 18 |
| Enviar artigo por email | 15 |
| Leia este artigo na íntegra | 15 |
| Mais Recentes | 9 |
| Mais Vistas | 6 |

## Caminho D: pares consecutivos da Camada 1 com corpo

| n | mín. | p10 | mediana | p90 | máx. |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 654 | 0,125 | 1,000 | 1,000 | 1,000 | 1,000 |

| Limiar | Redundantes (último rep.) | Redundantes (consecutiva) | Versões (último rep.) |
| ---: | ---: | ---: | ---: |
| 0,500 | 649 | 649 | 126 |
| 0,600 | 648 | 648 | 127 |
| 0,700 | 645 | 645 | 130 |
| 0,800 | 645 | 645 | 130 |
| 0,850 | 643 | 643 | 132 |
| 0,900 | 642 | 642 | 133 |
| 0,950 | 640 | 640 | 135 |
| 0,990 | 623 | 623 | 152 |
| 1,000 | 614 | 614 | 161 |

## Caminho D: os 60 pares rotulados

Pares com alguma captura sem corpo (tratados à parte): 3 — par 1 (texto alterado), par 50 (mesma versão), par 60 (mesma versão)

Pares comparáveis: 57.

| Limiar | "mesma versão" abaixo do limiar | "texto alterado" acima do limiar |
| ---: | ---: | ---: |
| 0,500 | 0 | 1 |
| 0,600 | 0 | 1 |
| 0,700 | 0 | 1 |
| 0,800 | 0 | 1 |
| 0,850 | 0 | 0 |
| 0,900 | 0 | 0 |
| 0,950 | 0 | 0 |
| 0,990 | 1 | 0 |
| 1,000 | 4 | 0 |

- Mínimo "mesma versão": 0,975; máximo "texto alterado": 0,840.
- Separação limpa: **sim**.

## Caminho B: pares artigo–jogador, texto completo vs. corpo

| Medida | B fechado (sem chrome persistente) | Corpo (c′) |
| --- | ---: | ---: |
| fraca | 1427 | 119 |
| persistencia | 287 | 113 |
| artigos_fraca | 116 | 60 |
| artigos_persistencia | 91 | 58 |
| jogadores_persistencia | 118 | 78 |

Estes valores são o resultado real desta execução, não uma estimativa.
