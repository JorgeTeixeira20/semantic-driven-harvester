# Experiências

## Experiência 1 — Paginação, deduplicação e maxItems na TextSearch

### Objetivo

Caracterizar, numa pesquisa controlada, a relação observável entre
`estimated_nr_results`, `maxItems`, `offset`, os parâmetros de deduplicação e o
número efetivo de resultados devolvidos pela API TextSearch do Arquivo.pt.

### Hipótese

- `offset=100` e `offset=200` poderão expor novas janelas mesmo quando a
  primeira resposta não inclui `next_page`.
- Omissão de `dedupField` e `dedupValue` poderá devolver mais ocorrências
  repetidas do mesmo URL do que `dedupField=url`, `dedupValue=1`.
- Valores maiores de `maxItems` poderão aumentar o número efetivo de
  resultados, mas não se assume uma relação linear nem que a API aceite 2000.

Estas hipóteses são proposições a testar, não conclusões prévias.

### Configuração

Execução realizada em 26 de agosto de 2026 com os parâmetros comuns:

```text
query = Sporting
siteSearch = record.pt
from = 2015
to = 2020
```

O cliente existente expandiu o domínio simples para os hosts `record.pt` e
`www.record.pt`. Foram executadas seis variantes:

| Teste | maxItems pedido | offset | Parâmetros dedup enviados |
| --- | ---: | ---: | --- |
| A | 100 | 0 | `dedupField=url`, `dedupValue=1` |
| B | 100 | 100 | `dedupField=url`, `dedupValue=1` |
| C | 100 | 200 | `dedupField=url`, `dedupValue=1` |
| D | 2000 | 0 | `dedupField=url`, `dedupValue=1` |
| E | 100 | 0 | nenhum |
| F | 200 | 0 | `dedupField=url`, `dedupValue=1` |

As respostas foram guardadas byte a byte em `data/raw/api_diagnostics/`.

### Resultados

| Teste | maxItems pedido/API | offset | dedup pedido/API | estimated | recebidos | URLs únicas | tstamps únicos | next_page |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| A | 100/100 | 0 | url/1 explícito | 6 721 102 | 33 | 33 | 33 | não |
| B | 100/100 | 100 | url/1 explícito | 6 721 102 | 0 | 0 | 0 | não |
| C | 100/100 | 200 | url/1 explícito | 6 721 102 | 0 | 0 | 0 | não |
| D | 2000/500 | 0 | url/1 explícito | 6 721 102 | 96 | 96 | 96 | não |
| E | 100/100 | 0 | omitido → url/2 | 6 721 102 | 53 | 46 | 53 | não |
| F | 200/200 | 0 | url/1 explícito | 6 721 102 | 57 | 57 | 57 | não |

Primeiro e último resultado na ordem devolvida pela API:

| Teste | Primeiro tstamp | Primeiro URL | Último tstamp | Último URL |
| --- | --- | --- | --- | --- |
| A | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170921171011 | http://www.record.pt/internacional/paises/espanha/detalhe/yeray-alvarez-volta-aos-treinos-apos-recuperar-de-tumor-nos-testiculos.html |
| B | n/a | n/a | n/a | n/a |
| C | n/a | n/a | n/a | n/a |
| D | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170913234951 | http://www.record.pt/modalidades/tenis/detalhe/kohlmann-acredita-que-a-alemanha-tem-boas-hipoteses-frente-a-portugal-mesmo-sem-zverevs.html |
| E | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170921171011 | http://www.record.pt/internacional/paises/espanha/detalhe/yeray-alvarez-volta-aos-treinos-apos-recuperar-de-tumor-nos-testiculos.html |
| F | 20191120063616 | https://www.record.pt/sabermais/sporting | 20170108221237 | http://www.record.pt/internacional/paises/espanha/detalhe/valencia-ja-chegou-a-acordo-com-a-juventus-por-zaza.html |

Comparação de offsets:

- B contém 0 URLs de A e 0 URLs novas, porque devolveu 0 resultados;
- C contém 0 URLs da união A/B e 0 URLs novas, porque devolveu 0 resultados.

Comparação dos parâmetros de deduplicação:

- A, com `url/1` explícito, devolveu 33 resultados e 33 URLs distintas;
- E, sem parâmetros enviados, devolveu 53 resultados, 46 URLs distintas e 7
  ocorrências repetidas;
- a resposta E reportou os defaults `dedupField=url`, `dedupValue=2`.

Comparação de `maxItems`:

- pedido 100: 33 resultados;
- pedido 200: 57 resultados;
- pedido 2000, normalizado pela API para 500: 96 resultados;
- A e F partilham 32 URLs; F acrescenta 25, mas omite 1 URL presente em A;
- F e D partilham 52 URLs; D acrescenta 44, mas omite 5 URLs presentes em F.

### Observações

- `estimated_nr_results` foi sempre 6 721 102, incluindo B e C, que devolveram
  zero itens.
- Nenhuma das seis respostas incluiu `next_page`.
- `offset=100` e `offset=200` não produziram novas janelas nesta execução.
- Foi possível ultrapassar os 33 resultados anteriores: F devolveu 57 e D
  devolveu 96.
- A API não aceitou literalmente `maxItems=2000`: em `request_parameters`
  registou `maxItems=500`.
- A omissão dos parâmetros de dedup não desativou a deduplicação; a resposta E
  registou `dedupField=url`, `dedupValue=2`.
- Os conjuntos obtidos com `maxItems` crescentes não são estritamente
  encaixados: alguns URLs de uma resposta menor estão ausentes da resposta
  maior.
- O primeiro resultado foi o mesmo em A, D, E e F. B e C não tiveram primeiro
  ou último resultado.

### Interpretação

- Os dados sugerem que `estimated_nr_results` não representa diretamente o
  número de itens acessíveis através desta combinação de filtros, dedup e
  offset. A experiência não determina o significado interno exato da
  estimativa.
- O facto de B e C serem vazios sugere que os offsets pedidos excedem a janela
  efetivamente materializada nesta configuração. Não demonstra onde ou quando
  o offset é aplicado internamente.
- Pedir um `maxItems` maior aumentou o número de resultados, mas também alterou
  a composição do conjunto; os dados não suportam interpretar F e D como meras
  extensões estáveis de A.
- A diferença entre A e E compara `dedupValue=1` explícito com o default
  `dedupValue=2`, não deduplicação ligada contra desligada. Assim, esta
  experiência não mede um verdadeiro modo “dedup OFF”.

### Conclusões suportadas

- Para esta pesquisa e nesta execução, `offset=100` e `offset=200` devolveram
  zero resultados e não permitiram ultrapassar a primeira janela.
- Aumentar o `maxItems` pedido de 100 para 200 e depois para 2000 aumentou os
  resultados observados de 33 para 57 e 96, respetivamente.
- A API limitou o pedido de 2000 a 500 segundo os próprios
  `request_parameters`.
- `next_page` esteve ausente em todas as respostas, mesmo com uma estimativa de
  milhões de resultados.
- A omissão dos parâmetros de dedup acionou defaults `url/2`; não produziu um
  modo sem deduplicação.

Continuam sem resposta:

- o significado operacional exato de `estimated_nr_results` neste cenário;
- a ordem interna entre pesquisa, filtros, ranking, dedup e aplicação de
  `maxItems`/`offset`;
- se existe uma forma suportada de desativar completamente a deduplicação;
- por que razão os conjuntos para diferentes `maxItems` não são encaixados;
- qual é o limite efetivo e estável de resultados acessíveis para esta query.

### Decisão

Para futuras experiências de construção do corpus:

- não usar `estimated_nr_results` como número de resultados recuperáveis;
- enviar `dedupField=url`, `dedupValue=1` explicitamente quando forem desejados
  URLs únicos;
- registar sempre os parâmetros reportados pela API, além dos pedidos;
- não assumir que `offset` funciona quando `next_page` está ausente;
- tratar `maxItems=500` como o máximo observado nesta chamada, sem concluir que
  é um limite universal da API;
- preservar raw e comparar conjuntos quando se alterar `maxItems`.

## Experiência 2 — Offset funciona quando a primeira página vem cheia?

### Objetivo

Testar especificamente se `offset` permite paginar quando a primeira página
devolvida pela API vem efetivamente cheia (`results_received == maxItems`).
Na Experiência 1, nenhuma das seis variantes preencheu o `maxItems` pedido
(máximo observado: 96 de 500), pelo que `offset=100` e `offset=200`
devolverem 0 podia refletir apenas a ausência de mais resultados
materializados para aquela pesquisa específica (`Sporting`, `record.pt`,
2015–2020), não uma limitação geral da API.

### Hipótese

- Quando a primeira página vem genuinamente cheia, `offset` permite obter
  janelas seguintes com resultados novos, incluindo nos valores 100 e 200 que
  na Experiência 1 devolveram 0.

### Seleção da pesquisa

Antes de fixar a configuração final, foram feitas sondagens diretas à API
(pedidos ad-hoc, fora do módulo de diagnóstico, sem raw preservado) para
encontrar uma combinação com maior probabilidade de devolver uma página
cheia:

- `Sporting`, `siteSearch=record.pt`, `maxItems=100`: 33 resultados (igual à
  Experiência 1).
- `Sporting`, sem `siteSearch`, `maxItems=20`, `dedupField=url`/`dedupValue=1`
  explícitos: 13, 12 e 5 resultados nas três primeiras janelas — ainda sem
  preencher a página. Esta tentativa foi executada como módulo formal (letras
  G/H/I) antes desta conclusão; os raw ficaram preservados com o prefixo
  `pilot_sporting_` em `data/raw/api_diagnostics_offset/` e os relatórios em
  `output/api_diagnostics_offset_pilot.csv`/`.md`.
- `futebol`, sem `siteSearch`, `maxItems=20`, sem `dedupField`/`dedupValue`
  explícitos (defaults da API): 20 de 20 resultados — página cheia.

A configuração final usa `futebol`, sem `siteSearch`, `maxItems=20`, sem
parâmetros de dedup explícitos, com offsets 0, 20, 40, 100 e 200. Os offsets
100 e 200 replicam os valores da Experiência 1; 20 e 40 verificam
continuidade entre páginas consecutivas.

### Configuração

Execução realizada em 17 de setembro de 2026 com os parâmetros comuns:

```text
query = futebol
siteSearch = (nenhum)
from = 2015
to = 2020
maxItems = 20
dedupField/dedupValue = (nenhum enviado; defaults da API)
```

Cinco variantes, implementadas em
`src/semantic_harvester/api_diagnostics_offset.py`:

| Teste | offset |
| --- | ---: |
| G | 0 |
| H | 20 |
| I | 40 |
| J | 100 |
| K | 200 |

As respostas foram guardadas byte a byte em
`data/raw/api_diagnostics_offset/`.

### Resultados

| Teste | maxItems pedido/API | offset | dedup reportado pela API | estimated | recebidos | página cheia | URLs únicas | tstamps únicos | next_page |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- |
| G | 20/20 | 0 | title/2 | 286 123 167 | 20 | sim | 13 | 20 | sim |
| H | 20/20 | 20 | title/2 | 286 123 167 | 20 | sim | 14 | 17 | sim |
| I | 20/20 | 40 | title/2 | 286 123 167 | 20 | sim | 17 | 20 | sim |
| J | 20/20 | 100 | title/2 | 245 042 486 | 20 | sim | 18 | 19 | sim |
| K | 20/20 | 200 | title/2 | 232 123 711 | 20 | sim | 20 | 19 | sim |

Sobreposição de URLs entre janelas:

- H: 3 URLs já presentes em G; 11 novas (a soma 3+11=14 corresponde às URLs
  distintas de H; a diferença até 20 reflete tstamps repetidos da mesma URL
  dentro da própria janela);
- I: 4 URLs já presentes na união G∪H; 13 novas;
- J (offset=100): 0 URLs já presentes na união G∪H∪I; 18 novas;
- K (offset=200): 0 URLs já presentes na união G∪H∪I∪J; 20 novas.

### Observações

- As cinco janelas devolveram exatamente 20 de 20 resultados pedidos —
  página cheia em todos os casos, ao contrário de todas as variantes da
  Experiência 1.
- `next_page` esteve presente nas cinco respostas, incluindo em offset=100 e
  offset=200 — o oposto do observado na Experiência 1 para os mesmos offsets.
- Os offsets 100 e 200 devolveram resultados totalmente novos (zero
  sobreposição com as janelas anteriores), tal como o offset 20 e 40
  devolveram maioritariamente resultados novos.
- `estimated_nr_results` não foi constante entre variantes desta execução
  (286 123 167 em G/H/I; 245 042 486 em J; 232 123 711 em K), apesar de a
  query, datas e `maxItems` pedidos serem os mesmos. A causa desta variação
  não foi investigada.
- O `dedupField` reportado por omissão foi `title` (com `dedupValue=2`) nesta
  execução, diferente do `url`/`dedupValue=2` reportado por omissão na
  Experiência 1 (teste E). Não foi identificada a causa desta diferença de
  default; pode depender de `siteSearch` estar ou não presente, ou de outro
  fator não isolado por estas duas experiências.
- Em G, H e I, `distinct_original_urls` foi inferior a 20 (13, 14, 17), com
  `distinct_tstamps` mais próximo de 20 — sinal de múltiplas capturas da
  mesma URL na mesma janela, consistente com dedup por `title` em vez de
  `url`.
- A tentativa preliminar com `Sporting` sem `siteSearch` e com
  `dedupField=url`/`dedupValue=1` explícitos não preencheu a página (13, 12 e
  5 de 20); só a combinação sem parâmetros de dedup explícitos, com a query
  `futebol`, produziu páginas cheias nesta exploração.

### Interpretação

- Quando a primeira página vem efetivamente cheia, `offset` demonstrou
  paginar corretamente nesta execução, incluindo nos valores 100 e 200 que na
  Experiência 1 devolveram 0. Isto é consistente com a hipótese de que o
  resultado vazio da Experiência 1 refletia o esgotamento dos resultados
  materializados para aquela pesquisa/dedup específicos, não uma limitação
  geral de `offset`.
- Esta experiência não isola qual variável (ausência de `siteSearch`,
  omissão de dedup explícito, ou a própria query) foi responsável por
  produzir páginas cheias; apenas demonstra que, nesta combinação, `offset`
  funcionou com página cheia.
- A variação de `estimated_nr_results` e do `dedupField` default entre
  execuções sugere que estes valores não são constantes por query, o que
  reforça a decisão já tomada na Experiência 1 de não usar
  `estimated_nr_results` como contagem fiável e de registar sempre os
  parâmetros reportados pela API.

### Conclusões suportadas

- Para a pesquisa `futebol` (sem `siteSearch`, sem dedup explícito,
  `maxItems=20`, 2015–2020) e nesta execução, `offset=20`, `offset=40`,
  `offset=100` e `offset=200` devolveram páginas cheias com resultados
  distintos das janelas anteriores.
- O resultado da Experiência 1 (offset=100/200 devolverem 0) não generaliza:
  não é uma limitação universal de `offset` na API TextSearch, mas depende de
  a pesquisa ter resultados materializados suficientes para essa janela.
- `next_page` esteve presente sempre que a página correspondente veio cheia
  nesta execução, ao contrário da Experiência 1, em que nunca esteve
  presente.

Continuam sem resposta:

- qual, entre a ausência de `siteSearch`, a omissão de dedup explícito e a
  escolha da query, foi determinante para obter páginas cheias;
- por que o `dedupField` default variou entre `url` (Experiência 1) e `title`
  (Experiência 2);
- por que `estimated_nr_results` variou entre variantes desta execução com a
  mesma query, datas e `maxItems`;
- qual é o limite efetivo de `offset` quando os resultados materializados se
  esgotam para uma pesquisa concreta.

### Decisão

Para o protocolo de recolha do Caminho A (corpus real de vários artigos):

- não descartar `offset` como mecanismo de paginação só porque uma pesquisa
  concreta o devolveu vazio; verificar primeiro se a página anterior veio
  cheia;
- continuar a registar os parâmetros reportados pela API (incluindo
  `dedupField`/`dedupValue` default) em vez de assumir os pedidos;
- continuar a não usar `estimated_nr_results` como contagem fiável, dado que
  variou entre variantes desta execução mesmo com os mesmos parâmetros
  pedidos;
- preservar evidência de tentativas preliminares (como os `pilot_*` desta
  experiência) em vez de as descartar, por documentarem parte do processo de
  seleção da pesquisa.
