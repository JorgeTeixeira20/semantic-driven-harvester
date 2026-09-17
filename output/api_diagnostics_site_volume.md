# Volume de queries genéricas em siteSearch=record.pt (Experiência 3)

Parâmetros comuns: `siteSearch=record.pt` (o cliente inclui também `www.record.pt`), `from=2015`, `to=2020`, `maxItems=20`, sem `dedupField`/`dedupValue` explícitos. Cada query foi repetida 3 vezes com os mesmos parâmetros para observar variação entre pedidos idênticos.

| Query | Tentativa | maxItems pedido/API | dedup reportado pela API | estimated | recebidos | página cheia | URLs únicas | next_page |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | --- |
| Sporting | 1 | 20/20 | url/2 | 6366674 | 5 | não | 5 | não |
| Sporting | 2 | 20/20 | url/2 | 6468098 | 3 | não | 3 | não |
| Sporting | 3 | 20/20 | url/2 | 6464286 | 7 | não | 7 | não |
| futebol | 1 | 20/20 | url/2 | 6494908 | 2 | não | 2 | não |
| futebol | 2 | 20/20 | url/2 | 6494908 | 2 | não | 2 | não |
| futebol | 3 | 20/20 | url/2 | 6494908 | 2 | não | 2 | não |
| desporto | 1 | 20/20 | url/2 | 6478714 | 2 | não | 2 | não |
| desporto | 2 | 20/20 | url/2 | 6463849 | 2 | não | 2 | não |
| desporto | 3 | 20/20 | url/2 | 6478714 | 2 | não | 2 | não |

## Resumo por query

| Query | Tentativas | recebidos min/max | alguma página cheia | estimated min/max |
| --- | ---: | --- | --- | --- |
| Sporting | 3 | 3/7 | não | 6366674/6468098 |
| futebol | 3 | 2/2 | não | 6494908/6494908 |
| desporto | 3 | 2/2 | não | 6463849/6478714 |

Os valores acima são observações desta execução. A variação entre tentativas idênticas da mesma query indica que a API TextSearch não é determinística por pedido nesta janela de observação; uma única amostra por query não é suficiente para concluir se uma query 'consegue encher uma página'.
