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

## Protocolo de queries para o corpus do Caminho A

**Estado em 2026-09-20: Caminho A concluído, com a retentativa dos textos e a
reconstrução do grafo feitas.** Fase 1: 26 pedidos, N = 159 artigos únicos.
Fase 2: 159/159 artigos, 0 falhas, 7 572 capturas, 125 artigos com mais do que
uma captura. Passo 6: 158 recursos distintos depois de normalizar http/https,
127 classificados como Artigo. Mapeamento RDF final: 127 artigos, 941
capturas, **789 textos disponíveis (83,8%) e 152 indisponíveis (16,2%)**,
13 482 triplos — ver "Resultados da retentativa e reconstrução do grafo" no
fim deste documento (substitui os 540/401 anteriores à retentativa).

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

### Facetas e termos — decisão final (Opção 2, ver "Decisão de dimensionamento" abaixo)

| Faceta | Termos | Nº de termos | Justificação |
| --- | --- | ---: | --- |
| Modalidade | `futebol`, `basquetebol`, `andebol`, `voleibol` | 4 | Modalidades com cobertura regular no Record; futebol como modalidade dominante, as outras três para alguma diversidade fora do futebol. |
| Clube | `Benfica`, `Sporting`, `Porto`, `SC Braga` | 4 | Os três clubes de futebol mais cobertos pela imprensa desportiva portuguesa, mais o SC Braga como quarto grande clube nacional; reutilizam queries já exploradas nas Experiências 1–3 (Sporting) e no M1 (Benfica). **Limitação assumida:** os quatro são clubes de futebol, o que enviesa esta faceta para essa modalidade. |
| Atleta conhecido | `Cristiano Ronaldo`, `Bruno Fernandes`, `Telma Monteiro`, `João Félix`, `Nelson Évora` | 5 | Três futebolistas amplamente cobertos pelo Record e duas atletas de outras modalidades (judo, atletismo), para reduzir a sobreposição total com a faceta "clube". |

Total: **13 termos de pesquisa distintos**. Esta lista é a decisão final do
autor e do Jorge (Opção 2 — Moderada, 2026-09-17); não é o resultado de uma
seleção sistemática do conteúdo real do Record, continua a ser uma amostra
deliberada (ver "Âmbito" acima).

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

### Estimativa de pedidos (Fase 1 — descoberta via TextSearch)

Esta secção cobre só os pedidos de descoberta (TextSearch). Os pedidos de
`version_history` por artigo único descoberto (Fase 2) são uma etapa
adicional, descrita depois da agregação/deduplicação, com a sua própria
estimativa.

| Faceta | Termos | Pedidos base (2×) | Pedidos condicionais (offset, se página cheia) |
| --- | ---: | ---: | --- |
| Modalidade | 4 | 8 | até 8 (se todas as 8 respostas vierem cheias) |
| Clube | 4 | 8 | até 8 |
| Atleta conhecido | 5 | 10 | até 10 |
| **Total** | **13** | **26** | **até 26** |

**Estimativa: mínimo 26 pedidos reais à API, máximo teórico 52** (se todas as
26 respostas base vierem com página cheia, o que a Experiência 3 não
observou em nenhuma das suas 9 tentativas com uma restrição de site
equivalente). O cenário mais provável, à luz da Experiência 3, é próximo do
mínimo de 26, com poucos ou nenhum pedido condicional de offset.

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

### Profundidade temporal: version_history por artigo (Fase 2)

**Isto não estava explícito na versão anterior desta proposta.** A versão
anterior descrevia apenas a descoberta de artigos via TextSearch (Fase 1),
sem dizer o que acontece depois por artigo. Sem este passo, o corpus final
teria só a captura devolvida pela TextSearch por artigo — tipicamente uma
única captura —, sem profundidade temporal nenhuma. Como a caracterização
temporal por artigo é metade do objetivo da dissertação segundo o RPD (a
outra metade sendo a estrutural), este passo é necessário, não opcional.

O M3 já resolveu este problema para um único artigo: `history_pipeline.py`
usa `ArquivoClient.version_history()` para obter, sem restrição de datas, o
histórico completo de capturas de um `originalURL`, com paginação por
`offset` já implementada em `collect_all_captures()` (repete pedidos
enquanto a página vier cheia e houver `next_page`, parando quando a página
vem incompleta ou vazia — a mesma lógica de paragem validada pela
Experiência 2). Hoje esta função só é chamada uma vez, para o URL fixo
`SAMPLE_ORIGINAL_URL` em `rdf_mapper.py`.

**Adição ao protocolo:** depois de agregar/deduplicar as capturas
descobertas pela Fase 1 (secção anterior), correr `collect_all_captures()`
uma vez por cada `originalURL` único resultante — generalizando
`run_history_pipeline()`/`collect_all_captures()` de "um artigo hardcoded"
para "a lista de artigos únicos descoberta por este protocolo", sem alterar
a lógica de paginação já testada. Isto é trabalho de implementação (loop
sobre vários URLs em vez de um), não uma experiência nova.

**Nota em aberto, não decidida aqui:** a Fase 2 podia correr sobre todos os
`originalURL` únicos da Fase 1, ou só sobre os já classificados como
`Artigo` (depois da regra Artigo/redirecionamento referida no ponto 8
acima), o que pouparia pedidos de `version_history` gastos em páginas de
secção/redirecionamento. Esta proposta não decide a ordem; fica como opção
a validar com o autor quando a regra de classificação for implementada.

#### Estimativa de pedidos (Fase 2 — version_history)

Ao contrário da Fase 1, o número de pedidos da Fase 2 depende de `N`, o
número de `originalURL` únicos descobertos — que só é conhecido depois de
executar a Fase 1 e a agregação. Não é inventado um valor de `N` aqui,
consistente com a limitação já registada abaixo sobre não prever o
rendimento das queries. O que pode ser dito sem executar nada:

- **Pedidos por artigo:** no mínimo 1 (`collect_all_captures` com
  `page_size=50`, sem restrição de datas); mais 1 por cada página adicional
  cheia, só se esse artigo tiver mais de 50 capturas no histórico. O único
  artigo já observado (M3) teve 3 capturas — muito abaixo de 50 — pelo que
  históricos com paginação são esperados como exceção, não a norma, mas não
  há dados sobre os artigos que este protocolo vai descobrir.
- **Total da Fase 2 ≈ N** pedidos, no cenário sem paginação adicional (o
  mais provável, à luz do M3).
- **Teto teórico absoluto:** o número de itens devolvidos na Fase 1 não pode
  exceder `pedidos_TextSearch × maxItems(50)`; logo `N` (que é ≤ esse total,
  porque a deduplicação só pode reduzir, nunca aumentar, o número de URLs
  únicos) está limitado por esse mesmo valor. Este teto é uma bound
  matemática, não uma previsão realista — a Experiência 3 mostrou
  contagens muito abaixo de `maxItems` em todos os pedidos testados.
- **Ponto de verificação proposto:** correr primeiro a Fase 1 completa
  (descoberta + agregação/deduplicação), confirmar o valor real de `N`, e só
  depois decidir/confirmar se avançar para a Fase 2 com esse número de
  pedidos. Isto evita comprometer à partida um orçamento de pedidos para a
  Fase 2 baseado numa previsão não validada.

### Limitações explícitas desta proposta

- A lista de termos (13) é uma amostra intencional, não uma cobertura
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

### Decisão de dimensionamento: Opção 2 (Moderada) — decidido em 2026-09-17

A Experiência 3 mostrou contagens baixas por pedido (2–7 de `maxItems=20`)
dentro de `siteSearch=record.pt`. Depois de deduplicar entre facetas
sobrepostas (ex.: "Cristiano Ronaldo" pode surgir também em "futebol" e em
"Sporting"), o corpus único resultante da opção mínima podia ficar pequeno.
Foram apresentadas três opções ao autor e ao Jorge; **a escolha final foi a
Opção 2 (Moderada)**, já refletida na tabela de termos acima (13 termos: 4
modalidades, 4 clubes, 5 atletas conhecidos, 2 repetições/termo).

Registo das três opções consideradas, por referência histórica:

| Opção | Modalidades | Clubes | Atletas conhecidos | Total termos | Repetições/termo | Fase 1 (min–max) |
| --- | --- | --- | --- | ---: | ---: | --- |
| 1 — Manter | futebol, basquetebol, andebol | Benfica, Sporting, Porto, SC Braga | Cristiano Ronaldo, Bruno Fernandes, Telma Monteiro | 10 | 2 | 20–40 |
| **2 — Moderada (escolhida)** | + voleibol (4) | (sem alteração, 4) | + João Félix, Nelson Évora (5) | 13 | 2 | 26–52 |
| 3 — Maior | + voleibol (4) | + Vitória de Guimarães (5) | + João Félix, Nelson Évora (5) | 14 | 3 | 42–84 |

Para a Opção 2, o teto teórico da Fase 2 (`version_history`) continua a ser
`26 × 50 = 1300` pedidos no limite matemático absoluto (zero sobreposição
entre pedidos da Fase 1) — não uma previsão; o valor real de `N` só é
conhecido depois de executar a Fase 1 e a agregação (ver "Ponto de
verificação" abaixo).

### Resultados da Fase 1 (execução real, 2026-09-17)

Execução real de `src/semantic_harvester/corpus_phase1.py`, implementando
exatamente os parâmetros descritos acima. Raw preservado byte a byte em
`data/raw/corpus_queries/` (26 ficheiros); relatórios em
`output/corpus_phase1_per_term.csv`, `output/corpus_phase1_captures.csv` e
`output/corpus_phase1_aggregation.md`.

#### Resumo

- Pedidos reais efetuados: **26** (mínimo previsto; nenhuma página veio
  cheia em nenhum dos 26 pedidos base, pelo que não houve pedidos
  condicionais de offset — consistente com a Experiência 3, agora também
  observado com `maxItems=50` em vez de 20).
- Itens brutos recebidos antes de deduplicar: 400.
- Capturas únicas por `(originalURL, tstamp)`: 160.
- **N = 159 artigos únicos por `originalURL`.**
- Capturas encontradas por mais do que uma query: 20.
- Divergências de metadados para a mesma `(originalURL, tstamp)`: 20.
- Um artigo (`.../sporting/detalhe/zahavi-espera-contacto-leonino-692448.html`)
  já apareceu com dois `tstamp` distintos (`20170228223739` e
  `20180413194101`) mesmo antes da Fase 2 — uma amostra de profundidade
  temporal já visível na própria descoberta.

#### Pedidos e resultados por termo

| Faceta | Termo | Resultados (rep 1 / rep 2) |
| --- | --- | ---: |
| modalidade | futebol | 21 / 21 |
| modalidade | basquetebol | 20 / 20 |
| modalidade | andebol | 21 / 21 |
| modalidade | voleibol | 19 / 19 |
| clube | Benfica | 19 / 19 |
| clube | Sporting | 20 / 20 |
| clube | Porto | 16 / 16 |
| clube | SC Braga | 3 / 3 |
| atleta | Cristiano Ronaldo | 20 / 20 |
| atleta | Bruno Fernandes | 15 / 15 |
| atleta | Telma Monteiro | 6 / 6 |
| atleta | João Félix | 12 / 12 |
| atleta | Nelson Évora | 8 / 8 |

Tabela completa por pedido em `output/corpus_phase1_per_term.csv`.

#### Observações

- **Nenhuma página veio cheia** (máximo observado: 21 de `maxItems=50`,
  mínimo: 3, para `SC Braga`). Confirma, com `maxItems=50`, o mesmo padrão
  que a Experiência 3 tinha observado com `maxItems=20` dentro de
  `siteSearch=record.pt`: aumentar `maxItems` não aproximou a página de
  vir cheia.
- **Repetição 1 e repetição 2 foram byte a byte idênticas para todos os 13
  termos** (verificado por comparação direta do raw de 6 termos
  escolhidos ao acaso, incluindo os de maior e menor volume; os restantes
  têm a mesma contagem exata rep1/rep2 na tabela acima). Isto contrasta
  com a Experiência 3, onde pedidos idênticos e consecutivos devolveram
  contagens diferentes (`Sporting`: 3, 5, 7). Não foi identificada a causa
  desta diferença de comportamento entre as duas execuções — possíveis
  fatores não isolados incluem `maxItems` (50 aqui vs. 20 na Experiência 3),
  `dedupField`/`dedupValue` explícitos (aqui `url`/`1` vs. omitidos na
  Experiência 3) ou simplesmente variação temporal do lado da API. Fica
  como questão em aberto, não resolvida por esta execução.
- **A única causa de divergência de metadados observada foi o campo
  `snippet`.** Nas 20 capturas divergentes, todos os outros campos
  (`digest`, `title`, `contentLength`, `tstamp`, etc.) foram idênticos
  entre queries; só o excerto destacado (`snippet`, com `<em>` à volta do
  termo pesquisado) variou conforme a query. Isto é o comportamento
  esperado de um campo de pesquisa (o excerto reflete a query, não o
  documento), não uma inconsistência de metadados como a observada no M3
  entre `TextSearch` e `versionHistory` (que envolvia `digest`,
  `contentLength` e `title`, não apenas o snippet). As duas situações não
  devem ser tratadas como o mesmo fenómeno.
- **A maioria das capturas encontradas por várias queries parece dever-se a
  conteúdo repetido em todas as páginas do site (menu de navegação com os
  nomes das modalidades), não a relevância temática real.** Ex.:
  "andebol;basquetebol;voleibol" aparecem juntas em 6 das 20 capturas
  multi-query, porque estes três nomes de modalidade surgem lado a lado no
  menu de navegação do Record em qualquer página. Duas páginas de perfil de
  jogador ("YEBDA - Saber Mais", "ze pedro - Saber Mais") também foram
  devolvidas por `andebol;basquetebol;voleibol`, sem relação de conteúdo
  aparente com essas modalidades. Isto sugere que a pesquisa da API
  considera o HTML completo da página (incluindo menus e blocos fixos), não
  só o corpo do artigo — relevante para interpretar `N` como "artigos
  únicos descobertos", não como "artigos relevantes para a query que os
  encontrou", e para a regra de classificação Artigo/redirecionamento (as
  páginas "Saber Mais" não são artigos).

#### Interpretação

- `N = 159` é o valor real confirmado nesta execução, não uma estimativa.
  Fica muito abaixo do teto teórico de 1300 pedidos da Fase 2, como a
  Experiência 3 sugeria.
- A ausência de páginas cheias reforça a decisão já tomada de não desenhar
  a Fase 1 à volta de `offset`: com esta configuração, a paginação nunca foi
  necessária.
- A estabilidade rep1/rep2 (idênticas) nesta execução, depois da
  instabilidade observada na Experiência 3, não permite concluir que a API
  se tornou determinística — apenas que, nesta janela de observação e com
  estes parâmetros, os pedidos repetidos coincidiram. Não deve ser assumido
  como garantia para execuções futuras.
- A sobreposição por conteúdo de navegação (não temático) significa que os
  159 artigos não devem ser lidos como "159 artigos sobre as respetivas
  queries"; são 159 páginas distintas devolvidas por pelo menos uma das 13
  queries, algumas por relevância de conteúdo, outras por texto de menu
  partilhado. A classificação Artigo/redirecionamento (pendente) vai
  precisar de lidar com isto, incluindo páginas de perfil ("Saber Mais").

**N confirmado: 159. A implementação e a agregação (passos 2–4) estão
concluídas. Conforme pedido, a execução PARA aqui — a Fase 2
(`version_history`) só avança com confirmação explícita do autor sobre
este valor de `N`.**

### Correção de bug em collect_all_captures() antes da Fase 2 (2026-09-18)

**Problema identificado pelo autor:** `collect_all_captures()`, em
`history_pipeline.py` (a função que a Fase 2 reutiliza tal e qual para
percorrer o `version_history` de cada artigo), tinha uma condição de
paragem da paginação que contradizia a decisão já registada na Experiência
1 — "não usar `estimated_nr_results` como contagem fiável, dado que é
instável e não representa o número real de resultados acessíveis":

```python
if estimated_total is not None and len(captures) >= estimated_total:
    break
```

Este código foi escrito no M3, antes da Experiência 1 caracterizar a
instabilidade de `estimated_nr_results`. Com um único artigo (M3), passou
despercebido. À escala de 159 artigos na Fase 2, se a estimativa da API
fosse demasiado baixa para algum artigo, a recolha desse artigo pararia
silenciosamente antes de esgotar as páginas reais, sem qualquer aviso —
enfraquecendo de forma invisível a profundidade temporal, que é metade do
objetivo do Caminho A.

**Verificação de testes existentes:** nenhum teste em
`tests/test_history_pipeline.py` dependia especificamente desta condição
para parar a paginação. `test_version_history_pagination` usa duas páginas
em que `next_page=None` já ocorre exatamente na mesma página em que a
condição do `estimated_total` também dispararia, pelo que o resultado do
teste (2 pedidos, 2 capturas) não muda com a remoção. Confirmado correndo a
suite antes e depois da alteração, sem diferenças.

**Correção aplicada:** removida a condição `len(captures) >=
estimated_total` de `collect_all_captures()`. `estimated_total` continua a
ser recolhido e devolvido (para reportar na dissertação), mas deixa de
decidir quando parar; só as duas condições já validadas nas Experiências 2
e 3 param a paginação — página incompleta (`len(page.results) <
page_size`) ou ausência de `next_page`.

**Teste de regressão acrescentado:**
`test_pagination_ignores_low_estimated_total` (novo, em
`tests/test_history_pipeline.py`) simula três páginas com
`estimated_nr_results=1` em todas (uma estimativa deliberadamente baixa),
mas com `next_page` presente nas duas primeiras e capturas reais nas três.
Confirma-se que a paginação continua até à terceira página (3 capturas, 3
pedidos com offsets `[0, 1, 2]`) e não para na primeira, como pararia com o
código antigo. Verificado que este teste falha (`1 != 3`, com respostas por
consumir) contra o código anterior à correção e passa depois dela.

**Suite completa:** `.venv/Scripts/python.exe -m unittest discover -s
tests -v` — **24 testes** (23 anteriores + 1 novo), todos passaram (`OK`),
sem chamadas à API real.

Esta correção precede e é pré-requisito da Fase 2: sem ela, os 159 artigos
da Fase 2 arriscavam profundidade temporal subestimada de forma
silenciosa, para artigos onde a estimativa da API fosse baixa.

### Resultados da Fase 2 (execução real, 2026-09-18)

Execução real de `src/semantic_harvester/corpus_phase2.py` sobre os 159
`originalURL` únicos da Fase 1, autorizada pelo autor depois da confirmação
de `N = 159` e da correção do passo 4b. Raw preservado byte a byte em
`data/raw/version_history/` (convenção já usada pelo M3); resultados em
`output/corpus_phase2_history.csv` (uma linha por artigo) e
`output/corpus_phase2_summary.md`.

#### Resumo

- Artigos processados: **159/159**, sem falhas.
- Pedidos reais efetuados (todos os artigos, incluindo paginação): **287**.
- Duração total: **109 segundos** — muito mais rápido do que a Fase 1
  (26 pedidos, ~15–20 minutos), porque `version_history` consulta um URL
  exato em vez de pesquisa de texto livre; a lentidão das fases anteriores
  não se generaliza a este tipo de pedido.
- Total de capturas encontradas: **7 572**.
- Artigos com mais do que uma captura: **125 de 159 (78,6%)** — profundidade
  temporal real na maioria da amostra, não só no caso isolado do M3.

#### Distribuição de capturas por artigo

| Capturas por artigo | Nº de artigos | % |
| --- | ---: | ---: |
| 1 | 34 | 21,4% |
| 2–5 | 75 | 47,2% |
| 6–10 | 15 | 9,4% |
| 11–20 | 11 | 6,9% |
| 21–50 | 8 | 5,0% |
| 51–100 | 3 | 1,9% |
| 101–500 | 8 | 5,0% |
| 501+ | 5 | 3,1% |

Distribuição completa (uma linha por contagem exata) em
`output/corpus_phase2_summary.md`.

#### Observações

- **Os 13 artigos com mais de 100 capturas (101–500 e 501+) não parecem ser
  artigos noticiosos.** Inspeção direta dos títulos confirma um padrão: são
  páginas persistentes do site, não notícias pontuais — 6 páginas
  `/sabermais/<nome>` ("Saber Mais: Futebol" com 1282 capturas, "Saber
  Mais: Sporting" com 1084, "Saber Mais: Cristiano Ronaldo" com 306, "Saber
  Mais: João Félix" com 119, "Saber Mais: Porto" com 118, "Saber Mais:
  Bruno Fernandes" com 143) e 3 páginas de secção/hub sem `/detalhe/`
  ("Benfica - Jornal Record" com 916, "Basquetebol - Jornal Record" com
  829, "Voleibol - Jornal Record", listagem de resultados, com 822). As
  restantes 4 são sub-páginas multimédia com `/detalhe/` na URL mas
  conteúdo não textual (fotogaleria com 472 capturas, vídeos com 162, 162 e
  135 capturas) — o padrão `/detalhe/` já identificado no profiling
  exploratório (`output/api_profiling.md`) como "apenas um indicador", não
  uma garantia, confirma-se aqui: nem toda a URL com `/detalhe/` é um
  artigo de texto.
- Estes 13 URLs são re-arquivados ordens de magnitude mais vezes do que um
  artigo isolado (M3: 3 capturas; mediana desta amostra: muito menor do que
  100), provavelmente por serem páginas persistentes/atualizadas em vez de
  publicações pontuais — hipótese consistente com os dados, não confirmada
  por inspeção do conteúdo real de cada captura.
- Entre os dois URLs devolvidos com esquemas diferentes (`http://` vs.
  `https://`) para a mesma página (`.../yuri-ribeiro-apresenta-se-aos-
  adeptos-do-rio-ave.html`), ambos têm exatamente 162 capturas — o esquema
  do URL não impediu a paginação, mas confirma que `originalURL` distingue
  `http://` de `https://` como artigos diferentes, duplicando esta página
  no corpus agregado. Só este par foi encontrado nos 159 artigos; não é
  generalizado como problema sistemático desta amostra.
- Nenhuma falha em 159 artigos e 287 pedidos — mais estável do que as
  Experiências 1–3, mas sobre uma pesquisa por URL exato, não por texto
  livre; não deve ser lido como evidência de estabilidade geral da API.

#### Interpretação

- A hipótese central do Caminho A (profundidade temporal como resultado
  real do corpus, não só do artigo único do M3) fica sustentada por esta
  execução: 78,6% dos 159 artigos têm mais do que uma captura, com uma
  cauda longa de páginas muito republicadas.
- Ao mesmo tempo, a cauda longa é um problema de qualidade concreto para a
  classificação Artigo/redirecionamento (passo 6, ainda pendente): sem
  filtrar as páginas `/sabermais/` e de secção, a "profundidade temporal"
  do corpus ficaria inflacionada por 13 URLs que não são artigos,
  totalizando sozinhos milhares das 7 572 capturas. Esta classificação
  precisa de lidar explicitamente com este padrão, não só com o critério
  genérico já previsto.
- A correção do passo 4b (não usar `estimated_nr_results` para parar a
  paginação) foi confirmada como necessária na prática: vários destes
  artigos têm centenas de capturas, exigindo várias páginas reais de
  `version_history` — exatamente o cenário em que uma estimativa baixa e
  não fiável poderia ter cortado a recolha prematuramente.

**Fase 2 concluída. N = 159 artigos processados, 0 falhas, 7 572 capturas,
125 artigos com profundidade temporal (>1 captura). O corpus bruto
(descoberta + histórico) está pronto para a classificação
Artigo/redirecionamento (passo 6), que ainda não foi implementada.**

### Próximos passos

1. ~~Validar com o autor e o Jorge a opção de dimensionamento, a lista de
   termos correspondente e o intervalo temporal.~~ **Concluído em
   2026-09-17: Opção 2.**
2. ~~Implementar e correr a recolha da Fase 1 (TextSearch).~~ **Concluído em
   2026-09-17: 26 pedidos, ver "Resultados da Fase 1" acima.**
3. ~~Implementar a agregação/deduplicação.~~ **Concluído em 2026-09-17:
   `output/corpus_phase1_captures.csv`.**
4. ~~Ponto de verificação: confirmar o valor real de `N`.~~ **Concluído em
   2026-09-17: N = 159. Aguarda confirmação explícita do autor antes do
   passo 5.**
4b. ~~Corrigir a condição de paragem por `estimated_nr_results` em
   `collect_all_captures()` antes de a reutilizar à escala da Fase 2.~~
   **Concluído em 2026-09-18: ver secção anterior.**
5. ~~Implementar e correr a Fase 2 (`version_history` por artigo único).~~
   **Concluído em 2026-09-18: 159/159 artigos, 0 falhas, 7 572 capturas —
   ver "Resultados da Fase 2" acima.**
6. ~~Aplicar a regra de classificação Artigo/redirecionamento.~~
   **Concluído em 2026-09-18 — ver secção seguinte.**

## Classificação Artigo vs. redirecionamento/não-artigo (passo 6)

### Objetivo

Decidir, para os 159 artigos únicos das Fases 1–2, quais ficam classificados
como `Artigo` (candidatos ao resto do Caminho A: download de texto,
mapeamento RDF) e quais são excluídos por serem páginas de
referência/secção/redirecionamento, não publicações editoriais. A regra
deve usar apenas sinais já documentados nas Fases 1–2, não critérios novos
sem justificação nos dados reais.

### Evidência disponível, recapitulada

- **Padrão de URL `/detalhe/` sozinho não chega** (Experiência de profiling,
  `output/api_profiling.md`, e confirmado de novo abaixo).
- **13 artigos com mais de 100 capturas** (`output/corpus_phase2_history.csv`),
  todos confirmados por título como páginas `/sabermais/<nome>` (6) ou de
  secção/hub sem `/detalhe/` (3) ou sub-páginas multimédia com `/detalhe/`
  mas conteúdo não editorial (4) — ver "Resultados da Fase 2" acima.
- **Conteúdo de menu de navegação partilhado** (Fase 1): algumas capturas
  foram devolvidas por várias queries de modalidade em simultâneo
  (`andebol;basquetebol;voleibol` e semelhantes).

### Sinal investigado e descartado: sobreposição de queries de modalidade

Antes de propor a regra final, testou-se se "devolvido por ≥3 queries de
modalidade distintas" (o sinal de menu de navegação da Fase 1) seria um
bom critério de exclusão. Cruzando esse sinal com o número de capturas da
Fase 2:

| Título | Queries de modalidade | Capturas |
| --- | ---: | ---: |
| YEBDA - Saber Mais - Record | 3 | 3 |
| ze pedro - Saber Mais - Record | 3 | 1 |
| Zainadine cortou mal a bola... | 3 | 135 |
| Zungu aproveitou distração... | 3 | 73 |
| Zagreb foi 'abaixo'... | 3 | 31 |
| **Danny deixa Zenit: «Respeito a decisão...»** | **4** | **3** |
| **Pep Guardiola: «Eu e o Zidane...»** | **4** | **2** |
| **Alaphilippe vence segunda etapa...** | **4** | **2** |

As duas últimas linhas (destacadas) têm `snippet` de menu de navegação
(confirmado na Fase 1), mas título, `/detalhe/` e conteúdo consistentes com
artigos noticiosos reais — "Danny deixa Zenit" é uma notícia de
transferência, "Alaphilippe vence..." é uma notícia de ciclismo (e tem duas
capturas distintas na própria Fase 1, sinal de artigo genuíno republicado).
**Este sinal produz falsos positivos em artigos reais e foi descartado como
critério de classificação.** A observação da Fase 1 sobre conteúdo de menu
partilhado mantém-se válida como descrição do comportamento da API, mas não
se traduz numa regra de exclusão fiável.

### Achado adicional durante a análise: páginas "Object moved"

Ao preparar a regra, encontraram-se **13 artigos com o título exato
`Object moved`**, todos em URLs do padrão antigo
`record.pt/<secção>/interior.aspx?content_id=...`. Este título é o próprio
texto de uma página de redirecionamento HTTP arquivada, não conteúdo
editorial — o sinal mais direto e inequívoco encontrado para
"redirecionamento" desde que a Experiência de profiling levantou a
distinção. Nenhum destes 13 se sobrepõe às páginas `/sabermais/` ou aos
outliers de capturas.

### Normalização http/https antes de classificar

A Fase 2 encontrou um par de URLs para a mesma página
(`.../yuri-ribeiro-apresenta-se-aos-adeptos-do-rio-ave.html`), um `http://`
e outro `https://`, com **conjuntos de `tstamp` idênticos** (162/162,
diferença simétrica zero — verificado por comparação direta do raw
preservado). Isto confirma que são a mesma página, não duas capturas
diferentes. **Decisão:** antes de classificar, agrupar `originalURL` que só
diferem no esquema (removendo `http://`/`https://` do início) e manter um
único identificador canónico, preferindo `https://` quando existir essa
variante (convenção atual do site; a escolha é arbitrária entre variantes
idênticas, dado que os dados confirmam serem a mesma página). Isto reduz os
159 artigos da Fase 1 para **158 recursos distintos**.

### Regra proposta

Depois da normalização de esquema, um recurso é classificado como `Artigo`
**apenas se nenhuma** das três condições seguintes se verificar (qualquer
uma delas classifica como não-artigo/redirecionamento):

1. `/sabermais/` está presente no caminho do URL → página de
   referência/perfil.
2. O `title` da captura mais recente é exatamente (ou começa por)
   `"Object moved"` → página de redirecionamento arquivada.
3. O número de capturas devolvido pela Fase 2 (`version_history`) é
   **superior a 100** → página persistente/reutilizada, não uma publicação
   editorial pontual. O limiar de 100 não é arbitrário: a distribuição real
   (`output/corpus_phase2_summary.md`) tem um intervalo vazio entre 74 e 117
   capturas — o artigo com mais capturas abaixo do limiar tem 73, o próximo
   valor observado é 118. Todos os 13 recursos acima desse intervalo vazio
   foram confirmados por título como não-artigos.

`/detalhe/` não faz parte da regra: está presente na maioria dos artigos
mantidos (115 de 127, ver abaixo), mas páginas AMP legítimas
(`.../amp/<slug>`) não o têm e são notícias reais (ex.: "Jorge Jesus assina
com Pini Zahavi", "Zinchenko elogia Bernardo Silva..."), confirmando de novo
que não é um critério fiável isoladamente.

### Resultados da aplicação (execução real sobre os dados já recolhidos)

- Recursos distintos depois da normalização de esquema: **158** (159 − 1
  par http/https fundido).
- Excluídos por `/sabermais/`: **12**.
- Excluídos por `Object moved`: **13**.
- Excluídos por capturas > 100 (não já contados acima): **6**.
- **Classificados como `Artigo`: 127 de 158 (80,4%)**.

Exemplos de cada categoria:

| Categoria | Exemplo | Capturas |
| --- | --- | ---: |
| Artigo (mantido) | "Carlos Xistra castigado por erro no golo do P. Ferreira frente ao Sporting" | 3 |
| Artigo (mantido, AMP, sem `/detalhe/`) | "Jorge Jesus assina com Pini Zahavi" | 2 |
| Excluído — `/sabermais/` | "Saber Mais: Cristiano Ronaldo" | 306 |
| Excluído — `Object moved` | `record.pt/Futebol/Nacional/1a_liga/Benfica/interior.aspx?content_id=930690` | 3 |
| Excluído — capturas>100 | "Benfica - Jornal Record" (página de secção) | 916 |

### Limitações conhecidas desta regra

- O limiar de 100 capturas foi calibrado no intervalo vazio observado nesta
  amostra de 158 recursos; não é validado noutra amostra ou escala maior.
- Pelo menos um caso conhecido não é capturado pela regra: "SC Braga x
  Vitória SC - Record Jogos em Direto" (`/jogos-em-direto/live/...`, 10
  capturas) é uma página de acompanhamento ao vivo, não uma notícia
  convencional, mas não aciona nenhuma das três condições. Não foi
  encontrada evidência suficiente (só este exemplo) para justificar uma
  quarta regra específica para `/jogos-em-direto/`; fica registado como
  falso negativo conhecido, não resolvido.
- A regra não distingue sub-páginas multimédia (`fotogalerias/`, `videos/`)
  de artigos de texto dentro do conjunto mantido como `Artigo`, exceto
  quando essas sub-páginas também excedem o limiar de capturas — algumas
  podem ter poucas capturas e continuar classificadas como `Artigo` sem
  serem texto editorial. Não investigado nesta iteração.
- Não usa `estimated_nr_results` nem qualquer sinal já rejeitado noutras
  experiências.

## Mapeamento RDF do corpus (passo final do Caminho A)

### Objetivo e método

Mapear os 127 artigos classificados como `Artigo` (passo 6) para um único
grafo RDF, com as suas capturas históricas e textos extraídos, sem repetir
pedidos de `version_history`: as capturas de cada artigo foram
reconstruídas a partir do raw já preservado pela Fase 2
(`data/raw/version_history/`) e só o download dos textos extraídos
(`build_manifest_records()`, que reutiliza texto já existente em
`data/raw/texts/`) fez pedidos novos à API. Implementação em
`src/semantic_harvester/corpus_rdf.py`; o mapeamento por artigo reutiliza
`build_article_history_graph()` (`rdf_mapper.py`) sem alterações.

A descarga foi concluída pelo autor no seu terminal, fora do Claude Code,
depois de várias sessões dentro do Claude Code terem sido interrompidas
pela proteção de memória do sistema (não por erro do código). Os números
abaixo foram verificados a partir dos ficheiros produzidos, não observados
em direto.

### Resultados iniciais (verificados; anteriores à retentativa dos textos)

**Estes números (540 textos disponíveis, 401 indisponíveis, 12 735 triplos) são
anteriores à retentativa e à reconstrução do grafo; os números finais estão em
"Resultados da retentativa e reconstrução do grafo", no fim deste
documento.**

Conferidos por soma direta de `output/corpus_rdf_report.csv` e por releitura
de `output/corpus_articles.ttl` com RDFLib:

- Artigos mapeados com sucesso: **127 de 127**, 0 falhas.
- Capturas no grafo: **941** (igual à soma das capturas dos 127 artigos em
  `output/corpus_classification.csv`).
- Textos extraídos disponíveis: **540 de 941 (57,4%)**; indisponíveis: **401
  (42,6%)**. 32 artigos não têm nenhum texto disponível e 30 têm todos.
- Triplos no grafo final: **12 735**. Instâncias: 127 `Artigo`, 1 `Jornal`,
  127 `RecursoWeb`, 941 `CapturaArquivada`, 540 `TextoExtraido`.
- Capturas com `originalURL` normalizado (variante de esquema/barras):
  **189, em 32 artigos** (os mesmos 32 identificados antes da correção);
  descartadas por não serem variante cosmética: 0.

Saídas: `output/corpus_articles.ttl` (grafo final),
`output/corpus_rdf_report.csv` (uma linha por artigo),
`output/corpus_rdf_summary.md`. Não foram alterados
`output/sample_capture.ttl` nem `output/article_history.ttl` (M2/M3).

### Ressalvas sobre estes números

- A divisão "descarregados" (281) vs "reutilizados" (259) depende das
  sessões: um texto obtido numa sessão interrompida conta como reutilizado
  na sessão seguinte. Só a soma (540 disponíveis) é significativa.
- **Causa real dos 401 textos indisponíveis** (análise posterior, 2026-09-19,
  sem pedidos novos à API). O relatório não guarda o erro de cada texto; a
  distinção foi reconstruída a partir das linhas `WARNING: Falha ao obter ...`
  de `output/corpus_rdf_progress.log` (não versionado), que acumula todas as
  sessões (Claude Code interrompido + terminal do autor). Método: analisar o
  parâmetro `m` de cada URL `textextracted` do log para obter `(originalURL,
  tstamp)`, normalizar o URL com `normalize_for_grouping()` e cruzar com as
  capturas do grafo sem `TextoExtraido`; a categoria vem da mensagem de erro.
  A análise foi feita com um script ad hoc, **não versionado** (este passo não
  alterou código); pode ser versionado se for útil.

  Reconciliação: das 555 linhas de falha no log, todas foram analisadas (0
  não analisáveis, 0 com formato de URL diferente), correspondendo a 441
  capturas distintas = **401 sem texto no grafo final + 40 que falharam pelo
  menos uma vez e acabaram por ter texto**. Cada uma das 401 tem pelo menos
  uma linha no log, pelo que os números reconciliam **exatamente**. A
  categoria de cada uma das 401 é a do **último** erro registado:

  | Causa (última tentativa registada) | Capturas | % das 401 |
  | --- | ---: | ---: |
  | Timeout de leitura (`Read timed out`) | 318 | 79,3% |
  | HTTP 404 | 77 | 19,2% |
  | Ligação cortada (`RemoteDisconnected`/`Connection aborted`) | 5 | 1,2% |
  | Timeout de ligação (`ConnectTimeoutError`) | 1 | 0,2% |
  | Outros | 0 | 0% |

  Ressalvas desta reconstrução: (a) as linhas de sucesso não são registadas;
  a "recuperação" das 40 é inferida por a captura constar do grafo final;
  (b) o log não distingue sessões nem guarda o resultado final por captura,
  pelo que "última tentativa registada" assume que é a definitiva; (c) 343
  das 401 tiveram uma única tentativa, 27 duas, 16 três, 11 quatro e 4 cinco
  (as repetições vêm de artigos reprocessados após interrupções, não de uma
  política de retentativa); 24 das 401 tiveram tentativas de mais do que uma
  categoria; (d) nas mensagens de timeout de leitura o limite reportado é 30 s
  em 370 linhas, 10 s em 14 e 15 s em 2 (o valor de 15 s é compatível com a sessão
  anterior à correção do timeout, mas não foi verificado linha a linha).

  Cruzamento com o `statusCode` do raw de `version_history`: as 540 capturas
  com texto têm todas `statusCode` 200; das 401 sem texto, 366 têm 200, 32
  têm 302, 2 têm 404 e 1 tem 301. Ou seja, **nenhuma das 35 capturas com
  `statusCode` diferente de 200 tem texto**, o que é coerente com serem
  respostas sem conteúdo de artigo. Dos 77 erros 404, 54 são de capturas com
  `statusCode` 200, 22 de capturas 302 e 1 de uma 301.

  Interpretação, com limites: o 404 (19,2%) é o único sinal claramente
  compatível com ausência real do texto. **Os timeouts e ligações cortadas
  (324 capturas, 80,8% das 401) não são evidência de ausência**, apenas de
  que o pedido não foi concluído numa única tentativa. Se todos fossem
  transitórios, a disponibilidade poderia subir dos 57,4% atuais para um
  teto teórico de 864/941 (91,8%); é um teto, não uma previsão. Há alguma
  evidência de que retentar ajuda: das 361 capturas cuja última falha
  registada foi timeout ou ligação cortada, 37 (10,2%) foram depois obtidas
  (31 após timeout de leitura, 5 após ligação cortada, 1 após timeout de
  ligação; mais 3 após 404). Este valor **não é uma taxa de recuperação**:
  só foram retentadas as capturas cujo artigo foi reprocessado após uma
  interrupção, por isso é um limite inferior enviesado. Não foi feita nenhuma
  nova tentativa; fazê-la exigiria pedidos novos à API.
- Existem 5 ficheiros em `data/raw/texts/` não referenciados pelo grafo
  (545 no disco vs 540 no grafo). Um dos três prefixos de hash foi
  confirmado como o URL `https://` de um artigo com variantes (descarregado
  antes da correção de `originalURL`, quando o nome do ficheiro ainda usava a
  variante); os outros dois são consistentes com a mesma origem mas não
  foram resolvidos individualmente. São inofensivos (não referenciados) e
  não estão versionados.

### Bugs encontrados durante a execução e correções

1. **`originalURL` heterogéneo dentro do `version_history` de um artigo**
   (commit `db55d8c`). O `version_history` de um URL devolve capturas cujo
   próprio `originalURL` difere em esquema (`http`/`https`), barras
   duplicadas ou barra final. `build_article_history_graph()` exige um único
   `original_url` e rejeitava o manifesto. Afeta 32 de 127 artigos (25%). Nos
   casos inspecionados os `tstamp` das variantes são distintos e
   intercalados com os do URL canónico (não duplicados), pelo que descartá-las
   subestimaria a profundidade temporal. Correção: reatribuir o `originalURL`
   canónico às variantes que só diferem em esquema/barras
   (`normalize_for_grouping()`), descartando e contando as que nem isso são
   (0 nesta execução). Verificado que a normalização agrupa todas as variantes
   dos 127 artigos.
2. **Timeout excessivo nos downloads de texto** (commit `0f8b8c6`). O cliente
   usava `timeout=(15, 120)`, copiado das Fases 1–2 sem justificação; houve
   intervalos de até 519 s entre entradas do log. Passou a usar o padrão do
   `ArquivoClient` (10 s/30 s). Não se mediu o ganho de forma controlada.
3. **Execução sem memória entre sessões** (commit `5035bd0`). Cada retoma
   recomeçava no artigo 1 e repetia as tentativas de rede já falhadas, pelo
   que ficava presa por volta do artigo 20 antes de cada corte. A execução
   passou a ser retomável por artigo (relatório CSV incremental e triplos em
   N-Triples apendáveis, `data/processed/corpus_articles_triples.nt`, não
   versionado). Teste de regressão que prova que uma segunda chamada não faz
   pedidos para artigos já concluídos.

### Observações não quantificadas

- Num artigo inspecionado, o `title` devolvido por `version_history` era o
  próprio URL e havia capturas com `statusCode` 302; noutro, capturas de 2022
  e 2023, fora da janela 2015–2020 da Fase 1 (esperado, pois `version_history`
  não restringe datas). Não foi medida a frequência destes fenómenos no
  corpus. O rótulo `rdfs:label` de cada `Artigo` vem do título da Fase 1
  (TextSearch); o `sdh:title` de cada captura vem de `version_history`, como no
  M3.
- As capturas com `statusCode` 302 ou sem texto ficam no grafo como
  `CapturaArquivada` sem `TextoExtraido`; não foi aplicado nenhum filtro por
  captura (só a classificação ao nível do artigo).

### Limitações

- Amostra deliberada de 13 termos (Opção 2) sobre `record.pt` 2015–2020; o
  corpus não é representativo do jornal Record.
- Na versão anterior à retentativa, 42,6% das capturas não tinham texto; nos
  números finais são 16,2% (152 de 941), o que ainda limita a análise textual
  posterior (Caminhos D e B).
- A classificação Artigo tem falsos negativos conhecidos (ex.:
  `/jogos-em-direto/`) e não distingue conteúdo multimédia de texto.
- O `.ttl` referencia ficheiros em `data/raw/texts/` (540 na versão anterior à
  retentativa, 789 nos números finais) que não acompanham um clone (raw
  ignorado pelo Git).

### Estado do Caminho A

Concluídos: descoberta (Fase 1), profundidade temporal (Fase 2),
classificação Artigo/redirecionamento (passo 6) e mapeamento RDF. O Caminho D
(redução de redundância) não foi iniciado.

## Caminho D — redução de redundância entre capturas (implementado; limiar pendente de rotulagem manual)

**Estado em 2026-09-24: desenho validado pelo autor e implementado em
`src/semantic_harvester/corpus_redundancy.py`; executado sobre o corpus real
(ver "Implementação e resultado da execução" no fim desta secção). O limiar
da Camada 1 continua por fixar, pendente de rotulagem manual.** O texto abaixo
até "Atualização com os textos finais" é a proposta tal como foi escrita,
mantida como registo; na altura: *nada foi implementado e não foram feitos
pedidos à API.* As estatísticas abaixo foram
calculadas sobre dados já recolhidos (`output/corpus_articles.ttl`, raw de
`version_history`, textos em `data/raw/texts/`) com scripts ad hoc não
versionados; são exploratórias, não uma calibração.

### Decisões já tomadas (PROJECT_STATUS.md)

Heurística de **similaridade textual simples**, aplicada ao corpus produzido
no Caminho A; não `digest` isolado, não embeddings (esses ficam como trabalho
futuro). Esta proposta não reabre essa decisão; decide como a aplicar e o que
fazer com as capturas sem texto.

### Evidência disponível

**Estrutura do corpus** (127 artigos, 941 capturas):

| Situação | Artigos |
| --- | ---: |
| Só 1 captura (nada a comparar) | 31 |
| Nenhuma captura com texto | 32 |
| Exatamente 1 captura com texto | 37 |
| 2 ou mais capturas com texto | 58 |

Só os 58 artigos com 2+ textos têm pares comparáveis: **445 pares
temporalmente consecutivos** (6 013 pares se comparados todos contra todos).
Dos 127, 69 (32 sem texto + 37 com um só) não têm nada que possa ser
comparado por texto.

**Capturas sem texto: 401 (42,6%)** — 340 em artigos que têm pelo menos um
texto e 61 nos 32 artigos sem nenhum. Nenhuma das 35 capturas com
`statusCode` diferente de 200 tem texto.

**O `digest` como sinal.** Dentro do mesmo artigo há 21 grupos de capturas
com `digest` igual, correspondendo a 44 capturas "redundantes por digest" (n−1
por grupo): 14 grupos só de capturas sem texto (34 capturas), 3 grupos só com
texto (4 capturas) e 4 grupos mistos (6 capturas). Testado contra os textos
reais: dos 3 grupos de `digest` igual com 2+ textos, os 3 tinham texto
idêntico (amostra demasiado pequena para concluir precisão); por outro lado,
dos 16 grupos de textos **byte a byte idênticos** dentro de um artigo, **13
(81%) tinham mais do que um `digest` distinto**. Ou seja, o `digest` parece ter
precisão alta mas cobertura baixa: deixaria escapar a maior parte das
duplicações reais, o que sustenta a decisão de usar texto. Ressalva
adicional: no M3 o `digest` da mesma captura diferiu entre TextSearch e
`versionHistory` (`observations.md`), pelo que a sua fiabilidade não está
estabelecida.

**O texto extraído inclui o "chrome" do site** (menus, login, secções), como
mostra o início de um texto real: "... - Judo - Jornal Record Menu Record
Login/Registo TV Assinar E-Paper Notificações ...". Os 540 textos têm entre
2 165 e 15 191 bytes (mediana 8 658), nenhum vazio. Medição exploratória de
similaridade (Jaccard sobre conjuntos de palavras do texto completo, sem
remover o chrome):

| Amostra | n | mín. | p10 | mediana | p90 | máx. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Artigos diferentes (pares aleatórios, semente 0) | 384 | 0,109 | 0,224 | 0,336 | 0,405 | 0,521 |
| Mesmo artigo, capturas consecutivas | 445 | 0,434 | 0,551 | 0,641 | 0,812 | 1,000 |

Dos 445 pares consecutivos, 53 têm similaridade ≥ 0,80, 29 ≥ 0,90, 25 ≥ 0,99
e 22 são exatamente 1,0. Duas consequências: (1) existe um "piso" de
similaridade de cerca de 0,34 entre artigos sem relação, devido ao chrome,
pelo que um limiar tem de ficar bem acima dele; (2) como o chrome também varia
no tempo, a maioria das capturas consecutivas do mesmo artigo (mediana 0,64)
**não** parece quase-duplicada por texto completo — o rendimento esperado com
esta medição simples é baixo (cerca de 6,5% dos pares consecutivos com texto
≥ 0,90). Isto pode mudar se o chrome for removido.

### Proposta de desenho

**1. Não destrutivo.** A redução não apaga capturas do grafo nem do raw. Uma
captura redundante continua a atestar que o texto estava inalterado naquele
momento, e a caracterização temporal é metade do objetivo da dissertação;
apagá-la perderia essa evidência. O resultado de D é uma **anotação** de cada
captura (representante ou redundante, com o representante e a similaridade) e
uma métrica derivada: nº de **versões textuais distintas** por artigo,
comparado com o nº de capturas.

**2. Primeira iteração fora da ontologia.** A anotação sai para
`output/corpus_redundancy.csv` (uma linha por captura) e um resumo em
Markdown. Não se altera `ontology/semantic_harvester.ttl` nesta iteração:
representar isto em RDF exigiria novas propriedades (por exemplo, uma relação
captura → captura representante e um valor de similaridade), o que é uma
mudança de ontologia a explicar e validar antes (AGENTS.md). Fica como
decisão posterior.

**3. Pré-processamento do texto.** Normalizar (Unicode, minúsculas, espaços).
Para o chrome, duas variantes a comparar na calibração: (a) nenhuma remoção
(referência); (b) remover unidades (n-gramas de palavras) presentes numa
fração alta das capturas **de artigos diferentes** — critério derivado do
corpus, sem regras manuais por site. A fração de corte não é fixada agora.

**4. Medida.** Jaccard sobre palavras ou n-gramas de palavras (a medida já
usada na exploração acima, por continuidade). A escolha entre conjuntos de
palavras e n-gramas fica para a calibração; igualdade exata do texto
normalizado é o nível trivial.

**5. Estratégia de comparação.** Por artigo, em ordem temporal, cada captura
com texto é comparada com o **último representante retido**, não só com a
anterior, para evitar que uma cadeia de pequenas alterações funda versões
muito diferentes entre si (A≈B, B≈C, mas A≉C). O custo não é a razão (6 013
pares são triviais); é semântica. A variante "comparar com a captura
consecutiva" é calculada em paralelo como análise de sensibilidade.

**6. Limiar por calibração, não por decreto.** Não se propõe um valor. Passos:
(i) recalcular a distribuição de similaridades com a variante de
pré-processamento escolhida; (ii) os autores rotulam manualmente uma amostra de
pares em cada faixa ("mesma versão" / "texto alterado"); (iii) fixar o limiar
onde os rótulos se separam e publicar a tabela de sensibilidade (nº de
redundantes por limiar). Na medição exploratória há 25 pares ≥ 0,99, apenas 4
entre 0,90 e 0,99 e 24 entre 0,80 e 0,90, o que sugere uma separação nítida no
topo, mas não dispensa a rotulagem.

### Capturas sem texto — decisão proposta

Não podem ser comparadas por similaridade textual. Alternativas consideradas:

- **A. Manter todas, sem qualquer redução (recomendada como resultado
  principal).** É a opção mais segura. Custo: as 401 capturas (42,6%) não
  contribuem para nenhuma redução, e o resultado de D aplica-se só às 540 com
  texto.
- **B. Critério mais fraco (mesmo `digest` e mesmo `contentLength` dentro do
  artigo) para as sem texto.** Rejeitada como critério de redução, pelas
  razões: reintroduziria o `digest` isolado exatamente onde não o podemos
  verificar contra texto; a sua fiabilidade não está estabelecida (M3); o
  ganho máximo é pequeno — 44 capturas (4,7% de 941) por digest, das quais só
  34 estão em grupos totalmente sem texto e 6 em grupos mistos.
- **Solução proposta (A com anotação, em camadas separadas):**
  - **Camada 1 (texto):** pares em que ambas têm texto → similaridade. É o
    único resultado que se apresenta como redução de redundância.
  - **Camada 2 (sem texto):** todas mantidas. Em paralelo, **anotam-se, sem
    remover**, os grupos de capturas sem texto do mesmo artigo com `digest` e
    `contentLength` iguais como "candidatas a redundância por digest, não
    verificadas por texto". Reportam-se à parte (nunca somadas ao resultado da
    Camada 1) como limite superior do que um critério fraco deduziria (34
    capturas em 14 grupos só sem texto; 6 em 4 grupos mistos, onde a captura
    sem texto tem o mesmo `digest` de uma com texto). Estas contagens são
    por `digest` apenas; exigir também `contentLength` igual não foi medido e
    só pode reduzi-las.
  - **Artigos sem nenhum texto (32 artigos, 61 capturas):** declarados "não
    avaliáveis" no resumo, todas as capturas mantidas.
  - **Capturas com `statusCode` ≠ 200 (35, nenhuma com texto):** ficam na
    Camada 2. Não são um problema de redundância mas de conteúdo; são apenas
    contabilizadas à parte.

### Questão prévia: retentar os textos por timeout?

Antes de implementar D importa decidir se se retentam as **324 capturas** cuja
falha foi timeout ou ligação cortada (não 404). Se muitas forem recuperadas, D
passa a ter mais pares comparáveis e menos capturas na Camada 2 (teto
teórico 864/941 = 91,8% de disponibilidade, não uma previsão). Exige pedidos
novos à API (até 324) e uma alteração de código, porque a retoma atual é por
artigo e não por captura (o script de retentativa e a proposta de
integração no grafo estão descritos na secção "Retentativa dos textos por
timeout ou ligação cortada", no fim deste documento). Opções: **(i) retentar primeiro (recomendada, dado
que 80,8% das falhas não indicam ausência)**; **(ii) avançar com os 540
textos atuais** e documentar a limitação.

**Resolvida em 2026-09-20:** a retentativa foi feita (249 das 324 recuperadas) e
o grafo foi reconstruído com 789 textos; ver "Atualização com os textos finais"
abaixo e "Resultados da retentativa e reconstrução do grafo".

### Saídas e testes previstos

`output/corpus_redundancy.csv` (por captura: artigo, `tstamp`, tem texto,
camada, representante, similaridade, rótulo), resumo em Markdown com contagens
por camada e tabela de sensibilidade ao limiar. Testes unitários com
fixtures sintéticas: textos idênticos, quase idênticos, diferentes; cadeia de
alterações (A≈B, B≈C, A≉C); artigo com uma só captura; artigo sem texto;
captura sem texto entre duas com texto; grupo de `digest` igual sem texto
(anotado, não removido).

### Limitações

- Similaridade textual não prova equivalência semântica (AGENTS.md); "mesma
  versão" significa apenas "texto extraído suficientemente semelhante".
- O limiar é um julgamento dos autores, calibrado nesta amostra de 127
  artigos (13 termos, `record.pt`, 2015–2020), e não generaliza ao Record.
- A medição exploratória usa texto completo com chrome e uma medida simples;
  resultados finais dependem do pré-processamento escolhido.
- 69 dos 127 artigos não têm pares comparáveis por texto; a redução só pode
  ser afirmada para os 58 restantes.

### Decisões pedidas para validar

1. Camadas 1 e 2 como descritas (nenhuma redução sem texto; anotação por
   digest só como candidata)?
2. Anotação em CSV nesta iteração, ontologia depois?
3. Comparar com o último representante (com sensibilidade à consecutiva)?
4. Calibrar o limiar por rotulagem manual, com o filtro de chrome derivado do
   corpus?
5. ~~Retentar as 324 capturas antes de implementar D, ou avançar já com 540
   textos?~~ **Resolvida: retentativa feita, 789 textos.**

### Atualização com os textos finais (2026-09-20)

Os números acima foram calculados com 540 textos, antes da retentativa. Com
os 789 textos finais (mesmos métodos, scripts ad hoc não versionados;
medição exploratória com a mesma semente):

| Medida | 540 textos | 789 textos |
| --- | ---: | ---: |
| Artigos sem nenhum texto | 32 | 2 |
| Artigos com exatamente 1 texto | 37 | 41 |
| Artigos com 2+ textos (comparáveis) | 58 | **84** |
| Pares consecutivos com texto | 445 | **664** |
| Pares todos-contra-todos | 6 013 | 9 796 |
| Capturas sem texto | 401 (42,6%) | **152 (16,2%)** |
| — em artigos com algum texto | 340 | 150 |
| — em artigos sem nenhum texto | 61 | 2 |
| Grupos de `digest` igual (dentro do artigo) | 21 | 21 |
| Capturas redundantes por `digest` | 44 | 44 |
| — grupos só com texto | 3 grupos, 4 capt. | 9 grupos, 12 capt. |
| — grupos só sem texto | 14 grupos, 34 capt. | 3 grupos, 23 capt. |
| — grupos mistos | 4 grupos, 6 capt. | 9 grupos, 9 capt. |
| Grupos de textos byte a byte idênticos | 16 | 28 |
| — com mais de um `digest` distinto | 13 (81%) | **23 (82%)** |
| Grupos de `digest` igual com 2+ textos: texto idêntico | 3 de 3 | **9 de 9** |
| Tamanho dos textos (mín./mediana/máx., bytes) | 2 165 / 8 658 / 15 191 | 2 165 / 8 095 / 21 721 |

Similaridade exploratória (Jaccard de palavras, texto completo com chrome):

| Amostra | n | mín. | p10 | mediana | p90 | máx. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Artigos diferentes (pares aleatórios, semente 0) | 388 | 0,155 | 0,221 | 0,334 | 0,411 | 0,520 |
| Mesmo artigo, capturas consecutivas | 664 | 0,434 | 0,561 | 0,655 | 0,995 | 1,000 |

Dos 664 pares consecutivos: 129 têm similaridade ≥ 0,80, 81 ≥ 0,90 (12,2%), 70
≥ 0,99 e 64 são exatamente 1,0 (11 entre 0,90 e 0,99 e 48 entre 0,80 e 0,90).

Consequências para a proposta:

- O desenho não muda; o que muda é a dimensão. A Camada 1 (comparação por
  texto) passa a cobrir 84 artigos e 664 pares consecutivos em vez de 58 e
  445, e a Camada 2 (sem texto) encolhe de 401 para 152 capturas (16,2%): 150
  em artigos que têm algum texto e 2 em 2 artigos sem nenhum.
- O limite superior do que um critério fraco por `digest` deduziria nas
  capturas sem texto desce de 40 para 32 capturas (23 em 3 grupos sem texto e
  9 em 9 grupos mistos), 3,4% do corpus. Reforça a recomendação de não o usar
  como critério de redução.
- A evidência contra o `digest` como critério principal mantém-se: 23 dos 28
  grupos de textos byte a byte idênticos (82%) têm mais de um `digest`.
- O rendimento esperado com texto completo sobe (12,2% dos pares consecutivos
  ≥ 0,90, contra 6,5% antes), mas continua condicionado pelo chrome do site e
  o limiar continua a exigir calibração por rotulagem manual, não a ser
  fixado por estes números.
- A "questão prévia" (retentar as 324 capturas) está resolvida: ver "Resultados
  da retentativa e reconstrução do grafo". As 35 capturas com `statusCode` ≠
  200 continuam todas sem texto e ficam na Camada 2.

### Implementação e resultado da execução (2026-09-24)

**Decidido (pedido do autor, 2026-09-24):** as decisões 1–4 acima foram aceites tal
como propostas — camadas 1 e 2, anotação em CSV nesta iteração (ontologia
inalterada), comparação com o último representante com a consecutiva como
sensibilidade, limiar calibrado por rotulagem manual e não por decreto.

**Implementação** (`corpus_redundancy.py`; comando no README). Não faz
pedidos à API, não altera o grafo nem o raw: lê `output/corpus_articles.ttl`
e os textos referenciados por `sdh:filePath`.

- Camada 1: capturas com texto **e** `statusCode` 200. Por artigo, em ordem
  de `tstamp`, cada uma é comparada com o último representante retido;
  redundante se Jaccard ≥ limiar, senão passa a representante. A variante
  "só com a consecutiva" é calculada em paralelo (sensibilidade).
- Similaridade: Jaccard de conjuntos de palavras `\w+` do texto normalizado
  (Unicode NFC, minúsculas, espaços colapsados), texto completo com chrome.
  Esta tokenização foi escolhida por continuidade: reproduz exatamente a
  medição exploratória da "Atualização com os textos finais" (a separação por
  espaços dava valores ligeiramente diferentes, p. ex. mínimo 0,391 em vez de
  0,434).
- Camada 2: todas as capturas sem texto (ou com `statusCode` ≠ 200) mantidas.
  Grupos com `digest` **e** `contentLength` iguais no artigo são anotados
  (`grupo_digest`): num grupo só sem texto, a primeira fica
  `mantida_sem_texto` e as restantes `candidata_digest_nao_verificada`; num
  grupo misto, as sem texto ficam `candidata_digest_nao_verificada_grupo_misto`.
  Nunca somadas à Camada 1.
- Artigos sem nenhum texto: camada `nao_avaliavel`, todas mantidas.
- **Sem limiar fixado**, as capturas da Camada 1 que dependem dele ficam
  `pendente_limiar` no CSV (a primeira com texto de cada artigo é
  representante para qualquer limiar); `--limiar X` preenche
  `representante`/`similaridade`/`rotulo` depois da calibração. A coluna
  `sim_consecutiva` não depende do limiar e está preenchida.
- Não implementado nesta iteração: a variante (b) de remoção do chrome
  (ponto 3 do desenho). Só existe a variante (a), sem remoção; a decisão de
  a acrescentar fica associada à calibração.
- Amostra para rotulagem (`output/corpus_redundancy_label_sample.csv`): pares
  **consecutivos** com texto (não dependem do limiar), 20 por faixa — baixa
  [0; 0,70), média [0,70; 0,90), alta [0,90; 1] — semente 0, repartidos em
  rotação por sub-faixas de 0,05 com o 1,0 exato numa sub-faixa própria, para
  a faixa alta não ficar só com pares idênticos. As faixas servem para espalhar
  a amostra, não são limiares propostos. Para cada par: palavras só em A/só em
  B (até 25, por ordem de aparecimento) e colunas `rotulo_manual`/`notas`
  vazias.
- Testes: 19 unitários em `tests/test_corpus_redundancy.py` com fixtures
  sintéticas (idênticos, quase idênticos, diferentes; cadeia A≈B, B≈C, A≉C
  nas duas estratégias; artigo com 1 captura; artigo sem texto; captura sem
  texto entre duas com texto; grupo de `digest` igual sem texto anotado e não
  removido; grupo misto; `statusCode` ≠ 200 com texto; execução completa
  sobre um Turtle sintético sem alterar os ficheiros de entrada).

**Resultado real da execução** (2026-09-24, sem limiar;
`output/corpus_redundancy_summary.md`, `output/corpus_redundancy.csv`). Os
checksums SHA-256 de `output/corpus_articles.ttl` e de todos os ficheiros de
`data/raw/texts/` foram iguais antes e depois.

| Camada | Capturas |
| --- | ---: |
| 1 — com texto e `statusCode` 200 | 789 |
| 2 — sem texto, em artigos com algum texto | 150 |
| Não avaliáveis (2 artigos sem nenhum texto) | 2 |
| Total | 941 |

As 35 capturas com `statusCode` ≠ 200 não têm texto e estão todas fora da
Camada 1. Estrutura: 84 artigos comparáveis (2+ textos), 41 com exatamente 1
texto, 2 sem texto; 31 artigos têm uma só captura.

Distribuição dos 664 pares consecutivos com texto: mín. 0,434, p10 0,561,
mediana 0,655, p90 0,995, máx. 1,000 (igual à exploração). Histograma por
faixas de 0,05 no resumo; destaque: 5 pares em [0,90; 0,95), 12 em
[0,95; 1,0) e 64 iguais a 1,0, contra 7 em [0,85; 0,90) e 41 em [0,80; 0,85).

Sensibilidade (redundantes na Camada 1, de 789):

| Limiar | Último representante | Consecutiva | Divergências | Artigos com redundantes |
| ---: | ---: | ---: | ---: | ---: |
| 0,50 | 624 | 648 | 108 | 84 |
| 0,60 | 518 | 540 | 72 | 72 |
| 0,70 | 210 | 212 | 5 | 57 |
| 0,80 | 124 | 129 | 34 | 34 |
| 0,85 | 88 | 88 | 0 | 22 |
| 0,90 | 81 | 81 | 0 | 15 |
| 0,95 | 75 | 76 | 3 | 12 |
| 0,99 | 70 | 70 | 0 | 12 |
| 1,00 | 64 | 64 | 0 | 12 |

(Divergências = capturas com classificação ou representante diferente entre
as duas estratégias; a coluna "Artigos" refere-se à estratégia principal.)
Leitura descritiva, não uma escolha de limiar: entre 0,85 e 1,00 as duas
estratégias quase coincidem (0–3 divergências) e o número de redundantes varia
pouco (88 → 64); abaixo de 0,80 a contagem sobe depressa e entra na zona onde
está a maioria dos pares consecutivos (mediana 0,655), que a exploração
atribui em parte à variação do chrome. A fusão por cadeia que a estratégia
principal evita só aparece com peso abaixo de 0,85.

Camada 2 (anotação, não redução): **9 grupos só sem texto, 14 candidatas;
0 grupos mistos.** Diferença face à exploração (só por `digest`: 3 grupos/23
capturas sem texto e 9 grupos mistos/9 capturas, que este código reproduz
quando se ignora o `contentLength`): exigir `contentLength` igual divide os
grupos sem texto e elimina todos os mistos — nos 9 casos, a captura sem texto
tem um `contentLength` diferente de todas as capturas com texto com o mesmo
`digest`. É mais um indício de que `digest` igual não implica resposta
idêntica neste corpus.

**Pendente:** o limiar da Camada 1 **não foi fixado** e fica pendente da
rotulagem manual da amostra de 60 pares (20 por faixa) pelos autores. Só
depois se corre `--limiar X` e se reportam versões textuais distintas por
artigo como resultado de D; até lá, os números acima são uma tabela de
sensibilidade, não o resultado da redução. Representação em RDF continua
fora desta iteração (decisão 2).

## Retentativa dos textos por timeout ou ligação cortada (script e proposta de integração)

**Estado em 2026-09-20: script escrito e testado em 2026-09-19 e executado pelo
autor localmente, fora do Claude Code (cortes de memória): 249 recuperadas, 75
falhas definitivas. A alternativa 2 de integração foi implementada e aplicada;
ver "Resultados da retentativa e reconstrução do grafo".** Só depois disto se
avança para o Caminho D. Este passo responde à questão prévia da
proposta do Caminho D ("retentar as 324 capturas antes de implementar?").

### Lista de candidatas (preservada)

`output/corpus_text_retry_candidates.csv` (versionado) contém as **324
capturas** cuja última falha registada em `output/corpus_rdf_progress.log` foi
timeout de leitura (318), ligação cortada (5) ou timeout de ligação (1) — a
análise de "Causa real dos 401 textos indisponíveis" acima, que foi feita com
um script ad hoc não versionado. A lista foi regenerada em 2026-09-19 com a
mesma lógica sobre `output/corpus_articles.ttl`, o log e o raw de
`version_history`, e verificada: 324 linhas, 324 pares `(originalURL, tstamp)`
únicos, distribuição idêntica à documentada, **89 artigos** afetados. Colunas:
`original_url` (canónico, tal como no grafo), `tstamp`,
`last_failure_category`, `attempts_logged` (nº de linhas de falha no log) e
`status_code` (do raw de `version_history`).

Expectativa, não garantia: 12 das 324 têm `statusCode` diferente de 200 (10 com
302, 2 com 404) e nenhuma das 35 capturas não-200 do corpus obteve texto até
agora, pelo que é provável que estas 12 falhem de novo.

### Desenho do script (`src/semantic_harvester/corpus_text_retry.py`)

Isolado e simples; não reescreve a resumibilidade de `corpus_rdf.py`.

- **Entrada:** a lista de candidatas acima.
- **Tentativas:** `ArquivoClient.download_extracted_text()` diretamente (com
  `skip_existing=True`, pelo que um texto já em cache conta como sucesso sem
  pedido), até **3 tentativas** por captura com espera crescente de **10 s e
  20 s** entre elas. Reaproveita o padrão das Fases 1–2 (3 tentativas, 10 s),
  com espera crescente em vez de fixa. Um **HTTP 404 não é retentado** (resposta
  definitiva). Timeout do cliente: o padrão do `ArquivoClient` (10 s/30 s), o
  mesmo de `corpus_rdf.py` depois da correção. Pior caso teórico de duração:
  cada captura a esgotar 3 × 30 s + 30 s de espera ≈ 120 s, ou seja, até
  cerca de 10,8 h para as 324 — um limite máximo, não uma previsão.
- **Resumível por captura:** cada resultado (sucesso ou falha definitiva
  depois de todas as tentativas) é escrito com flush em
  `output/corpus_text_retry_report.csv`; uma nova execução salta as capturas já
  presentes. Para retentar uma falha definitiva, apaga-se a sua linha.
- **Relatório:** `outcome` (`success`, `success_cached`, `failed`), `cause`
  (as categorias da análise: `timeout_de_leitura`, `timeout_de_ligacao`,
  `ligacao_cortada`, `http_404`, `outro_http`, `outros`), `attempts`, último
  `error`, `text_path` e `size_bytes`. Resumo em
  `output/corpus_text_retry_summary.md`; log de progresso (a cada 10 capturas)
  em `output/corpus_text_retry_progress.log` (não versionado).
- **Isolamento:** não lê nem escreve `output/corpus_rdf_report.csv`, os
  triplos em `data/processed/` nem o grafo. O único efeito nos dados do corpus é
  acrescentar textos a `data/raw/texts/`, com o nome que `corpus_rdf.py` usa
  (as capturas vão com o `originalURL` canónico).

Testes (`tests/test_corpus_text_retry.py`, 11 testes, fixtures sintéticas e
uma sessão HTTP simulada que consegue levantar erros de rede): sucesso à
primeira tentativa; sucesso após falhas transitórias com espera crescente
(10 s, 20 s); falha persistente registada com a causa; 404 não retentado; texto
já em cache sem pedido; relatório escrito captura a captura; segunda chamada
sem repetir capturas concluídas; retoma só da captura em falta após uma
interrupção; não toca no relatório RDF, no grafo nem nos triplos; erro claro
se faltar a lista; categorias de erro. Suite completa: 58 testes, todos a
passar.

Como correr (no terminal do autor, com o ambiente ativo):
`python -m semantic_harvester.corpus_text_retry`. Depois, versionar
`output/corpus_text_retry_report.csv` e `output/corpus_text_retry_summary.md`
(os textos em `data/raw/texts/` não são versionados).

### Proposta: como os textos recuperados entram no grafo (validada; alternativa 2 implementada em 2026-09-20)

**O problema.** Depois da retentativa, os textos ficam só em cache
(`data/raw/texts/`). `corpus_rdf.py` salta os artigos já presentes em
`output/corpus_rdf_report.csv` e o grafo Turtle é regenerado a partir dos
triplos acumulados em `data/processed/corpus_articles_triples.nt`; por isso,
voltar a correr `corpus_rdf.py` tal como está **não altera nada** (127 de 127
artigos saltados) e os textos novos nunca entrariam no grafo nem em
`corpus_rdf_report.csv`.

**Constatação que condiciona a solução:** os 324 candidatos estão em **89 dos
127 artigos (70%)**. Reprocessar "só os artigos afetados" não é, portanto, uma
fração pequena.

Alternativas consideradas:

1. **Cirurgia nos ficheiros de retoma** (apagar as linhas afetadas de
   `corpus_rdf_report.csv` e os seus triplos do `.nt`, e correr `corpus_rdf.py`).
   Contras: apagar triplos por artigo num `.nt` apendável é propenso a erro
   (os triplos do `Jornal` são partilhados) e é edição manual de outputs; e a
   reexecução tentaria **de novo a rede** para as capturas ainda sem texto
   desses até 89 artigos (404 e novas falhas), com uma tentativa e os
   problemas de duração e memória já vistos.
2. **Reconstrução completa offline (recomendada).** Acrescentar a
   `corpus_rdf.py` um modo `--rebuild-offline`: um cliente só de cache (um
   texto conta como disponível se o ficheiro existir em `data/raw/texts/`; caso
   contrário fica indisponível **sem qualquer pedido**) e reprocessamento dos
   127 artigos a partir do raw de `version_history`, da classificação e da
   cache, com o mesmo código de produção (`build_one_article_graph()`). É
   determinístico, sem rede, e demora segundos. Fluxo: (i) guardar cópia do
   `.nt` atual (o Turtle, o relatório e o resumo já estão no Git); (ii)
   reconstruir; (iii) verificar; (iv) versionar os outputs.
3. **Acrescento pontual de triplos** (gerar só os triplos `TextoExtraido` das
   capturas recuperadas e anexá-los ao `.nt`, que é apendável). Mais leve, mas
   duplica a lógica de `build_article_history_graph()` e deixa
   `corpus_rdf_report.csv` (contagens por artigo) desatualizado, exigindo
   reescrevê-lo à parte; risco de divergência entre o grafo e o código de
   produção.
4. **Não atualizar o grafo e ler os textos da cache no Caminho D.** Rejeitada:
   o grafo (entregável do Caminho A) e as análises passariam a divergir.

**Recomendação: alternativa 2.** Verificações de aceitação a fazer depois da
reconstrução (propostas, não implementadas):

- 127 artigos, 941 capturas e 12 735 triplos base inalterados, exceto o
  acrescento de textos;
- `TextoExtraido` no novo grafo = 540 + nº de capturas recuperadas
  (`success` + `success_cached` no relatório da retentativa), e cada
  `filePath` existe em disco;
- **todos os triplos do grafo antigo continuam no novo** e a diferença
  contém apenas triplos de `TextoExtraido` (tipo, `filePath`,
  `temTextoExtraido`) — deteta uma cache incompleta ou corrompida, que de
  outro modo daria menos textos em silêncio;
- o Turtle relê sem erros.

Ressalvas: (a) em modo offline todos os textos contam como "reutilizados", pelo
que as colunas `texts_downloaded_now`/`texts_reused` do relatório perdem
significado (já só a soma era informativa, ver "Ressalvas sobre estes
números"); a causa das falhas continua nos relatórios e logs; (b) a
reconstrução exige a cache local completa, daí a verificação de inclusão;
(c) exige uma alteração de código e testes (cliente só de cache,
`--rebuild-offline`, teste sintético em que um texto aparece na cache entre
duas construções e só os triplos desse texto são acrescentados) — **implementada
em 2026-09-20** (`--rebuild-offline`).

### Sequência prevista

1. O autor corre `corpus_text_retry` localmente e versiona o relatório e o
   resumo.
2. Valida-se a alternativa de integração e implementa-se; reconstrução offline
   do grafo com as verificações acima.
3. Só então se avança para a implementação do Caminho D, com a
   disponibilidade de textos real e conhecida.

## Resultados da retentativa e reconstrução do grafo (números finais do Caminho A, 2026-09-20)

**Estado: retentativa executada pelo autor; grafo reconstruído offline e
verificado.** Estes são os números finais do Caminho A e substituem os
anteriores à retentativa (540 textos/401 indisponíveis), que ficam como
histórico nas secções acima.

### Retentativa (corrida pelo autor, fora do Claude Code)

Das 324 candidatas: **249 recuperadas (76,9%)** e **75 falhas definitivas
(23,1%)** (`output/corpus_text_retry_report.csv`; verificado por soma direta
do relatório: 324 pares únicos, o mesmo conjunto da lista de candidatas).

- Por categoria de falha original: 243 das 318 de timeout de leitura
  recuperadas (76,4%); as 5 de ligação cortada e a de timeout de ligação
  recuperadas todas.
- Das 249 recuperadas, 188 à 1.ª tentativa, 36 à 2.ª e 25 à 3.ª: 61 (24,5%)
  precisaram de repetição, o que justifica a política de várias tentativas.
- Das 75 falhas: **51 são HTTP 404** (41 à 1.ª tentativa, 9 à 2.ª e 1 à 3.ª;
  o 404 não é retentado, pelo que as tentativas anteriores falharam por
  timeout) e **24 são timeouts de leitura persistentes** (3 tentativas cada).
  Estão em 35 artigos.
- Todas as 249 recuperadas são capturas com `statusCode` 200. As 12
  candidatas com `statusCode` diferente de 200 (10 com 302, 2 com 404)
  falharam todas, como se previa.

Duas correções às estimativas anteriores: (a) o teto teórico de 91,8% era
otimista, porque 51 das falhas que o log registava como timeout escondiam um
404 (ausência real); o resultado real é 83,8% (789/941); (b) os 10,2% de
"recuperação" da análise das falhas eram um limite inferior muito enviesado;
numa retentativa sistemática a recuperação observada foi 76,9%.

### Reconstrução offline (implementada em `corpus_rdf.py`)

`python -m semantic_harvester.corpus_rdf --rebuild-offline` (com
`--check-only` para só verificar): `CacheOnlyClient` (um texto está
disponível se o ficheiro existir em `data/raw/texts/`; nunca faz pedidos, a
sessão HTTP levanta erro se for usada), `rebuild_graph_offline()` (reutiliza
`build_one_article_graph()` e o resto do código de produção, sem duplicar
lógica), `verify_rebuild()` e `rebuild_offline()`. Reconstrói os 127 artigos em
memória (cerca de 5 s), corre as verificações e **só substitui os outputs se
todas passarem**; antes de escrever copia o `.nt` para
`data/processed/corpus_articles_triples.nt.pre-rebuild` (não versionado).

Verificações de aceitação (as da proposta), executadas primeiro em
`--check-only` e depois na aplicação; todas **OK**:

| Verificação | Resultado |
| --- | --- |
| `artigos` | 127 `Artigo`, 127 retidos, 0 com erro |
| `capturas` | 941 `CapturaArquivada`, 941 esperadas pela classificação |
| `textos_esperados` | 789 `TextoExtraido` = 540 no grafo antigo + 249 recuperadas |
| `antigo_contido_no_novo` | 12 735 triplos antigos, 0 ausentes do novo |
| `diferenca_so_textos` | 747 triplos acrescentados, 0 que não são de `TextoExtraido` |
| `filepaths_existem` | 789 caminhos, 0 sem ficheiro em disco |
| `turtle_reler` | relido, 13 482 triplos, iguais aos do grafo em memória |

Verificação independente depois da escrita, contra o Turtle do commit
anterior (`git show HEAD:output/corpus_articles.ttl`): 0 triplos antigos
ausentes, 747 acrescentados (= 249 textos × 3 triplos: `rdf:type`, `filePath`,
`temTextoExtraido`), e uma retoma normal (`build_corpus_graph()`) reconstrói
exatamente o mesmo grafo a partir do `.nt` novo.

Testes: 10 novos em `tests/test_corpus_rdf.py` (cliente só de cache sem
pedidos; o teste proposto, em que um texto aparece na cache entre duas
construções e só os 3 triplos desse texto são acrescentados; escrita e
releitura; recuperação incorporada com todas as verificações OK; `--check-only`
sem escrever nada; verificação falhada, por cache incompleta, que deixa os
ficheiros intactos; contagem de textos incoerente com o relatório da
retentativa; validação do argumento). Suite completa: **68 testes, todos a
passar**.

### Números finais do Caminho A

| Medida | Antes da retentativa | Final |
| --- | ---: | ---: |
| Artigos mapeados | 127 | 127 |
| Capturas no grafo | 941 | 941 |
| Textos disponíveis | 540 (57,4%) | **789 (83,8%)** |
| Capturas sem texto | 401 (42,6%) | **152 (16,2%)** |
| Triplos | 12 735 | **13 482** |
| Artigos sem nenhum texto | 32 | **2** |
| Artigos com todos os textos | 30 | **77** |

Instâncias no grafo final: 127 `Artigo`, 1 `Jornal`, 127 `RecursoWeb`, 941
`CapturaArquivada`, 789 `TextoExtraido`. Capturas com `originalURL`
normalizado: 189 em 32 artigos (inalterado).

As **152 capturas sem texto**: 128 HTTP 404 (77 da recolha original + 51 da
retentativa) e 24 timeouts de leitura persistentes. Só os 24 não são evidência
de ausência. Por `statusCode`: as 789 com texto são todas 200; das 152 sem
texto, 117 são 200, 32 são 302, 2 são 404 e 1 é 301 — **as 35 capturas com
`statusCode` diferente de 200 continuam todas sem texto**.

### Ressalvas

- Numa reconstrução offline todos os textos contam como "reutilizados": em
  `output/corpus_rdf_report.csv` `texts_downloaded_now` é 0 e `texts_reused`
  é o nº de textos disponíveis por artigo. A divisão histórica
  descarregados/reutilizados (281/259) só existe no relatório do commit
  `72c7afb` e já não era informativa. Só o total disponível é significativo.
- 24 capturas (2,6%) ficam com timeout persistente após 3 tentativas; não foram
  retentadas mais e não se pode afirmar que o texto não exista.
- `data/raw/texts/` tem 794 ficheiros para 789 textos no grafo: os mesmos 5
  ficheiros órfãos já descritos (não referenciados, inofensivos, não
  versionados).
- A reconstrução exige a cache local completa; a verificação
  `antigo_contido_no_novo` é a salvaguarda (uma cache incompleta em
  outra máquina faria a reconstrução falhar em vez de perder textos em
  silêncio).
- A retentativa foi corrida pelo autor; os números foram verificados a partir
  dos ficheiros produzidos, não observados em direto.
