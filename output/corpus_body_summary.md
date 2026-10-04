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
| Últimas Notícias | 102 |
| Mais Hora Record | 44 |
| (fim do texto) | 34 |
| Mais Fotos | 29 |
| Mais Vídeos | 20 |
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
| 0,500 | 641 | 643 | 134 |
| 0,600 | 637 | 637 | 138 |
| 0,700 | 634 | 634 | 141 |
| 0,800 | 634 | 634 | 141 |
| 0,850 | 632 | 632 | 143 |
| 0,900 | 631 | 631 | 144 |
| 0,950 | 630 | 630 | 145 |
| 0,990 | 618 | 618 | 157 |
| 1,000 | 609 | 609 | 166 |

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
| fraca | 1427 | 131 |
| persistencia | 287 | 114 |
| artigos_fraca | 116 | 63 |
| artigos_persistencia | 91 | 58 |
| jogadores_persistencia | 118 | 79 |

Estes valores são o resultado real desta execução, não uma estimativa.
