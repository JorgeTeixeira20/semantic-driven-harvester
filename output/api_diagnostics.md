# Diagnóstico controlado da API TextSearch

Pesquisa comum: `Sporting`, `siteSearch=record.pt`, `from=2015`, `to=2020`. O cliente inclui também `www.record.pt`.

| Teste | maxItems pedido/API | offset | dedup pedido/API | estimated | recebidos | URLs únicas | tstamps únicos | next_page |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| A | 100/100 | 0 | url/1 explícito | 6721102 | 33 | 33 | 33 | não |
| B | 100/100 | 100 | url/1 explícito | 6721102 | 0 | 0 | 0 | não |
| C | 100/100 | 200 | url/1 explícito | 6721102 | 0 | 0 | 0 | não |
| D | 2000/500 | 0 | url/1 explícito | 6721102 | 96 | 96 | 96 | não |
| E | 100/100 | 0 | omitido → url/2 | 6721102 | 53 | 46 | 53 | não |
| F | 200/200 | 0 | url/1 explícito | 6721102 | 57 | 57 | 57 | não |

## Primeiro e último resultado

| Teste | Primeiro tstamp | Primeiro URL | Último tstamp | Último URL |
| --- | --- | --- | --- | --- |
| A | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170921171011 | http://www.record.pt/internacional/paises/espanha/detalhe/yeray-alvarez-volta-aos-treinos-apos-recuperar-de-tumor-nos-testiculos.html |
| B | n/a | n/a | n/a | n/a |
| C | n/a | n/a | n/a | n/a |
| D | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170913234951 | http://www.record.pt/modalidades/tenis/detalhe/kohlmann-acredita-que-a-alemanha-tem-boas-hipoteses-frente-a-portugal-mesmo-sem-zverevs.html |
| E | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170921171011 | http://www.record.pt/internacional/paises/espanha/detalhe/yeray-alvarez-volta-aos-treinos-apos-recuperar-de-tumor-nos-testiculos.html |
| F | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170108221237 | http://www.record.pt/internacional/paises/espanha/detalhe/valencia-ja-chegou-a-acordo-com-a-juventus-por-zaza.html |

## Offset analysis

- URLs de B já presentes em A: 0.
- URLs novas em B: 0.
- URLs de C já presentes na união A/B: 0.
- URLs novas em C: 0.

## Dedup analysis

- Resultados com dedup ON (A): 33.
- Resultados sem parâmetros explícitos, com defaults `url/2` (E): 53.
- URLs distintas com os defaults `url/2`: 46.
- Ocorrências repetidas de URL com os defaults `url/2`: 7.
- E não representa dedup desativado: a API aplicou `dedupField=url` e `dedupValue=2` por omissão.

## maxItems analysis

- maxItems=100: 33 resultados.
- maxItems=200: 57 resultados.
- maxItems=2000: 96 resultados.
- A/F: 32 URLs em comum, 25 novas em F e 1 de A ausente em F.
- F/D: 52 URLs em comum, 44 novas em D e 5 de F ausentes em D.
- No teste D, a API reportou `maxItems=500` apesar de terem sido pedidos 2000.

Os valores acima são observações da execução. Não demonstram, por si só, em que fase interna a API aplica paginação ou deduplicação.
