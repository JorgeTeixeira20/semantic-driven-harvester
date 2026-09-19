# Estado do projeto

Atualizado em **2026-09-16**, a partir do código, testes, documentação e histórico
até `a3208f4`. Este documento é um retrato datado, não substitui a inspeção do
checkout atual. Regras de trabalho: [AGENTS.md](../AGENTS.md); comandos:
[README.md](../README.md).

## Objetivo e âmbito implementado

O Semantic Driven Harvester é um protótipo de dissertação de Mestrado que
recolhe metadados/textos do Arquivo.pt e os representa em RDF, distinguindo
recurso Web, captura temporal e texto extraído. A implementação demonstra
pesquisa, mapeamento de uma captura editorial selecionada e histórico desse
artigo. Existem ainda experiências de caracterização da recuperação TextSearch.

## Marcos concluídos e evidência

| Marco | Estado sustentado | Referência Git |
| --- | --- | --- |
| M1 | Cliente TextSearch, preservação raw e descarga de textos; smoke test real. | `5b17fd7` (2026-08-25) |
| M2 | Ontologia base, IDs determinísticos e mapeamento RDF do sample selecionado. | `8c78391` (2026-08-25) |
| M3 | versionHistory, manifesto, métricas e RDF temporal de um artigo. | `4651860` (2026-08-26); execução documentada em 2026-08-25 |
| Profiling/diagnóstico | Seis pesquisas exploratórias e seis variantes de diagnóstico; relatórios e decisões. | `4651860` (2026-08-26) |
| Testes offline | Fixtures sintéticas e temporários substituem dependências dos raw/outputs históricos. | `a3208f4` (2026-09-16) |

## Implementação e arquitetura

O pacote [src/semantic_harvester/](../src/semantic_harvester/) contém:

- `arquivo_client.py`: cliente HTTP injetável, respostas TextSearch/versionHistory
  guardadas byte a byte e descarga/reutilização de textos.
- `history_pipeline.py`: paginação por offset, manifesto JSONL, métricas e
  orquestração do histórico; não deduplica capturas pelo digest.
- `rdf_mapper.py`: grafos RDFLib, IDs SHA-256 do URL, com `tstamp` nas URIs de
  captura/texto; um `article_id` comum às capturas do mesmo URL.
- `smoke_test.py`, `api_profiling.py`, `api_diagnostics.py`: execuções manuais
  contra a API, com parâmetros definidos nos módulos.

O fluxo é API → raw local → manifesto/metadados → Turtle. A
[ontologia](../ontology/semantic_harvester.ttl) define as classes e propriedades;
`Artigo → RecursoWeb → CapturaArquivada → TextoExtraido` resume as relações principais.
Não estão implementados NER, deduplicação semântica/local, base de dados,
frontend ou LLMs. Há parâmetros de deduplicação enviados à API; isso não é uma
implementação local de deduplicação. `EntidadeMencionada` e `Tema` existem no
vocabulário, mas não há pipeline de extração/enriquecimento correspondente.

## Experiências e resultados conhecidos

Estes são **resultados históricos documentados**, não medições novas nem
garantias sobre a API atual. Detalhes e decisões permanecem nas fontes:

- [Observações M1/M3](observations.md): M1 registou 11 resultados e 11 textos,
  sem falhas, totalizando 86 151 bytes. M3 registou 3 capturas, 2 textos
  disponíveis e 1 falha HTTP 404; metadados de uma mesma captura diferiram
  entre pesquisa e versionHistory.
- [Profiling](../output/api_profiling.md) e [CSV](../output/api_profiling.csv):
  seis pesquisas; Sporting 2015–2020 teve 33 URLs distintas, das quais 26
  continham `/detalhe/`. Esse padrão é apenas um indicador exploratório.
- [Experiência de diagnóstico](experiments.md), [relatório](../output/api_diagnostics.md)
  e [CSV](../output/api_diagnostics.csv): para Sporting 2015–2020, offsets 100
  e 200 devolveram zero itens; pedidos maxItems 100/200/2000 devolveram
  33/57/96 itens. O pedido 2000 foi reportado como 500 pela API. Omitir dedup
  acionou defaults `url/2`, não desativou deduplicação.
- [Experiência 2 — offset com página cheia](experiments.md),
  [relatório](../output/api_diagnostics_offset.md) e
  [CSV](../output/api_diagnostics_offset.csv), executados em 17 de setembro
  de 2026: para a query `futebol` sem `siteSearch` e sem dedup explícito
  (`maxItems=20`, 2015–2020), as cinco janelas testadas (offsets 0, 20, 40,
  100 e 200) vieram todas cheias (20/20) com `next_page` presente e
  resultados distintos das janelas anteriores — incluindo nos offsets 100 e
  200, que na Experiência 1 tinham devolvido zero. Isto é consistente com a
  hipótese de que aquele resultado vazio refletia o esgotamento dos
  resultados materializados para a pesquisa específica da Experiência 1, não
  uma limitação geral de `offset`. Uma tentativa preliminar (`Sporting`, sem
  `siteSearch`, dedup `url/1` explícito) não chegou a produzir página cheia;
  os seus raw e relatórios ficaram preservados com o prefixo/sufixo `pilot`.
- [Experiência 3 — volume de queries genéricas](experiments.md),
  [relatório](../output/api_diagnostics_site_volume.md) e
  [CSV](../output/api_diagnostics_site_volume.csv), executados em 17 de
  setembro de 2026: com `siteSearch=record.pt` e `maxItems=20`, nem a query
  específica `Sporting` (3, 5 e 7 resultados em três tentativas) nem as
  genéricas `futebol`/`desporto` (2 resultados em todas as tentativas)
  encheram a página. Um termo genérico não resolveu o problema de página
  incompleta enquanto a pesquisa continuar restrita ao site — o fator que
  permitiu página cheia na Experiência 2 parece estar ligado à ausência de
  `siteSearch`, não à generalidade do termo. Pedidos idênticos e
  consecutivos também devolveram contagens diferentes de `results_received`
  e `estimated_nr_results` (ex.: `Sporting` variou entre 3 e 7), evidenciando
  que a API TextSearch não é determinística por pedido nesta janela de
  observação — o que limita a validade de comparações baseadas numa única
  amostra por variante nas experiências anteriores, embora as diferenças de
  maior magnitude aí observadas excedam esta variação.

`docs/experiments.md` já contém hipóteses, interpretação, questões abertas e
decisões metodológicas. Não existe um ADR ou documento de arquitetura separado;
este resumo, o mapa em AGENTS.md, o código e a ontologia cumprem essas funções.

## Limitações e problemas conhecidos

- Em 2026-09-16, `data/raw/` continha apenas `.gitkeep`; desde então o corpus do
  Caminho A foi recolhido localmente, mas o Git continua a ignorar as respostas
  e textos reais (incluindo os 540 textos referenciados por
  `output/corpus_articles.ttl`); o clone não inclui esses artefactos. As afirmações de
  preservação nas observações descrevem a execução histórica, não disponibilidade atual.
- O [manifesto](../data/processed/captures_manifest.jsonl) e os Turtle em
  `output/` continuam versionados, mas referenciam textos atualmente ausentes.
  Não é possível revalidar integralmente os resultados históricos só com este checkout.
- O sample M2 exige o URL e timestamp fixos em `rdf_mapper.py`. Gerá-lo exige
  o JSON M1 selecionado e respetivo texto. A geração RDF final do comando M3
  também procura esse JSON M1, mesmo depois de recolher versionHistory.
- O mapper do histórico só emite `TextoExtraido` quando há sucesso registado
  e o ficheiro existe; não inferir a disponibilidade atual pelo manifesto antigo.
- O significado operacional das estimativas, a ordem interna dos filtros/dedup
  e os limites estáveis de recuperação continuam em aberto em `experiments.md`.
  O coletor versionHistory atual usa a estimativa como um dos critérios de
  paragem; a experiência TextSearch não demonstra completude desse coletor.
- As dependências têm intervalos em `pyproject.toml`, sem lockfile versionado.
  Não há configuração de CI nem testes dedicados a profiling/diagnóstico no repositório.

## Testes existentes

Suite completa: `python -m unittest discover -s tests -v`, após instalação do
pacote conforme o README. Existem 47 testes em quatro módulos de `tests/`.
Cobrem processamento TextSearch/versionHistory, paginação (incluindo a não
dependência de `estimated_nr_results` como condição de paragem, corrigida em
2026-09-18), metadados do manifesto, IDs, `article_id` comum, ontologia,
relações/contagens RDF, ficheiros de texto, reutilização, preservação de
bytes, releitura de Turtle, a classificação Artigo/redirecionamento
(`test_corpus_classification.py`, incluindo a normalização http/https) e
o mapeamento RDF do corpus (`test_corpus_rdf.py`: reconstrução do raw,
normalização de `originalURL`, fusão de artigos e retoma sem repetir pedidos).

Última validação em **2026-09-19**, com o Python 3.13.1 do ambiente virtual:
`.venv/Scripts/python.exe -m unittest discover -s tests -v` — **47 testes,
todos passaram (`OK`)**, sem chamadas à API real.

[tests/support.py](../tests/support.py) fornece respostas simuladas, temporários
e bloqueio de rede. As [fixtures](../tests/fixtures/README.md) são sintéticas.
Passar esta suite verifica o comportamento local testado, não reproduz as
experiências reais nem valida disponibilidade/completude do Arquivo.pt.

## Trabalho em aberto e plano acordado (setembro 2026)

Esta secção substitui a proposta anterior por um plano já discutido e acordado
com o autor, à luz do Relatório Pré-Dissertação (RPD, "Motor de colheita de
informação orientado por ontologias", setembro de 2025, partilhado fora do
repositório) e do estado real da implementação. O RPD é usado como referência
do problema, objetivos e âmbito originalmente propostos, não como especificação
técnica imutável: os pontos abaixo assinalados como "decisão de âmbito" são
reduções conscientes face ao RPD, feitas por razões de tempo, e devem ser
justificadas como tal na dissertação, não apresentadas como o RPD original.

**Prazo-alvo:** entregar a dissertação até 31 de outubro de 2026 (objetivo do
autor; sujeito a fatores externos como reuniões e aprovação do orientador).

**Sequência de trabalho acordada:**

1. **C (curto) — concluído em 2026-09-17.** Nova experiência controlada e
   pequena (Experiência 2 em `experiments.md`), focada especificamente em
   saber se `offset` permite paginar quando a primeira página vem
   efetivamente cheia. Na Experiência 1, nenhuma variante devolveu tantos
   resultados quanto o `maxItems` pedido, pelo que `offset=100` e
   `offset=200` devolverem 0 podia refletir apenas a ausência de mais
   resultados materializados para aquela pesquisa específica, não uma
   limitação geral da API. Resultado: com uma pesquisa que preencheu
   genuinamente `maxItems=20` (`futebol`, sem `siteSearch`, sem dedup
   explícito), `offset` paginou corretamente em todas as janelas testadas,
   incluindo 100 e 200. Este passo informa o protocolo de recolha do passo A:
   verificar se a página anterior veio cheia antes de descartar `offset` como
   mecanismo de paginação.

   **Teste de volume adicional, concluído em 2026-09-17** (Experiência 3 em
   `experiments.md`), antes de iniciar o passo A: testou se trocar uma query
   específica por um termo genérico (`futebol`, `desporto`) ajuda a encher a
   página quando a pesquisa continua restrita a `siteSearch=record.pt`
   (restrição necessária para o corpus do Record). Resultado: nem a query
   específica (`Sporting`) nem as genéricas encheram `maxItems=20` em
   nenhuma das nove tentativas (3 repetições por query); o termo genérico
   não resolveu o problema. Foi também observada variação entre pedidos
   idênticos e consecutivos (`Sporting` devolveu 3, 5 e 7 resultados em três
   tentativas), indicando que a API não é determinística por pedido nesta
   janela de observação. Implicação para o passo A: não assumir que
   `siteSearch=record.pt` devolverá páginas cheias com nenhuma query testada
   até agora; considerar várias queries pequenas (por ano, secção,
   jogador/equipa) em vez de poucas queries genéricas, e repetir pedidos
   antes de tirar conclusões de uma única amostra.
2. **A** — generalizar a colheita e o mapeamento RDF (hoje restritos a uma
   única captura fixa em `rdf_mapper.py`) para um corpus real de vários artigos
   do jornal Record, incluindo uma regra explícita de classificação
   Artigo/redirecionamento.

   **Protocolo de queries: Opção 2 (Moderada); Fase 1 e Fase 2 executadas
   em 2026-09-17/18.** Ver "Protocolo de queries para o corpus do Caminho A"
   em `experiments.md`. Fase 1 (TextSearch, descoberta; 13 termos — 4
   modalidades, 4 clubes, 5 atletas conhecidos —, 2 repetições/termo): 26
   pedidos reais, nenhuma página cheia, **N = 159 artigos únicos**
   confirmado por `(originalURL, tstamp)`/`originalURL`, com 20 capturas
   encontradas por mais do que uma query (maioritariamente por conteúdo de
   navegação partilhado — menu de modalidades —, não relevância temática
   real; ver observações em `experiments.md`) e 20 divergências de
   metadados, todas isoladas ao campo `snippet` (esperado, não um problema
   de qualidade). Raw em `data/raw/corpus_queries/`; relatórios em
   `output/corpus_phase1_*`. Explicitamente uma amostra pequena e não
   exaustiva, não uma cobertura sistemática do Record.

   **Correção de bug em `collect_all_captures()`, 2026-09-18.** A função
   parava a paginação quando `len(captures) >= estimated_nr_results`,
   contrariando a decisão da Experiência 1 de não confiar nessa estimativa;
   escrito no M3, com um único artigo, o risco de paragem silenciosa antes
   de esgotar as páginas reais passou despercebido, mas seria significativo
   à escala dos 159 artigos da Fase 2. Removida essa condição; ficam só as
   duas condições já validadas (página incompleta, sem `next_page`).
   `estimated_total` continua a ser recolhido para relatório, só deixou de
   decidir a paragem. Teste de regressão acrescentado
   (`test_pagination_ignores_low_estimated_total`).

   **Fase 2 (`version_history` por artigo único, generalizando
   `history_pipeline.py`/`collect_all_captures()` já corrigida), executada
   em 2026-09-18 depois de autorizada pelo autor:** 159/159 artigos
   processados, **0 falhas**, 287 pedidos reais (159 + paginação),
   **7 572 capturas** no total, **125 de 159 artigos (78,6%) com mais do
   que uma captura**. Execução rápida (109s) — `version_history` consulta
   um URL exato, não pesquisa de texto livre, pelo que a lentidão das
   experiências anteriores não se generaliza a este tipo de pedido. Raw em
   `data/raw/version_history/`; relatórios em `output/corpus_phase2_*`.
   **Achado relevante para o passo 6:** os 13 artigos com mais de 100
   capturas (até 1282) não são artigos noticiosos — são páginas
   `/sabermais/<nome>` (perfis) e páginas de secção/hub sem `/detalhe/`, o
   que dá evidência concreta do que a classificação Artigo/redirecionamento
   precisa de filtrar; ver detalhe em `experiments.md`.

   **Passo 6 (classificação Artigo/redirecionamento) implementado e
   aplicado em 2026-09-18**, sobre os dados já recolhidos, sem pedidos
   novos à API — `src/semantic_harvester/corpus_classification.py`. Regra
   com três sinais, cada um justificado por evidência já documentada:
   `/sabermais/` no URL (página de referência/perfil), `title` igual a
   "Object moved" (página de redirecionamento arquivada — achado novo
   desta análise, 13 casos), e mais de 100 capturas na Fase 2 (página
   persistente, não editorial pontual — limiar calibrado num intervalo
   vazio real da distribuição, entre 74 e 117 capturas). Um sinal candidato
   da Fase 1 (sobreposição de ≥3 queries de modalidade) foi testado e
   **rejeitado** por produzir falsos positivos em artigos reais (ex.:
   "Danny deixa Zenit..."). Antes de classificar, normaliza `originalURL`
   que só diferem no esquema http/https (par identificado na Fase 2, com
   conjuntos de `tstamp` idênticos), reduzindo os 159 artigos a 158
   recursos distintos. Resultado: **127 de 158 (80,4%) classificados como
   Artigo**; 12 excluídos por `/sabermais/`, 13 por `Object moved`, 6 por
   capturas acima do limiar. 8 testes novos (unitários sobre `classify()` e
   de integração sobre `classify_corpus()`, com CSV sintéticos, incluindo o
   caso http/https); suite completa com 32 testes, todos a passar.
   Relatórios em `output/corpus_classification.csv` e
   `output/corpus_classification_summary.md`; detalhe e limitações
   conhecidas (ex.: páginas `/jogos-em-direto/` não cobertas pela regra)
   em `experiments.md`.

   **Mapeamento RDF do corpus (passo final) concluído em 2026-09-19 —
   Caminho A concluído.** `src/semantic_harvester/corpus_rdf.py` mapeia os
   127 artigos retidos para `output/corpus_articles.ttl`, reconstruindo as
   capturas do raw de `version_history` já preservado (sem repetir esses
   pedidos) e descarregando só os textos. Números verificados por soma do
   relatório e releitura do Turtle: **127/127 artigos, 941 capturas, 540
   textos disponíveis (57,4%) e 401 indisponíveis (42,6%), 12 735 triplos**
   (127 `Artigo`, 1 `Jornal`, 127 `RecursoWeb`, 941 `CapturaArquivada`, 540
   `TextoExtraido`); 32 artigos sem nenhum texto e 30 com todos. A descarga
   final foi corrida pelo autor fora do Claude Code, por cortes de memória
   do sistema. Três bugs encontrados e corrigidos (variantes cosméticas de
   `originalURL` em 32 artigos, timeout excessivo, ausência de retoma por
   artigo). Ressalva: dos 401 textos indisponíveis, 318 (79,3%) falharam por timeout
   de leitura, 77 (19,2%) por HTTP 404, 5 por ligação cortada e 1 por timeout
   de ligação (reconstruído a partir do log de progresso, reconcilia
   exatamente; ver `experiments.md`). Só o 404 é compatível com ausência
   real; os 324 timeouts/ligações cortadas não foram retentados de forma
   sistemática, pelo que a disponibilidade de 57,4% pode estar subestimada
   (teto teórico 91,8%). Detalhe em `experiments.md`.

   O Caminho D não foi iniciado.
3. **D** — redução de redundância entre capturas do mesmo artigo. **Decisão de
   âmbito:** heurística de similaridade textual simples (não `digest` isolado,
   não embeddings), aplicada à escala do corpus produzido em A; comparação com
   trabalho relacionado (ver abaixo) sustenta que isto já é mais rigoroso do
   que o precedente conhecido. Deteção de equivalência semântica mais
   sofisticada (ex.: embeddings) fica como trabalho futuro, condicional a
   tempo disponível.
4. **B** — povoamento de `EntidadeMencionada`/`Tema` (definidos na ontologia
   desde o início, nunca usados em código). **Decisão de âmbito:** caracterização
   descritiva/quantitativa (contagens, frequências), não uma avaliação formal
   de precisão do reconhecimento; a considerar um vocabulário fechado
   (clubes/competições/jogadores) em vez de um NER genérico em português.
5. **Protótipo de navegação** — objetivo do RPD ainda sem nenhuma implementação.
   **Decisão:** versão mínima baseada em SPARQL sobre o grafo já existente,
   construída cedo (não deixada para o fim) para reduzir o risco de ficar sem
   este entregável; uma interface mais interativa fica condicional a sobrar tempo.

**Trabalho relacionado consultado:** *Major Minors* (Martins & Costa, Prémio
Arquivo.pt 2021, também referido no RPD) deduplica apenas por título exato
(94.309 URIs → 48.949 títulos não repetidos, segundo a sua "Descrição Sumária
do Trabalho") e não parece modelar histórico temporal por artigo; a extração
de entidades usa aparentemente vocabulário fechado por categoria, não NER
genérico. Estas leituras vêm de documentos externos consultados pontualmente,
não de inspeção do código deles.

**Nota operacional:** este ambiente de execução remoto tem `arquivo.pt`
bloqueado pela política de rede do sandbox. Passos que exigem chamadas reais
à API (C, A, D, B) devem ser executados numa sessão local do Claude Code ou
diretamente no terminal local, nunca aqui.

Continuam por resolver as questões de recuperação listadas em `experiments.md`
e a ausência dos raw necessários para reproduzir os artefactos históricos
anteriores a este plano.

Atualizar este documento quando mudar o estado implementado, a validação ou
as limitações; manter resultados detalhados e decisões nas fontes acima.
