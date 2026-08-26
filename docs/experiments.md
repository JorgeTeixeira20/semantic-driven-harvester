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
