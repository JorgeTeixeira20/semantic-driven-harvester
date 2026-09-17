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

## Experiência 3 — Volume de queries genéricas em siteSearch=record.pt

### Objetivo

Testar, antes de iniciar o Caminho A, se substituir uma query específica
(nome de jogador/equipa) por um termo genérico (`futebol`, `desporto`)
aumenta a probabilidade de uma página cheia quando a pesquisa continua
restrita a `siteSearch=record.pt` — restrição que o Caminho A precisa de
manter, porque o corpus visado é especificamente de artigos do Record. A
Experiência 2 tinha mostrado página cheia sem `siteSearch`; esta experiência
verifica se esse resultado se mantém com a pesquisa restrita ao site.

### Hipótese

- Um termo genérico, por cobrir mais páginas do site, poderá preencher
  `maxItems` mais facilmente do que um nome específico como `Sporting`
  (Experiência 1: 33 de 100 pedidos).

### Observação preliminar sobre instabilidade

Antes de formalizar o teste, sondagens diretas à API (fora do módulo,
parâmetros idênticos, pedidos consecutivos, sem raw preservado) mostraram
contagens diferentes de `results_received` e `estimated_nr_results` para o
mesmo pedido repetido: `Sporting` devolveu 6, depois 4, depois 6 resultados
em três pedidos seguidos; `futebol` (sem `siteSearch`) devolveu 2 e depois
17. Por esta razão, o teste formal repete cada query `TRIALS=3` vezes com os
mesmos parâmetros, em vez de usar uma única amostra por query.

### Configuração

Execução realizada em 17 de setembro de 2026 com
`src/semantic_harvester/api_diagnostics_site_volume.py`:

```text
siteSearch = record.pt (o cliente inclui também www.record.pt)
from = 2015
to = 2020
maxItems = 20
dedupField/dedupValue = (nenhum enviado; defaults da API)
queries = Sporting, futebol, desporto
tentativas por query = 3
```

As respostas foram guardadas byte a byte em
`data/raw/api_diagnostics_site_volume/`.

### Resultados

| Query | Tentativa | maxItems pedido/API | dedup reportado pela API | estimated | recebidos | página cheia |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| Sporting | 1 | 20/20 | url/2 | 6 366 674 | 5 | não |
| Sporting | 2 | 20/20 | url/2 | 6 468 098 | 3 | não |
| Sporting | 3 | 20/20 | url/2 | 6 464 286 | 7 | não |
| futebol | 1 | 20/20 | url/2 | 6 494 908 | 2 | não |
| futebol | 2 | 20/20 | url/2 | 6 494 908 | 2 | não |
| futebol | 3 | 20/20 | url/2 | 6 494 908 | 2 | não |
| desporto | 1 | 20/20 | url/2 | 6 478 714 | 2 | não |
| desporto | 2 | 20/20 | url/2 | 6 463 849 | 2 | não |
| desporto | 3 | 20/20 | url/2 | 6 478 714 | 2 | não |

Resumo por query: `Sporting` recebeu entre 3 e 7 (de 20); `futebol` recebeu
exatamente 2 nas três tentativas; `desporto` recebeu exatamente 2 nas três
tentativas. Nenhuma das nove tentativas encheu a página pedida
(`maxItems=20`).

### Observações

- Nenhuma das três queries, com `siteSearch=record.pt`, encheu a página em
  nenhuma das três tentativas — nem a específica (`Sporting`), nem as
  genéricas (`futebol`, `desporto`).
- `Sporting` variou entre tentativas idênticas nesta execução formal (3, 5,
  7), confirmando instabilidade por pedido também dentro do módulo de
  diagnóstico, não apenas nas sondagens preliminares.
- `futebol` e `desporto` foram estáveis (2/2/2) dentro desta execução, ao
  contrário da variação observada informalmente antes de escrever o módulo
  (2 e depois 17). Não foi possível determinar, com estas nove tentativas,
  em que condições a variação ocorre ou não.
- `estimated_nr_results` variou ligeiramente entre tentativas da mesma query
  (ex.: `Sporting` entre 6 366 674 e 6 468 098), reforçando a decisão já
  tomada de não o tratar como contagem fiável.
- O `dedupField`/`dedupValue` default nesta execução foi sempre `url`/`2`,
  consistente com a Experiência 1 (teste E) e diferente do `title`/`2`
  observado na Experiência 2 (sem `siteSearch`). Isto é consistente com a
  hipótese, ainda não confirmada, de que o default de `dedupField` depende
  da presença de `siteSearch`.

### Interpretação

- Nesta execução, trocar uma query específica por um termo genérico não
  resolveu o problema de página incompleta enquanto a pesquisa continuar
  restrita a `siteSearch=record.pt`. O fator que permitiu página cheia na
  Experiência 2 parece estar ligado à ausência de `siteSearch` (ou a outra
  variável não isolada), não apenas à generalidade do termo de pesquisa.
- A variação de `results_received` para pedidos idênticos (`Sporting`: 3, 5,
  7) mostra que a contagem de resultados devolvida pela API não é uma
  propriedade estável da combinação de parâmetros nesta janela de
  observação. Isto limita a validade de qualquer comparação baseada numa
  única amostra por variante, incluindo nas Experiências 1 e 2: as
  diferenças observadas entre variantes podem estar parcialmente
  confundidas com esta variação por pedido, embora as diferenças de maior
  magnitude (ex.: 0 vs. 20 resultados, ou 33 vs. 96) sejam maiores do que a
  variação aqui observada (3 a 7).
- Não é possível, com esta amostra, distinguir se a variação reflete
  alterações reais no índice, comportamento de cache/balanceamento de carga,
  ou amostragem interna da API.

### Conclusões suportadas

- Para as três queries testadas, com `siteSearch=record.pt` e
  `maxItems=20`, nenhuma tentativa (de nove) encheu a página.
- Um termo genérico (`futebol`, `desporto`) não produziu, nesta execução,
  mais resultados do que o termo específico `Sporting`; pelo contrário,
  `Sporting` obteve mais resultados (3–7) do que `futebol`/`desporto`
  (2 em todas as tentativas).
- Pedidos idênticos e consecutivos à mesma query podem devolver contagens
  diferentes de `results_received` e `estimated_nr_results`; a API TextSearch
  não é determinística por pedido nesta janela de observação.

Continuam sem resposta:

- se existe alguma query ou combinação de parâmetros que encha uma página
  com `siteSearch=record.pt` de forma estável;
- a causa da variação de resultados entre pedidos idênticos (índice, cache,
  balanceamento de carga, ou amostragem interna);
- se o default de `dedupField` depende da presença de `siteSearch` ou de
  outro fator.

### Decisão

Para o protocolo de recolha do Caminho A:

- não assumir que uma query "mais ampla" resolve, por si só, o problema de
  página incompleta dentro de `siteSearch=record.pt`; esta experiência não
  encontrou nenhuma combinação estável que a preenchesse;
- planear a recolha para páginas tipicamente incompletas quando restrita ao
  site (ex.: várias queries pequenas — por ano, por secção, por
  jogador/equipa — em vez de poucas queries genéricas com `maxItems` grande);
  isto é uma implicação prática desta experiência, não uma solução já
  testada;
- repetir pedidos idênticos pelo menos uma vez antes de tirar conclusões
  sobre uma query ou combinação específica, dado a instabilidade observada;
- continuar a registar os parâmetros reportados pela API e a preservar o raw
  de cada tentativa, para permitir revisitar a variação observada.

## Protocolo de queries para o corpus do Caminho A (proposta — por validar, sem execução)

**Estado: proposta escrita para validação do autor. Nenhum pedido à API foi
feito para esta secção; os números abaixo são estimativas de contagem de
pedidos, não resultados observados.**

Este protocolo é uma ferramenta operacional de recolha — uma grelha de termos
de pesquisa a combinar com `siteSearch=record.pt` — e não deve ser confundida
com conceitos da ontologia como `EntidadeMencionada` ou `Tema`
([ontology/semantic_harvester.ttl](../ontology/semantic_harvester.ttl)), que
são categorias do modelo de dados final, não termos de pesquisa. Não
corresponde a uma "árvore de conhecimento": é apenas a lista de queries a
enviar à API TextSearch para popular o corpus do Caminho A.

### Motivação

A Experiência 3 mostrou que, dentro de `siteSearch=record.pt`, nem uma query
específica (`Sporting`) nem termos genéricos (`futebol`, `desporto`) enchem
uma página, e que pedidos idênticos e consecutivos podem devolver contagens
diferentes. Isto significa que não é viável construir o corpus com uma ou
duas queries largas: é necessário combinar várias queries pequenas, cobrindo
diferentes dimensões do conteúdo do Record, e agregar/deduplicar os
resultados no fim.

### Âmbito: amostra deliberada, não exaustiva

Consistente com a regra do [AGENTS.md](../AGENTS.md) de não generalizar
conclusões de uma amostra para toda a API ou, aqui, para todo o Record: esta
proposta não pretende cobrir todas as modalidades, clubes, atletas ou anos
cobertos pelo Record. É uma amostra pequena e deliberada, dimensionada pelo
prazo de 31 de outubro de 2026 e pelo custo de repetir pedidos por causa da
não-determinismo observado na Experiência 3. O corpus resultante deve ser
descrito na dissertação como uma amostra intencional destas facetas e destes
termos, não como uma cobertura representativa do jornal Record.

### Facetas e termos propostos

| Faceta | Termos propostos | Nº de termos | Justificação |
| --- | --- | ---: | --- |
| Modalidade | `futebol`, `basquetebol`, `andebol` | 3 | Modalidades com cobertura regular no Record; futebol como modalidade dominante, as outras duas para alguma diversidade fora do futebol. |
| Clube | `Benfica`, `Sporting`, `Porto` | 3 | Os três clubes de futebol mais cobertos pela imprensa desportiva portuguesa; reutilizam queries já exploradas nas Experiências 1–3 (Sporting) e no M1 (Benfica). **Limitação assumida:** os três são clubes de futebol, o que enviesa esta faceta para essa modalidade. |
| Atleta conhecido | `Cristiano Ronaldo`, `Bruno Fernandes`, `Telma Monteiro` | 3 | Dois futebolistas amplamente cobertos pelo Record (incluindo período de ligação a clubes portugueses) e uma atleta de outra modalidade (judo), para reduzir a sobreposição total com a faceta "clube". |

Total: **9 termos de pesquisa distintos**. Estes termos são candidatos a
validar/ajustar com o autor antes de qualquer execução; não são o resultado
de uma seleção sistemática do conteúdo real do Record.

### Intervalo temporal

Um único intervalo, aplicado a todos os termos: `from=2015`, `to=2020`
(o mesmo já usado nas Experiências 1–3, por continuidade e comparabilidade).
Não se propõe testar vários intervalos por termo nesta amostra — isso
multiplicaria os pedidos sem necessidade clara, dado que o problema
identificado (página incompleta) não foi associado ao intervalo temporal em
nenhuma experiência anterior.

### Parâmetros comuns por pedido

```text
siteSearch = record.pt (o cliente inclui também www.record.pt)
from = 2015
to = 2020
maxItems = 50
dedupField = url
dedupValue = 1
```

`maxItems=50` (maior do que os 20 usados nas Experiências 2–3) pede mais
resultados por pedido sem custar pedidos adicionais; dado que a Experiência 3
não encontrou nenhuma combinação que enchesse `maxItems=20` dentro de
`siteSearch=record.pt`, não há indicação de que 50 vá gerar mais chamadas de
paginação do que 20 geraria. `dedupField=url`/`dedupValue=1` explícitos
seguem a decisão da Experiência 1 (queremos URLs únicos por pedido, ao
contrário das Experiências 2–3, que omitiram propositadamente o dedup para
testar o preenchimento de página).

### Pedidos por termo e contingência de offset

Dado o achado da Experiência 3 de repetir pedidos idênticos antes de tirar
conclusões, e para tirar partido da própria não-determinismo (repetições
podem trazer artigos diferentes da mesma query, não só confirmar
estabilidade):

- cada termo é pedido **2 vezes** (pedido inicial + 1 repetição) com os
  mesmos parâmetros — **pedidos base**;
- se uma dessas respostas vier com página cheia (`results_received ==
  maxItems`), pede-se também `offset=maxItems` para essa combinação
  específica, seguindo a decisão da Experiência 2 de só usar `offset` depois
  de confirmar página cheia — **pedido condicional**;
- se a resposta ao offset também vier cheia, repete-se o mesmo critério
  (mais offset), mas não se propõe um limite superior de páginas nesta
  proposta — isso seria decidido caso a caso se o cenário ocorrer, dado que a
  Experiência 3 não encontrou nenhuma página cheia em `siteSearch=record.pt`.

### Estimativa de pedidos

| Faceta | Termos | Pedidos base (2×) | Pedidos condicionais (offset, se página cheia) |
| --- | ---: | ---: | --- |
| Modalidade | 3 | 6 | até 6 (se todas as 6 respostas vierem cheias) |
| Clube | 3 | 6 | até 6 |
| Atleta conhecido | 3 | 6 | até 6 |
| **Total** | **9** | **18** | **até 18** |

**Estimativa: mínimo 18 pedidos reais à API, máximo teórico 36** (se todas as
18 respostas base vierem com página cheia, o que a Experiência 3 não
observou em nenhuma das suas 9 tentativas com uma restrição de site
equivalente). O cenário mais provável, à luz da Experiência 3, é próximo do
mínimo de 18, com poucos ou nenhum pedido condicional de offset.

### Agregação e deduplicação entre queries

Vários termos desta grelha podem devolver a mesma captura (ex.: um artigo
sobre Cristiano Ronaldo pode surgir tanto na query `futebol` como em
`Cristiano Ronaldo`). A agregação é feita offline, depois de todos os
pedidos, sem chamadas adicionais à API:

1. Preservar o raw de cada pedido byte a byte, com um nome que identifique
   faceta, termo e número da repetição (ex.:
   `data/raw/corpus_queries/<faceta>_<termo>_rep<N>.json`), seguindo o
   padrão já usado em `api_diagnostics.py` e módulos seguintes.
2. Ler todos os `response_items` de todos os ficheiros raw e anotar cada
   item com a proveniência (faceta, termo, repetição, ficheiro de origem).
3. Identidade de captura: `(originalURL, tstamp)`, o mesmo par já usado em
   `rdf_mapper.py` para gerar IDs determinísticos de `CapturaArquivada`. Não
   introduzir um novo critério de identidade paralelo.
4. Identidade de artigo/recurso: `originalURL`, o mesmo campo já usado para
   `article_id` em `history_pipeline.py`, partilhado por todas as capturas
   do mesmo URL.
5. Quando o mesmo par `(originalURL, tstamp)` aparecer em mais do que um
   ficheiro raw, manter uma única captura no corpus agregado, mas registar a
   união das proveniências (quais faceta/termo a devolveram) como metadado
   de recolha — não é um campo da ontologia, apenas informação sobre o
   processo, útil para caracterizar a amostra na dissertação.
6. Se os campos do mesmo `(originalURL, tstamp)` diferirem entre ocorrências
   (já observado no M3 entre `TextSearch` e `versionHistory` para a mesma
   captura), preservar ambas as versões raw e sinalizar a divergência, em
   vez de escolher uma automaticamente — consistente com a forma como essa
   divergência já foi tratada no M3.
7. Capturas distintas do mesmo `originalURL` (tstamps diferentes) não são
   deduplicadas nesta etapa: várias capturas por artigo já são o
   comportamento esperado e desejado do modelo (`RecursoWeb` →
   `CapturaArquivada`). A redução de redundância textual entre capturas do
   mesmo artigo é explicitamente o âmbito do Caminho D, não desta agregação.
8. A classificação `Artigo` vs. página de secção/redirecionamento (já
   identificada como pendente no plano do Caminho A) acontece depois desta
   agregação, sobre a lista já deduplicada por identidade de captura — não
   é resolvida por este protocolo de queries.

### Limitações explícitas desta proposta

- A lista de termos (9) é uma amostra intencional, não uma cobertura
  sistemática das modalidades, clubes ou atletas do Record; outras escolhas
  de termos são igualmente válidas e não foram testadas.
- A faceta "clube" está enviesada para futebol; não foi incluído nenhum
  clube identificado principalmente com outra modalidade.
- Não é feita nenhuma previsão do número de artigos únicos que este protocolo
  vai produzir — a Experiência 3 mostrou que a contagem de resultados por
  pedido varia mesmo para parâmetros idênticos, pelo que qualquer estimativa
  de rendimento seria inventada, não uma medição.
- Este protocolo não resolve, nem tenta resolver, a causa da não-determinismo
  da API nem a razão de `siteSearch=record.pt` limitar tanto os resultados;
  apenas assume essas limitações como dadas e desenha a recolha em torno
  delas.

### Próximos passos (após validação)

1. Validar com o autor a lista de termos e o intervalo temporal acima.
2. Implementar a recolha seguindo exatamente os parâmetros e a contingência
   de offset descritos, preservando raw por faceta/termo/repetição.
3. Implementar a agregação/deduplicação descrita acima como um passo
   separado e testável, antes de qualquer mapeamento RDF do corpus.
4. Só depois disso, aplicar a regra de classificação Artigo/redirecionamento
   e prosseguir com o resto do Caminho A.

Esta secção não deve ser executada como recolha em massa sem validação
explícita do autor, dado o custo de pedidos reais e a não-determinismo já
observada.
