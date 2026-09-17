# Diagnóstico controlado do offset (Experiência 2)

Pesquisa comum: `futebol`, sem `siteSearch`, `from=2015`, `to=2020`, `maxItems=20`, sem `dedupField`/`dedupValue` explícitos (defaults da API). Objetivo: verificar se `offset` pagina quando a primeira página vem efetivamente cheia (complementa a Experiência 1 em `experiments.md`, onde nenhuma variante preencheu o `maxItems` pedido). Uma tentativa preliminar com `Sporting`, sem `siteSearch` e com `dedupField=url`/`dedupValue=1` explícitos não preencheu a página (ver `output/api_diagnostics_offset_pilot.md`); esta configuração foi escolhida por preencher genuinamente `maxItems`.

| Teste | maxItems pedido/API | offset | dedup reportado pela API | estimated | recebidos | página cheia | URLs únicas | tstamps únicos | next_page |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- |
| G | 20/20 | 0 | title/2 | 286123167 | 20 | sim | 13 | 20 | sim |
| H | 20/20 | 20 | title/2 | 286123167 | 20 | sim | 14 | 17 | sim |
| I | 20/20 | 40 | title/2 | 286123167 | 20 | sim | 17 | 20 | sim |
| J | 20/20 | 100 | title/2 | 245042486 | 20 | sim | 18 | 19 | sim |
| K | 20/20 | 200 | title/2 | 232123711 | 20 | sim | 20 | 19 | sim |

## Primeiro e último resultado

| Teste | Primeiro tstamp | Primeiro URL | Último tstamp | Último URL |
| --- | --- | --- | --- | --- |
| G | 20160210203525 | http://www.futebol365.pt/ | 20160210203526 | http://www.futebol.desportoaveiro.pt/ |
| H | 20190320080020 | http://portal-futebol.blogspot.com/ | 20190901093101 | http://futeboltotal-victor.blogspot.com/ |
| I | 20160204173835 | http://www.portalfutebol.net/ | 20160204130944 | http://www.afutebollisboa.org/ |
| J | 20181013091047 | http://www.afguarda.pt/ | 20150408103302 | http://www.afviseu.org/ |
| K | 20181023151422 | http://www.espn.com.br/futebol/resultados | 20191011120712 | https://www.publico.pt/futebol0 |

## Offset analysis

- URLs de H já presentes em G: 3.
- URLs novas em H: 11.
- URLs de I já presentes na união G/H: 4.
- URLs novas em I: 13.
- URLs de J (offset=100) já presentes na união G/H/I: 0.
- URLs novas em J: 18.
- URLs de K (offset=200) já presentes na união G/H/I/J: 0.
- URLs novas em K: 20.

Os valores acima são observações desta execução. Não demonstram, por si só, em que fase interna a API aplica o offset nem generalizam para outras queries ou combinações de parâmetros.
