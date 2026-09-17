# Diagnóstico controlado do offset (Experiência 2)

Pesquisa comum: `Sporting`, sem `siteSearch`, `from=2015`, `to=2020`, `maxItems=20`, `dedupField=url`/`dedupValue=1` explícitos. Objetivo: verificar se `offset` pagina quando a primeira página vem efetivamente cheia (complementa a Experiência 1 em `experiments.md`, onde nenhuma variante preencheu o `maxItems` pedido).

| Teste | maxItems pedido/API | offset | dedup pedido/API | estimated | recebidos | página cheia | URLs únicas | tstamps únicos | next_page |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- |
| G | 20/20 | 0 | url/1 pedido → url/1 | 108054864 | 13 | não | 13 | 12 | não |
| H | 20/20 | 20 | url/1 pedido → url/1 | 108211542 | 12 | não | 12 | 12 | não |
| I | 20/20 | 40 | url/1 pedido → url/1 | 108211542 | 5 | não | 5 | 5 | não |

## Primeiro e último resultado

| Teste | Primeiro tstamp | Primeiro URL | Último tstamp | Último URL |
| --- | --- | --- | --- | --- |
| G | 20160211055158 | http://www.sporting.pt/ | 20190914034528 | http://sportingtv.pt.to/ |
| H | 20180407053844 | https://pt.wikipedia.org/wiki/Sporting_Clube_de_Portugal | 20191005133946 | http://sportingvintage.blogspot.com/ |
| I | 20180716160812 | http://sportingforever.blogspot.com/ | 20190323101910 | http://sportingtap.blogspot.com/ |

## Offset analysis

- URLs de H já presentes em G: 0.
- URLs novas em H: 12.
- URLs de I já presentes na união G/H: 0.
- URLs novas em I: 5.

Os valores acima são observações desta execução. Não demonstram, por si só, em que fase interna a API aplica o offset nem generalizam para outras queries ou combinações de parâmetros.
