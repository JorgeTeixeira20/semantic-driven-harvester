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

## Caminho D — redução de redundância entre capturas (concluído: variante c′, limiar 0,90; variantes a e b como histórico)

**Estado em 2026-09-24: desenho validado pelo autor e implementado em
`src/semantic_harvester/corpus_redundancy.py`; executado sobre o corpus real
(ver "Implementação e resultado da execução" no fim desta secção). Amostra de
60 pares rotulada manualmente pelo autor em 2026-10-02 ("Rotulagem manual da
amostra"); variante (b), remoção do chrome, implementada e avaliada contra esses
rótulos no mesmo dia, sem separação ("Variante (b): remoção do chrome").
Caminho D fechado em 2026-10-02 com a variante (a) e limiar 0,80 ("Fecho do
Caminho D"); em 2026-10-09 os autores adotaram a variante (c′) com limiar 0,90,
que passa a ser o resultado reportado ("Adoção da variante (c′)"); (a) e (b)
ficam como histórico, testadas e não adotadas.** O texto abaixo
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

**Pendente (em 2026-09-24; a rotulagem foi feita depois, ver a subsecção
seguinte):** o limiar da Camada 1 **não foi fixado** e fica pendente da
rotulagem manual da amostra de 60 pares (20 por faixa) pelos autores. Só
depois se corre `--limiar X` e se reportam versões textuais distintas por
artigo como resultado de D; até lá, os números acima são uma tabela de
sensibilidade, não o resultado da redução. Representação em RDF continua
fora desta iteração (decisão 2).

### Rotulagem manual da amostra (2026-10-02)

**Método.** O autor rotulou os 60 pares de
`output/corpus_redundancy_label_sample.csv` um a um ("mesma versão" / "texto
alterado", colunas `rotulo_manual` e `notas`, versionadas no commit
`e9de48c`). Para cada par foram mostradas a similaridade e as palavras só em
A / só em B e, a pedido ou como apoio, o texto completo ou o corpo do artigo
isolado de A e B com as diferenças palavra a palavra. Essa extração do corpo
foi feita com um script ad hoc não versionado (heurística por título e
marcadores de fim como "Mais notícias", "O Record recomenda para si", "Mais
Fotos"), verificada à mão nos primeiros pares; serviu só de apoio à leitura,
a decisão foi sempre do autor. Critério seguido, coerente com as Limitações
acima: "mesma versão" quando o conteúdo do artigo no texto extraído é o mesmo,
mesmo que o chrome mude.

**Resultado.**

| Faixa | mesma versão | texto alterado |
| --- | ---: | ---: |
| baixa [0; 0,70) | 19 | 1 |
| média [0,70; 0,90) | 19 | 1 |
| alta [0,90; 1] | 20 | 0 |
| Total | 58 | 2 |

Os dois "texto alterado": par 1 (0,434), em que a captura posterior não
contém o artigo, só menus e manchetes; par 29 (0,780), página de jogo em
direto (`…/fc-porto-chelsea-final-da-uefa-youth-league-em-direto`) capturada
ao intervalo e depois do fim, com título, abertura e relato reescritos. Nos
58 "mesma versão", o corpo do artigo era idêntico (ou só diferia num contador
de visualizações, num marcador "PUB" ou na posição das etiquetas "Temas") e as
diferenças estavam no chrome: data do dia, menus, colunistas, manchetes e
blocos "Mais notícias"/"Mais Fotos"/"Mais Hora Record". 7 dos 60 pares eram
textos iguais byte a byte (todos com similaridade 1,0).

**Consequência para o limiar (descritiva; o limiar não foi fixado).** Contra
estes rótulos, com a medida atual (texto completo com chrome):

| Limiar | "mesma versão" abaixo do limiar (de 58) | "texto alterado" acima do limiar (de 2) |
| ---: | ---: | ---: |
| 0,50 | 5 | 1 |
| 0,60 | 13 | 1 |
| 0,70 | 19 | 1 |
| 0,80 | 28 | 0 |
| 0,85 | 33 | 0 |
| 0,90 | 38 | 0 |
| 0,95 | 43 | 0 |
| 0,99 | 48 | 0 |
| 1,00 | 51 | 0 |

Os rótulos **não se separam por similaridade**: há "mesma versão" desde 0,438
(par 2), praticamente ao nível do "texto alterado" mais baixo (0,434), e o
"texto alterado" do par 29 (0,780) fica acima de 19 pares "mesma versão".
Nenhum limiar acerta nos 60: os que evitam fundir os 2 "texto alterado"
(≥ 0,80) deixam de reconhecer pelo menos 28 dos 58 pares "mesma versão". A
causa observada é a que a exploração antecipava: a similaridade sobre o texto
completo é dominada pelo chrome, que varia de captura para captura mesmo
quando o artigo não muda. Isto é evidência a favor de reconsiderar a variante
(b) do ponto 3 do desenho (remover o chrome) antes de fixar o limiar; a decisão
cabe aos autores e não foi tomada aqui.

**Observações registadas nas notas** (não quantificadas no corpus inteiro):

- 7 pares de artigos **Premium** (3 artigos distintos) sem corpo: as capturas
  só têm título, subtítulo/primeiro parágrafo e o aviso de acesso pago; foram
  rotulados "mesma versão" pelo conteúdo visível, mas o corpo nunca pode ser
  comparado.
- 2 pares da página `https://www.record.pt/jogos-em-direto/live/78799`, que
  no texto extraído é só título e menu: não é um artigo. É um caso concreto da
  limitação já registada da classificação (páginas `/jogos-em-direto/` não
  cobertas pela regra).
- 3 pares cujo conteúdo não é de futebol/desporto, segundo o autor (Record
  Auto, running/equipamento, Record Gaming); um quarto é de ciclismo.
- 1 par (31, fotogaleria) em que o autor indicou que a foto muda; o texto
  extraído não inclui imagens e é idêntico, por isso foi rotulado "mesma
  versão" com essa nota.
- A amostra cobre só 34 artigos distintos: um vídeo (Abel Xavier, Hora Record)
  aparece em 11 dos 60 pares, e outros 5 artigos em 3 pares cada. Os pares
  consecutivos concentram-se em artigos capturados com muita frequência, o que
  limita o que estes 60 rótulos dizem sobre o corpus.

**Pendente (em 2026-10-02, antes da subsecção seguinte):** fixar o limiar (ou
decidir antes a remoção do chrome e repetir a distribuição e, se necessário, a
rotulagem) e só depois correr `--limiar X` e reportar as versões textuais
distintas por artigo.

### Variante (b): remoção do chrome (2026-10-02)

**Implementação** (`src/semantic_harvester/corpus_chrome.py`; comando no
README). Ponto 3(b) do desenho, sem marcadores manuais: um n-grama de palavras
(texto normalizado como na variante a) é **chrome** se aparecer numa fração ≥ `f`
dos **artigos distintos** com texto e em pelo menos 2 artigos. A frequência é
contada por artigo, não por captura, para que um artigo muito capturado não
faça o seu próprio conteúdo passar por chrome (leitura literal de "capturas de
artigos diferentes"). As palavras cobertas por algum n-grama de chrome são
retiradas e a medida é a mesma (Jaccard de conjuntos de palavras) sobre o que
sobra. n = 5 por omissão (trigramas arriscam apanhar expressões comuns do
próprio texto jornalístico; 8-gramas deixam escapar manchetes curtas), com
n = 3 e n = 8 como sensibilidade. Não altera o grafo, o raw nem as saídas da
variante (a) (checksums de `output/corpus_articles.ttl`, `data/raw/texts/` e
`output/corpus_redundancy*` iguais antes e depois). 19 testes unitários com
fixtures sintéticas (`tests/test_corpus_chrome.py`).

**Escolha da fração, só pela distribuição e antes de olhar para os rótulos.**
Primeiro correu-se `--so-distribuicao` (`output/corpus_chrome_summary.md`):
789 capturas da Camada 1 de 125 artigos, 223 142 5-gramas distintos, dos quais
166 085 aparecem em 1 artigo e 40 272 em 2. A curva das palavras removidas tem
um patamar entre ≥ 13 e ≥ 38 artigos (frações 0,10–0,30: 43,2% → 39,2% das
palavras), sobe depressa abaixo dele (46,0% a ≥ 8 artigos, 54,0% a ≥ 4,
58,0% a ≥ 3) e cai a pique acima (29,9% a 0,40, 15,5% a 0,50, 3,8% a 0,75).
Fixou-se **f = 0,10 (≥ 13 artigos)**, o limite inferior do patamar: remove o
máximo de chrome persistente sem entrar na zona de baixa frequência, onde
manchetes rotativas e conteúdo partilhado por poucos artigos se misturam.
Resultado: 1 714 5-gramas de chrome; nenhuma captura fica vazia.

**Resultado real na Camada 1 (texto sem chrome).** Pares consecutivos (664):
mín. 0,225, p10 0,340, mediana 0,457, p90 0,995, máx. 1,000 (com chrome:
0,434 / 0,561 / 0,655 / 0,995 / 1,000). Redundantes pela estratégia principal:
253 a 0,50, 142 a 0,60, 99 a 0,70, 82 a 0,80, 78 a 0,85, 75 a 0,90, 73 a 0,95,
70 a 0,99, 66 a 1,00 (tabela completa no resumo).

**Teste contra os 60 rótulos manuais (o teste que interessa), texto sem
chrome, n = 5, f = 0,10** (`output/corpus_chrome_label_eval.csv`):

| Limiar | "mesma versão" abaixo do limiar (de 58) | "texto alterado" acima do limiar (de 2) |
| ---: | ---: | ---: |
| 0,50 | 18 | 1 |
| 0,60 | 27 | 1 |
| 0,70 | 33 | 1 |
| 0,80 | 37 | 0 |
| 0,85 | 40 | 0 |
| 0,90 | 43 | 0 |
| 0,95 | 46 | 0 |
| 0,99 | 48 | 0 |
| 1,00 | 50 | 0 |

**Os rótulos continuam sem se separar, e a sobreposição aumentou** face ao
texto com chrome (tabela da subsecção anterior: 28 erros a 0,80, agora 37).
Mínimo "mesma versão" 0,240; máximo "texto alterado" 0,713. O par 1 (texto
alterado) desce de 0,434 para 0,228 e fica abaixo de todos os "mesma versão";
o par 29 (texto alterado) desce de 0,780 para 0,713. **34 pares continuam
ambíguos**: o par 29 e os 33 pares "mesma versão" com similaridade ≤ 0,713 —
pares 2 (0,240), 9, 6, 3, 4, 5, 15, 7, 10, 16, 8, 17, 11, 13, 14, 12, 18, 20,
28, 30, 24, 23, 19, 25, 22, 21, 26, 27, 32, 33, 31, 36 e 40 (0,689), por ordem
crescente de similaridade (valores por par no CSV). Não se propõe limiar: com
esta medida nenhum valor separa os rótulos.

Sensibilidade (calculada depois de fixada a fração, só para verificar que a
conclusão não depende dela; mesma função `evaluate()`):

| n / fração | mín. "mesma versão" | máx. "texto alterado" | pares ambíguos | erros a 0,80 (mesma abaixo / alterado acima) |
| --- | ---: | ---: | ---: | ---: |
| 5 / 0,02 | 0,225 | 0,707 | 31 | 34 / 0 |
| 5 / 0,05 | 0,245 | 0,709 | 35 | 37 / 0 |
| 5 / 0,10 | 0,240 | 0,713 | 34 | 37 / 0 |
| 5 / 0,20 | 0,241 | 0,726 | 34 | 37 / 0 |
| 5 / 0,30 | 0,240 | 0,737 | 34 | 37 / 0 |
| 5 / 0,50 | 0,331 | 0,772 | 33 | 32 / 0 |
| 3 / 0,10 | 0,238 | 0,708 | — | — |
| 8 / 0,10 | 0,239 | 0,714 | — | — |

Nenhuma combinação testada separa os rótulos.

**Porquê (diagnóstico observado).** A remoção apanha o chrome persistente
(menus, rodapés, blocos fixos de cada época do layout), mas o que difere entre
duas capturas do mesmo artigo é sobretudo o chrome **rotativo**: manchetes do
dia, colunistas, números da tabela de clubes. No par 2, quase todos os 5-gramas
não removidos que contêm palavras exclusivas de A aparecem em 2–4 artigos do
corpus (340 em 2, 107 em 4): as manchetes de um dia só surgem nos poucos
artigos capturados nesse dia, e com 125 artigos espalhados por 2017–2019 a
frequência entre artigos não as distingue do conteúdo próprio. Ao retirar a
parte estável e comum, a interseção encolhe e as diferenças rotativas ficam,
pelo que a Jaccard dos pares "mesma versão" desce. A variante (b), tal como
desenhada, **não resolve** o problema identificado na rotulagem.

**Limitações deste teste.**

- A amostra rotulada **não é representativa de artigos**: 60 pares de só 34
  artigos distintos; um vídeo (Abel Xavier, Hora Record) contribui sozinho com
  11 pares e outros 5 artigos com 3 pares cada. Os pares consecutivos
  concentram-se em artigos capturados com muita frequência. A conclusão
  "nenhum limiar separa" é robusta dentro da amostra (vale para todas as
  frações e n testados), mas a amostra limita o quanto se generaliza ao corpus.
- Só há 2 pares "texto alterado"; os limites do lado "alterado" assentam em
  dois casos.
- A frequência por artigo depende do tamanho e da dispersão temporal do corpus;
  num corpus com muitos artigos capturados nos mesmos dias, o chrome rotativo
  poderia ganhar frequência suficiente para ser apanhado. Não foi testado.

**Estado do limiar depois disto (2026-10-02, antes do fecho):** continua **por fixar**. Nem a variante (a)
nem a (b) separam os 60 rótulos com Jaccard de palavras; escolher um limiar
agora seria forçado. As opções seguintes (frequência do chrome por proximidade
temporal das capturas, isolamento do corpo do artigo, ou outra medida) são
decisões dos autores e não foram tomadas aqui.

### Fecho do Caminho D: variante (a) com limiar 0,80 (2026-10-02)

**Decisão (dos autores):** fechar o Caminho D com a **variante (a)** (texto
completo, com chrome) e **limiar 0,80**. A variante (b) fica documentada como
testada e **não adotada**: não separou os rótulos e piorou a sobreposição
(subsecção anterior).

**Critério de escolha do limiar.** É uma escolha **pragmática, não uma
calibração limpa**: nem a variante (a) nem a (b) separam os 60 rótulos
manuais com nenhum limiar, em nenhuma das configurações de Jaccard de palavras
testadas (texto completo; texto sem chrome com frações 0,02–0,50 e n = 3, 5, 8).
Entre os limiares da grelha, 0,80 é o menor que não classifica como igual
nenhum dos pares rotulados "texto alterado". Contra os rótulos, com a
variante (a):

- **0 de 2** "texto alterado" ficam com similaridade ≥ 0,80. O erro grave
  (fundir numa só versão textos realmente alterados) é evitado na amostra.
- **28 de 58** "mesma versão" ficam abaixo de 0,80 e são marcados como
  versões distintas. É um **erro conservador**, aceite porque o Caminho D é só
  uma anotação não destrutiva: não apaga capturas do grafo nem do raw, só
  aumenta o número de "versões distintas".

**Execução real** (`python -m semantic_harvester.corpus_redundancy --limiar
0.80`; `output/corpus_redundancy.csv`, sem `pendente_limiar`;
`output/corpus_redundancy_summary.md`; novo
`output/corpus_redundancy_versions.csv` com as versões por artigo). Os
checksums do grafo, dos textos, da amostra rotulada e das saídas da variante
(b) ficaram iguais. Antes de correr, corrigiu-se um defeito: `run()`
reescrevia sempre a amostra de rotulagem e teria apagado os rótulos manuais;
agora uma amostra rotulada nunca é reescrita (coberto por teste).

| Camada / rótulo | Capturas |
| --- | ---: |
| Camada 1 — representante (versão textual distinta) | 665 |
| Camada 1 — redundante | 124 |
| Camada 2 — mantida sem texto | 136 |
| Camada 2 — candidata por `digest` (não verificada) | 14 |
| Não avaliáveis | 2 |
| Total | 941 |

**Versões textuais distintas:** 665 em 789 capturas da Camada 1 de 125
artigos (2 artigos sem texto não avaliáveis). Por artigo: 55 com 1 versão, 21
com 2, 28 com 3–5, 7 com 6–10, 14 com ≥ 11. Dos 84 artigos com 2 ou mais
capturas com texto, 14 ficam com uma única versão.

**Limitação conhecida, visível no resultado.** O erro conservador concentra-se
nos artigos muito capturados, onde o chrome muda de captura para captura:

| Capturas da Camada 1 por artigo | Artigos | Capturas | Versões distintas | Artigos com todas as capturas como versões |
| --- | ---: | ---: | ---: | ---: |
| 1 | 41 | 41 | 41 (100%) | 41 |
| 2–5 | 56 | 165 | 140 (84,8%) | 34 |
| 6–20 | 17 | 159 | 115 (72,3%) | 8 |
| ≥ 21 | 11 | 424 | 369 (87,0%) | 8 |

Por exemplo, o vídeo `…/zungu-aproveitou-distracao-da-defesa-do-benfica-para-marcar.html`
fica com 71 versões em 71 capturas, embora os seus 3 pares na amostra tenham
sido rotulados "mesma versão" com o corpo idêntico. As 665 "versões
distintas" são por isso um **limite superior** das versões textuais reais, não
uma contagem exata. A validação assenta numa amostra de 60 pares de só 34
artigos (um vídeo com 11 pares, mais 5 artigos com 3 pares cada) e em apenas
2 pares "texto alterado"; não é representativa do corpus.

**Trabalho futuro (decisão em aberto, não tomada):** avaliar uma medida de
similaridade semântica (embeddings) ou outra abordagem que isole o conteúdo do
artigo. Ver `PROJECT_STATUS.md` para as condições.

## Caminho B — povoamento de `Tema` e `EntidadeMencionada` (fonte decidida; primeira execução real)

**Estado (2026-10-02): fonte do vocabulário decidida pelo autor (Wikidata,
ver abaixo); scripts implementados e testados; vocabulário construído e
primeira execução real sobre o corpus feita ("Resultado real", no fim desta
secção).** O texto até "Limitações" é a proposta tal como foi escrita. Os
únicos números do corpus abaixo vêm da estrutura dos `originalURL` dos 127
artigos (metadados já versionados em `output/corpus_classification.csv`), não
de qualquer análise dos textos.

### Decisões já tomadas (PROJECT_STATUS.md)

Vocabulário fechado (clubes/competições/jogadores) em vez de NER genérico;
caracterização descritiva/quantitativa (contagens, frequências), não avaliação
formal de precisão. Esta proposta não reabre essas decisões; decide a fonte do
vocabulário, a fronteira Tema/Entidade e a forma de detetar.

### O que a ontologia fixa

`sdh:temTema` (Artigo → Tema) e `sdh:mencionaEntidade` (Artigo →
EntidadeMencionada) têm ambas **domínio `Artigo`**: a anotação é por artigo,
não por captura nem por texto extraído. As classes só têm `rdfs:label`, sem
definição; a distinção abaixo apoia-se nos nomes das propriedades.

### Distinção Tema vs. EntidadeMencionada (proposta)

- **Tema** = classificação **editorial** do artigo: aquilo de que o artigo
  trata, tal como o próprio Record o arquiva — modalidade, competição e
  clube-secção. "Tem tema" não exige que a palavra apareça no texto.
- **EntidadeMencionada** = nome próprio que **ocorre no texto** do artigo
  ("menciona"): atletas e clubes (e, se o vocabulário os incluir, outras
  pessoas/organizações).
- Consequência: o mesmo clube pode ser as duas coisas (o artigo está na secção
  do Sporting → Tema "Sporting"; o texto cita o Benfica → Entidade "Benfica").
  A modalidade é sempre Tema; um atleta é sempre Entidade.

### Fonte do vocabulário fechado — opções

**(a) Reutilizar os 13 termos da Fase 1** (4 modalidades, Benfica/Sporting/
Porto/SC Braga, 5 atletas; "Facetas e termos").

- Prós: já existe, é pequeno, decidido pelos autores.
- Contras: **circular** — o corpus foi recolhido pesquisando estes termos, logo
  "encontrá-los" é em grande parte garantido e não diz nada de independente;
  ignora todos os outros clubes/atletas do corpus; "Porto" sozinho é ambíguo
  (cidade). Serve, no máximo, como **controlo** (taxa com que os termos de
  pesquisa reaparecem no texto), nunca como resultado de B.

**(b) Temas a partir do `originalURL` + vocabulário fechado só para entidades
no texto.** O caminho do URL já traz a classificação editorial sem NER:
`futebol/futebol-nacional/liga-nos/<clube>/detalhe/...`,
`modalidades/<modalidade>/...`, `internacional/competicoes-de-selecoes/<competição>/...`.

- Prós: independente dos termos de pesquisa e do texto (não é afetado pelo
  chrome); determinístico; regras estruturais por posição no caminho, não uma
  lista de nomes.
- Contras: cobertura parcial. Nos 127 artigos: 50 têm o clube no caminho
  (`liga-nos/<clube>`, 10 clubes distintos), mas 20 estão em `multimedia/…`
  (vídeos/fotogalerias, sem clube nem modalidade no URL) e vários em
  `internacional/…`, `opiniao/…`, `fora-de-campo` etc. só dão a secção. Os
  slugs são ortográficos (`sp--braga`, `v--guimaraes`) e precisam de um rótulo
  legível — mapeamento de apresentação, não de deteção.
- A parte "entidades no texto" continua a exigir uma lista fechada de atletas
  (e clubes), cuja **fonte independente** tem de ser escolhida: por exemplo,
  plantéis dos clubes da Liga NOS 2015–2020 numa base pública como a Wikidata
  (reprodutível, mas implica uma recolha nova fora do Arquivo.pt), ou uma
  lista curada pelos autores com critério explícito.

**Recomendação: (b), com (a) só como controlo separado.** Temas pelo URL (o
que o artigo é, segundo o próprio jornal); Entidades por lista fechada de
fonte independente dos termos de pesquisa; os 13 termos da Fase 1, se forem
usados, reportados à parte e nunca somados. **Decisão pedida ao autor:** a
fonte da lista de atletas/clubes para as Entidades.

### Decisão do autor sobre a fonte (2026-10-02) e construção do vocabulário

**Decidido:** opção (b) com a lista de entidades a partir da **Wikidata** —
jogadores dos plantéis dos clubes da Primeira Liga (Liga NOS) nas épocas
2015–16 a 2019–20. Na prática, o vocabulário fechado de entidades é só de
**jogadores**; os clubes entram como Tema pelo URL.

Construção (`src/semantic_harvester/wikidata_vocabulary.py`, endpoint SPARQL
público da Wikidata, um pedido de cada vez, respostas guardadas em bruto em
`data/raw/wikidata/`, vocabulário em
`data/processed/caminho_b_vocabulario_wikidata.csv`):

1. Clubes = participantes (`wdt:P1923`) dos itens de época 2015–16 a 2019–20,
   uma consulta por época (com `VALUES`, o endpoint devolveu clubes de todas
   as épocas existentes, observado na exploração).
2. Jogadores = futebolistas (`wdt:P106 wd:Q937857`) com uma passagem
   (`p:P54`) por um desses clubes cujas datas se sobrepõem ao intervalo
   (início ≤ 2020 e fim ≥ 2015 ou sem fim). Passagens sem nenhuma data ficam
   de fora: não se pode confirmar o período.
3. Uma linha por rótulo (pt, ou en se faltar); variantes = o rótulo na outra
   língua (sempre, mesmo de uma palavra: é o nome principal do item, por
   exemplo "Pizzi" em en para "Luís Miguel Afonso Fernandes" em pt) e nomes
   alternativos pt/en com 2 ou mais palavras (os de uma palavra, como
   "Ronaldo", são ambíguos e ficam de fora); homónimos (mesmo rótulo em vários
   jogadores) fundidos numa linha com todos os identificadores; variantes
   partilhadas por mais de uma linha descartadas.

Observado na exploração (consultas de leitura, antes do script), a confirmar
na execução: só 3 das 5 épocas (2016–17, 2017–18, 2019–20) têm participantes
na Wikidata, 18 clubes cada, 23 clubes distintos; clubes que só jogaram em
2015–16 ou 2018–19 (por exemplo, Académica e União da Madeira) ficam de fora.
Na mesma exploração, homónimos e rótulos que não são o nome usado na
imprensa já apareceram (vários "Bruno Fernandes"; "Pizzi" sem rótulo pt com
esse nome).

### Estratégia de deteção (sem NER)

1. Normalização para comparar: Unicode NFC → minúsculas (`casefold`) →
   remoção de acentos (NFKD sem marcas combinantes) → palavras `\w+`.
2. Correspondência **exata de sequências de palavras** (limites de palavra
   garantidos pela tokenização): "Bruno Fernandes" só conta se as duas
   palavras aparecerem seguidas; cada entrada do vocabulário pode ter
   variantes ("FC Porto", "F.C. Porto"). Sem correspondência parcial nem
   aproximada; termos ambíguos ("Porto") só entram em variantes desambiguadas.
3. **Chrome.** No texto completo, os menus de todas as páginas contêm
   "Benfica", "Sporting", "FC Porto" e as manchetes rotativas citam
   jogadores: a correspondência direta encontraria os três clubes em quase
   todos os artigos. Propõe-se, por omissão:
   - procurar no texto **sem o chrome persistente**, reutilizando a remoção do
     Caminho D, variante (b) (5-gramas em ≥ 10% dos artigos). No D essa
     variante não foi adotada porque não removia o chrome **rotativo**; aqui o
     objetivo é outro — retirar os menus, que são persistentes — e é para isso
     que ela funciona. Não reabre a decisão do D;
   - contra o chrome rotativo, **persistência entre capturas**: uma entidade
     conta para o artigo se aparecer em todas as suas capturas com texto (o
     corpo do artigo repete-se, as manchetes do dia não). O CSV guarda
     "capturas com menção / capturas com texto", para se poder reportar
     também a regra fraca (≥ 1 captura) como sensibilidade. Artigos com uma
     só captura não têm esta proteção e são assinalados.
4. Temas pelo URL: regras posicionais sobre o caminho (modalidade =
   `futebol` ou o segmento a seguir a `modalidades/`; competição = o segmento
   a seguir a `futebol-nacional/` ou a `competicoes-de-*/`; clube = o segmento
   a seguir à competição nacional; `secao` = primeiro segmento). Ignoram
   marcadores técnicos (`detalhe`, `amp`/`AMP`).

### Saídas e testes previstos

- `output/corpus_entities.csv`: uma linha por (artigo, tipo, categoria,
  rótulo), com origem (`url`/`texto`), capturas com menção, capturas com
  texto, nº de ocorrências e se cumpre a regra de persistência.
- `output/corpus_entities_summary.md`: frequências por tema e por entidade
  (nº de artigos), artigos sem tema/sem entidade, artigos de uma só captura,
  e a comparação regra forte vs. fraca.
- Testes com fixtures sintéticas: normalização (acentos/maiúsculas), limite
  de palavra ("Portimonense" não conta como "Porto"), sequência multi-palavra,
  variantes, entidade só no menu removida pelo chrome, entidade só numa
  manchete de uma captura falha a persistência, temas a partir de URLs de
  cada forma, artigo sem texto, saídas não destrutivas.

### Limitações

- Correspondência de strings sem NER: falha alcunhas e formas não previstas
  ("CR7"), e não resolve homónimos.
- O corpus vem de pesquisas por 13 termos: as frequências caracterizam esta
  amostra, não o Record.
- A remoção do chrome e a persistência reduzem, mas não eliminam, falsos
  positivos vindos do chrome; e o texto Premium sem corpo só dá título/lead.
- Representação em RDF (`mencionaEntidade`/`temTema`, IDs das instâncias)
  fica para uma iteração seguinte, como no Caminho D.

### Resultado real (2026-10-02)

**Vocabulário** (`wikidata_vocabulary`, 28 pedidos à Wikidata: 5 épocas + 23
clubes; respostas em bruto em `data/raw/wikidata/`, fora do Git): só 2016–17,
2017–18 e 2019–20 têm participantes (18 clubes cada, 23 distintos). **1 094
futebolistas** com passagem datada sobreposta a 2015–2020 → **1 091
rótulos** em `data/processed/caminho_b_vocabulario_wikidata.csv`; 3 rótulos
com homónimos (por exemplo "Bruno Fernandes", vários jogadores fundidos numa
linha), 54 rótulos de uma só palavra, 85 nomes alternativos de uma palavra
descartados, 8 variantes partilhadas descartadas.

Na primeira construção, a regra das 2 palavras descartava também o rótulo
noutra língua: o "Pizzi" (rótulo en) perdia-se para o rótulo pt "Luís Miguel
Afonso Fernandes". Corrigido antes da versão usada (o rótulo noutra língua
conta sempre; a regra das 2 palavras fica só para nomes alternativos).
Lacunas de cobertura verificadas nas respostas em bruto: alcunhas que só
existem como nome alternativo de uma palavra ("Rafa", "Charles") não entram;
há jogadores sem passagem datada nos clubes certos (por exemplo "Xadas", só
com uma passagem sem datas) ou não ligados a estes clubes ("Zungu", "Ferro").

**Execução** (`corpus_entities --vocabulario
data/processed/caminho_b_vocabulario_wikidata.csv`, texto sem o chrome
persistente, f = 0,10; `output/corpus_entities.csv`,
`output/corpus_entities_summary.md`). Sem rede; checksums do grafo, dos
textos, do vocabulário e das saídas do Caminho D iguais antes e depois.

*Temas (URL), 127 artigos:* secção em 127 (14 valores); modalidade em 71
(futebol 59; atletismo, ciclismo, judo e motores 2 cada; outras 1); competição
em 62 (liga-nos 52; europeu 4; 2.ª liga 2; outras 1); clube-secção em 50
(sporting 17, benfica 16, fc-porto 5, v--guimaraes 3, boavista, moreirense e
sp--braga 2 cada, aves, maritimo e portimonense 1).

*Entidades (jogadores no texto), 125 artigos com texto:*

| Medida | Regra fraca (≥ 1 captura) | Regra de persistência (todas as capturas) |
| --- | ---: | ---: |
| Pares artigo–jogador | 1 424 | 291 |
| Artigos com pelo menos um jogador | 118 | 93 |
| Jogadores distintos | 228 | 119 |

Mais frequentes pela persistência (nº de artigos): João Félix 16, Jonas 16,
Bruno Fernandes 15, Luisão 11, Bas Dost 11, Bernardo Silva 9, Pepe 7, Pizzi
(rótulo "Luís Miguel Afonso Fernandes") 7, Renato Sanches 6. 65 dos 119
jogadores aparecem num só artigo.

**O que os números mostram sobre a deteção.**

- A remoção do chrome persistente quase não muda os jogadores (291 pares pela
  persistência sem remoção do chrome: 298). Os jogadores não estão nos menus
  persistentes, estão nas manchetes rotativas; o filtro que pesa é a
  **persistência entre capturas** (1 424 → 291). A remoção continua necessária
  para os clubes, que estão nos menus, mas os clubes entram aqui como Tema
  pelo URL.
- **163 dos 291 pares** vêm dos 41 artigos com uma só captura com texto, onde a
  persistência não filtra nada: aí as manchetes do dia contam como menções.
  Só 128 pares (56 artigos) passaram por um teste de persistência real.
- 62 dos 291 pares vêm de rótulos de uma só palavra (Jonas 16, Luisão 11,
  Pepe 7, Moreira 5, …), com maior risco de homonímia ("Moreira" é também um
  apelido comum).
- Circularidade residual: João Félix e Bruno Fernandes estavam entre os
  termos de pesquisa da Fase 1 e somam 31 dos 291 pares (os outros três atletas
  da Fase 1 não estão no vocabulário: não são jogadores destes plantéis).

**Limitações** (além das da proposta): não há avaliação de precisão (decisão
de âmbito), por isso estes números são contagens de correspondências, não de
menções verificadas; o vocabulário depende da completude da Wikidata (épocas
sem participantes, passagens sem datas, alcunhas); os 41 artigos de uma
captura não têm proteção contra manchetes. Representação em RDF continua por
fazer.

### Contaminação por chrome: diagnóstico e sinal `clube_coerente` (2026-10-03)

**Dois casos reportados pelo autor, investigados no texto real.**

1. `…/running---equipamento/amp/divulgadas-primeiras-imagens-dos-novos-nike-pegasus-36-turbo-e-zoom-fly-3`
   (hash `334c91e33971c03a`, 4 capturas com texto; artigo sobre sapatilhas):
   "Jonas", "Bernardo Silva" e "Wilson Eduardo" vêm do bloco **"Últimas
   Notícias"** da página AMP — em `20190322194121`: "19:33 Vídeos O momento
   em que Jonas se emocionou e agradeceu ao Benfica", "19:30 Internacional
   Wilson Eduardo apontou o golo da vitória de Angola sobre o Botsuana"; em
   `20190321194332`: "Zinchenko elogia Bernardo Silva…". Nenhum aparece em
   todas as capturas: contam só pela regra fraca, não pela persistência.
2. `…/liga-nos/detalhe/a-cronica-do-boavista-moreirense-1-0-um-tiro-certeiro-e-xeque-mate.html`
   (hash `99f811299bc25610`): é o artigo **Premium sem corpo** já visto no
   Caminho D, com **28 capturas** (novembro–dezembro de 2017). O texto é quase
   todo chrome e cada captura traz as manchetes do seu dia: 49 jogadores pela
   regra fraca. As menções vêm dos blocos de manchetes — "Últimas Notícias /
   Mais Recentes / Mais Vistas / Mais Comentadas" ("04h20 Benfica Luisão faz o
   pleno…"), "Mais notícias", e a lista de manchetes logo a seguir ao menu
   ("Bas Dost coloca Sporting provisoriamente na liderança", "Dez momentos dos
   10 anos de Rui Patrício na Europa", "Foi desta forma que Jonas chegou ao
   golo 100…"). Pela persistência fica só **Carraça** (28/28, citado no
   subtítulo "golo de Carraça", menção legítima); **Luisão** fica de fora por
   pouco (23/28), porque esteve em manchete durante semanas.

**Causa real:** não é um índice alfabético nem um índice de jogadores; são
**manchetes rotativas do chrome** (blocos de últimas notícias, mais lidas,
"Mais notícias", "Notícias MAIS" e a faixa de manchetes sob o menu). Não são
persistentes ao longo do corpus, por isso a remoção por n-gramas frequentes
não as apanha (já observado no Caminho D).

**Mais duas falhas verificadas ao inspecionar pares que passam a persistência
mas não coincidem com o clube do artigo:**

- **Capturas próximas no tempo partilham manchetes**: no artigo do Yuta
  Koike (Portimonense, 5 capturas no mesmo dia), "Jonas" vem de "Notícias MAIS
  … 05h21 - Benfica Jonas confiante na renovação"; no do Charles (Marítimo, 7
  capturas), "Alan Ruiz" vem de "'Tareias' de Jesus não fazem mossa em Alan
  Ruiz". A regra de persistência só protege quando as capturas estão
  espaçadas.
- **Rótulo de uma palavra dentro de outro nome**: no mesmo artigo do Charles,
  "Moreira" corresponde a "André Moreira" (outro jogador).

**Sinal `clube_coerente`** (`corpus_entities`, coluna nova nas linhas de
entidade; tabela explícita slug do URL → clube em
`data/processed/caminho_b_clubes_url.csv`, 10 clubes com identificador
Wikidata, porque a comparação por palavras é ambígua — "sporting" ocorre em
três clubes, "v--guimaraes" não partilha palavras com "Vitória Sport Clube"):
`sim` se um clube do jogador no vocabulário coincide com o tema `clube` do
URL, `nao` se não coincide, `sem_tema` se o URL não tem clube. **Não remove
nem corrige nenhuma menção.** Resultado real (resto do CSV igual à execução
anterior; checksums das entradas iguais):

| clube_coerente | Pares (regra fraca) | Pares (persistência) | — artigos com 2+ capturas | — artigos com 1 captura |
| --- | ---: | ---: | ---: | ---: |
| sim | 189 | 82 | 46 | 36 |
| nao | 333 | 41 | 22 | 19 |
| sem_tema | 902 | 168 | 60 | 108 |
| Total | 1 424 | 291 | 128 | 163 |

Leitura: só 50 dos 127 artigos têm clube no URL, por isso a maioria dos pares
fica `sem_tema` — incluindo **os dois casos acima**, que o sinal não pode
assinalar. Onde há comparação, a regra fraca dá mais `nao` do que `sim`
(333 vs. 189) e a persistência inverte a proporção (41 vs. 82), coerente com a
persistência filtrar manchetes. `nao` é um indício, não uma prova: um jogador
pode ser legitimamente mencionado num artigo de outro clube (transferências,
adversários, antigos jogadores), e `sim` também não prova uma menção no corpo
(o clube pode vir de uma manchete sobre o mesmo clube).

**Limitações acrescentadas ao Caminho B:** as manchetes rotativas do chrome
são a principal fonte de falsos positivos; a persistência atenua-as só com
capturas espaçadas no tempo e não atua nos 41 artigos de uma captura; o sinal
de clube cobre apenas os 50 artigos com clube no URL e não distingue
menções legítimas a outros clubes.

## Protótipo de navegação (implementado e gerado, 2026-10-03)

**Âmbito já decidido (PROJECT_STATUS.md):** versão mínima baseada em SPARQL
sobre o grafo existente; interface mais interativa só se sobrar tempo. Por
decisão dos autores, ruído, homonímia e chrome (Caminhos D e B) não voltam a
ser refinados nesta fase.

**Dados.** Só `output/corpus_articles.ttl` (Caminho A: `Jornal`, `Artigo`,
`RecursoWeb`, `CapturaArquivada`, `TextoExtraido`). As saídas de D
(redundância) e B (temas/entidades) existem só em CSV, sem RDF — já registado
como "por fazer" nos dois Caminhos; integrá-las no grafo e no protótipo fica
como trabalho seguinte.

**Tecnologia: (b) página HTML estática gerada, sobre (a) queries + script.**
Ambas usam só `rdflib` (SPARQL em memória sobre o Turtle; nenhuma dependência
nova). As queries ficam em ficheiros `.rq` versionados em `queries/`, legíveis
e reutilizáveis noutra ferramenta SPARQL. O script corre-as e gera
`output/prototipo/`: um `index.html` com as tabelas agregadas e a lista de
artigos, e uma página por artigo com o histórico de capturas, ligadas entre si
e às capturas no Arquivo.pt (`archiveURL`). Escolhe-se (b) porque o esforço
extra sobre (a) é pequeno (só gerar HTML a partir de resultados que (a) já
teria) e o resultado é navegável e apresentável sem servidor: abre-se o
`index.html` no browser. HTML autocontido (sem CSS/JS externos), valores
escapados.

**Queries (5), cobrindo estrutura, tempo e agregação:**

1. `artigos.rq` (estrutural): cada artigo com título, `RecursoWeb`/
   `originalURL`, nº de capturas, nº de textos disponíveis, primeira e última
   captura.
2. `historico_artigo.rq` (temporal): histórico completo de um artigo
   (`?artigo` ligado na execução), por ordem cronológica: data, `tstamp`,
   `statusCode`, `digest`, `contentLength`, `archiveURL`, texto disponível.
3. `mais_capturados.rq` (agregada): os 10 artigos com mais capturas e o
   intervalo temporal que cobrem.
4. `capturas_por_ano.rq` (agregada/temporal): capturas e textos disponíveis
   por ano de captura.
5. `textos_por_status.rq` (agregada): capturas com e sem texto por
   `statusCode`.

**Testes:** só onde a lógica pode falhar — contagens das queries agregadas
sobre um grafo pequeno (o risco real é a contagem errada com `OPTIONAL` +
`COUNT`), a ordem e o filtro por artigo do histórico, e a geração (todas as
ligações entre páginas apontam para ficheiros gerados; títulos com `<`/`&`
escapados). A formatação das tabelas não tem teste dedicado.

### Resultado real (2026-10-03)

`python -m semantic_harvester.navigation_prototype` (cerca de 3 s; sem rede;
checksum de `output/corpus_articles.ttl` igual antes e depois) gerou
`output/prototipo/` (816 KB): `index.html` + 127 páginas de artigo, com 127
ligações locais (todas para ficheiros gerados) e 941 linhas de histórico no
total. Os totais coincidem com os do Caminho A: 127 artigos, 941 capturas, 789
com texto.

Exemplos de saída (valores reais das queries):

*Capturas por ano* (`capturas_por_ano.rq`):

| Ano | Capturas | Com texto | Artigos |
| ---: | ---: | ---: | ---: |
| 2017 | 554 | 491 | 52 |
| 2018 | 246 | 194 | 43 |
| 2019 | 117 | 104 | 47 |
| 2020 | 12 | 0 | 4 |
| 2021 | 6 | 0 | 2 |
| 2022 | 4 | 0 | 1 |
| 2023 | 2 | 0 | 1 |

Observação que o protótipo tornou visível e não estava registada: **não há
capturas de 2015 nem de 2016** (a pesquisa da Fase 1 foi feita para 2015–2020,
mas as capturas do `version_history` começam em 2017), e as 24 capturas de
2020–2023 não têm nenhum texto.

*Texto disponível por `statusCode`* (`textos_por_status.rq`): 200 → 906
capturas, 789 com texto; 302 → 32, 0; 404 → 2, 0; 301 → 1, 0 (as 35 capturas
não-200 já documentadas, todas sem texto).

*Artigos com mais capturas* (`mais_capturados.rq`, os 3 primeiros): vídeo
"Zungu aproveitou distração da defesa do Benfica para marcar", 73 capturas
(2017-05-30 a 2017-08-11); vídeo "Abel Xavier: «Vemos o FC Porto à imagem de
Sérgio Conceição»", 72 (2018-02-15 a 2018-04-28); "Exibição de Zivkovic não
espanta 'Drulo'", 51 (2017-01-05 a 2017-03-03).

*Histórico de um artigo* (`historico_artigo.rq`, página do vídeo do Zungu,
primeiras linhas): `2017-05-30 01:01 · 20170530010157 · 200 ·
VMAEIADT… · 23319 · texto sim · Arquivo.pt`, `2017-05-31 01:00 ·
20170531010057 · 200 · SQQKVPJJ… · 23284 · sim`, … — uma linha por captura,
com ligação à captura no Arquivo.pt.

**Pesquisa e filtro (acrescentados a pedido do autor, 2026-10-03):** a lista
"Todos os artigos" tem uma caixa de pesquisa (título e URL, sem distinguir
maiúsculas nem acentos, várias palavras combinadas), um filtro por secção do
site (primeiro segmento do URL, com contagens: futebol 59, internacional 22,
multimedia 20, modalidades 12, …) e um contador "N de 127 artigos". JavaScript
embutido na página, sem bibliotecas externas nem servidor; a lógica foi
verificada com Node sobre as linhas reais (por exemplo "zivkovic" → 7
artigos), não num browser automatizado.

**Limitações:** HTML estático (a pesquisa só filtra a lista de artigos; cada
nova pergunta ao grafo exige uma nova query `.rq` e regenerar); só o grafo do Caminho A — redundância
(D) e temas/entidades (B) continuam fora até terem representação RDF; as
ligações para o Arquivo.pt dependem da disponibilidade do serviço; os textos
extraídos não são mostrados (estão fora do Git).

## Correção da identidade dos artigos: variantes de URL por parâmetros de rastreio (2026-10-04)

**Achado (do autor e do Jorge, ao navegar no protótipo).** Dois dos 127
artigos eram o mesmo artigo contado duas vezes, porque `originalURL` só
diferia em parâmetros de rastreio da origem do clique:

- `…/record-mais/detalhe/yamila-rodriguez-argentina-louca-por-ronaldo?ref=HP_4BucketDestaquesPrincipais`
  (1 captura) e `…?ref=HP_BlocoColoridoSec%C3%A7%C3%A3oDestaque` (7);
- `…/fotogalerias/detalhe/equipamento-do-barcelona-para-20192020-vai-ser-em-xadrez`
  (2) e o mesmo com `?utm_medium=Social&…&act=0&est=Aberto` (1).

Causa: `canonical_key()`/`choose_canonical_url()` (classificação) e
`normalize_for_grouping()` (RDF) só normalizavam esquema e barras, nunca a
query string. Verificado: em cada par o caminho e o título são iguais e as
capturas não se repetem (0 `tstamp` em comum).

**A query não pode ser ignorada por inteiro.** Dos 159 URLs da Fase 1, 28
têm query: 15 do site novo (`/detalhe/<slug>`), todos só com `ref`, `utm_*`,
`act`, `est`; e 13 do site antigo (`interior.aspx?content_id/x3d…`), onde a
query **é** o identificador do artigo — ignorá-la fundiria 8 artigos
diferentes em 3 (todos "Object moved", sem efeito nos artigos retidos, mas
com relatório de classificação errado). **Decisão do autor (opção A):**
ignorar só os parâmetros de rastreio conhecidos `ref`, `utm_*`, `act`, `est`;
qualquer outro parâmetro é mantido.

**Correção** (`src/semantic_harvester/url_identity.py`, regra única usada
por `corpus_classification` e `corpus_rdf`):

- a classificação agrupa por esquema + rastreio; o URL canónico guardado é
  um URL real do grupo (prefere `https`, depois sem rastreio, depois o de
  mais capturas); capturas de variantes de rastreio somam-se (as de esquema
  não, porque devolveram os mesmos `tstamp`); nova coluna `variantes`;
- `corpus_rdf` junta o raw de `version_history` de todas as variantes (já em
  cache, sem pedidos novos), sem `tstamp` repetidos, e a reconstrução
  offline procura cada texto também pelo hash do **URL real da captura**
  (os textos das variantes foram guardados com esse hash);
- as verificações de `--rebuild-offline` foram generalizadas: só podem
  desaparecer triplos de URLs declarados como variante (`variantes_fundidas`,
  `antigo_contido_no_novo`), nenhum ficheiro de texto pode deixar de ser
  referenciado (`ficheiros_de_texto_preservados`) e os textos novos têm de
  ser explicados (`textos_esperados`).

**Segundo achado, apanhado pela verificação.** A primeira reconstrução
falhou `textos_esperados`: 793 textos em vez de 789. Os 4 a mais são textos
**já em cache desde 2026-09-18**, guardados com o hash de URLs com barra
dupla (`http://www.record.pt//futebol/…/fc-porto-b-sp-braga-b-1-3-…`, 3
capturas; `…/entrevistas//detalhe/daniel-ramos-expulsao-de-zainadine-e-estranha.html`,
1), descarregados antes da correção das variantes cosméticas; depois dessa
correção a procura só pelo hash canónico deixou de os ver. Conteúdo
verificado (título do artigo certo, `tstamp` da captura). Decisão do autor:
incorporá-los; `textos_esperados` conta-os numa categoria explícita.

**Execução offline de toda a cadeia** (classificação → `corpus_rdf
--rebuild-offline` → D com limiar 0,80 → B com o mesmo vocabulário →
protótipo), todas as verificações OK:

| | Antes | Depois |
| --- | ---: | ---: |
| Recursos distintos na classificação | 158 | 156 |
| Artigos | 127 | **125** |
| Capturas | 941 | 941 |
| Textos disponíveis | 789 (83,8%) | **793 (84,3%)** |
| Triplos | 13 482 | 13 482 |
| Yamila Rodríguez (capturas / textos) | 1/1 + 7/7 | 8/8 |
| Equipamento do Barcelona (capturas / textos) | 2 + 1 | 3/2 |
| D — Camada 1 / Camada 2 / não avaliáveis | 789 / 150 / 2 | 793 / 146 / 2 |
| D — versões distintas / redundantes (0,80) | 665 / 124 | 666 / 127 |
| D — validação na amostra (alterado ≥ 0,80; mesma < 0,80) | 0/2; 28/58 | 0/2; 28/58 |
| B — pares artigo–jogador, persistência / fraca | 291 / 1 424 | 287 / 1 427 |
| B — artigos com jogador, persistência / fraca | 93 / 118 | 91 / 116 |
| B — `clube_coerente` (persistência) sim / nao / sem_tema | 82 / 41 / 168 | 82 / 41 / 164 |
| Protótipo — páginas de artigo | 127 | 125 |

As capturas totais não mudam (só passam a pertencer a um artigo). A
amostra rotulada do Caminho D não foi reescrita (proteção existente) e os
seus 60 pares não incluem os artigos fundidos. As secções anteriores deste
documento mantêm os números medidos na altura; os números atuais são os
desta tabela. As saídas da variante (b) do Caminho D
(`output/corpus_chrome_*`, testada e não adotada) não foram regeneradas e
continuam a descrever o corpus de 127 artigos.

## Variante (c′): corpo do artigo por âncoras literais (2026-10-04)

**Estado: avaliada em 2026-10-04; adotada em 2026-10-09 nos Caminhos D
(limiar 0,90) e B, com "Mais Premium" como 14.º marcador (ver "Adoção da
variante (c′)", a seguir).** Esta secção regista a avaliação tal como foi
feita, com 13 marcadores.

**Porquê (c′) e não "cortar no primeiro marcador".** A ideia inicial era
cortar o texto no primeiro marcador de bloco de chrome. Verificado nos 793
textos antes de implementar: em **712** o primeiro marcador ("Últimas
Notícias", item do menu do topo) vem **antes** do corpo, pelo que o corte
apagaria o artigo. Decisão do autor: delimitar o corpo entre duas âncoras
literais — **início** no título do artigo dentro do texto, a seguir ao
título da página (nas AMP, que não têm o sufixo " - … - Jornal Record",
depois de "Home"; ignorando o título quando aparece listado no menu logo
antes de um marcador), **fim** no primeiro dos 13 marcadores depois do
início; sem início localizável, a captura fica **"sem corpo"** (terceira
categoria, fora das comparações).

**Lista de marcadores (13, decisão do autor):** "Mais notícias", "O Record
recomenda para si", "Mais Fotos", "Mais Hora Record", "Últimas Notícias",
"Mais Recentes", "Mais Vistas", "Mais Comentadas", "Notícias MAIS" (da
rotulagem e do diagnóstico do B) e "Veja também", "Mais Vídeos", "Enviar
artigo por email", "Leia este artigo na íntegra" (do script de apoio da
rotulagem). Verificação nos 793 textos, antes de confiar na lista: todas as
ocorrências são cabeçalhos de bloco e começam com maiúscula, **exceto
"mais recentes" a meio de uma frase** no artigo da Record Auto sobre o SUV
da Xiaomi (`64ba9625…`, 4 capturas: "Os mais recentes rumores dão conta
de…"); e sem limites de palavra "cer**veja também**" contaria como "Veja
também". Decisão do autor: correspondência sem acentos, com limites de
palavra e com a **primeira letra maiúscula no texto original**. Variações
reais cobertas por isto: "Últimas notícias", "Notícias Mais", "MAIS
Notícias". Implementação em `src/semantic_harvester/corpus_body.py` (9
testes, incluindo a regressão do "mais recentes"); as 4 capturas da Xiaomi
mantêm o corpo completo.

**Delimitação nas 793 capturas da Camada 1 (real):** 775 com corpo, 18 sem
corpo (a página `/jogos-em-direto/` e capturas que não contêm o artigo).
Corpo mediano de 754 caracteres (11,2% do texto). Marcadores que fecharam o
corpo: "Mais notícias" 216, "Veja também" 168, "O Record recomenda para si"
117, "Últimas Notícias" 102, "Mais Hora Record" 44, fim do texto 34, "Mais
Fotos" 29, "Mais Vídeos" 20, "Enviar artigo por email" 15, "Leia este
artigo na íntegra" 15, "Mais Recentes" 9, "Mais Vistas" 6.

### Caminho D: as três variantes contra os 60 pares rotulados

| Limiar | (a) texto completo: "mesma" < limiar (de 58) / "alterado" ≥ limiar (de 2) | (b) sem chrome por n-gramas | (c′) corpo: "mesma" (de 56) / "alterado" (de 1) |
| ---: | ---: | ---: | ---: |
| 0,50 | 5 / 1 | 18 / 1 | 0 / 1 |
| 0,60 | 13 / 1 | 27 / 1 | 0 / 1 |
| 0,70 | 19 / 1 | 33 / 1 | 0 / 1 |
| 0,80 | 28 / 0 | 37 / 0 | 0 / 1 |
| 0,85 | 33 / 0 | 40 / 0 | **0 / 0** |
| 0,90 | 38 / 0 | 43 / 0 | **0 / 0** |
| 0,95 | 43 / 0 | 46 / 0 | **0 / 0** |
| 0,99 | 48 / 0 | 48 / 0 | 1 / 0 |
| 1,00 | 51 / 0 | 50 / 0 | 4 / 0 |

Na (c′), 3 pares ficam à parte por terem uma captura sem corpo: **par 1**
("texto alterado": a captura posterior não contém o artigo — é exatamente o
que o rótulo dizia) e **pares 50 e 60** ("mesma versão", página
`/jogos-em-direto/`, sem corpo nas duas capturas). Nos 57 comparáveis,
**os rótulos separam-se de forma limpa**: mínimo "mesma versão" 0,975 (par
2), máximo "texto alterado" 0,840 (par 29); qualquer limiar em ]0,840; 0,975]
separa (na grelha: 0,85, 0,90, 0,95). Com (a) e (b) nenhum limiar separava.

**Ressalvas, sem as quais este resultado seria sobrevalorizado:**

- O lado "texto alterado" assenta **num único par comparável** (o 29, página
  em direto); o outro (par 1) é a categoria "sem corpo". A margem observada
  (0,840 → 0,975) é real mas medida com n = 1 de um lado.
- A amostra continua a ser a mesma: 60 pares de 34 artigos, um vídeo com 11
  pares.
- Nos 654 pares consecutivos da Camada 1 com corpo, a distribuição muda de
  forma radical (mediana 0,655 → 1,000; 609 iguais), mas **23 pares ficam
  abaixo de 0,90** e foram inspecionados um a um:
  - 13 são do **layout de 2019**: entre o fim do artigo ("Deixe o seu
    comentário") e "Últimas Notícias" há um bloco de manchetes rotativas com
    o cabeçalho **"Mais Premium"**, que não está na lista; entra no corpo;
  - 4 são do artigo Premium "Exibição de Zivkovic…": umas capturas mostram o
    aviso Premium e outras o **artigo completo desbloqueado** — diferença
    real no que foi arquivado;
  - 3 são falhas da âncora de início (o título encontrado numa listagem de
    outro bloco antes do artigo: "Vídeo-árbitro…", "Cristiano Ronaldo quis
    entrar com o pé direito…", "Yuri Ribeiro…");
  - 3 restantes (0,58–0,89) não foram caracterizados em detalhe; num deles
    uma captura traz o endereço de um embed de vídeo em vez da legenda.
- Sensibilidade não aplicada (só calculada): acrescentar "Mais Premium" como
  14.º marcador baixaria os 23 pares para 12 e não mudaria a separação dos
  rótulos. **Não foi acrescentado** (a lista foi fixada em 13 pelo autor).

### Caminho B: o corpo (c′) em vez do texto sem chrome persistente

Os dois casos investigados em 2026-10-03:

- **Nike** (`334c91e33971c03a`, 4 capturas, todas com corpo): as 3 menções
  falsas (Jonas, Bernardo Silva, Wilson Eduardo) **desaparecem** — 0 menções.
- **Crónica Boavista-Moreirense** (`99f811299bc25610`, 28 capturas, todas com
  corpo): de 49 jogadores pela regra fraca fica **só Carraça** (28/28, citado
  no subtítulo, menção legítima).

Corpus inteiro (mesmo vocabulário; "antes" = configuração fechada do B):

| Medida | B fechado (sem chrome persistente) | Corpo (c′) |
| --- | ---: | ---: |
| Pares artigo–jogador, regra fraca | 1 427 | 131 |
| Pares artigo–jogador, persistência | 287 | 114 |
| Artigos com jogador, regra fraca | 116 | 63 |
| Artigos com jogador, persistência | 91 | 58 |
| Jogadores distintos, persistência | 118 | 79 |

Dos 287 pares persistentes do B fechado, 109 mantêm-se e 178 desaparecem.
Numa amostra aleatória de 12 dos desaparecidos (semente 1), **todos** vinham
do chrome (blocos "Notícias MAIS", "Últimas Notícias", listas de opinião e
de mais lidas); um deles era ainda homonímia ("Pedro Santos" dentro de
"Pedro Santos Guerreiro", um colunista). Não se fez uma avaliação de
precisão (fora do âmbito do B); isto é uma verificação por amostra. As
limitações da (c′) acima (bloco "Mais Premium" de 2019, falhas da âncora)
também afetam o B; com "Mais Premium" (não aplicado) a regra fraca daria
119 pares.

**Saídas** (`python -m semantic_harvester.corpus_body --vocabulario
data/processed/caminho_b_vocabulario_wikidata.csv`, sem rede; checksums do
grafo, dos textos e das saídas fechadas de D e B iguais antes e depois):
`output/corpus_body_summary.md`, `output/corpus_body_label_eval.csv`,
`output/corpus_body_entities.csv`.

**Decisões em aberto na altura (tomadas em 2026-10-09, ver a secção
seguinte):** (1) se a (c′) deve
substituir a variante (a) no Caminho D — e, nesse caso, com que limiar
dentro de ]0,840; 0,975] — sabendo que a separação assenta num só par
"alterado"; (2) se a (c′) deve passar a ser a base do Caminho B; (3) se
"Mais Premium" entra como 14.º marcador. O limiar 0,80 da variante (a)
mantém-se até decisão em contrário.

## Adoção da variante (c′) nos Caminhos D e B (2026-10-09)

**Decisões dos autores.**

1. **Caminho D: (c′) substitui a variante (a), com limiar 0,90.** Na amostra
   rotulada qualquer limiar em ]0,840; 0,975] separa os rótulos; escolheu-se
   0,90, a meio caminho entre as duas fronteiras observadas, em vez de 0,85
   (o mínimo que ainda funciona), por haver um só par "texto alterado" de
   referência: fica folga dos dois lados.
2. **Caminho B: (c′) passa a ser a base** (em vez do texto sem o chrome
   persistente).
3. **"Mais Premium" entra como 14.º marcador** (bloco de manchetes do layout
   de 2019; não muda a separação dos rótulos e reduz os pares consecutivos
   abaixo de 0,90 de 23 para 12).

As variantes (a) (texto completo, limiar 0,80) e (b) (remoção de n-gramas
frequentes) ficam como **histórico documentado: testadas, não adotadas**.

**Implementação.** A delimitação do corpo passou para
`src/semantic_harvester/article_body.py` (sem dependências), usada por
`corpus_redundancy` e `corpus_entities`, ambos com `--texto corpo` por
omissão (`--texto completo` repõe a variante (a); no B, `--texto sem-chrome`
repõe a configuração anterior). No D, capturas com texto mas sem corpo
localizável ficam numa camada própria, `sem_corpo`, fora da Camada 1 e dos
grupos por `digest`; a validação recalcula a similaridade dos pares
rotulados sobre o corpo e põe à parte os que não têm corpo. No B, capturas
sem corpo não contam para a regra de persistência. A amostra rotulada não é
reescrita. 3 testes novos.

**Os 12 pares consecutivos abaixo de 0,90 (com 14 marcadores), todos
explicados:**

| Pares | Causa |
| ---: | --- |
| 4 | Artigo Premium "Exibição de Zivkovic…": umas capturas mostram o aviso Premium, outras o artigo completo desbloqueado (diferença real no que foi arquivado) |
| 4 | Âncora de início numa listagem do título noutro bloco antes do artigo ("Vídeo-árbitro…", "Cristiano Ronaldo quis entrar com o pé direito…", "Yuri Ribeiro…", "Özil recorda palavras de Ronaldo…"); o resto do corpo é igual |
| 1 | Par 29 (página de jogo em direto reescrita depois do fim) — alteração real |
| 1 | "Centro teleguiado de Zivkovic e Jonas…" (0,581): legenda de ~20 palavras; numa captura aparece o endereço do embed do vídeo e um contador ("511 6"), que num corpo tão curto pesam muito |
| 1 | "As 'borlas' do mercado de transferências…" (0,815): contadores numéricos ("8") presentes numa captura e não na outra |
| 1 | "Equipamento do Barcelona…" (0,893): uma manchete rotativa dentro do corpo, vinda de um bloco **"Mais Fotogalerias"** (galerias do layout de 2019), que não está na lista ("Mais Fotos" não corresponde por causa dos limites de palavra) |

**Resultado oficial do Caminho D** (`corpus_redundancy --limiar 0.90`, corpo;
grafo, textos, amostra rotulada e vocabulário inalterados):

| Camada | Capturas |
| --- | ---: |
| Camada 1 — com texto, corpo e `statusCode` 200 | 775 |
| Sem corpo — com texto, sem corpo de artigo localizável | 18 |
| Camada 2 — sem texto, em artigos com alguma captura na Camada 1 | 144 (14 candidatas por `digest`) |
| Não avaliáveis — artigos sem nenhuma captura na Camada 1 | 4 |
| Total | 941 |

- **133 versões textuais distintas** e 642 capturas redundantes nas 775 da
  Camada 1, em 121 artigos: 112 artigos com 1 versão, 8 com 2, 1 com 5 (o
  Zivkovic Premium). O vídeo do Zungu, que a variante (a) dava como 71
  versões em 71 capturas, tem agora 1.
- Pares consecutivos com corpo: 654; mediana 1,000 (variante a: 0,655).
- Validação na amostra: 57 pares comparáveis; 0 de 1 "texto alterado" ≥ 0,90
  e 0 de 56 "mesma versão" < 0,90; à parte, por terem captura sem corpo, os
  pares 1 ("texto alterado", a captura posterior não tem o artigo), 50 e 60
  ("mesma versão", página `/jogos-em-direto/`).
- Das 133 versões, as 9 a mais (artigos com 2 ou mais versões) vêm todas
  dos 12 pares acima: só o par 29 e o Zivkovic Premium correspondem a
  diferenças reais no texto arquivado; as restantes vêm das limitações
  listadas.

**Resultado oficial do Caminho B** (`corpus_entities`, corpo):

| Medida | Antes (sem chrome persistente) | Agora (corpo, c′) |
| --- | ---: | ---: |
| Pares artigo–jogador, regra fraca | 1 427 | 119 |
| Pares artigo–jogador, persistência | 287 | 113 |
| Artigos com jogador, regra fraca / persistência | 116 / 91 | 60 / 58 |
| Pares de artigos com uma só captura com corpo (persistência) | 158 | 31 |
| `clube_coerente` (persistência): sim / nao / sem_tema | 82 / 41 / 164 | 34 / 16 / 63 |

Os 16 pares `nao` foram inspecionados no corpo: 11 são menções legítimas a
jogadores de outros clubes (transferências, antigos jogadores, adversários)
e 5 são falsos positivos — 1 manchete que ficou dentro do corpo (Júlio César
no artigo "A 'incubadora' do Seixal…") e 4 de **homonímia** ("Pêpê" contado
como Pepe por a comparação ignorar acentos; "Moreira de Cónegos", a
localidade; "Fábio Lima", o autor, contado como Lima; Zé Pedro, o músico,
num artigo sobre o Tim). O chrome deixou de ser a fonte principal de erro;
a homonímia, adiada por decisão dos autores, continua.

**Limitações (resultado reportado).**

- **Só 1 par "texto alterado" de referência** na amostra rotulada com corpo
  (o par 29); o limiar 0,90 tem folga dos dois lados, mas a separação foi
  observada com n = 1 desse lado.
- A amostra rotulada cobre 34 artigos (um vídeo com 11 dos 60 pares).
- Âncora de início frágil em páginas onde o título aparece listado noutro
  bloco antes do artigo (4 casos encontrados); bloco "Mais Fotogalerias"
  fora da lista; corpos muito curtos (legendas) sensíveis a contadores e
  embeds; 18 capturas sem corpo.
- As 133 versões são uma contagem por similaridade do corpo extraído, não
  uma verificação de cada versão; o B continua sem avaliação de precisão
  (decisão de âmbito) e com homonímia por resolver.
- Os resultados das variantes (a) e (b) mantêm-se nas secções anteriores
  como histórico; `output/corpus_chrome_*` continua a descrever o corpus de
  127 artigos (variante b, não regenerada).

## RDF dos Caminhos D e B (2026-10-10)

**Objetivo.** Passar a RDF o que até aqui só existia em CSV: a anotação de
redundância do Caminho D (`output/corpus_redundancy.csv`, variante c′,
limiar 0,90) e os temas e entidades do Caminho B
(`output/corpus_entities.csv`, variante c′). Desenho decidido pelo autor;
implementado em `src/semantic_harvester/corpus_redundancy_rdf.py` e
`corpus_entities_rdf.py`, sem pedidos à API.

**Ontologia** (`ontology/semantic_harvester.ttl`, acrescentados sem remover
nada, com `rdfs:label`/`rdfs:comment` em português):
`sdh:versaoDe` (CapturaArquivada → CapturaArquivada) e `sdh:similaridade`
(`xsd:float`, rácio de Jaccard calculado em vírgula flutuante) para o D;
`sdh:Mencao`, `sdh:temMencao` (Artigo → Mencao), `sdh:sobreEntidade` (Mencao
→ EntidadeMencionada), `sdh:capturasComMencao`, `sdh:capturasComTexto`,
`sdh:ocorrencias` (`xsd:nonNegativeInteger`), `sdh:persistente`
(`xsd:boolean`) e `sdh:clubeCoerente` (`xsd:string`: "sim", "nao",
"sem_tema") para o B; `sdh:categoriaTema` e `sdh:valorTema` para o Tema.
`sdh:mencionaEntidade` e `sdh:temTema` mantêm-se e são usados em paralelo com
`Mencao` (relação n-ária: o triplo direto responde a perguntas de um salto;
a `Mencao` guarda as métricas). Não há nó intermédio para o Tema (as linhas
de tema não têm colunas quantitativas) nem propriedade `uma_so_captura`
(derivável de `capturasComTexto = 1`). `capturasComTexto` mantém o nome da
coluna do CSV, embora sob a variante c′ o denominador seja "capturas com
corpo".

**Identidade dos nós.**

- `Artigo` e `CapturaArquivada`: os mesmos URIs de `corpus_articles.ttl`
  (`rdf_mapper.article_uri`/`capture_uri`, chave `originalURL` e
  `(originalURL, tstamp)`), por isso os três Turtle se combinam sem
  conversão.
- `EntidadeMencionada`: um nó por entidade, partilhado entre artigos. Rótulo
  com um só QID no vocabulário (`homonimos == 1`) → **URI da Wikidata**
  (`http://www.wikidata.org/entity/<QID>`), reutilizando a identidade
  externa. Rótulo de homónimos (`homonimos > 1`) → `sdh:entity/<sha256(rotulo)>`:
  a deteção por vocabulário fechado não distingue qual das pessoas é
  mencionada, por isso não se atribui um QID sem fundamento. Também não se
  desambigua por clube: a coluna `clubes` do vocabulário já vem fundida entre
  as pessoas homónimas.
- `Tema`: um nó por (categoria, valor), partilhado entre artigos
  (`sdh:tema/<sha256(categoria|valor)>`), com `categoriaTema`, `valorTema` e
  `rdfs:label` "categoria: valor". **Decisão tomada nesta implementação, não
  discutida antes com o autor** (consistente com a das entidades: permite
  perguntar "todos os artigos deste tema"); fica sinalizada para revisão.
- `Mencao`: uma por par artigo–entidade (`sdh:mencao/<sha256(artigo|rotulo)>`).
- Toda a `EntidadeMencionada` e todo o `Tema` têm `rdfs:label`.

**Camada 2 e capturas sem corpo: sem triplos.** No D só as capturas
redundantes da Camada 1 recebem triplos. As representantes não recebem
nenhum (não há nada anterior para apontar); as capturas `sem_corpo` e as da
Camada 2 também não, porque não têm comparação nem representante
calculados. O critério da Camada 2 (`digest` + `contentLength`) continua
reconstituível por SPARQL a partir de `sdh:digest`/`sdh:contentLength`, já
no grafo desde o M2/M3; representá-lo ao lado da redundância confirmada
esbateria a distinção entre "confirmado" e "nunca verificado".

**Salvaguardas** (acrescentadas na implementação): cada execução verifica
por checksum que `output/corpus_articles.ttl` não muda; artigos ou capturas
referidos que não existam nesse grafo, linhas da Camada 1 com limiar
diferente de 0,9 e entidades ausentes do vocabulário fazem a execução falhar
em vez de gerar RDF inconsistente. Testes: `tests/test_corpus_annotations_rdf.py`
(4), incluindo a verificação de que todos os predicados usados estão
declarados na ontologia.

**Resultado real** (`output/corpus_redundancy_rdf_summary.md`,
`output/corpus_entities_rdf_summary.md`):

| Ficheiro | Triplos | Conteúdo |
| --- | ---: | --- |
| `output/corpus_redundancy.ttl` | 1 284 | 642 capturas redundantes × (`versaoDe` + `similaridade`); 133 representantes, 18 `sem_corpo`, 144 da Camada 2 e 4 não avaliáveis sem triplos |
| `output/corpus_entities.ttl` | 1 703 | 40 nós `Tema` (308 linhas de tema, nos 125 artigos); 82 nós `EntidadeMencionada` (81 com URI da Wikidata, 1 próprio); 119 nós `Mencao` em 60 artigos |

`corpus_articles.ttl` ficou inalterado (13 482 triplos). Os três ficheiros
combinados dão **16 469 triplos**; todos os sujeitos e objetos de `versaoDe`
e todos os artigos com `temTema`/`temMencao` existem no grafo do corpus.
Exemplo de consulta sobre o grafo combinado (entidades com menção
persistente no maior número de artigos): João Félix 6, Bruno Fernandes 5,
Pepe 5, Marvin Zeegelaar 4, Bas Dost 3.

**Exceção dos homónimos, com a contagem real.** O vocabulário tem 3 rótulos
homónimos ("André Silva", "Chico", "Pedro Mendes", 2 QIDs cada) — é uma
propriedade do vocabulário, não do corpus. No `corpus_entities.csv` atual
(c′) só "Pedro Mendes" ocorre, numa linha: o artigo
`…/desporto-universitario/detalhe/AMP/universidade-do-porto-vence-no-xadrez.html`.
Pelo tema (xadrez universitário), é plausível que não se trate de nenhum dos
dois futebolistas do vocabulário — o tipo de caso em que o URI próprio, em
vez de um QID, evita uma afirmação sem fundamento. Não foi verificado.
"André Silva" e "Chico" deixaram de ocorrer quando a deteção passou a
procurar só no corpo do artigo (na versão anterior, sem chrome persistente,
os três somavam 19 linhas).

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

## Alcance temporal do `record.pt` no Arquivo.pt: RSS, homepage e pesquisa por palavra-chave (2026-10-15)

### Motivação

Depois de confirmado o limite 2015–2020 do corpus atual (Caminho A), o autor
pediu para explorar duas vias de alargar a cobertura temporal: (1) o feed RSS
do site, como fonte de descoberta adicional; (2) até onde o `record.pt`
recua no Arquivo.pt, com a esperança inicial de 20–30 anos. Todos os testes
desta secção foram corridos manualmente pelo autor no browser, colando os
URLs pedidos e reportando o JSON devolvido; nada foi integrado no corpus.

### 1. `version_history` do feed RSS: `/rss` e `/rss/` não são pesquisas distintas

Pedir `version_history` para `www.record.pt/rss` e, em separado, para
`www.record.pt/rss/` devolveu as duas vezes o mesmo `estimated_nr_results`
(889) e o mesmo ponto de corte real (`offset=850` com dados, `offset=900`
vazio), com o mesmo `tstamp` mais antigo. Confirmado por inspeção direta:
os `originalURL` devolvidos por uma única pesquisa já vêm misturados, com e
sem barra final — o Arquivo.pt normaliza a barra internamente antes de
calcular o histórico, tal como o achado já documentado em `corpus_rdf.py`
sobre variantes cosméticas de `originalURL` num único `version_history`.
**Correção a uma recomendação anterior:** não é preciso pesquisar as duas
formas em separado e juntar os resultados à mão; uma só pesquisa já basta.

### 2. Alcance do feed RSS: só a partir de 2018-08-06

Com `from=2015&to=2020`, a última página com dados (`offset=850`) tem como
último item `tstamp=20180806190610`; `offset=900` vem vazio, confirmando o
fim real da paginação (não só o `next_page`, que nesta API nem sempre é de
confiar — ver Experiência 1). **O feed RSS não tem nenhuma captura antes de
6 de agosto de 2018.** Não serve para cobrir 2015–2017; o único ganho real
seria 2020–2026, período ainda não coberto pela descoberta atual.

### 3. A homepage está arquivada desde 1998 — mas essa captura não é o jornal

`version_history` de `www.record.pt` (sem `from`/`to`) alcança `offset=4900`
como última página com dados, com `tstamp` mais antigo `19981202152653`
(2 de dezembro de 1998). Testado o conteúdo dessa captura via pesquisa por
palavra-chave (`q=record&siteSearch=record.pt&from=1998&to=1999`): o único
resultado tem título **"Servidor WWW Virtual da Esoterica"**, snippet
"Esoterica's virtual web server directory... webmaster@esoterica.pt", e
`collection: "IA"` (não as coleções próprias do Arquivo.pt vistas noutras
experiências). **Não é o jornal — é a página de um domínio estacionado num
serviço de alojamento genérico.** A data de 1998 não conta como início do
Record Online.

### 4. A pesquisa por palavra-chave não vem ordenada por data

Achado metodológico, confirmado por contradição direta: com
`q=futebol&siteSearch=record.pt&from=1998&to=2005`, a página 1 tinha como
último item `tstamp=20010914172917` (set. 2001); a última página real da
mesma pesquisa (`offset=40480`) devolveu `tstamp=20020125061748` (jan.
2002) — **mais recente**, não mais antigo. Se a ordenação fosse
cronológica descendente, como no `version_history`, isto seria impossível.
**Consequência prática:** para encontrar o extremo temporal de uma
pesquisa por palavra-chave, não se pode confiar na última página de uma
janela larga — é preciso estreitar `from`/`to` diretamente e repetir.

### 5. Origem real do Record Online: 1999

Sequência de pesquisas por palavra-chave, estreitando `from`/`to` a cada
passo (todas com `siteSearch=record.pt`):

| Janela | Palavra | Resultado |
| --- | --- | --- |
| 1998–1999 | `futebol`, `jogo`, `notícia` | 0 resultados |
| 1998–1999 | `record` | 1 resultado: placeholder Esoterica (`tstamp=19990125091626`) |
| 1998–2001 | `futebol` | "Record On-Line" genuíno, `tstamp=20000707011057`, `record.pt/tn1cs.asp?nid=133349` |
| 1999–2000 | `record` | "Record On-Line" genuíno em `tstamp=19991128140726`; Esoterica ainda em `19990125091626` |
| 1999-02 a 1999-11 | `record` | "Record On-Line" genuíno desde `tstamp=19990829110932` (29 ago.); Esoterica ainda em `tstamp=19990208010000` (8 fev.) |

Os itens genuínos têm título "Record On-Line", um menu de modalidades no
`snippet` (Futebol, Andebol, Atletismo, ...) e URLs no formato
`record.pt/tn0cs.asp?nid=<id>` ou `record.pt/tn1cs.asp?nid=<id>`.
**Conclusão:** a transição de domínio estacionado para jornal real
aconteceu entre 8 de fevereiro e 29 de agosto de 1999. Decisão do autor:
não apertar mais a data exata (retornos cada vez menores); fica registado
**1999** como o ano real de nascimento do Record Online no Arquivo.pt, não
1998 (artefacto do domínio estacionado) nem a janela 2015–2020 do corpus
atual.

Nota técnica: a API aceita `from`/`to` com mais precisão que o ano —
`request_parameters` devolveu `"from": "19990000000000"` para um `from=1999`
pedido, e aceitou sem erro `from=19990200` (um prefixo de timestamp mais
longo), o que permitiu apertar a janela até ao mês.

### 6. Consequências para trabalho futuro (nada implementado nesta sessão)

- **Novo critério de exclusão necessário**, análogo ao `"Object moved"` já
  usado em `corpus_classification.py`: título exato
  `"Servidor WWW Virtual da Esoterica"` identifica uma página de domínio
  estacionado, não conteúdo editorial.
- **Terceiro esquema de URL legado a reconhecer**: `tn0cs.asp?nid=<id>` /
  `tn1cs.asp?nid=<id>` (visto em 1999–2000), distinto do `interior.aspx?
  content_id=...` do "site antigo" já tratado em `url_identity.py` e do
  `/detalhe/<slug>` do site atual. Se o corpus for alargado a 1999–2015, a
  identidade do artigo e a classificação têm de reconhecer também este
  padrão.
- O feed RSS (ponto 2) só vale a pena como fonte de descoberta adicional
  para 2020–2026; para 1999–2015 a via é a pesquisa por palavra-chave já
  usada no Caminho A, com as duas ressalvas dos pontos 1 e 4 em conta.

## Protótipo ligado aos Caminhos D e B (2026-10-15)

**Objetivo.** `navigation_prototype.py` só lia `output/corpus_articles.ttl`
(Caminho A); os dados de D (redundância) e B (temas/entidades), já em RDF
desde 2026-10-10 ("RDF dos Caminhos D e B"), não entravam no protótipo.
Implementado: quando `output/corpus_redundancy.ttl` e
`output/corpus_entities.ttl` existem, juntam-se ao mesmo grafo em memória
(os URIs de `Artigo`/`CapturaArquivada` já são partilhados, sem conversão,
tal como documentado nessa secção). Sem esses dois ficheiros, o protótipo
continua a gerar-se só com o Caminho A — testado explicitamente
(`test_generate_without_db_files_skips_extra_pages`).

**O que mudou:**

- `historico_artigo.rq` passa a devolver, por captura, `representanteTstamp`
  e `similaridade` quando essa captura está marcada `sdh:versaoDe` de outra
  (Caminho D); a tabela de histórico de cada artigo ganha uma coluna
  "Redundância (Caminho D)". Nota: uma captura sem essas colunas pode ser
  representante **ou** não ter sido avaliada por D (`sem_corpo`, Camada 2) —
  o grafo não distingue os dois casos, só o `corpus_redundancy.csv` o faz.
- Duas queries novas por artigo (`temas_artigo.rq`, `mencoes_artigo.rq`) e
  duas secções novas na página do artigo ("Temas", "Entidades mencionadas",
  só aparecem quando há dados).
- Duas queries globais (`temas_resumo.rq`, `entidades_resumo.rq`,
  `redundancia_resumo.rq`) e duas páginas novas, `temas.html` e
  `entidades.html`, ligadas do índice quando não vazias.

**Resultado real, correndo contra o corpus atual** (125 artigos):
`temas: 40; entidades: 82; capturas redundantes: 642` — os mesmos números já
publicados em "RDF dos Caminhos D e B" (40 nós `Tema`, 82 `EntidadeMencionada`,
642 capturas redundantes) e a mesma ordenação de entidades por persistência
já ali reportada (João Félix 6, Bruno Fernandes 5, Pepe 5, Marvin Zeegelaar 4,
Bas Dost 3), confirmando que a ligação lê os dados certos.

Testes: 5 novos em `tests/test_navigation_prototype.py` (as três queries
novas com um grafo sintético D+B; geração completa com e sem os ficheiros de
D/B). Suite completa: **190 testes, todos a passar**.

## Política de texto para artigos novos: só a captura mais antiga (implementada, não executada; 2026-10-15)

### Decisão

Para alargar o corpus sem descarregar o texto de todas as capturas de cada
artigo novo:

- O `version_history` continua a ser paginado até ao fim;
  `estimated_nr_results` não é usado para nada.
- `download_extracted_text` só é chamado para a captura **mais antiga** de
  cada artigo (menor `tstamp` por `originalURL`, depois da normalização das
  variantes cosméticas de URL).
- As outras capturas entram no manifesto e no grafo (`CapturaArquivada`, sem
  `TextoExtraido`) com `text_requested = False`: **"não pedido"**, que não se
  confunde com um 404 nem com um timeout.
- Se o texto da captura mais antiga falhar, conta como falha e **não** se
  tenta a seguinte (decisão do Jorge: só a primeira).
- A descoberta continua a ser a pesquisa por palavra-chave com
  `siteSearch=record.pt`; o RSS não é usado (ver a secção anterior).

### Implementação

- `history_pipeline.build_manifest_records(..., text_policy=...)` passa a
  exigir a política explicitamente: `TEXT_POLICY_FIRST` (`"primeira"`) ou
  `TEXT_POLICY_ALL` (`"todas"`); não há valor por omissão silencioso.
- `corpus_rdf.build_corpus_graph` (recolha online, retomável) usa
  `"primeira"`. Como salta os artigos já em `output/corpus_rdf_report.csv`, a
  política só se aplica a artigos **novos**; os 125 do corpus atual não são
  reprocessados.
- `corpus_rdf.rebuild_graph_offline` (`--rebuild-offline`) e o M3
  (`run_history_pipeline`) usam `"todas"`: a reconstrução do corpus histórico
  continua a usar o texto de todas as capturas em cache.
- As falhas de texto (`texts_failed` no relatório, `text_failures` nas
  métricas do M3) passam a contar só capturas **com pedido**. O número de
  "não pedidos" é derivado (`captures_used − descarregados − reutilizados −
  falhados`) em vez de ser uma coluna nova, para não mudar o esquema do
  relatório retomável, que é escrito em modo append; o resumo
  (`corpus_rdf_summary.md`) ganha uma linha para ele.

### Testes (offline, fixtures sintéticas)

Só a mais antiga é pedida, mesmo com o `version_history` fora de ordem
cronológica; as outras ficam "não pedido" e não contam como falha; 404 na
mais antiga conta como falha, sem tentar a seguinte; política desconhecida
é rejeitada; a recolha online de um artigo novo pede um só texto e não toca
no artigo histórico já no relatório, com o esquema do relatório inalterado;
a reconstrução offline continua a usar o texto de uma captura que não é a
mais antiga. Suite completa: 190 testes OK.

### O que não foi feito

Nada foi corrido contra a API real e o corpus de 125 artigos não foi
regenerado. Correr a política sobre dados reais, ou alargar o corpus com ela,
é uma decisão à parte.

## Âmbito da ontologia OWL: subclasses de Tema (2026-10-18)

**Decisão (reunião com o orientador):** a ontologia fica mesmo em RDF/OWL,
não uma hierarquia de pastas — resolve a tensão já identificada entre as
duas abordagens.

**Âmbito definido e implementado**: os 4 valores de `categoriaTema` já em
uso em `corpus_entities.csv` (`secao`, `modalidade`, `competicao`, `clube`)
passam a ser subclasses formais de `sdh:Tema` — `sdh:Secao`, `sdh:Modalidade`,
`sdh:Competicao`, `sdh:Clube` — declaradas `owl:AllDisjointClasses` (um Tema
nunca é duas categorias ao mesmo tempo, já verdade nos dados). Cada nó `Tema`
passa a ter, além de `a sdh:Tema`, também `a` a subclasse específica
(`corpus_entities_rdf.py`); `categoriaTema`/`valorTema` mantêm-se, por
continuidade com o CSV. Uma categoria fora destas 4 falha a execução em vez
de gerar um Tema sem subclasse. Também declaradas `owl:FunctionalProperty`
em `sdh:originalURL` e `sdh:temTextoExtraido` — já eram verdade na
construção do grafo, agora formalizadas para um reasoner poder verificar.

**O que ficou fora deste âmbito, por decisão consciente**: restrições de
cardinalidade (`owl:Restriction`) além das duas propriedades funcionais, e
qualquer subclasse de `EntidadeMencionada` (ex.: por modalidade) — fica para
quando o vocabulário de entidades for alargado a outras modalidades, que
ainda não está feito.

Testes: 2 novos em `tests/test_corpus_annotations_rdf.py` (a subclasse
específica aparece no grafo; uma categoria desconhecida falha). Suite
completa: **191 testes, todos a passar**. Nada foi corrido contra a API.

## Corpo do artigo no HTML original do Record: alternativa às âncoras da c′? (2026-10-18)

### Motivação

A variante c′ (`article_body.py`) nunca vê o HTML: trabalha sobre o
`linkToExtractedText` do Arquivo.pt, já aplanado, e delimita o corpo por
âncoras literais (título repetido, depois o primeiro dos 14 marcadores de
chrome). Pergunta: o HTML em bruto (`linkToOriginalFile`, URL `…id_/…`) tem
uma marcação fiável só do corpo (`<article>`, `<div>` com classe/id estável,
`itemprop="articleBody"` ou JSON-LD) que sirva de alternativa mais robusta?
Nada foi mudado em `article_body.py`; esta secção só recolhe dados para a
decisão.

### 1. Prova de conceito: 7 capturas dos casos difíceis conhecidos

Pedidas pelo `linkToOriginalFile` (7 pedidos, todos HTTP 200), guardadas em
`data/raw/original_html/` (não versionado). Escolhidas para cobrir os casos
já registados neste ficheiro: um artigo normal de 2017 (entrevista Daniel
Ramos, `20171001032744`) e um de 2019 (Carlos Xistra, `20191102192301`); o
artigo **Premium** sem corpo (crónica Boavista-Moreirense, `20171127045348`);
os dois lados do **par 29**, página de jogo em direto reescrita
(`20190429170841` e `20190430202203`); e duas páginas **AMP** (Jorge Jesus /
Pini Zahavi, `20190228191520`; Nike Pegasus, `20190322194121`). Inspeção com
o `html.parser` da biblioteca padrão (sem BeautifulSoup, que não está no
ambiente).

**Não há uma marcação única.** Nenhuma das 7 tem `itemprop="articleBody"`.
Todas têm um bloco JSON-LD `NewsArticle`, mas sem `articleBody` (traz
`headline`, `description`, `datePublished`, `keywords`, …). As tags
`<article>` existem às dezenas, mas marcam os cartões de manchetes, não o
corpo. O que existe é **um contentor diferente por template**, igual dentro
de cada template:

| Template | Contentor do corpo | Capturas |
| --- | --- | --- |
| site 2017 | `div.article-body` | normal 2017 |
| site 2019 | `div.text_container` | normal 2019, direto (as duas) |
| AMP (2019) | `div.bodybox` | Jorge Jesus, Nike |

**Comparação com a c′** (Jaccard sobre conjuntos de palavras, texto do
contentor vs. corpo da c′ sobre o texto extraído da mesma captura):

| Captura | Palavras HTML / c′ | Jaccard | Observação |
| --- | ---: | ---: | --- |
| normal 2017 | 137 / 154 | 0,97 | a c′ só acrescenta título, lead e crédito da foto |
| AMP Nike | 134 / 135 | 1,00 | idênticos |
| direto, intervalo | 1594 / 1775 | 0,92 | a c′ inclui o formulário "Enviar o artigo…" e 4 manchetes de outras notícias |
| direto, fim | 2191 / 2298 | 0,96 | a c′ inclui o formulário "Enviar o artigo…" |
| **Premium 2017** | 0 / 113 | 0,00 | sem `div.article-body`; ver abaixo |
| normal 2019 | 233 / — | — | captura da Camada 2: sem texto extraído |
| AMP Jorge Jesus | 316 / — | — | captura da Camada 2: sem texto extraído |

- **Premium: falso positivo real da c′.** No HTML, o `div.article-body` não
  existe e aparece `div.article-premium` com o aviso "Esta notícia é
  exclusiva para Assinantes Record Premium…": a página diz explicitamente que
  não tem corpo. A c′ devolve `found=True` com 113 palavras — título, lead e
  o texto do paywall —, tratando o aviso como corpo.
- **Sinal estruturado de paywall, só em 2019.** O JSON-LD do template de
  2019 declara `isAccessibleForFree` e `hasPart` com
  `cssSelector: ".paywall"` (no artigo normal: `True`). Não existe em 2017 nem
  nas AMP; nesta amostra não havia nenhum Premium de 2019 para ver o valor
  `False`.
- **Camada 2.** As duas capturas sem texto extraído têm, no HTML original, o
  corpo completo (233 e 316 palavras).
- O par 29 continua "texto alterado" pelo HTML: o relato é o conteúdo real
  da página e difere entre as duas capturas.

**Ressalva.** São 7 capturas escolhidas a dedo: prova de conceito, não
medição do corpus. Não se sabe ainda quantos templates há no corpus, como é
o site anterior (`interior.aspx`, `tn0cs.asp`) nem o Premium de 2019. O HTML
tem 120–340 KB por captura e não está em cache: usá-lo exige descarregá-lo.

### 2. Amostra alargada: 251 capturas (templates, Premium, Camada 2)

251 pedidos ao `linkToOriginalFile`, todos HTTP 200, guardados em
`data/raw/original_html/` com o resultado por captura em
`data/raw/original_html/html_body_sample.csv` (nada disto é versionado; os
scripts da verificação estão em `data/raw/original_html/_scripts/`). Três
grupos, com sobreposição: **template** — 1 captura por artigo, a mais antiga
com status 200 e texto em cache (125); **Camada 2** — todas as capturas com
status 200 e sem texto extraído (113: as 110 da `2_sem_texto` e 3 "não
avaliáveis"; as 31 de 301/302 e as 2 de 404 não têm corpo a recuperar);
**`sem_corpo`** — as 18 em que a c′ não encontrou corpo.

**Templates (1 por artigo, 125).** 109 têm um dos três contentores da prova
de conceito: `article-body` 42 (2017–2018), `text_container` 39
(2018–2019), `bodybox` 28 (AMP, 2017–2019). As 16 sem nenhum deles:
5 Premium (`article-premium`), 8 páginas multimédia (vídeos e galerias,
sem corpo de texto ou com uma descrição curta em `noticia_text`), 1 crónica
de opinião (`article-opiniao-content`, quarto template), 1 AMP antiga de
2017 (`div.mainBox`, quinto template) e 1 página `jogos-em-direto/live`.
Nenhum template novo em notícias normais fora destes.

**Concordância com a c′** (template com contentor e c′ com corpo, sem
Premium: 98 capturas). Jaccard mediano 0,893 (mínimo 0,237); 34 com
≥ 0,95 e 37 abaixo de 0,8. Por contentor: `article-body` mediana 0,953
(40), `bodybox` 0,875 (26), `text_container` 0,728 (32). Os 37 casos abaixo
de 0,8 dividem-se assim:

- 25 com **texto a mais na c′** (`text_container` 23, `article-body` 2): nas
  notícias de 2018–2019 as palavras só da c′ são o chrome do template — o
  formulário "O meu email / Destinatários / Enviar", o aviso de login, "Deixe
  o seu comentário", "Temas" —, que em notícias curtas puxa o Jaccard para
  baixo; nas fotogalerias, a lista "Mais Fotogalerias", que não é um dos 14
  marcadores. Aqui o HTML é mais limpo.
- 12 com **chrome dentro do contentor HTML** (todos `bodybox`): em algumas
  versões AMP o `div.bodybox` engloba "O Record recomenda para si" e
  "Últimas Notícias"; a c′ corta bem nesses marcadores. Aqui o HTML é pior.

21 páginas têm dois `div.text_container`; em todas o segundo está aninhado no
primeiro e tem o mesmo texto, por isso ler o primeiro basta.

**Premium.** Dois sinais estruturais, um por geração do site:
`div.article-premium` (2017–2018) e `div.container_assinatura` (2018–2020,
com `premiumBox_header` e o teaser em `p.fadeoutPremium`). Juntos marcam 26
capturas de 12 artigos, exatamente as 26 em que o HTML tem o aviso "exclusiva
para assinantes" — nenhuma página com sinal sem aviso, nenhuma com aviso sem
sinal. **O JSON-LD não generaliza:** `isAccessibleForFree` só existe a partir
de 2019 e marca 5 das 26 (`False` nas 5; `True` em 9 gratuitas); 3 Premium de
2018–2019 com `container_assinatura` não o têm. **Premium de 2019 encontrado:**
"Yony González é reforço para o Benfica" (`20191114000138`), com
`isAccessibleForFree: False` e `hasPart` `{cssSelector: ".paywall",
isAccessibleForFree: False}`; o `div.text_container.paywall` só tem o teaser
(32 palavras). A c′ deu `found=True` em 11 das 13 capturas Premium com texto em
cache — o mesmo falso positivo da prova de conceito, também em 2019. Um artigo
(Zivkovic/Drulo) tem 6 de 8 capturas Premium e 2 não (páginas sem o artigo).

**Camada 2 (113 capturas, 46 artigos).** O HTML original recupera o corpo
em **55 capturas de 33 artigos** (`article-body` 33, `bodybox` 11,
`text_container` 6, `article-opiniao-content` 5; mediana 222 palavras,
mínimo 43); 2 desses 33 artigos não tinham nenhuma captura com corpo
comparável. As restantes 58: 12 Premium (sem corpo, com sinal explícito),
29 multimédia só com descrição curta (`noticia_text`, 2 artigos), 16
multimédia sem texto (vídeo/galeria, 4 artigos) e 1 `jogos-em-direto/live`.

**`sem_corpo` da c′ (18).** O HTML encontra corpo em 2: a AMP de 2017
(`mainBox`, 347 palavras, onde a c′ não localiza o título) e uma notícia de
2019 (`text_container`, 326 palavras). Nas outras 16 os dois métodos
concordam que não há corpo: 8 `jogos-em-direto/live`, 3 multimédia sem
texto, 2 Premium e 3 páginas sem o artigo (só menu e "O Record recomenda para
si").

**Achado lateral: texto extraído de outra captura.** Em 2 das 136 capturas
com texto em cache e HTML, mais de 10% das palavras do texto em cache não
existem em lado nenhum do HTML da mesma captura (27% e 11%). No caso
verificado (Yuri Ribeiro, `20180717172856`), o HTML (`Memento-Datetime`
exatamente 17:28:56, sem redirecionamento) é a versão "(em atualização)",
mas o ficheiro em cache — descarregado a 18 set — é byte a byte igual ao
texto da captura seguinte (`20180717181217`, `digest` diferente). O mesmo
pedido ao `textextracted`, feito agora, devolve a versão curta, coerente com
o HTML. A causa não foi apurada; fica registado que o `textextracted` pode,
pelo menos às vezes, ter devolvido o texto de uma captura vizinha.

### 3. Leitura (sem decisão)

- **A favor do HTML:** deteta o Premium sem ambiguidade em todas as gerações
  vistas (a c′ não); dá corpo sem o chrome do template de 2018–2019; recupera
  corpo em 55 capturas da Camada 2 e em 2 `sem_corpo`; não depende de o título
  se repetir nem da lista de marcadores.
- **Contra ou por resolver:** precisa de um seletor por template (5 vistos,
  mais os de multimédia); o `bodybox` de algumas AMP traz chrome e
  precisaria dos marcadores da c′ para cortar; exige descarregar o HTML de
  cada captura (cerca de 120–340 KB, contra o texto já em cache).
- A recuperação da Camada 2 e a deteção do Premium valem por si,
  independentemente de qual for o método principal.
- Os números são desta amostra (251 capturas, 125 artigos, 2017–2020 pela
  captura mais antiga); o site anterior a 2017 não está representado.

## Descoberta de artigos: limite da TextSearch e páginas de secção (2026-10-19)

### Motivação

Antes de decidir como alargar a descoberta de artigos (por exemplo, divisão
recursiva de datas ou descoberta pelas páginas de secção), duas perguntas de
facto: (1) a TextSearch trava perto de 2000 resultados por pesquisa?
(2) com que frequência estão arquivadas as páginas de secção por modalidade,
e quanto do que publicam é visível nas capturas? Pedidos reais à API; nada
mudou no código de produção nem no corpus. JSON e HTML em bruto em
`data/raw/api_diagnostics/limite_2026-10-19/` e
`data/raw/api_diagnostics/seccoes_2026-10-19/`; scripts e logs em
`data/raw/api_diagnostics/_scripts_2026-10-19/` (não versionados).

### 1. Limite de resultados da TextSearch: não há travão perto de 2000

Pesquisas `q=futebol` e `q=Benfica`, `siteSearch=record.pt`, `maxItems=500`,
sem datas e com `from=19990101000000&to=20261231235959`. Paginação por
`offset`, de 500 em 500, seguindo a convenção do próprio `next_page`.

- **Tamanho real da página.** A API normaliza `maxItems` para 500 e aplica por
  omissão `dedupField=url`, `dedupValue=2` (até 2 capturas por URL): uma
  página traz cerca de 500 URLs distintos mas 550–800 itens (ex.: 718 itens,
  497 URLs na primeira página de "futebol"). "Página incompleta" mede-se,
  portanto, em URLs, não em itens.
- **Paginação contínua até `offset=20000`** (teto de segurança do script) nas
  quatro combinações, sempre com cerca de 500 URLs novos por página e zero
  repetidos das páginas anteriores: 20 324 URLs únicos para "futebol" e
  20 461 para "Benfica", iguais com e sem datas.
- **Fim real, por sondagens e bisseção com passo de 500:**

| Termo | Última página com dados | Primeira página vazia | `estimated_nr_results` |
| --- | --- | --- | ---: |
| futebol | `offset=826000` (436 URLs) | `offset=826500` | 2 613 366 |
| Benfica | `offset=810000` (143 URLs) | `offset=810500` | 2 460 613 |

  A mesma fronteira com e sem o intervalo de datas. Isto dá cerca de 826 mil
  e 810 mil URLs alcançáveis — cerca de um terço do `estimated_nr_results`.
  Nas sondagens de `offset` 50 000, 100 000, 200 000 e 500 000 os resultados
  continuam a ser todos do `record.pt` e nenhum repete os de 0–20 000; em
  `offset=500000` aparecem já capturas de 2001–2007. Ressalva: entre 20 000
  e o fim só foram pedidos os offsets da bisseção; o total assume que não
  há páginas vazias pelo meio.
- **`next_page` não marca o fim:** continua presente em páginas vazias (até
  `offset=2600000`, o mais alto pedido). O sinal fiável foi página com menos
  de 500 URLs seguida de página vazia.

### 2. Páginas de secção por modalidade: andebol, judo, natação

URLs confirmados: `https://www.record.pt/modalidades/andebol`, `.../judo`,
`.../natacao` (secções presentes nos URLs dos artigos do corpus). O
`versionHistory` (pedido com `maxItems=500`, aceite) devolve juntas as
variantes com e sem barra final, com `//` e com `http://`; paginado até ao
fim.

| Secção | Capturas | Mais antiga | Mais recente | Por ano |
| --- | ---: | --- | --- | --- |
| andebol | 919 | 2018-08-06 | 2025-12-23 | 2018: 386 · 2019: 383 · 2020: 134 · 2021: 3 · 2022: 3 · 2023: 2 · 2024: 1 · 2025: 7 |
| judo | 919 | 2018-08-06 | 2025-12-19 | igual ao andebol |
| natação | 918 | 2018-08-06 | 2025-12-19 | 2018: 385 · 2019: 383 · 2020: 134 · 2021: 3 · 2022: 3 · 2023: 3 · 2024: 1 · 2025: 6 |

- **Espaçamento.** Intervalo mediano entre capturas consecutivas de 0,98 dias
  (Q1 0,08, Q3 1,00) nas três: praticamente diário de agosto de 2018 a meados
  de 2020, por vezes várias por dia. Depois, 12–13 intervalos acima de 30
  dias, o maior de 582 dias (2024-01-28 → 2025-09-01).
- **Mesmo calendário nas três secções:** 650 dos 651 dias com captura de
  andebol têm também captura de judo, com `tstamp` desfasados de minutos —
  são recolhas do site inteiro, não da secção. A mais antiga (2018-08-06)
  coincide com o início do feed RSS (ver "Alcance temporal do `record.pt`").
  Antes disso não há nada para estes URLs.
- `statusCode` 200 em 904–906 capturas por secção; 12–13 de 302 e 1–2 de 404.

**Artigos listados (andebol).** Links `…/detalhe/…` extraídos do HTML
original de capturas escolhidas:

- Cada captura lista 24–28 artigos de andebol (59–75 links `/detalhe/` no
  total da página).
- Capturas vizinhas: 2018-08-06 → 2018-08-07, 0 artigos de andebol novos
  (26 de 26 em comum); 2019-03-15 → 2019-03-16, 2 novos (25 em comum).
- Capturas afastadas (221 dias, 360 dias, cerca de 5 anos): 0 artigos de
  andebol em comum.
- **22 dias seguidos** (uma captura por dia, 2019-03-15 a 2019-04-05): 67
  artigos de andebol distintos, 1,9 novos por dia em média (máximo 5). Os 16
  artigos que entraram e saíram dentro da janela ficaram listados 10–15 dias
  (mediana 12); por a janela ter só 22 dias, a medida tende a subestimar a
  permanência.

**Leitura (sem decisão).** Em 2018–2020, com captura quase diária e cada
artigo listado cerca de 12 dias, as capturas de uma secção cobrem
praticamente tudo o que ela publicou; fora dessa janela (1–7 capturas por
ano) quase tudo escapa. A TextSearch, por seu lado, não trava em 2000: o
alcance é da ordem de centenas de milhares de URLs por termo genérico.

## Alcance real da pesquisa por palavra-chave e das páginas de secção (2026-10-19)

**Execução real, numa sessão local com acesso à API** (este ambiente remoto
tem `arquivo.pt` bloqueado pela política de rede do sandbox — ver
`docs/PROJECT_STATUS.md`, "Nota operacional"). Motivação: saber se existe um
limite de 2000 resultados por pesquisa e se as páginas de secção por
modalidade (`record.pt/modalidades/<nome>`) servem como fonte de descoberta
alternativa à pesquisa por palavra-chave, para alargar o corpus do Caminho A
além da janela 2015–2020.

### 1. Não há limite de 2000 resultados

Pesquisas com os termos de alto volume `futebol` e `Benfica`,
`siteSearch=record.pt`, `maxItems=500`, testadas sem restrição de datas e
com `from=1999&to=2026` (as duas variantes dão a mesma fronteira). Paginação
contínua por `offset` até 20 000 devolveu 20 324 URLs únicos para `futebol`
e 20 461 para `Benfica`, sem nenhum URL repetido — já overdetermina que não
há parede a 2000. A partir daí, sondagem por bisseção encontrou o fim real
de cada pesquisa:

| Termo | Última página com dados | Primeira página vazia | URLs alcançáveis (aprox.) | `estimated_nr_results` |
| --- | --- | --- | ---: | ---: |
| `futebol` | `offset=826000` (436 URLs) | `offset=826500` | ~826 400 | 2 613 366 |
| `Benfica` | `offset=810000` (143 URLs) | `offset=810500` | ~810 100 | 2 460 613 |

**~826 mil URLs alcançáveis para "futebol", ~810 mil para "Benfica" — não há
parede nenhuma a 2000.** Ressalva do autor da investigação: fora do
intervalo 0–20 000 só se verificaram os pontos da bisseção, não cada offset;
o total aproximado assume que não há páginas vazias isoladas entre esses
pontos.

**Confirmação de que `next_page` e `estimated_nr_results` continuam a não
ser sinais fiáveis**, agora também a esta escala: `next_page` continua
presente mesmo em páginas já vazias (verificado até `offset=2600000`) — não
serve para detetar o fim; o sinal fiável é uma página incompleta seguida de
uma vazia. `estimated_nr_results` também não serve como contagem: é
consistentemente **cerca de 3× o valor real** (2 613 366 vs. ~826 400 para
`futebol`; 2 460 613 vs. ~810 100 para `Benfica`), não apenas "pouco
fiável" como já registado nas Experiências 1–3. Achado adicional sobre
deduplicação: sem `dedupField`/`dedupValue` explícitos a API aplica por
omissão `dedupValue=2` (até 2 capturas por URL), por isso `maxItems=500`
devolve ~500 URLs únicos mas 550–800 itens brutos.

### 2. Páginas de secção: só cobrem bem 2018–meados de 2020

Teste concreto sobre três secções de modalidade (`record.pt/modalidades/
{andebol,judo,natacao}`), pedindo o `version_history` completo de cada URL,
paginado até ao fim:

| Secção | Capturas | Mais antiga | Mais recente | Intervalo mediano |
| --- | ---: | --- | --- | --- |
| andebol | 919 | 2018-08-06 | 2025-12-23 | 0,98 dias |
| judo | 919 | 2018-08-06 | 2025-12-19 | 0,98 dias |
| natação | 918 | 2018-08-06 | 2025-12-19 | 0,98 dias |

As três secções coincidem em 650 dos 651 dias cobertos, com minutos de
diferença entre si — não é uma recolha dedicada à secção, é o crawl do site
inteiro do Arquivo.pt nessa janela, visível em qualquer URL de secção. Um
teste de 22 dias consecutivos (15 de março a 5 de abril de 2019) sobre as
capturas de `andebol` confirma a granularidade real nessa janela: 67
artigos distintos, com uma média de 1,9 novos artigos por dia (máximo 5) —
praticamente diário. Fora dessa janela a cobertura cai para 1 a 7 capturas
por ano, com lacunas de até 582 dias (ex.: 2024-01 a 2025-09).

**Conclusão: as páginas de secção só servem bem para 2018–meados de 2020
(crawl diário do site inteiro nessa janela); fora disso ficam dispersas —
não chegam para cobrir 1999–2026.**

### Decisão

- Abandonar a divisão recursiva de pesquisas por data — não há parede de
  2000 resultados que a justifique.
- Abandonar as páginas de secção como método principal de descoberta — só
  cobrem bem uma janela de ~2 anos já parcialmente coberta pela amostra
  atual.
- Alargar a lista de termos da Fase 1 (`corpus_phase1.py`) com nomes de
  modalidade e competição diretamente, mantendo o mesmo método já validado
  (pesquisa por palavra-chave, `siteSearch=record.pt`), com `from=1999` e
  `to=2026` em vez de `2015`/`2020`. Ver "Download do HTML em bruto da
  captura mais antiga e lista alargada de termos" abaixo para a lista exata
  e o que ficou implementado.

## HTML em bruto como alternativa à heurística do corpo do artigo (2026-10-19)

**Investigação, numa sessão local com acesso à API; só decisão de design,
nada disto está implementado.** Motivação: saber se o Record marca o corpo
do artigo de forma fiável no HTML em bruto (`linkToOriginalFile`, distinto
de `linkToExtractedText`, já usado), como alternativa ou complemento à
heurística de âncoras literais (variante c′, `article_body.py`) usada em D
e B.

### Prova de conceito (7 capturas)

Amostra deliberada: a crónica Premium (Boavista–Moreirense), as duas
páginas do "par 29" (FC Porto–Chelsea, direto), 2 páginas AMP (Jorge
Jesus/Pini Zahavi e Nike Pegasus) e 2 artigos normais (2017 e 2019); os 7 pedidos devolveram 200.

- Nenhuma tem `itemprop="articleBody"`; há JSON-LD em todas, mas sem a
  propriedade `articleBody` (só `headline`, `datePublished`, `keywords`).
- Contentores do corpo variam por geração do site: `article-body`/
  `noticia-content` (2017), `text_container`/`mainTexto` (2019),
  `bodybox` (AMP).
- No artigo Premium, `.article-body` é substituído por
  `.article-premium` (aviso de paywall) — a heurística atual dá **falso
  positivo**: encontra corpo (113 palavras), tratando o aviso como o texto
  do artigo.
- Na página AMP, o Jaccard entre os dois métodos (heurística vs.
  contentor HTML) é 1,00.

### Amostra maior (251 capturas: 1 por artigo nos 125 artigos, mais Camada 2 e `sem_corpo`)

- **Templates**: 109 dos 125 artigos têm um dos três contentores já vistos
  (`article-body` em 42, `text_container` em 39, `bodybox`/AMP em 28). Os 16
  restantes: 5 Premium, 8 páginas multimédia, 1 crónica de opinião
  (`article-opiniao-content`), 1 AMP antiga de 2017 (`mainBox`) e 1 página
  `jogos-em-direto`/direto.
- **Concordância** (98 capturas comparáveis, sem Premium): Jaccard mediano
  0,893; 37 capturas abaixo de 0,8 — em 25 delas o HTML é mais limpo (a
  heurística inclui chrome do layout de 2018–19), nas outras 12 o HTML é
  pior (todas AMP: `bodybox` inclui blocos como "O Record recomenda para
  si"/"Últimas Notícias").
- **Deteção de Premium generaliza**: um sinal estrutural no HTML
  (`article-premium` desde 2017–18, `container_assinatura` desde 2018–20)
  acerta em 26 de 26 capturas Premium testadas; `isAccessibleForFree` do
  JSON-LD só existe desde 2019 e só identifica 5 das 26. A heurística atual
  (âncoras de texto) erra 11 de 13 capturas Premium que têm texto em cache.
- **Recuperação na Camada 2** (capturas sem texto em cache: 113 capturas,
  46 artigos): o HTML em bruto recupera corpo em 55 capturas de 33 artigos
  (mediana 222 palavras, mínimo 43); em 2 desses artigos é a única captura
  com corpo disponível.
- **Achado lateral**: em 2 das 136 capturas com texto em cache e HTML
  disponíveis, o texto em cache não corresponde ao HTML da mesma captura.
  Um caso confirmado (Yuri Ribeiro, `tstamp=20180717172856`): o ficheiro em
  cache é igual, byte a byte, ao da captura seguinte, mas com `digest`
  diferente; pedir o texto outra vez hoje já devolve a versão correta.
  Causa não apurada — fica registado como anomalia pontual, não como padrão.

### Decisão de design (híbrido, não substituição da heurística)

Usar o contentor HTML por template para duas coisas específicas, sem
substituir a heurística de âncoras (variante c′) como método principal:

1. **Detetar Premium sem ambiguidade** (sinal estrutural, não
   `isAccessibleForFree`) e marcar essas capturas como "sem corpo,
   paywall", em vez de arriscar o falso positivo já documentado.
2. **Recuperar corpo na Camada 2** (capturas sem texto extraído em cache)
   a partir do contentor HTML, quando a heurística de texto não tem nada
   para processar.

Em ambos os casos, reaplicar os mesmos 14 marcadores de chrome da
heurística por cima do texto do contentor extraído do HTML — resolve o
caso AMP, em que o contentor `bodybox` por si só vem "sujo" (inclui blocos
de chrome que os outros contentores não têm).

**Estado: decisão de design registada, nada disto implementado.** A
`article_body.py` e a lógica de Camada 2 de `corpus_redundancy.py` não
foram alteradas. O único passo desta investigação que foi implementado é o
download e a preservação do HTML em bruto em si — ver a secção seguinte.

## Download do HTML em bruto da captura mais antiga e lista alargada de termos (implementado, não corrido; 2026-10-19)

### Decisão

Consequência das duas investigações anteriores:

- Ao pedir o texto da captura mais antiga de um artigo novo
  (`TEXT_POLICY_FIRST`, "Política de texto para artigos novos" acima),
  pedir também o HTML em bruto dessa mesma captura, no mesmo passo, para
  não ter de voltar a pedir à API mais tarde caso a heurística do corpo
  venha a mudar (secção anterior).
- Alargar a Fase 1 (`corpus_phase1.py`) com mais 11 termos de pesquisa, a
  somar aos 13 já usados, com `from=1999`/`to=2026` em vez de
  `2015`/`2020` — mesmo método (pesquisa por palavra-chave,
  `siteSearch=record.pt`), sem dividir por datas nem usar páginas de
  secção (secção anterior).
- Corrigir a paragem da paginação da Fase 1 para não depender de
  `next_page`, só de página incompleta/vazia (achado da secção "Alcance
  real da pesquisa por palavra-chave" acima).

### Implementação

- **`ArquivoClient.download_original_html()`** (`arquivo_client.py`),
  espelho de `download_extracted_text()`: lê `linkToOriginalFile` (em vez
  de `linkToExtractedText`) e grava em `data/raw/original_html/<tstamp>_
  <hash-do-url>.html`, com o mesmo comportamento de reutilização
  (`skip_existing`) e o mesmo tratamento de falhas (campo ausente, erro de
  rede). Ao contrário do texto extraído, não há derivação de URL quando o
  campo falta — não existe (ainda) uma fórmula confirmada para
  `linkToOriginalFile` equivalente à de `linkToExtractedText`.
- **`history_pipeline.build_manifest_records()`** passa a chamar
  `download_original_html()` quando `text_policy == TEXT_POLICY_FIRST` e o
  texto dessa captura é pedido (mesma condição que já pede o texto). Cada
  registo do manifesto ganha `original_html_path`, `html_download_success`,
  `html_downloaded_now`, `html_size_bytes`, `html_error` e `html_requested`;
  fora dessa condição estes campos ficam no valor "não pedido" (mesma lógica
  já usada para o texto). `TEXT_POLICY_ALL` (M3, reconstrução offline do
  corpus histórico via `CacheOnlyClient`) não é afetado — continua sem
  pedir HTML, evitando qualquer pedido de rede no caminho offline já testado.
- **`corpus_phase1.py`**: `MODALIDADES` ganha `atletismo`, `ciclismo`,
  `judo`, `motores`, `natação` (5 novas; `andebol` já estava nos 4 termos
  originais); nova faceta `COMPETICOES` com `2.ª Liga`, `CAN`, `Europeu`,
  `Liga Jovem da UEFA`, `Taça das Confederações`, `Taça de Portugal` (6).
  Total: **24 termos** (13 já usados + 11 novos). `FROM_DATE`/`TO_DATE`
  passam de `2015`/`2020` para `1999`/`2026`. A origem dos valores novos é
  uma query SPARQL sobre `output/corpus_entities.ttl` (instâncias
  `sdh:Tema` por `categoriaTema`/`valorTema`), já usado no corpus atual —
  não são termos inventados para esta expansão.
- **Ressalva não resolvida**: a mesma consulta devolve ainda 3 valores
  reais não incluídos nesta lista, sem justificação registada para a
  exclusão — modalidade `desporto-universitario` e `jogos-europeus`,
  competição `liga-nos` (distinta dos 4 clubes já pesquisados). Fica para o
  autor e o Jorge decidirem se entram também, antes ou depois da primeira
  corrida da descoberta alargada.
- **`collect_term_repetition()`** (Fase 1, paginação por `offset`) deixa de
  parar por ausência de `next_page`; passa a parar só quando a página vem
  incompleta (`len(resultados) < maxItems`), consistente com o achado desta
  semana de que `next_page` não é um sinal fiável de fim mesmo a esta
  escala. `collect_all_captures()` (Fase 2, `version_history`) **não foi
  alterado** — esta investigação testou especificamente a paginação do
  TextSearch em pesquisas de grande volume, não o `version_history`; não se
  generaliza uma conclusão de um endpoint para o outro sem evidência própria.

### Testes

Novos testes offline (fixtures sintéticas, sem rede) para
`download_original_html()` (reutilização de ficheiro existente, campo
ausente, falha de rede) e para a ligação ao `history_pipeline` (HTML pedido
só quando `TEXT_POLICY_FIRST` e o texto é pedido; `TEXT_POLICY_ALL` nunca
pede HTML, preservando o caminho offline do `CacheOnlyClient`). Suite
completa a confirmar depois da implementação.

### O que não foi feito

- A extração do corpo a partir do HTML (decisão da secção anterior,
  deteção de Premium e recuperação na Camada 2) continua por implementar;
  isto cobre só o download e a preservação do raw.
- **Nada foi corrido contra a API real**: este ambiente remoto não tem
  acesso a `arquivo.pt` (ver `docs/PROJECT_STATUS.md`). A descoberta
  alargada (24 termos, 1999–2026) tem de ser executada numa sessão local
  ou no terminal, nunca aqui.
- A ressalva dos 3 valores de vocabulário não incluídos (acima) fica em
  aberto.

## Correção: página incompleta também não é sinal fiável de fim (2026-10-19)

**Achado, numa sessão local, ao enumerar clubes e modalidades reais** (ver
secção seguinte): a meio de uma paginação por `offset` apareceram páginas
com 490–499 resultados de `maxItems=500`, seguidas de uma página seguinte
ainda cheia. Ou seja, uma página **incompleta não é o fim** — ao contrário
do que a correção de `collect_term_repetition()` em "Download do HTML em
bruto..." (acima) assumia (`if not page_full: break`). Isto confirma, com
um caso concreto, a formulação já usada em "Alcance real da pesquisa por
palavra-chave" ("o sinal fiável é uma página incompleta **seguida de uma
vazia**") — a implementação anterior não tinha, na prática, essa segunda
parte: parava já na primeira página incompleta, sem esperar pela vazia.

**Correção:** `collect_term_repetition()` passa a parar só quando a página
vem **vazia** (`len(resultados) == 0`); uma página incompleta mas não vazia
já não para a recolha, continua a pedir a próxima página pelo offset real
devolvido. O teto de `MAX_PAGES_PER_TERM` continua a ser a única rede de
segurança contra uma recolha sem fim, consistente com a amostra deliberada
do protocolo (não se pretende esgotar cada termo).

Esta correção não foi generalizada a `collect_all_captures()`
(`version_history`, Fase 2) — essa função tem os seus próprios testes de
regressão validados para "página incompleta OU sem `next_page`", sobre um
endpoint diferente (histórico de um único URL, não pesquisa por palavra-
chave em grande volume); não há evidência própria de que o mesmo problema
ocorra ali.

Teste de regressão em `tests/test_corpus_phase1.py` (no `main`, a mesma
regra ficou em `collect_term_year()`, testada por
`test_incomplete_page_does_not_stop_only_an_empty_page_does`).

## Fase 1 alargada: lista final de 108 termos (implementada; 2026-10-19)

### Decisão

A Fase 1 deixa de ser a "Opção 2 — Moderada" (13 termos, explicitamente uma
amostra pequena) e passa a uma **decisão de âmbito explícita e muito mais
ampla**: as facetas de modalidade, clube e competição enumeram os valores
reais encontrados nos URLs do `record.pt`, e não uma lista escolhida à mão.
Origem: a enumeração de 2026-10-19 com `themes_from_url()` (309 348
`originalURL` únicos; tabelas e raw em
`data/raw/api_diagnostics/enumeracao_2026-10-19/`). Decisões do autor sobre
os casos ambíguos:

- **39 modalidades.** Excluídas `outras`, `record-pela-patagonia` e
  `aventura-em-mocambique` (secções editoriais, não modalidades).
- **57 clubes.** `ac-viseu`/`ac--viseu` fundidos em "Académico de Viseu";
  `belenenses-sad`/`b-sad` fundidos em "Belenenses SAD"; `campeao` excluído
  (não é clube); as equipas B entram por terem ≥ 20 URLs na enumeração, não
  por pedido explícito.
- **7 competições:** as 6 já usadas e "Liga NOS", que cobre por completo os
  valores reais da categoria.
- **5 atletas, sem alterações:** é uma faceta de descoberta, não vocabulário
  de entidades (decisão do Caminho B sobre circularidade); não se alarga.

Total: **108 termos**, sem duplicados nem colisões de slug.

### Implementação

`corpus_phase1.py`: novas listas, docstring do módulo e um `RUN_LABEL =
"alargada"` que separa esta execução da original. Sem ele, o raw da nova
execução reescreveria os 26 ficheiros da Fase 1 original em
`data/raw/corpus_queries/` (não versionados: perda irreversível), e os
relatórios reescreveriam `output/corpus_phase1_*`, que a Fase 2 e a
classificação leem por omissão. A execução alargada escreve em
`data/raw/corpus_queries/alargada/` e `output/corpus_phase1_alargada_*`; a
original, que deu o corpus de 125 artigos, fica intacta e continua a ser a
entrada por omissão da Fase 2 até o `N` ser confirmado.

Mantêm-se os restantes parâmetros: `maxItems=50`, `dedupValue=1`, 2
repetições, no máximo 6 páginas (300 URLs) por termo/repetição e paragem na
primeira página com menos de 50 resultados. Dois pontos já observados que
afetam o `N` e ficam em aberto: o teto de 6 páginas limita cada termo a 300
URLs por repetição; e, na enumeração de 2026-10-19 (com `maxItems=500`),
houve páginas a meio da paginação com 490–499 URLs únicos seguidas de
páginas cheias, pelo que uma página com menos de `maxItems` nem sempre é o
fim.

Testes offline (`test_corpus_phase1.py`): totais por faceta (39/57/5/7, 108),
sem duplicados nem colisões de slug, casos ambíguos conforme a decisão,
atletas inalterados. Suite completa: 206 testes OK.

### Resultado da execução real (2026-10-19)

`python -m semantic_harvester.corpus_phase1`, 108 termos × 2 repetições,
`from=1999`/`to=2026`. 1 280 pedidos, todos com resposta (2 timeouts
recuperados na segunda tentativa). Raw em `data/raw/corpus_queries/alargada/`
(1 280 ficheiros, não versionados); relatórios em
`output/corpus_phase1_alargada_{per_term.csv,captures.csv,aggregation.md}`.
A Fase 1 original ficou intacta (checksum SHA-256 dos seus 26 ficheiros de
raw e 3 relatórios igual antes e depois).

- Itens brutos: 63 972; capturas únicas por `(originalURL, tstamp)`:
  30 242; **N (artigos únicos por `originalURL`): 28 782**. Divergências de
  metadados para a mesma captura: 1 445.

| Faceta | Termos | Pedidos | Itens | Capturas | Artigos | Só por esta faceta | Termo/rep. no teto de 6 páginas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| modalidade | 39 | 454 | 22 688 | 10 860 | 10 503 | 10 089 | 70 de 78 |
| clube | 57 | 682 | 34 084 | 16 118 | 15 313 | 14 905 | 112 de 114 |
| atleta | 5 | 60 | 3 000 | 1 496 | 1 486 | 1 358 | 10 de 10 |
| competição | 7 | 84 | 4 200 | 2 097 | 2 052 | 1 876 | 14 de 14 |

- **O `N` é limitado pelo teto, não pelo conteúdo.** 206 das 216
  combinações termo/repetição pararam no limite de 6 páginas (300
  resultados). Só 3 termos terminaram antes, nas duas repetições: "pólo
  aquático" (98), "esgrima" (148) e "Lank Vilaverdense" (242). A
  sobreposição entre facetas é pequena (a maioria dos artigos só aparece por
  uma faceta), pelo que o `N` cresce quase linearmente com o número de termos
  × 300.
- As duas repetições de cada termo devolveram o mesmo número de resultados
  nos 108 termos. Nenhum termo deu 0 resultados; todos os URLs são do
  `record.pt`.
- **Distribuição temporal das capturas:** 1999–2010: 2 147; 2011–2015: 0;
  2016: 1; 2017–2020: 22 908; 2021–2024: 5 186. Com o teto de 300 por termo e
  a ordem da TextSearch (não cronológica), nenhuma captura de 2011–2015
  entrou nesta descoberta.
- O `N` conta `originalURL` distintos: variantes do mesmo artigo (esquema,
  `?ref=`) ainda não estão juntas, e páginas que não são artigos ainda não
  foram filtradas (isso é a classificação, depois da Fase 2).

## Teste de blocos de data e recolha ano a ano na Fase 1 (2026-10-19)

### Teste controlado: 2 termos × 3 blocos

Motivação: na Fase 1 alargada (`from=1999`/`to=2026` num só intervalo), as
capturas concentraram-se em 2017–2020, com 0 em 2011–2015. Teste com
"Benfica" e "Vitória de Guimarães" (clubes; o segundo tinha batido no
teto), mesmos parâmetros da Fase 1 (`maxItems=50`, `dedupValue=1`, até 6
páginas), paragem só em página vazia, 1 repetição, em três blocos pedidos
com o ano sozinho: 1999–2016, 2017–2020, 2021–2026. Raw, sondas e script em
`data/raw/corpus_queries/teste_blocos_2026-10-19/` (não versionados).

| Termo | Bloco | Páginas | Paragem | Resultados | Por ano |
| --- | --- | ---: | --- | ---: | --- |
| Benfica | 1999–2016 | 6 | teto | 300 | 2001: 1 · 2006: 2 · 2007: 144 · 2008: 146 · 2009: 7 |
| Benfica | 2017–2020 | 6 | teto | 300 | 2017: 86 · 2018: 106 · 2019: 108 |
| Benfica | 2021–2026 | 6 | teto | 300 | 2021: 58 · 2022: 86 · 2023: 106 · 2024: 50 |
| V. Guimarães | 1999–2016 | 6 | teto | 300 | 1999: 1 · 2000: 4 · 2001: 45 · 2002: 18 · 2003: 1 · 2004: 13 · 2006: 27 · 2007: 88 · 2008: 65 · 2009: 37 · 2010: 1 |
| V. Guimarães | 2017–2020 | 6 | teto | 300 | 2017: 95 · 2018: 54 · 2019: 151 |
| V. Guimarães | 2021–2026 | 6 | teto | 300 | 2021: 87 · 2022: 88 · 2023: 70 · 2024: 55 |

Na corrida sem blocos, os mesmos termos tinham 300 capturas cada:
Benfica 2007–2009: 17, 2017–2019: 271, 2020: 12; V. Guimarães 2001: 1,
2007: 3, 2017–2020: 213, 2021–2024: 83. Os blocos triplicam os resultados
por termo e repartem-nos melhor, mas cada bloco bate no teto e, dentro de um
bloco largo, os 300 resultados concentram-se em 2–3 anos (1999–2016:
2007–2008 para Benfica).

Sondas de uma página, com datas de 14 dígitos: 2011-01-01 a 2016-12-31 e
2025-01-01 a 2026-12-31 deram **0 resultados** para os dois termos; 2020
inteiro deu 50 (página cheia) para cada um. A Fase 1 original
(`from=2015`/`to=2020`) também só tem capturas de 2017–2019. A lacuna de
2011–2016 é, para estes termos, do índice da TextSearch para o `record.pt`,
não do teto nem da divisão em blocos.

### Erro de datas: um ano sozinho é o início desse ano

A API lê `to=2020` como `20200000000000` (confirmado no
`request_parameters` devolvido: `from=2017&to=2020` →
`from=20170000000000`, `to=20200000000000`), excluindo o ano de 2020
inteiro. Afetou a Fase 1 original (`to=2020`, por isso nunca teve 2020), a
Fase 1 alargada (`to=2026`) e o bloco "2017–2020" do teste acima. Correção:
todo o `from`/`to` passa a ser construído com 14 dígitos, `AAAA0101000000`
a `AAAA1231235959` (`corpus_phase1.year_bounds`), o mesmo formato do
`tstamp`. O `ArquivoClient` não muda: só serializa o que recebe.

### Decisão: recolha ano a ano

Como um bloco largo (18 anos) ainda concentra quase tudo em 2–3 anos, a
Fase 1 passa a pedir cada termo **um ano de cada vez**, de 1999 a 2026 (28
intervalos), com a paginação corrigida: paragem só na primeira página vazia
(uma página com menos de 50 resultados não é o fim) ou no teto de 6
páginas, agora por ano. `REPETITIONS` passa de 2 para 1 (decisão de âmbito
do autor, pelo prazo; na corrida alargada as duas repetições deram sempre o
mesmo número de resultados). Implementado em `corpus_phase1.py`:
`collect_term_year()` substitui `collect_term_repetition()`; o ano entra no
nome do raw (`<faceta>_<termo>_<ano>_rep1_offset-NNNN.json`), para não
colidir entre anos; a execução retoma a partir do raw já gravado. Escreve
em `data/raw/corpus_queries/por_ano/` e `output/corpus_phase1_por_ano_*`,
sem tocar nas execuções original e alargada. Testes offline: datas de 14
dígitos enviadas, página incompleta não pára e página vazia pára, teto de
páginas, ano no nome do raw, retoma sem pedido; suite completa 211 testes
OK.

### Resultado da execução ano a ano (2026-10-19)

`python -m semantic_harvester.corpus_phase1`: 108 termos × 28 anos, 1
repetição. **10 613 pedidos** (1 falha pontual de rede, recuperada na
segunda tentativa); 421 494 itens brutos; 269 719 capturas únicas por
`(originalURL, tstamp)`; **N (artigos únicos por `originalURL`): 211 359**.
Raw em `data/raw/corpus_queries/por_ano/` (10 613 ficheiros); relatórios em
`output/corpus_phase1_por_ano_*` (não versionados). As execuções original e
alargada ficaram intactas (checksum SHA-256 de 1 313 ficheiros igual antes e
depois).

| Ano | Pedidos | Resultados | Termos no teto (de 108) | Termos com 0 | Capturas únicas | Artigos (pelo ano da 1.ª captura) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1999 | 260 | 6 226 | 17 | 35 | 394 | 348 |
| 2000 | 432 | 16 403 | 6 | 7 | 5 453 | 4 528 |
| 2001 | 497 | 21 566 | 63 | 6 | 11 932 | 11 591 |
| 2002 | 461 | 19 122 | 57 | 6 | 7 316 | 6 998 |
| 2003 | 206 | 3 210 | 2 | 54 | 688 | 632 |
| 2004 | 251 | 5 283 | 4 | 38 | 1 426 | 972 |
| 2005 | 327 | 8 454 | 5 | 10 | 1 337 | 608 |
| 2006 | 499 | 20 976 | 53 | 3 | 14 012 | 8 858 |
| 2007 | 542 | 24 288 | 68 | 2 | 16 115 | 12 905 |
| 2008 | 546 | 24 720 | 61 | 2 | 13 202 | 7 882 |
| 2009 | 501 | 21 553 | 60 | 5 | 8 596 | 7 752 |
| 2010 | 177 | 1 910 | 0 | 68 | 770 | 724 |
| 2011 | 108 | 0 | 0 | 108 | 0 | 0 |
| 2012 | 108 | 0 | 0 | 108 | 0 | 0 |
| 2013 | 113 | 7 | 0 | 103 | 5 | 4 |
| 2014 | 112 | 5 | 0 | 104 | 3 | 1 |
| 2015 | 117 | 333 | 1 | 103 | 324 | 324 |
| 2016 | 113 | 34 | 0 | 103 | 33 | 9 |
| 2017 | 629 | 30 927 | 99 | 2 | 24 443 | 20 002 |
| 2018 | 629 | 31 098 | 101 | 2 | 26 921 | 20 944 |
| 2019 | 630 | 31 201 | 101 | 2 | 27 179 | 22 482 |
| 2020 | 627 | 30 769 | 97 | 2 | 25 464 | 20 504 |
| 2021 | 622 | 30 505 | 92 | 1 | 19 122 | 15 232 |
| 2022 | 625 | 30 563 | 93 | 0 | 21 063 | 15 480 |
| 2023 | 637 | 31 500 | 96 | 0 | 22 778 | 16 886 |
| 2024 | 628 | 30 841 | 97 | 0 | 21 143 | 15 693 |
| 2025 | 108 | 0 | 0 | 108 | 0 | 0 |
| 2026 | 108 | 0 | 0 | 108 | 0 | 0 |

| Faceta | Termos | Pedidos | Itens | Capturas | Artigos | Só por esta faceta | Termo-anos no teto | Termo-anos com 0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| modalidade | 39 | 3 735 | 146 995 | 98 785 | 82 534 | 58 567 | 417 | 419 |
| clube | 57 | 5 705 | 227 916 | 156 842 | 125 359 | 97 571 | 633 | 553 |
| atleta | 5 | 447 | 16 490 | 16 188 | 15 143 | 8 519 | 44 | 54 |
| competição | 7 | 726 | 30 093 | 29 401 | 26 316 | 13 382 | 79 | 64 |

- **2011–2016 continua quase vazio** (365 capturas em 6 anos, 324 delas em
  2015) e **2025–2026 vazio**, agora com intervalos de um ano inteiro e
  datas de 14 dígitos: confirma, para os 108 termos, o que as sondas do
  teste de blocos mostraram para 2 — é a cobertura do índice da TextSearch
  para o `record.pt`, não um efeito da forma de pedir.
- **O teto de 6 páginas continua a limitar**, agora por ano: 1 173 dos
  3 024 pares termo/ano bateram nas 300 resultados, sobretudo em 2017–2024
  (92–101 dos 108 termos por ano) e em 2001–2002 e 2006–2009 (53–68).
- As 66 587 "divergências de metadados" do relatório agregado são, numa
  amostra de 4 000 ficheiros de raw, quase todas no campo `snippet` (que
  depende do termo pesquisado; 36 909 casos) e uma no `digest`: não são
  divergências reais da captura.
- O `N` conta `originalURL` distintos, ainda sem juntar variantes do mesmo
  artigo nem filtrar páginas que não são artigos (isso é a classificação,
  depois da Fase 2).

## Fase 1 ano a ano: N com `originalURL` normalizado e Fase 2 separada (2026-10-20)

### Agregação corrigida (sem pedidos à API)

O N de 211 359 contava `originalURL` exatos, pelo que variantes cosméticas
do mesmo artigo contavam como artigos diferentes. A agregação passa a usar a
regra de "mesma página" já usada pela classificação e pelo RDF,
`normalize_for_grouping()` (movida de `corpus_rdf.py` para
`url_identity.py`, onde está o resto da regra; `corpus_rdf` continua a
exportá-la): sem esquema, barras repetidas colapsadas, sem barra final, sem
`ref`/`utm_*`/`act`/`est`; a restante query string mantém-se (no site
antigo é o identificador do artigo). Cada grupo fica com um URL
representativo: sem parâmetros de rastreio, depois sem `//`, depois
`https`, depois o que tem mais capturas, depois a ordem alfabética. O CSV de
capturas ganha a coluna `url_variants` (as outras formas reais).

`python -m semantic_harvester.corpus_phase1 --rebuild-offline` refez os
relatórios a partir dos 10 613 ficheiros de raw já em disco
(`data/raw/corpus_queries/por_ano/`), sem rede; o CSV anterior ficou em
`output/corpus_phase1_por_ano_captures.pre-normalizacao.csv`.

- `originalURL` exatos: 211 359 → **N corrigido: 164 373** (46 986 variantes
  juntadas: 44 330 só por parâmetros de rastreio, 2 605 por barras
  duplas, 51 por rastreio e barra final). Capturas únicas: 269 718.
- `www.record.pt` e `record.pt` não se juntam (o host é diferente), tal
  como na classificação.
- A divergência de metadados só se compara entre itens com o mesmo
  `originalURL` real (entre variantes os campos com o URL diferem por
  construção). As 66 587 que se mantêm são, como já registado, o `snippet`.

### Fase 2 separada da original

`corpus_phase2.py` ganha `--captures-csv` e `--label`. Com
`--label por_ano`, os resultados vão para
`output/corpus_phase2_por_ano_{history.csv,summary.md,progress.log}` e o raw
de `version_history` para `data/raw/phase2_por_ano/version_history/` (não
versionado). Sem isto, a nova execução escreveria no
`output/corpus_phase2_history.csv` da Fase 2 original e reescreveria, para
os URLs em comum, o raw de `data/raw/version_history/` de que depende a
reconstrução offline do corpus de 125 artigos. Testes offline: a execução
com etiqueta só escreve nos seus caminhos e é retomável. Suite completa:
218 testes OK.

### 429 Too Many Requests na Fase 2 (2026-10-20)

Lançada às 01:01 (`nohup caffeinate -i python -m
semantic_harvester.corpus_phase2 --captures-csv
output/corpus_phase1_por_ano_captures.csv --label por_ano`), a Fase 2
processou 2 415 artigos em cerca de 13 minutos (~3 por segundo, sem pausa
entre pedidos) e registou 3 falhas, todas **429 Too Many Requests**: o
serviço a pedir para abrandar, não 404 nem quebra de rede. O código tratava
o 429 como qualquer erro (3 tentativas com 10 s de intervalo) e depois
marcava o artigo como falhado. Execução parada (CSV íntegro, última linha
completa) e corrigida: num 429, `_collect_with_retries` espera o
`Retry-After` indicado (ou 60 s) e repete sem gastar as 3 tentativas, até 20
esperas por artigo; os outros erros mantêm o comportamento anterior. Não se
acrescentou uma pausa fixa entre pedidos (triplicaria a duração); o ritmo só
abranda quando o serviço o pede. Testes offline: 429 com e sem
`Retry-After` seguido de sucesso; 500 continua a gastar as tentativas.
Suite completa: 220 testes OK.

### Dois achados de escala (2026-10-20)

**1. A taxa de variantes de URL da amostra pequena não generalizou.** Na
Fase 1 original (159 `originalURL`), as variantes cosméticas do mesmo
artigo eram 3: um par `http`/`https` (159 → 158 recursos, "Normalização
http/https antes de classificar") e dois pares por parâmetros de rastreio
(127 → 125 artigos retidos, "Correção da identidade dos artigos", 2026-10-04)
— cerca de **1,9%**. Na Fase 1 ano a ano (211 359 `originalURL`), as
variantes juntadas pela mesma regra foram **46 986, cerca de 22,2%**, quase
todas (44 330) só por parâmetros de rastreio. A taxa observada na amostra
pequena não servia de estimativa para o corpus alargado; a normalização do
`originalURL` antes de contar o N é obrigatória a esta escala, não um
detalhe.

**2. O Arquivo.pt limita o ritmo de pedidos (429).** Sem pausa entre
pedidos (~3 pedidos de `version_history` por segundo), a primeira resposta
**429 Too Many Requests** chegou cerca de 4 minutos depois do arranque
(01:01:33 → 01:05:16); em cerca de 13 minutos e 2 415 artigos houve 3
artigos marcados como falhados só por isso. Nas execuções da Fase 1
(TextSearch, também sem pausa explícita, mas a cerca de 1 pedido por segundo
pela própria latência do serviço: 10 613 pedidos em cerca de 3,3 horas), não
houve nenhum 429 em 11 893 pedidos (1 280 na alargada, 10 613 na ano a ano). A correção não impõe uma pausa
fixa: num 429 respeita-se o `Retry-After` (ou 60 s quando falta) e repete-se
sem contar como falha, pelo que o ritmo só abranda quando o serviço o pede.
Nos primeiros 6 minutos depois do relançamento (01:16) houve 2 dessas
esperas e 0 falhas, a cerca de 1,6 artigos por segundo em média (550 em
350 s, incluindo as esperas). É um facto sobre o Arquivo.pt como
infraestrutura: qualquer recolha longa tem de tratar o 429 como "esperar",
não como erro.

## Corpus alargado sem Fase 2: paragem, classificação por URL e RDF da Fase 1 (2026-10-20)

### Decisão: parar a Fase 2

A Fase 2 ano a ano (`version_history` dos 164 373 artigos) foi parada às
09:13 de 2026-10-20, por decisão do autor, com **62 414 artigos processados
(38,0%)**, 698 702 capturas e 0 falhas depois da correção do 429 (houve 192
esperas por 429 até então, todas resolvidas). Ao ritmo medido (cerca de 2
artigos por segundo, limitado pelo serviço), faltariam cerca de 15 horas.
Razões: a classificação deixou de precisar do número de capturas por artigo
(ver abaixo), e a profundidade temporal por artigo já foi estudada no corpus
pequeno e não é central para este motor (`docs/PROJECT_STATUS.md`,
"Limitações e problemas conhecidos"). O que correu fica como está, sem uso
a jusante: `output/corpus_phase2_por_ano_{history.csv,summary.md,progress.log}`
e `data/raw/phase2_por_ano/` (não versionado). O raw de `version_history` do
corpus de 125 artigos e a Fase 2 original ficaram intactos (checksum
SHA-256 igual antes e depois, 290 ficheiros).

### Classificação sem a Fase 2: sinal de caminho de URL

`corpus_classification.py` substitui o sinal "mais de 100 capturas na Fase
2" por um sinal de caminho de URL: um recurso só é `Artigo` se o URL seguir
um dos esquemas de página de artigo do Record (`ARTICLE_URL_SCHEMES`), além
de não ser `/sabermais/` nem ter título "Object moved" (os dois sinais
anteriores, que já vêm do CSV da Fase 1). Os esquemas incluídos são os três
formatos de página individual de notícia conhecidos em gerações diferentes
do site, para o sinal não depender da época:

- `/detalhe/` ou `/amp/` no caminho — site atual (o AMP antigo aparece como
  `/detalhe/AMP/`, já coberto por `/detalhe/`);
- `interior.aspx?content_id=` — site antigo; no corpus pequeno o `=`
  aparece codificado (`content_id/x3d…`), por isso aceitam-se as duas formas;
- `tn0cs.asp?nid=` / `tn1cs.asp?nid=` — 1999–2000 ("Alcance temporal do
  `record.pt`").

Comparação feita em minúsculas. A classificação lê
`output/corpus_phase1_por_ano_captures.csv` e escreve
`output/corpus_classification_por_ano.{csv,_summary.md}` (`--label`), sem
reescrever `output/corpus_classification.csv`, de que dependem o RDF e os
Caminhos D e B do corpus de 125 artigos.

**Resultado real (sem pedidos à API):** 164 373 recursos; **83 320
Artigo**; excluídos 2 945 por `/sabermais/`, 0 por "Object moved" e 78 108
por URL fora dos esquemas. Artigos por esquema: `/detalhe/` 72 170, `/amp/`
8 790, `tn0cs.asp` 1 695, `tn1cs.asp` 665, `interior.aspx?content_id` 0.

**Observação e decisão (2026-10-20).** Nesta descoberta não há nenhum URL
`interior.aspx?content_id`. Com só os esquemas acima, o corpus não tinha
nenhum Artigo de 2001 a 2009 (83 320 Artigos: 1999: 294, 2000: 2 066,
2017–2024: 80 960). Entre os excluídos por URL estavam três esquemas do site
de 2000–2009 com o mesmo padrão de "um id por notícia": `noticia.asp?id=`
(33 773 recursos, 2001–2009), `shownews.asp?id=` (8 410, 2000–2001) e
`noticia.aspx?id=` (3 814, sobretudo 2009); os títulos são em geral
genéricos (":.: Jornal Record :.:", "Record"), mas há títulos de notícia
reais em `noticia.aspx`. **Decisão do autor: incluí-los** em
`ARTICLE_URL_SCHEMES`. `imprimir.asp` e `enviar.asp` (versões de
impressão/envio da mesma notícia) e as outras queries no mesmo ficheiro (por
exemplo `noticia.aspx?idcanal=`) continuam excluídos.

**Resultado final:** **129 317 Artigo** em 164 373 recursos; excluídos
2 945 por `/sabermais/`, 0 por "Object moved" e 32 111 por URL fora dos
esquemas. Por esquema: `/detalhe/` 72 170, `noticia.asp` 33 773,
`/amp/` 8 790, `shownews.asp` 8 410, `noticia.aspx` 3 814, `tn0cs.asp`
1 695, `tn1cs.asp` 665, `interior.aspx?content_id` 0. Por ano da captura
mais antiga: 1999: 294 · 2000: 4 430 · 2001: 10 376 · 2002: 6 586 · 2003: 16
· 2004: 43 · 2005: 156 · 2006: 6 981 · 2007: 10 602 · 2008: 5 119 · 2009:
3 754 · 2017: 16 819 · 2018: 14 179 · 2019: 12 444 · 2020: 10 554 · 2021:
5 564 · 2022: 6 786 · 2023: 7 609 · 2024: 7 005.

### RDF a partir só da Fase 1 (implementado, não corrido)

`corpus_rdf.py --fase1 por_ano`: os artigos vêm de
`output/corpus_classification_por_ano.csv`; cada um é registado com **uma
só captura, a mais antiga que a descoberta encontrou**, lida do raw da
TextSearch (`data/raw/corpus_queries/por_ano/`, agrupando variantes com
`normalize_for_grouping`), sem `version_history`. **Ressalva:** é a captura
mais antiga *conhecida* (a que a TextSearch devolveu dentro do teto de
páginas), não necessariamente a mais antiga que existe no Arquivo.pt. Texto
e HTML só dessa captura (`TEXT_POLICY_FIRST`). Os itens da TextSearch não
trazem `statusCode` nem `contentLength` (o `version_history` trazia), que
ficam ausentes do grafo. Outputs separados e retomáveis:
`output/corpus_articles_por_ano.ttl`,
`output/corpus_rdf_por_ano_{report.csv,summary.md,progress.log}` e
`data/processed/corpus_articles_por_ano_triples.nt`. Testes offline: usa a
captura mais antiga (incluindo de uma variante de rastreio), escreve só nos
caminhos etiquetados, retoma sem pedidos. Suite completa: 225 testes OK.

### 429 também nos downloads de texto e HTML (2026-10-20)

Antes de correr `corpus_rdf --fase1 por_ano` (129 317 Artigos, 258 634
pedidos: texto e HTML da captura mais antiga conhecida), um piloto de 63
artigos, estratificado por esquema de URL, mediu 0,55 s de rede por artigo
(mediana 0,39 s, máximo 7,9 s): cerca de 20 horas sem limitação de ritmo,
ou cerca de 36 horas ao ritmo sustentado de ~2 pedidos por segundo
observado na Fase 2 com 429. Texto obtido em 62 de 63 (1 404); HTML em 58
de 63, as 5 falhas todas `500` e todas em `noticia.asp` (5 de 16).
Espaço estimado: ~21 GB de HTML e ~1,1 GB de texto.

O download de texto e HTML do `ArquivoClient` tratava um 429 como falha
definitiva; como o relatório do `corpus_rdf` é retomável por artigo, esse
texto nunca seria pedido outra vez. Correção, a mesma da Fase 2:
`_get_respecting_rate_limit()` espera o `Retry-After` (ou 60 s) e repete,
até 20 esperas por pedido; só depois um 429 conta como falha. Os outros
erros (404, 500, rede) mantêm o comportamento anterior, sem repetição.
Testes offline: 429 com e sem `Retry-After` seguido de sucesso (texto e
HTML), 429 persistente como falha depois das esperas, 404/500 sem
repetição. Suite completa: 229 testes OK.

### Execução de `corpus_rdf --fase1 por_ano` e artefactos de rede (2026-10-20/21)

Lançada às 10:03:37 de 2026-10-20 (`nohup caffeinate -i`); os 129 317
artigos foram processados até às 00:09:34 e o Turtle final ficou escrito às
01:09 (2 208 257 triplos). Nenhum 429. Mas a partir de ~22:52 o serviço
degradou-se: primeiro respostas **400 Bad Request** para URLs válidos (2 514
de texto, 1 909 de HTML) e, a partir de 22:57, **"Connection reset by
peer"** em série (34 731 de HTML e 34 712 de texto, mais de 1 200 por
minuto, cada pedido a falhar em ~50 ms); mais 243/225 erros de ligação e
11/8 timeouts. Às 01:14 o serviço respondia normalmente, incluindo os URLs
exatos que tinham dado reset e 400 (verificado por amostragem). Estes erros
são artefactos, não falhas reais: afetam **37 481 artigos** (37 479 com o
texto em falta, 36 872 com o HTML). Os 500 do HTML (5 418, quase todos
`noticia.asp`) persistem (5 de 6 testados de novo) e contam como reais, tal
como os 404.

Salvaguarda antes de repetir só esses artigos: `ArquivoClient` ganha
`connection_error_max_waits` — num erro de ligação, espera 60 s e repete
até esse número de vezes por pedido, para uma quebra pausar a recolha em vez
de gerar falhas em série. Desligado por omissão (o `corpus_text_retry` tem a
sua própria retentativa, que não muda); `corpus_rdf --fase1` usa 10. Testes
offline: reset seguido de sucesso, erro persistente como falha depois das
esperas, sem repetição por omissão. Suite completa: 232 testes OK.

**Primeira repetição (2026-10-21, 01:20–03:59) e ritmo explícito.** A
repetição dos 37 481 artigos refez 7 850 (texto obtido em 4 453) até os
400 voltarem às 01:47 e os "connection reset" às 01:49; a salvaguarda de
ligação fez 120 esperas, mas os 400 continuaram a contar como falha. Às
03:59 até um pedido isolado (`curl`) levava "connection reset": sinal de
bloqueio ou de serviço degradado, não de sobrecarga momentânea. Repetição
parada (retomável). Às 10:07 dois pedidos isolados aos mesmos URLs
responderam 200 com conteúdo. Decisão do autor: retomar a ~1 pedido por
segundo, não aos 2–4 de antes (o serviço degradou-se sem nunca responder
429). `ArquivoClient` ganha `min_request_interval` (pausa mínima entre
downloads de texto/HTML; desligada por omissão), que `corpus_rdf --fase1`
usa com 1 s. Os 3 393 artigos que falharam na repetição por 400 ou erro de
ligação voltaram a ser marcados como artefacto (os 404 e 500 ficam como
reais): **33 024 artigos pendentes**. O autor contactou a equipa do
Arquivo.pt. Suite completa: 234 testes OK.

## Candidatos a entidade fora do vocabulário fechado — teste exploratório (proposta e script testado, não corrido sobre o corpus real; 2026-10-21)

### Motivação

Discussão sobre alargar o Caminho B (vocabulário fechado da Wikidata,
"Decisões já tomadas" acima) a uma abordagem híbrida: perguntar à Wikidata
só pelos nomes próprios que o vocabulário fechado não encontra, em vez de
todos os candidatos de todos os artigos. Essa ideia reduziria o volume de
pedidos à Wikidata, mas não resolve dois problemas:

1. Para saber que um nome (ex. "Estádio da Pedreira") é candidato a
   verificar, é preciso primeiro alguma deteção genérica de candidatos —
   o próprio passo de reconhecimento leve que a opção (b) ("Fonte do
   vocabulário fechado — opções", acima) tentava evitar. A híbrida só
   limita onde essa dependência é usada depois, não a elimina.
2. Perguntar à Wikidata sobre um candidato desconhecido não diz de
   antemão que tipo de coisa é (estádio, treinador, árbitro, competição
   menor, ...); cada tipo precisaria de validação própria para não
   aceitar uma correspondência errada — trabalho de desambiguação novo.

**Decisão:** não implementar a híbrida nem qualquer pedido à Wikidata
nesta sessão. Em vez disso, um teste pequeno e barato, só com o que já
existe (corpus e vocabulário atuais): aplicar uma deteção leve de
candidatos (heurística, não NER a sério) e ver quantos não batem com o
vocabulário fechado, para decidir com evidência própria se vale a pena
avançar. A Bola/Expresso ficam fora de qualquer implementação (apenas
reconhecimento leve por pesquisa manual, já registado como parágrafo
separado, fora do âmbito desta secção).

Esta proposta não reabre a decisão "vocabulário fechado em vez de NER
genérico" do `PROJECT_STATUS.md`; é um teste exploratório para informar
se/como estender essa decisão, não uma mudança a ela.

### Heurística (deliberadamente simples)

Implementada em `src/semantic_harvester/corpus_candidate_entities.py`,
sem pedidos à API nem à Wikidata, sem alterar o Caminho B, o grafo ou o
raw:

1. O texto do corpo do artigo (variante c′, como no Caminho B) é partido
   em frases por pontuação final (`.`, `!`, `?`).
2. Cada frase é ainda partida em cláusulas por vírgula/ponto e vírgula/
   parênteses/aspas — sem isto, duas sequências separadas só por uma
   vírgula (ex. "no Estádio da Luz, Bruno Fernandes marcou") fundir-se-
   iam num só candidato, porque a tokenização por palavra descarta a
   pontuação.
3. Um candidato é uma sequência de 2 ou mais palavras capitalizadas,
   podendo incluir no meio os conectores "de", "da", "do", "das", "dos"
   e "e" (para apanhar nomes como "Estádio da Pedreira"), desde que não
   comece na primeira palavra da frase (só a primeira cláusula de cada
   frase tem essa exclusão; uma cláusula depois de uma vírgula pode
   começar com um candidato).
4. Candidatos cuja forma normalizada (igual à de `corpus_entities.py`:
   NFC, minúsculas, sem acentos, limites de palavra) corresponde a, ou
   está contida em, uma variante já presente no vocabulário fechado
   indicado são descartados.

Agrega por artigo: para cada candidato fora do vocabulário, nº de
artigos distintos, nº de ocorrências e um `originalURL` de exemplo, para
inspeção manual de uma amostra — esse exame é trabalho humano fora do
script, não uma avaliação de precisão automática.

### Testes (offline, fixtures sintéticas) e o que não foi corrido

16 testes novos em `tests/test_corpus_candidate_entities.py`: deteção
pura (exclusão de início de frase, conector a juntar duas palavras,
conector "e" entre dois nomes, sequência de uma só palavra não conta,
cláusulas separadas por vírgula não se fundem, duas frases contribuem
candidatos separados), correspondência com o vocabulário (exata e por
contenção), agregação por artigo (contagem de artigos/ocorrências,
captura sem texto ou não-200 ignorada, ordenação) e uma execução sobre
um corpus Turtle sintético (não destrutiva, filtra a entidade já
conhecida, reporta o novo candidato). Suite completa: **219 testes,
todos a passar** no ramo antes de juntar o `main`; **248** depois.

**Nada foi corrido sobre o corpus real de 125 artigos.** Este ambiente
remoto não tem os textos de `data/raw/texts/` (preservados fora do Git,
ver `PROJECT_STATUS.md`) — a mesma limitação operacional que já impede
chamadas reais à API aqui. `python -m semantic_harvester.corpus_candidate_entities
--vocabulario data/processed/caminho_b_vocabulario_wikidata.csv` fica
pronto a correr numa sessão local ou no terminal, mas os resultados
sobre os artigos reais (quantos candidatos distintos, que proporção
parece ruído vs. nomes próprios genuínos) ainda não têm evidência
própria; não inventar esses números aqui.

### Não corre sobre o corpus alargado tal como está (verificado no código, 2026-10-21)

O script foi escrito para o corpus de 125 artigos
(`output/corpus_articles.ttl`). Sobre o corpus alargado
(`output/corpus_articles_por_ano.ttl`, 129 317 Artigos, uma captura cada,
"Corpus alargado sem Fase 2" acima) não funciona sem adaptação — e o
mesmo vale para o Caminho B (`corpus_entities.py`) e o D, que partilham a
leitura do corpus:

- `load_corpus()` (`corpus_redundancy.py`) faz `int(...)` de
  `sdh:contentLength` e a Camada 1 exige `statusCode == 200`; o grafo da
  Fase 1 não tem nenhum dos dois (a TextSearch não os devolve). Resultado:
  erro na leitura, ou, se fosse contornado, nenhuma captura na Camada 1.
- A variante c′ (`article_body.py`) foi calibrada no site 2017–2020
  (título com " - " e 14 marcadores de chrome); as páginas de 1999–2009
  (`noticia.asp`, `shownews.asp`, `tn0cs.asp`) têm outra estrutura e é
  provável que fiquem "sem corpo" — não verificado.
- O vocabulário fechado só tem futebolistas da Primeira Liga 2015–2020:
  num corpus de 1999–2024 com todas as modalidades, a lista "fora do
  vocabulário" será dominada por isso, não pela qualidade da heurística.
- Escala: carregar 2,2 milhões de triplos com `rdflib` e ler ~95 000
  textos é viável, mas lento; não medido.

Recomendação: correr primeiro sobre o corpus de 125 artigos (que funciona
como está) para ter evidência barata; adaptar a leitura ao corpus alargado
só se essa evidência justificar.

### O 400 como sinal de quota na recolha do `corpus_rdf --fase1` (2026-10-21)

Segunda repetição (10:09, ~1 pedido por segundo): 1 600 artigos sem
nenhuma falha durante 46 minutos; às 10:55 o serviço passou a responder 400
a todos os pedidos (texto e HTML, ~60 por minuto) e o vigia parou o processo
às 11:00 (288 erros em 5 minutos). URLs que tinham dado 400 um minuto antes
responderam 200 com conteúdo; pedidos isolados passam sempre. O 400 é,
portanto, um sinal de quota por janela de tempo, não um erro do URL: surgiu
ao fim de ~12 h na execução principal, de 27 min a ~3 pedidos por segundo e
de 46 min a ~1 pedido por segundo. Os 154 artigos afetados voltaram a ser
marcados como artefacto: **31 573 pendentes** (97 744 de 129 317
concluídos; texto em 95 400, 2 344 falhas reais de texto).

**Decisão do autor:** tratar o 400 como o 429, só no modo `--fase1`, a 1
pedido por segundo: num 400 o pedido pausa ~10 min e repete; se o mesmo URL
der 400 depois de 3 pausas, conta como falha real. Implementado como
`bad_request_max_pauses` no `ArquivoClient` (desligado por omissão;
`BAD_REQUEST_PAUSE_SECONDS = 600`, `BAD_REQUEST_MAX_PAUSES = 3`). Testes
offline: 400 seguido de sucesso; 400 depois de 3 pausas como falha real; sem
pausa por omissão. Suite completa: 253 testes OK.

## Vocabulário alargado 1999–2024: medição e construção (2026-10-21)

**Pedido do autor:** alargar o vocabulário fechado do Caminho B (só
futebolistas da Primeira Liga 2015–2020) a (a) 1999–2024, (b) as 39
modalidades de `corpus_phase1.MODALIDADES` e (c) dois tipos de entidade,
jogadores/atletas e clubes. Módulo novo `wikidata_vocabulary_alargado.py`;
`wikidata_vocabulary.py` e `data/processed/caminho_b_vocabulario_wikidata.csv`
ficam intocados (o módulo recusa escrever nesse caminho; teste com checksum).
Raw em `data/raw/wikidata/alargado/` (byte a byte, fora do Git; 228
ficheiros, 37 MB), vocabulário em
`data/processed/caminho_b_vocabulario_wikidata_alargado.csv`, resumo
completo da execução (JSON) em `output/wikidata_vocabulario_alargado.md`.
**Não foi aplicado a nenhum corpus:** `corpus_entities`/`corpus_entities_rdf`
não foram corridos (escrevem nos outputs oficiais), e o corpus de 129 317
artigos ainda não carrega em `load_corpus()` (falta `contentLength`/
`statusCode` no grafo da Fase 1; trabalho separado).

### Passo 1 — medição

Exploração com consultas de leitura (mesmo User-Agent, uma de cada vez,
≥ 1 s), e depois a execução final do módulo, de onde vêm todos os números
abaixo (115 pedidos, nenhuma consulta falhada; a execução anterior de
desenvolvimento ficou em `data/raw/wikidata/alargado_iteracoes_2026-10-21/`).

**Futebol — clubes.** Participantes (`wdt:P1923`) nas épocas 1999–2000 a
2023–24: na Primeira Liga só 3 de 25 épocas (2016–17, 2017–18, 2019–20), na
Segunda Liga só 1 de 25 (2017–18) → 38 clubes. Exploração: `wdt:P710` dá 0
em todas as épocas e `wdt:P1344` (participa em) no máximo 3 clubes por
época. Alternativa medida: clubes portugueses com `wdt:P118` (liga) Primeira
ou Segunda Liga (sem datas; a propriedade também aparece em pessoas,
filtradas) → 57; épocas ∪ liga = 58. Contra os 57 clubes de `CLUBES` (Fase 1),
resolvidos à mão para QIDs (`CLUBES_QID`, a partir de uma consulta por
rótulo/nome alternativo, escolhendo o clube masculino principal): 52 estão
nas épocas ou na liga; **5 só entram pela tabela explícita: Fafe, Lank
Vilaverdense, Mafra, Olhanense, Sporting Clube Oriental** (este último
resolvido para o Clube Oriental de Lisboa, Q2749186; Lank Vilaverdense para
o Vilaverdense FC, Q7930110). Os 10 clubes de `caminho_b_clubes_url.csv`
estão todos nas épocas ou na liga. Total: 63 clubes de futebol.

**Modalidades.** Para cada termo, um item de desporto e uma ou mais
ocupações de atleta (a consulta inclui subclasses, `wdt:P279*`); rótulos
verificados na execução (nenhum QID sem rótulo). 33 mapeados (7 de equipa:
futebol, basquetebol, andebol, voleibol, hóquei em patins, rugby, pólo
aquático; 26 individuais). Quatro são termos guarda-chuva e foram mapeados a
várias ocupações, explicitamente: motores (pilotos de automóveis, ralis,
F1, motociclismo, motocross), desportos de combate (boxe, kickboxing,
karaté, taekwondo, luta; judo e MMA têm termo próprio), desportos radicais
(skate, BMX, bodyboard, escalada) e desportos de inverno (esqui alpino e de
fundo, biatlo, patinagem artística, snowboard, esqui de montanha); desporto
adaptado → atleta paralímpico / para-atleta. **Sem mapeamento (6):**
desporto-universitario e desporto escolar (enquadramentos competitivos, os
atletas pertencem às modalidades que praticam), jogos olímpicos e
jogos-europeus (eventos multidesportivos), NFL (liga estrangeira de futebol
americano; entidades estrangeiras fora do âmbito) e aventura (secção que
agrega trail/corridas de aventura/montanha, sem ocupação de atleta própria).
Padel e orientação têm item e ocupação, mas **0** atletas portugueses na
Wikidata.

Atletas por modalidade (pessoas devolvidas → incluídas pela regra abaixo).
Desportos de equipa = passagem (`p:P54`) por clube português (`wdt:P17
wd:Q45`, excluídas 118 seleções nacionais) ∪ nacionalidade portuguesa
(`wdt:P27 wd:Q45`); futebol = passagens pelos 63 clubes (futebolistas
portugueses na Wikidata, para comparação: 4 521). Individuais = nacionalidade
portuguesa.

| Modalidade | Pessoas | Incluídas | — pela regra original (passagem datada) |
| --- | ---: | ---: | ---: |
| futebol | 6 045 | 4 980 | 3 913 |
| basquetebol | 1 269 | 1 226 | 54 |
| andebol | 106 | 101 | 19 |
| voleibol | 105 | 100 | 41 |
| hóquei em patins | 87 | 76 | 45 |
| rugby | 95 | 75 | 4 |
| pólo aquático | 10 | 5 | 0 |
| ciclismo | 440 | 315 | — |
| atletismo | 375 | 301 | — |
| badminton | 244 | 174 | — |
| natação | 100 | 77 | — |
| motores | 146 | 86 | — |
| ténis | 71 | 60 | — |
| remo | 90 | 57 | — |
| ginástica | 71 | 50 | — |
| judo | 41 | 38 | — |
| canoagem | 36 | 32 | — |
| desportos de combate | 49 | 29 | — |
| xadrez | 38 | 26 | — |
| vela | 58 | 24 | — |
| desporto adaptado | 32 | 23 | — |
| esgrima | 61 | 16 | — |
| triatlo | 20 | 16 | — |
| surf | 19 | 13 | — |
| tiro | 54 | 13 | — |
| desportos de inverno | 13 | 11 | — |
| ténis de mesa | 10 | 8 | — |
| golfe | 9 | 6 | — |
| MMA | 5 | 5 | — |
| desportos radicais | 5 | 3 | — |
| snooker | 2 | 2 | — |
| padel, orientação | 0 | 0 | — |

**Datas.** No futebol há 12 044 passagens datadas, 4 só com fim e 1 459 sem
nenhuma data. Os atletas individuais quase nunca têm período de atividade
(`P2031`/`P2032`): por exemplo 5 de 375 no atletismo, 1 de 440 no ciclismo,
23 de 71 no ténis; quase todos têm data de nascimento. Com a regra original
("passagem sem datas fica de fora", e sem regra para individuais), o
futebol ficaria com 3 913 dos 4 980 jogadores (perdem-se 1 067: 988 só com
passagens sem datas e nascimento no intervalo, 77 com período de atividade,
2 só com data de fim) e nenhum atleta individual entraria.

### Regras escolhidas e custo

- **Passagem:** com início, conta se início ≤ 2024 e (fim ≥ 1999 ou sem
  fim) — a regra original com o intervalo novo; só com fim, conta se fim ≥
  1999; sem datas, conta se a pessoa estiver ativa no intervalo.
- **Pessoa ativa** (passagens sem datas e atletas individuais): pelo período
  de atividade (`P2031`/`P2032`) se existir (prevalece sobre o nascimento);
  senão, **pelo nascimento como aproximação**: idade de 15 a 40 anos algures
  em 1999–2024, isto é nascida em 1959–2009, e sem morte antes de 1999; sem
  nenhuma destas datas, fica de fora.
- **Custo:** a maioria das inclusões fora do futebol depende só do
  nascimento (por exemplo 1 079 dos 1 226 no basquetebol, 297 dos 301 no
  atletismo); a aproximação inclui quem nasceu no intervalo mas não competiu
  nele (juniores, carreiras curtas) e exclui carreiras longas (tiro, vela,
  xadrez: 41 de 54, 34 de 58 e 12 de 38 pessoas ficam de fora). No futebol
  ficam de fora 1 065 pessoas, das quais 176 tinham alguma passagem sem
  datas e 18 não tinham nenhuma data.

### Passo 2 — construção

- **Clubes** (categoria `clube`, coluna nova `modalidade`): os 63 de
  futebol mais os clubes portugueses das passagens que contam nos outros
  desportos de equipa. O "principal campeonato nacional" destas modalidades
  não é utilizável na Wikidata (exploração: `wdt:P118` liga 5 clubes à Liga
  Portuguesa de Basquetebol, 6 à de andebol, 1 à A1 de voleibol, 1 à de pólo
  aquático), por isso os clubes vêm das passagens: inclui divisões
  inferiores e alguns erros da Wikidata (por exemplo itens de futebol
  feminino ligados a jogadores de voleibol).
- **Regra das cidades:** um nome de clube de uma palavra que seja rótulo de
  município, cidade, sede de município ou distrito português não entra
  (Chaves, Fafe, Fátima/Fatima, Freamunde, Guimarães, Porto); se for o
  rótulo, usa-se a forma mais longa com 2+ palavras. Junta-se uma lista
  manual de palavras comuns com o mesmo tratamento (Aves, Estrela, Nacional,
  Naval, Real, Técnico, União, Vitória) — **decisão a confirmar pelo autor**.
  Ao contrário dos jogadores, os outros nomes alternativos de uma palavra
  dos clubes entram (32: "Benfica" não, por não ser alias; "Marítimo",
  "Belenenses", "Sporting", "SLB", "FCP", "Leixões", "Estoril", …), porque a
  regra das cidades só faz sentido se os restantes entrarem.
- **Jogadores/atletas** (categoria `jogador`, com `modalidade` e `clubes`):
  regras do vocabulário original (rótulo pt ou en; rótulo noutra língua
  sempre; nomes alternativos só com 2+ palavras, 309 descartados);
  homónimos fundidos numa linha com todos os QIDs **entre modalidades e entre
  clube e jogador** (a chave é o rótulo, qualquer que seja a categoria;
  categoria `clube|jogador` se misturar); variantes partilhadas descartadas
  (170).

**Totais:** 7 780 linhas — 133 clubes (141 QIDs) e 7 647 jogadores/atletas
(7 855 QIDs; 32 pessoas em mais de uma modalidade; 54 sem rótulo pt/en
descartadas); 179 rótulos com homónimos (173 de jogadores, 6 de clubes,
por exemplo "Sport Lisboa e Benfica" com 4 QIDs de secções), 129 deles entre
modalidades diferentes (por exemplo "Rui Silva": atletismo e basquetebol);
nenhum entre clube e jogador; 235 rótulos de uma só palavra. Por modalidade
(linhas; uma linha pode ter várias): clubes — futebol 63, basquetebol 30,
voleibol 21, hóquei em patins 15, andebol 14, rugby 7; jogadores — futebol
4 932, basquetebol 1 211, ciclismo 304, atletismo 283, badminton 172,
andebol 98, voleibol 98, motores 85, rugby 68, hóquei em patins 68, ténis
60, remo 56, ginástica 50, judo 38, canoagem 32, desportos de combate 29,
xadrez 26, vela 24, desporto adaptado 23, esgrima 16, triatlo 16, surf 13,
tiro 13, desportos de inverno 11, ténis de mesa 8, golfe 6, MMA 5, pólo
aquático 5, desportos radicais 3, snooker 2. **Todos os clubes de `CLUBES` e
de `caminho_b_clubes_url.csv` aparecem no vocabulário** (por QID). O CSV
carrega com `corpus_entities.load_vocabulary` (7 780 termos; as colunas
extra são ignoradas).

**Testes** (`tests/test_wikidata_vocabulary_alargado.py`, 14, offline, com
sessão simulada): consultas novas, regra das datas (passagem e pessoa),
regra das cidades e das palavras comuns, fusão de homónimos entre
modalidades e entre clube e jogador, seleções nacionais excluídas, não
sobrescrita do vocabulário original (checksum), reutilização do raw sem
pedidos, falha repetida uma vez e registada, carregamento por
`load_vocabulary`. Suite completa: 267 testes OK.

### Limitações

- **Cobertura da Wikidata:** épocas quase sem participantes (4 de 50);
  ligas das outras modalidades quase vazias; passagens e atletas dependem
  do que está registado (padel e orientação sem ninguém; 1 166 jogadores
  portugueses de basquetebol contra 41 judocas sugerem importações em massa
  desiguais, não a realidade desportiva).
- **Aproximação pelo nascimento:** a maioria dos atletas fora do futebol
  entra só por ela (ver custo acima).
- **Âmbito português:** atletas estrangeiros só entram por passagem por
  clube português; clubes e ligas estrangeiras ficam de fora (por exemplo
  NFL; os clubes estrangeiros de jogadores portugueses não estão em
  `clubes`).
- **Mais homónimos e mais ambiguidade:** 179 rótulos com homónimos (contra
  3 no vocabulário original) e 235 rótulos de uma palavra; os nomes de
  clube de uma palavra admitidos ("Sporting", "Estoril") e a lista manual
  de palavras comuns são decisões a rever antes de aplicar a um corpus.
- **Clubes por passagem** nas outras modalidades incluem divisões
  inferiores e erros de ligação da Wikidata.

### O 400 vem da sessão do processo, não de uma quota (2026-10-21)

Terceira repetição (16:06, 1 pedido por segundo, 400 = pausa de 10 min):
860 artigos sem falhas até às 16:35; depois, 400 em todos os pedidos. O
URL `noticia.asp?id=745057` esgotou as 3 pausas e foi marcado como falha
real às 17:05 (falso positivo, de novo pendente). Às 17:11, a partir da
mesma máquina e do mesmo IP, esse URL devolveu **200** a um `curl` e a uma
sessão Python nova, enquanto o processo longo continuava a receber 400: o
400 vem do estado acumulado da sessão HTTP do processo (cookies
reencaminhados pelo replay — o `noFrame/replay` devolve `Set-Cookie:
ASPSESSIONID…` das páginas ASP antigas, com domínio `arquivo.pt` — ou
ligações reutilizadas), não de uma quota do serviço. Em 12 capturas
`noticia.asp` testadas com uma sessão nova não se acumulou nenhum cookie,
pelo que a causa exata ficou por confirmar. Repetição parada às 17:13.

Decisão do autor e correção (`ArquivoClient`, opções desligadas por
omissão; `corpus_rdf --fase1` liga-as): cada 400 regista no log o início do
corpo da resposta e o número e tamanho dos cookies da sessão; num 400 a
sessão é renovada (cookies limpos, ligações fechadas) e o pedido repete-se
logo, e só se o 400 persistir se aplicam as pausas de 10 min e o limite de 3
por URL; os downloads deixam de guardar cookies (`store_cookies=False`;
`--guardar-cookies` mantém-nos, para diagnóstico); as esperas por erro de
ligação mantêm-se (os "connection reset" das 03:59, até com `curl`
isolado, não se explicam por cookies). Testes offline: diagnóstico,
renovação sem pausa, pausa quando o 400 persiste, sessão que recusa
cookies. Suite completa: 270 testes OK.

### Vocabulário alargado: decisões do autor e correspondência mais longa (2026-10-21)

**Decisões confirmadas.** A lista manual de palavras comuns tratadas como os
nomes de lugar (`COMMON_WORDS` em `wikidata_vocabulary_alargado.py`: Aves,
Estrela, Nacional, Naval, Real, Técnico, União, Vitória) é uma **decisão
manual do autor**, fixada no código. Os nomes alternativos de uma palavra
entram só para clubes (para jogadores continuam excluídos).

**"Benfica" sozinho (acrescento manual).** Correção ao que a secção
anterior afirma ("Benfica" não, por não ser alias): a Wikidata **tem**
"Benfica" como nome alternativo de Q131499 (Sport Lisboa e Benfica), mas
também do clube multidesportivo Q2895813 ("S.L. Benfica", que entra pelas
passagens de andebol), e a regra das variantes partilhadas descartava-o das
duas linhas. Nova tabela manual `MANUAL_CLUB_VARIANTS` (`Q131499 →
"Benfica"`), como a dos 57 clubes: aplicada depois da regra das cidades e
das palavras comuns, com prioridade sobre a regra das partilhadas (fica só
na linha do clube indicado e sai das outras). Regenerado com
`--reutilizar-raw` (0 pedidos): a única diferença no CSV é "Benfica" nas
variantes de "Sport Lisboa e Benfica". **Limitação:** "Porto" sozinho
continua de fora (é a cidade), pelo que o vocabulário só encontra o FC Porto
por formas com mais de uma palavra ("FC Porto", "Futebol Clube do Porto").

**Oriental e Lank Vilaverdense (por fixar; dados para a decisão).**

| Termo da Fase 1 | QID atribuído | Rótulo / sede / liga na Wikidata | Como aparece no Record |
| --- | --- | --- | --- |
| Sporting Clube Oriental | Q2749186 | Clube Oriental de Lisboa; Lisboa; II Divisão (P118); fundado em 1946 | `…/campeonato-de-portugal/oriental/…` e `…/portugal-prio/oriental/…` (6 URLs, 2017–2018), títulos "… - Oriental - Jornal Record" |
| Lank Vilaverdense | Q7930110 | Vilaverdense Futebol Clube; Vila Verde; III Divisão (P118); fundado em 1953 | `…/2--liga/lnk-vilaverdense/…` (4 URLs, 2024), títulos "… - Länk Vilaverdense - Jornal Record" |

O Oriental do Record é o clube de Lisboa (Q2749186); o nome do termo da
Fase 1, "Sporting Clube Oriental", não é o nome do clube (o Record usa
"Oriental"; a Wikidata, "Clube Oriental de Lisboa"). Para o Länk
Vilaverdense, a Wikidata tem dois itens "Vilaverdense FC": Q7930110
(masculino, o atribuído) e Q28225985 (**feminino**), e é este último que
tem os nomes alternativos "Länk Vilaverdense" e "Länk". As notícias do
Record (2.ª Liga, transferências para o Tondela) referem-se à equipa
masculina. Nenhuma das formas usadas pelo Record ("Oriental", "Länk
Vilaverdense") está hoje no vocabulário.

**Correspondência mais longa em `count_mentions` (preparada, por ligar).**
Hoje cada variante conta em todas as posições, mesmo dentro de outra mais
longa ("Sporting de Braga" conta também "Sporting"). Nova opção
`longest_match` (então `--correspondencia-mais-longa`, desligada; ligada por omissão desde 2026-10-22, ver abaixo):
em cada posição conta só a variante mais comprida, e a leitura continua
depois dela; empates contam todos. Verificado sobre o corpus de 125 artigos
com o vocabulário **antigo**, em memória (sem escrever outputs): por
omissão, o código reproduz `output/corpus_entities.csv` exatamente (427
linhas); com a regra ligada mudam 2 linhas, ambas falsos positivos
corrigidos — "Rodrigo Moreno Machado" (variante "Rodrigo") deixa de
aparecer no artigo FC Porto B–SC Braga B, onde as 308 ocorrências em 44
capturas eram todas "Rodrigo Pinho" (outro jogador do vocabulário, que
continua contado); "Danilo Luiz da Silva" passa de 4 para 3 ocorrências
num artigo da Taça das Confederações (uma era "Danilo Pereira"). Testes:
regra ligada e desligada, nome curto dentro do de outro jogador, um rótulo
uma só vez por posição. Suite completa: 274 testes OK. O vocabulário novo
não foi aplicado a nenhum corpus.

### Evidência do 400: cabeçalho `Cookie` demasiado grande (2026-10-21)

Repetição de diagnóstico (20:07, `--guardar-cookies`, 1 pedido por segundo,
renovação da sessão ligada): o primeiro 400 chegou às 20:27, ao fim de 20
minutos e cerca de 660 artigos. Diagnóstico registado no momento: **166
cookies na sessão, 7 800 bytes no cabeçalho `Cookie`**; corpo da resposta:
"400 Bad Request — Your browser sent a request that this server could not
understand" (a página de erro do Apache, que é a que o Apache devolve
quando um campo do cabeçalho passa o limite, por omissão 8 190 bytes; não
vem a frase "Request Header Or Cookie Too Large", que é a do nginx). A
sessão foi renovada e o pedido repetido de imediato, e a recolha continuou
sem nenhuma pausa nem falha (680 artigos às 20:30). Causa confirmada: o
`noFrame/replay` reencaminha os `Set-Cookie` das páginas arquivadas (por
exemplo `ASPSESSIONID…` do site ASP antigo), com domínio `arquivo.pt`; a
sessão acumulava-os e, perto dos 8 KB, o servidor passava a recusar todos
os pedidos dessa sessão. Explica o padrão observado: os 400 só apareciam
depois de muitos pedidos, nunca em pedidos isolados, e começavam nos
`noticia.asp`. O "connection reset" das 03:59 (também com `curl` isolado)
não se explica por isto e continua com a sua própria espera.

Diagnóstico parado às 20:30 e recolha relançada **sem cookies** (modo
normal do `--fase1`), sobre os 30 016 artigos pendentes.

### Correspondência mais longa ligada por omissão; Caminho B regenerado (2026-10-22)

Decisão do autor: a regra da correspondência mais longa passa a ser a de
omissão em `count_mentions` (`--correspondencia-simples` repõe a contagem
anterior). `corpus_body.py`, a avaliação histórica da variante c′, fixa
`longest_match=False`, para os números publicados continuarem
reproduzíveis.

**Comparação antes/depois** (corpus de 125 artigos, vocabulário antigo,
corpo do artigo; as duas execuções feitas primeiro numa pasta temporária,
com os outputs oficiais intactos; a execução sem a regra reproduz o CSV
oficial anterior byte a byte). Mudam 2 das 427 linhas, ambas **falsos
positivos corrigidos**:

| Artigo | Entidade | Antes | Depois | Causa |
| --- | --- | --- | --- | --- |
| FC Porto B 1-3 SC Braga B (2.ª Liga) | Rodrigo Moreno Machado | 44 capturas, 308 ocorrências | linha removida | as ocorrências de "Rodrigo" eram todas "Rodrigo Pinho", outro jogador do vocabulário (continua contado) |
| "Danilo: Nova Zelândia tem bons argumentos…" (Taça das Confederações) | Danilo Luiz da Silva | 4 ocorrências | 3 | uma era "Danilo Pereira" |

Pares artigo–entidade: **119 → 118** pela regra fraca e **113 → 112** pela
de persistência ("sem tema": 69/63 → 68/62); "Rodrigo Moreno Machado" passa
de 2 artigos para 1. Outputs oficiais regenerados: `output/corpus_entities.csv`
(426 linhas), `output/corpus_entities_summary.md`,
`output/corpus_entities.ttl` e `output/corpus_entities_rdf_summary.md`
(`corpus_articles.ttl` intacto, checksum). No Turtle: **1 `Mencao` a menos
(119 → 118)**, ou seja, menos 9 triplos, mais a troca do literal de
ocorrências do Danilo (4 → 3). O total passa de 1 703 para **1 734
triplos** porque o Turtle versionado era anterior às subclasses OWL de
`Tema` (`0009a21`, que não o tinha regenerado): essas acrescentam 40
triplos (um `a sdh:Clube`/`Competicao`/`Modalidade`/`Secao` por cada nó
`Tema`), independentes desta regra.

### Clubes manuais: Oriental e Länk Vilaverdense (2026-10-22)

Decisão do autor, acrescentada a `MANUAL_CLUB_VARIANTS` (regenerado com
`--reutilizar-raw`, 0 pedidos; as únicas diferenças no CSV são estas duas
linhas):

- **Q2749186, Clube Oriental de Lisboa** (Lisboa; P118 = II Divisão;
  sem nome oficial P1448 na Wikidata): variantes "Clube Oriental" e
  "Oriental de Lisboa". **Nunca "Oriental" sozinho** — palavra comum
  ("Timor Oriental", "Europa Oriental"), embora seja a forma que o Record
  usa nos títulos e URLs.
- **Q7930110, Vilaverdense Futebol Clube** (Vila Verde; P118 = III Divisão;
  sem P1448): variantes "Länk Vilaverdense" e "Vilaverdense FC" (o rótulo
  "Vilaverdense Futebol Clube" já é a forma principal). **Nunca
  "Vilaverdense" sozinho** (gentílico de Vila Verde).

**Limitação:** a equipa feminina (Q28225985, "Vilaverdense FC", que é na
Wikidata o item com os nomes alternativos "Länk Vilaverdense" e "Länk")
usa o mesmo nome; o texto não distingue as duas, e uma menção a "Länk
Vilaverdense" conta sempre para o Q7930110 (masculino), que é a equipa das
notícias do Record na 2.ª Liga em 2024.

### Contentor do corpo no HTML por esquema de URL e época (medição, 2026-10-22)

Sem pedidos à rede e sem tocar na recolha em curso. Amostra de 20 capturas
por esquema de URL entre os HTML já descarregados pelo `corpus_rdf --fase1`
(`data/raw/original_html/`; a captura mais antiga de Artigos escolhidos ao
acaso; scripts e lista da amostra em `data/raw/original_html/_scripts/`).
Um contentor conta como encontrado se tiver ≥ 30 palavras e as suas
primeiras 8 palavras estiverem no texto extraído da mesma captura (o texto
que o corpus usa). O extrator ainda não foi implementado.

**Disponibilidade:** só `/detalhe/`, `/amp/` e `noticia.asp` têm HTML em
disco. `noticia.aspx` (0 de 3 814), `shownews.asp` (0 de 8 410),
`tn0cs.asp` (0 de 1 695) e `tn1cs.asp` (0 de 665) ainda não têm nenhum: as
suas capturas estavam na zona dos 400 e a recolha só lá chega depois dos
`noticia.asp`. Ficam por medir quando houver HTML.

| Esquema | Época | Contentor do corpo | Encontrado |
| --- | --- | --- | --- |
| `/detalhe/` | 2017 | `div.row.article-body` > `div#readerBody.article-main` | 4/4 |
| `/detalhe/` | 2018–2024 | `div.text_container` | 12/16 (2018: 1/4; 2019: 1/1; 2020: 4/4; 2021: 2/2; 2022: 1/1; 2023: 1/1; 2024: 2/3) |
| `/amp/` | 2018–2020 | `div.bodybox` | 19/20 (mediana 130 palavras) |
| `noticia.asp` | 2002–2007 | tag própria `<aux>` (em 2007 dentro de `span.apreto12n`, numa célula `td[width=600]`; antecedida pelo comentário `ENDParams …Noticia`) | 19/19 com texto extraído (2002: 4/4; 2006: 8/8; 2007: 7/7) |

As falhas explicam-se todas:

- **`/detalhe/` 2018 (3) e 2024 (1):** 2 são páginas AMP dentro do
  `/detalhe/` (`…/detalhe/amp/…`), com o template AMP (o contentor certo é
  `bodybox`): o template depende da página, não só do esquema de URL; 2
  são **Premium** (2018 sem corpo, com `article-premium`; 2024 com o
  `text_container` reduzido ao teaser, 29 palavras, e `container_assinatura`)
  — ficar sem corpo é o resultado correto.
- **`/amp/` 2020 (1):** fotogaleria cujo `bodybox` tem só a descrição (27
  palavras, abaixo do limiar). `div.mainBox` existe nas 20, mas engloba mais
  do que o corpo (mediana 212 palavras contra 130 do `bodybox`).
- **`noticia.asp` 2001 (1):** o texto extraído desta captura está vazio,
  pelo que não há como validar (o `<aux>` existe, com 63 palavras); é a
  única captura de 2001 na amostra.

Duas notas para o extrator: no `noticia.asp` a página declara
`iso-8859-1` (a primeira medição deu 6/7 em 2007 por ter descodificado como
UTF-8; com a codificação declarada, 7/7); e em todas as 20 capturas
`noticia.asp` a variante c′ não encontra corpo no texto extraído, porque o
título da página é genérico (":.: Jornal Record :.:") e a c′ ancora o corpo
no título — para o site de 2000–2009, o HTML é a única via medida até agora
para isolar o corpo.

## Caminho B sobre o corpus da Fase 1: leitura do grafo (implementada, não corrida; 2026-10-22)

### Problema

`load_corpus()` (`corpus_redundancy.py`), usado pelos Caminhos D e B e pelo
teste de candidatos, só lia o Turtle do corpus de 125 artigos e exigia
`sdh:contentLength` (com `int(...)`) e, para a Camada 1, `statusCode == 200`.
O grafo do corpus da Fase 1 não tem nenhum dos dois, nem `digest` fiável (a
TextSearch não os devolve; "RDF a partir só da Fase 1"): a leitura falhava. O
Turtle desse corpus (2,2 milhões de triplos) também é pesado de carregar
inteiro em `rdflib` só para tirar os poucos triplos usados.

### Alterações

- `load_corpus()` aceita o N-Triples apendável que o `corpus_rdf --fase1`
  escreve (`data/processed/corpus_articles_<etiqueta>_triples.nt`), lido em
  streaming (`W3CNTriplesParser` com um sink que só guarda os triplos usados).
  Um artigo refeito numa repetição aparece duas vezes nesse ficheiro
  (primeiro sem texto, depois com texto): as capturas juntam-se, não se
  duplicam. O Turtle continua a ser lido como antes.
- `Capture`: `digest` e `content_length` podem faltar; a Camada 1 aceita
  `statusCode` ausente (conta o facto de haver texto). Um `statusCode`
  registado diferente de 200 continua a excluir a captura. **Sem efeito no
  corpus de 125 artigos**, verificado no `output/corpus_articles.ttl`
  versionado: as 941 capturas têm `statusCode`, `contentLength` e `digest`, e
  as 793 com texto são todas 200.
- `Capture.html_path`: o HTML em bruto da mesma captura, se existir, procurado
  em `data/raw/original_html/` com o nome do ficheiro de texto (a convenção
  do `ArquivoClient`; o grafo não regista o caminho do HTML). Ainda não é
  usado: é o encaixe para o extrator do corpo pelo contentor do HTML.
- `corpus_entities`, `corpus_entities_rdf` e `corpus_candidate_entities`
  ganham `--corpus ETIQUETA`: leem o N-Triples desse corpus e escrevem
  `output/<saída>_<etiqueta>*`, sem tocar nas saídas oficiais do corpus de
  125 artigos. `corpus_entities_rdf` ganha `--vocabulario` (tem de ser o
  vocabulário que gerou o CSV) e obtém os `Artigo` do grafo pela mesma
  leitura em streaming.
- `clube_coerente`: no corpus da Fase 1 há muitos clubes no URL fora de
  `caminho_b_clubes_url.csv`; com `--corpus`, um slug sem correspondência dá
  `sem_mapa` em vez de erro, e o resumo lista esses slugs e o número de
  artigos de cada um, para a tabela poder ser alargada. No corpus de 125
  artigos o erro mantém-se. Uma entidade da categoria `clube` (vocabulário
  alargado) compara-se pelo próprio rótulo com o clube do URL.
- O resumo do teste de candidatos lista só os 200 primeiros; o CSV tem todos.

### Escala (medida com um grafo sintético, não com o real)

Um N-Triples sintético com 129 317 artigos e 1 810 438 triplos, gerado pelo
mesmo `build_article_history_graph`, foi lido em 34 s com um pico de 370 MB
de memória (sessão remota Linux). Os textos (~95 000 ficheiros, ~1,1 GB
estimados) somam-se a isto; não medido.

### Testes e o que não foi feito

11 testes novos em `tests/test_phase1_corpus_reading.py`, com um N-Triples
escrito como o do `corpus_rdf --fase1`: captura sem `statusCode`/
`contentLength`/`digest` na Camada 1, `html_path` presente e ausente,
artigo repetido no ficheiro apendável, Turtle e N-Triples a darem o mesmo
corpus, `statusCode` 404 ainda excluído, caminhos iguais aos do
`corpus_rdf`, `sem_mapa` e coerência de uma entidade clube, e execuções
etiquetadas de B, do RDF de B e do teste de candidatos que não criam as
saídas oficiais. Suite completa: **286 testes, todos a passar.**

**Nada foi corrido sobre o corpus real** (os textos não estão nesta sessão).
O Caminho D não foi adaptado: no corpus da Fase 1 cada artigo tem uma só
captura, por isso não há redundância entre capturas a anotar. A extração do
corpo continua a ser a c′; o extrator pelo contentor do HTML é o passo
seguinte.

## Corpo do artigo pelo contentor do HTML (implementado, validado só com HTML sintético; 2026-10-22)

### Medição de partida (sessão local, sem rede, HTML já em disco)

20 capturas por esquema, esqueletos em `output/html_corpo_templates.md` (fora
do Git). Contentor do corpo: `div.article-body > div#readerBody` em
`/detalhe/` 2017 (4/4); `div.text_container` em `/detalhe/` 2018–2024
(12/16: 2 são páginas AMP dentro de `/detalhe/` — o template depende da
página, não só do esquema de URL — e 2 são Premium, sem corpo, o resultado
certo); `div.bodybox` em `/amp/` 2018–2020 (19/20; a falha é uma
fotogaleria de 27 palavras); a tag `<aux>` em `noticia.asp` 2002–2007
(19/19; a captura de 2001 não tem texto para validar). **A c′ não encontra
corpo em nenhuma das 20 `noticia.asp`**: para o site de 2000–2009 o HTML é a
única via medida. Por medir: `noticia.aspx`, `shownews.asp`, `tn0cs.asp` e
`tn1cs.asp` (ainda sem HTML em disco).

Codificação: em 2017–2024, `<meta charset="utf-8">` e bytes UTF-8; em
`noticia.asp` a declaração (`iso-8859-1`, ou nenhuma) nem sempre é fiável —
em 2002, UTF-8 em 3 de 4 páginas declaradas `iso-8859-1`; 2006–2007 latin-1.

### Implementação (`src/semantic_harvester/html_body.py`)

Segue a decisão de 2026-10-19 ("Decisão de design (híbrido, não
substituição da heurística)"): a c′ continua a ser o método principal; o
HTML serve para (1) detetar Premium e (2) recuperar o corpo quando a c′ não
o encontra.

- Contentores tentados por ordem, em qualquer esquema de URL:
  `div#readerBody`, `div.text_container`, `div.bodybox`, `<aux>` (todas as
  `<aux>` da página, pela tag e não pela classe do `span`, que muda com a
  época).
- Dentro do contentor retiram-se os blocos medidos que não são corpo:
  `script`, `style`, `noscript`, `iframe`, `button`, `amp-analytics`,
  `amp-ad`, `figure` (foto e crédito), `h1`, `h2.subtitle`;
  `div#escondec.lerMaisCont` ("Continuar a ler"), `div#relacContainer`,
  `p.autorDetalhe`; `div.pub_inside_text`, `div#incontent`;
  `ul.texto_socialShare`, `div.adbox`, `span.texto_autor`,
  `div.container_assinatura`. `div#restText` (o resto do corpo de 2017)
  fica.
- Sobre o texto do contentor aplicam-se os 14 marcadores de chrome da c′,
  mais "Relacionadas" (blocos de chrome dentro do `bodybox` das AMP em
  `/detalhe/`: "Relacionadas", "O Record recomenda para si", "Últimas
  Notícias").
- Premium: classe `container_assinatura` ou `article-premium` em qualquer
  ponto da página (a classe `paywall` aparece também em artigos gratuitos e
  não conta).
- Codificação: UTF-8 estrito e, se falhar, latin-1.
- HTML mal fechado (site antigo): uma tag de fecho fecha tudo até à
  correspondente, se estiver aberta; senão é ignorada.

Ligação ao Caminho B e ao teste de candidatos: `--texto corpo-html`
(`to_body_corpus(use_html=True)`). Por captura com texto: Premium no HTML →
sem corpo (`premium`); senão a c′ (`c′`); se a c′ não encontrar corpo, o
contentor do HTML (`html:<contentor>`); senão `sem_corpo`. O resumo do B
conta capturas por origem do corpo. Sem `corpo-html` nada muda, incluindo
os resultados oficiais. O HTML só é encontrado para capturas com texto (o
caminho do HTML deriva do nome do ficheiro de texto).

`python -m semantic_harvester.html_body FICHEIROS...` mostra, por ficheiro,
contentor, Premium, número de palavras e início do corpo — para validar nos
HTML reais.

### Testes e o que não foi feito

14 testes novos (13 em `tests/test_html_body.py`, 1 em
`tests/test_phase1_corpus_reading.py`), com HTML **sintético** que imita a
estrutura medida: cada template e os seus blocos a retirar, cortes de chrome
no `bodybox`, `<aux>` em latin-1 com tags por fechar, UTF-8 com declaração
`iso-8859-1` errada, Premium e `paywall`, página sem contentor, a ordem
c′ → HTML → sem corpo, e uma notícia `noticia.asp` em que a entidade só é
encontrada pelo HTML. Suite completa: **300 testes, todos a passar.**

**Não validado em HTML real** (não está nesta sessão): falta correr o
comando acima sobre as amostras da medição e comparar com os esqueletos.
Os esquemas `noticia.aspx`, `shownews.asp`, `tn0cs.asp` e `tn1cs.asp` não
foram medidos; se tiverem outro contentor, a lista tem de crescer.

### Validação em HTML real e correções (2026-10-22)

A sessão local correu `python -m semantic_harvester.html_body` sobre as
mesmas 60 capturas da medição (saída em
`output/html_body_validacao_cli.tsv`, fora do Git), sem alterar código.
Contentor certo: `readerBody` 4/4; `text_container` 13/14 (a 14.ª é um
Premium de 2018 sem corpo, correto); `bodybox` 20/20; AMP dentro de
`/detalhe/` 2/2; `<aux>` 20/20. Premium certo em todas: 7 detetados, que são
exatamente as 7 páginas com `container_assinatura` ou `article-premium`.
Em 2021–2024 a frase "exclusiva para assinantes" está num modal escondido em
todas as páginas e não serve de sinal; a classe sim.

Falhas e correção de cada uma (um teste de regressão por falha, em
`tests/test_html_body.py`):

1. **Dois `text_container`** (1 de 3 em 2024): o primeiro é um destaque
   promocional (15 palavras em vez de 116). Agora usa-se o mais longo dos
   contentores iguais da página (as `<aux>` continuam a juntar-se).
2. **Corte a mais** (2 em 2020, 1 em 2021): um `div.relacionadas` (título
   `h2.moduleTitle` "Relacionadas") a meio do corpo fazia cortar tudo a
   partir dali (75 palavras em vez de 444). Agora o elemento é saltado; o
   corte por "Relacionadas" mantém-se para os blocos das AMP em
   `/detalhe/`, que foram bem cortados.
3. **"Continuar a ler" em 2018**: a classe é `lerMais` (botão
   `a.btLerMais`), não `lerMaisCont`. Acrescentadas.
4. **"Deixe o seu comentário" e "PUB Comentar"** no fim do `bodybox` (18 de
   20, e as 2 AMP em `/detalhe/`): `div.comentarBtn` e
   `div.detalheAds > div.pub`. Acrescentadas.
5. **Fotogalerias e vídeos AMP** (3): o texto está no `h2.subtitle`, que era
   descartado, e sobrava só "Deixe o seu comentário". **Decisão:** o
   subtítulo passa a contar como corpo — é texto editorial da própria
   notícia (o lead), não chrome, e não traz menções de outras notícias. O
   `div.videoElement_description` não foi tratado: não se sabe onde está na
   página; a confirmar.
6. **Pontuação no `<aux>`** (4 de 15, 2006–2007): a alternativa ao UTF-8 era
   latin-1, que transforma “ ” ’ – (bytes 0x80–0x9F) em caracteres de
   controlo. Agora tenta-se UTF-8, depois cp1252 e só por fim latin-1. As
   letras acentuadas já estavam certas em todos os anos.

O teaser dos Premium (30 palavras em 2024, com `premium=True`) não é usado:
no `--texto corpo-html` uma captura Premium fica sem corpo, como na decisão
de 2026-10-19. Suite completa depois das correções: **306 testes, todos a
passar.** Falta repetir a validação nos HTML reais com estas correções.

## Protótipo principal para o corpus da Fase 1 (implementado, gerado só com dados sintéticos; 2026-10-22)

### Decisões do autor

- **Um protótipo principal para o corpus alargado.** O protótipo do corpus
  de 125 artigos (`navigation_prototype.py`) fica como está: é o único
  corpus com várias capturas por artigo, e por isso o estudo de caso da
  profundidade temporal.
- **A página principal é um painel, não uma lista**: 129 317 artigos numa
  lista não são navegáveis. A lista aparece filtrada, paginada (50 por
  página), por baixo dos resumos.
- **Preenchimento de modalidade e clube, com a origem registada**: os URLs
  do site de 1999–2009 não têm caminho temático (74 076 Artigos sem
  modalidade no URL). Modalidade: pelo URL; sem ela, pelos termos de
  pesquisa de modalidade que encontraram o artigo na Fase 1. Clube: pelo
  URL; sem ele, pelos clubes mencionados no texto (vocabulário alargado).
  Na página, os valores preenchidos assim aparecem marcados ("termo de
  pesquisa", "no texto").

### Implementação

- `navigation_corpus.py` lê, sem rede: o N-Triples do corpus da Fase 1 em
  streaming (URL, título do `Artigo`, captura, texto); as saídas etiquetadas
  do Caminho B (`corpus_entities_por_ano.csv` e o novo
  `corpus_entities_por_ano_corpo.csv`, com a origem do corpo por captura,
  escrito pelo `corpus_entities` sempre que pesquisa o corpo); o
  vocabulário (QID, categoria, modalidade); a tabela slug → clube (com QID);
  e o CSV de capturas da Fase 1 (termos de pesquisa por URL, juntando
  variantes por `normalize_for_grouping`). **Não usa SPARQL**, ao contrário
  do protótipo de 125 artigos: carregar 2,2 milhões de triplos em `rdflib`
  só para os consultar seria lento e pesado; os dados vêm do mesmo grafo,
  lido em streaming.
- Clubes e entidades identificados pelo QID quando o rótulo não é
  homónimo: o clube do URL (pela tabela) e o mesmo clube mencionado no texto
  são o mesmo filtro. Rótulos homónimos ficam `h:<rótulo>`, sem QID.
- Época do site pelo esquema de URL: 1999–2000 (`tn0cs`/`tn1cs`),
  2000–2009 (`noticia.asp`, `shownews.asp`, `noticia.aspx`), 2017–2024
  (`/detalhe/`, `/amp/`).
- Saída em `output/prototipo_<etiqueta>/`: `index.html` (página única, sem
  dependências nem servidor; CSS e JavaScript embutidos), `data.js` (uma
  linha compacta por artigo, carregada por `<script>` para funcionar em
  `file://`) e `resumo.md` (tabelas para as conclusões: artigos por ano e com
  entidade, origem do corpo por época, modalidades, clubes e atletas mais
  mencionados, origem do preenchimento).
- A página: indicadores, artigos por ano (com a lacuna escrita por extenso),
  clubes e atletas mais mencionados (com uma entidade escolhida, passam a ser
  as co-menções), modalidades, época do site e origem do corpo — cada resumo
  calculado com todos os filtros menos o seu, e clicável para filtrar;
  filtros por ano, época, modalidade, clube, entidade e pesquisa no título
  (sem acentos nem maiúsculas); ficha da entidade com ligação à Wikidata;
  cada artigo ligado à sua captura no Arquivo.pt
  (`https://arquivo.pt/wayback/<tstamp>/<URL>`). O estado fica no endereço
  (`#entidade=Q131499&ano=2019`). Modo escuro e telemóvel.

### Verificação

7 testes offline em `tests/test_navigation_corpus.py` (ordem e título dos
artigos, época, modalidade pelo URL e pelo termo — a partir da variante
`http://` e do termo acentuado —, clube pelo URL e pelo texto com o mesmo QID,
slug sem mapa, entidades por QID, origem do corpo, página e resumo). Suite
completa: **313 testes, todos a passar.**

No Chromium (sessão remota), com 129 317 artigos sintéticos (`data.js` de
20 MB): carregamento em 1–2 s, cada filtro em ~130 ms; filtros, pesquisa,
paginação, ligações diretas por endereço (incluindo um homónimo e uma
modalidade inexistente, que dá 0), ficha de entidade, títulos com HTML
escapado, modo escuro e largura de telemóvel (390 px, sem scroll
horizontal), sem erros de JavaScript.

**Ainda não gerado com os dados reais**: depende do fim da recolha e da
corrida do Caminho B com `--corpus por_ano --texto corpo-html`.

## Abordagem híbrida: candidatos confirmados na Wikidata (implementada, não corrida; 2026-10-22)

### Decisões do autor

Avançar com a abordagem híbrida discutida em "Candidatos a entidade fora do
vocabulário fechado", numa versão limitada (um dia de trabalho), com:

- tipos aceites: **clubes, atletas, treinadores, estádios e competições**
  (árbitros não);
- competições internacionais **incluídas** quando organizadas pela UEFA,
  FIFA ou COI, pelas provas europeias e mundiais em que jogam clubes e
  seleções portugueses;
- mínimo de artigos para um candidato ser procurado: "2 ou 3" — fixado em
  **3 por omissão**, com `--min-artigos 2` disponível.

### Como responde às duas objeções iniciais

1. *Detetar candidatos exige reconhecimento genérico*: usa-se a heurística
   já existente (sequências capitalizadas fora do início de frase), sem NER,
   e só para nomes repetidos em vários artigos.
2. *Cada tipo precisa de validação própria*: a regra é explícita e igual
   para todos — nome exato, um único item, tipo permitido, ligação a
   Portugal. Na dúvida, o candidato fica de fora.

### Regra (`src/semantic_harvester/wikidata_candidates.py`)

Para cada candidato com pelo menos `--min-artigos` artigos, um pedido SPARQL
procura itens com esse nome exato como rótulo ou nome alternativo, em pt ou
en, e classifica-os:

| Tipo (categoria) | Classe na Wikidata | Ligação a Portugal |
| --- | --- | --- |
| treinador | humano (`Q5`) com ocupação ⊑ treinador (`Q41583`) | nacionalidade (`P27`) Portugal, ou passagem (`P54`) / treinador de (`P6087`) equipa com país Portugal |
| jogador | humano com ocupação ⊑ atleta (`Q2066131`) | nacionalidade Portugal, ou passagem por equipa com país Portugal |
| clube | ⊑ clube desportivo (`Q847017`) | país (`P17`) Portugal |
| estadio | ⊑ recinto desportivo (`Q1076486`) | país Portugal |
| competicao | ⊑ competição desportiva (`Q13406554`), liga (`Q623109`) ou evento multidesportivo (`Q167170`) | país Portugal, ou organizador (`P664`) UEFA (`Q35572`), FIFA (`Q253414`) ou COI (`Q40970`) |

Decisão por candidato (`output/wikidata_candidatos_<etiqueta>.csv`):
`aceite` (um só item válido, novo); `variante_nova` (um só item válido que
já está na lista fechada: o candidato era uma forma em falta);
`ambiguo` (mais de um item válido); `fora_do_ambito` (tipo certo, sem
ligação a Portugal); `tipo_nao_aceite`; `sem_correspondencia`;
`falha_pedido`. Um item de vários tipos fica com o primeiro de clube,
estádio, competição, treinador, jogador (um ex-jogador que treina fica
treinador). **Os QIDs das classes e organizadores acima foram escritos sem
consulta à Wikidata nesta sessão (sem acesso) e têm de ser confirmados na
primeira execução** (por exemplo, que o Estádio da Luz, a Taça de Portugal
e a Liga dos Campeões são aceites).

Vocabulário híbrido (`data/processed/caminho_b_vocabulario_hibrido_<etiqueta>.csv`):
a lista alargada intacta mais os confirmados, com a coluna `origem`
(`lista_fechada`, `candidato`, `lista_fechada+candidato`). Uma entidade nova
fica com o rótulo pt da Wikidata se tiver 2+ palavras e não for já forma de
outra linha; senão com a forma vista no texto; todas as formas do texto
ficam como variantes; vários candidatos do mesmo QID ficam numa linha. O
vocabulário alargado não é alterado.

### Ligações ao resto

- Caminho B: corre com o vocabulário híbrido como com qualquer outro.
  `clube_coerente` passa a `nao_aplicavel` para treinadores, estádios e
  competições (não têm clubes no vocabulário); o comentário de
  `sdh:clubeCoerente` na ontologia passa a listar os cinco valores
  (incluindo `sem_mapa`, de "Caminho B sobre o corpus da Fase 1").
- RDF: **propriedade nova** `sdh:origemVocabulario` (domínio
  `EntidadeMencionada`, `xsd:string`), escrita só quando o vocabulário tem a
  coluna `origem`; os outputs oficiais do corpus de 125 artigos não mudam
  (o vocabulário original não a tem).
- Painel: lista própria de treinadores, estádios e competições (os atletas
  ficam só atletas); a ficha da entidade mostra a origem; `resumo.md` ganha
  a tabela desses tipos e a das origens.

### Testes e o que falta

12 testes novos (10 em `tests/test_wikidata_candidates.py`, com respostas
SPARQL simuladas: aceite, variante nova, ambíguo, fora do âmbito, tipo não
aceite, sem correspondência, falha, mínimo de artigos, fusão de duas formas
do mesmo estádio, vocabulário alargado intacto; 1 de RDF/coerência e 1 do
painel), mais a sintaxe da consulta verificada pelo parser SPARQL do
`rdflib` e a página verificada no Chromium. Suite completa: **325 testes,
todos a passar.**

**Não corrido.** Ordem prevista, na sessão local, depois da recolha:
`corpus_entities` e `corpus_candidate_entities` com o vocabulário alargado
(`--corpus por_ano --texto corpo-html`); `wikidata_candidates --corpus
por_ano`; rever à mão uma amostra de ~50 aceites (descritivo); `corpus_entities`
e `corpus_entities_rdf` com o vocabulário híbrido; `navigation_corpus` com o
vocabulário híbrido. Para comparar "só lista fechada" com "lista fechada +
híbrida", guardar as saídas da primeira passagem antes da segunda.

### Verificação com 8 nomes conhecidos e regras revistas (2026-10-22)

A sessão local correu a consulta inicial contra a Wikidata com 8 nomes, sem
gravar nada no projeto. Só 3 deram o esperado (Jorge Jesus → treinador
Q527550; Jogos Olímpicos → competição Q5389; Real Madrid → fora do âmbito).
Os outros 5 falharam por duas razões, não pelos QIDs das classes:

- **Dois itens válidos com o mesmo nome** → `ambiguo`: Estádio da Luz
  (Q2736585 e Q7875112, ambos estádio em Portugal), Estádio José Alvalade
  (Q287359, o atual, e Q3059094, o de 1956, "defunct sports venue"), Taça de
  Portugal (Q29224, futebol, e Q2718266, râguebi) e Sérgio Conceição
  (Q317298, o treinador, e Q86922080, outra pessoa; um terceiro item é uma
  página de desambiguação e não conta).
- **O nome no texto não é o rótulo**: "Liga dos Campeões" só existe como
  rótulo pt de uma página de desambiguação; a competição da UEFA chama-se
  "Liga dos Campeões da UEFA" → `tipo_nao_aceite`.

Regras revistas (`wikidata_candidates.py`):

1. **Desempate por proeminência**: entre vários itens válidos, aceita-se o
   que tem mais artigos na Wikipédia (`wikibase:sitelinks`) **só se tiver
   pelo menos o dobro do segundo** (coluna `desempate`: `unico` ou
   `proeminencia`); senão continua `ambiguo`. É um critério de popularidade
   comum em ligação de entidades; não usa o contexto do artigo.
2. **Pesquisa como segunda tentativa**: se o nome exato não der nenhum item
   válido, repete-se com a pesquisa da Wikidata (`EntitySearch`, rótulos e
   nomes alternativos que começam pelo nome, 20 resultados), com as mesmas
   regras (coluna `metodo`: `nome_exato` ou `pesquisa`). Mais larga do que o
   nome exato, por isso só quando este falha.
3. **Estrangeiros aceites (decisão do autor)**: a ligação a Portugal passa a
   ser registada (coluna `portugal` nas decisões e no vocabulário híbrido;
   `sim` em toda a lista fechada) e não exigida; `--so-portugal` repõe a
   regra inicial. Justificação: a lista fechada define o domínio à partida
   (desporto português); a camada híbrida parte do que aparece de facto no
   texto, em vários artigos, e o Record cobre muito desporto internacional.

Ainda **não verificado contra a Wikidata** com as regras revistas (esta
sessão não tem acesso): que o desempate escolhe o estádio atual e a Taça de
futebol, e que a pesquisa encontra a Liga dos Campeões da UEFA. Testes com
respostas simuladas para os três casos; suite completa: **326 testes, todos
a passar.**

### Verificação das regras revistas: 12 nomes (2026-10-22)

Sessão local, contra a Wikidata, sem gravar nada no projeto: **os 12 nomes
aceites como esperado**, sem falhas de consulta.

| Nome | Tipo | QID | Portugal | Método | Desempate |
| --- | --- | --- | --- | --- | --- |
| Estádio da Luz | estadio | Q7875112 | sim | nome_exato | proeminencia |
| Estádio José Alvalade | estadio | Q287359 | sim | nome_exato | proeminencia |
| Estádio do Dragão | estadio | Q271454 | sim | nome_exato | unico |
| Taça de Portugal | competicao | Q29224 | sim | nome_exato | proeminencia |
| Liga dos Campeões | competicao | Q18756 | sim (UEFA) | pesquisa | proeminencia |
| Liga Europa | competicao | Q18760 | sim (UEFA) | pesquisa | proeminencia |
| Jorge Jesus | treinador | Q527550 | sim | nome_exato | unico |
| Sérgio Conceição | treinador | Q317298 | sim | nome_exato | proeminencia |
| Real Madrid | clube | Q8682 | não | nome_exato | proeminencia |
| Lionel Messi | jogador | Q615 | não | nome_exato | unico |
| Premier League | competicao | Q9448 | não | nome_exato | proeminencia |
| Jogos Olímpicos | competicao | Q5389 | sim (COI) | nome_exato | unico |

No Estádio da Luz o desempate escolheu o atual (Q7875112, inaugurado em
2003, sem data de demolição) e não o antigo (Q2736585, 1954–2003). Messi e
Premier League não têm rótulo pt na Wikidata: o rótulo passa a cair para o
inglês quando falta o português (teste novo). Amostra de nomes conhecidos,
escolhidos para testar as regras; não substitui a revisão de uma amostra dos
aceites na corrida real. Suite completa: **327 testes, todos a passar.**

## Contentor do corpo no `noticia.aspx` (2009) (2026-10-22)

Medição na sessão local, 20 páginas `noticia.aspx`, todas de 2009 (esqueleto
em `output/html_corpo_noticia_aspx.md`, fora do Git): nenhum dos contentores
do `html_body.py` existe (0 de 20) e a página não usa `<aux>`. O corpo está em
`table[width=980] > tr > td[width=600] > table > tr > td > span.apreto12n`
(texto com `<br>` ou `<p>`), em 15 de 20 com 30 ou mais palavras, validado
contra o texto extraído. `apreto12n` é só uma classe de tipo de letra (9 a 16
elementos por página); numa página o maior é a pergunta de uma votação
(`form#votacao`), fora da coluna `td[width=600]`. Das outras 5: 2 são tabelas
de classificação (Volta), sem texto corrido; 3 têm 1 a 21 palavras nesse
caminho e título genérico, sem corpo identificado. Codificação: 16 declaram
UTF-8, 4 nada.

**Implementação:** novo contentor `apreto12n` no `html_body.py`, tentado
depois do `<aux>`: um `span.apreto12n` dentro da coluna `td[width=600]`;
havendo vários, o mais longo (como no `text_container`). O `<aux>` continua a
ter prioridade (nas `noticia.asp` de 2007 o `<aux>` está dentro de um
`span.apreto12n`). Sem mínimo de palavras: as tabelas de classificação dão os
nomes que contêm. 3 testes novos com um esqueleto sintético (votação fora da
coluna, `span` de data curto, publicidade em `document.write`, prioridade do
`<aux>`). Suite completa: **330 testes, todos a passar.** Falta validar nas 20
páginas reais com `python -m semantic_harvester.html_body`.
