# Estado do projeto

Atualizado em **2026-10-19** (alcance real da descoberta e download do HTML
em bruto), a partir do código, testes, documentação e histórico; a última
revisão integral foi até `a3208f4`.
Este documento é um retrato datado, não substitui a inspeção do checkout
atual. Regras de trabalho: [AGENTS.md](../AGENTS.md); comandos:
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
A redução de redundância entre capturas (Caminho D) está concluída como
anotação por similaridade textual em `corpus_redundancy.py`, sobre o corpo do
artigo (variante c′, `article_body.py`) com limiar 0,90 (ver "Trabalho em
aberto"). Não estão implementados NER,
deduplicação semântica, base de dados,
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

- O Git continua a ignorar `data/raw/` e o `data/processed/corpus_articles_triples.nt`
  (ver `.gitignore`); um clone deste repositório não inclui esses artefactos,
  incluindo os 793 textos referenciados por `output/corpus_articles.ttl`. As
  afirmações de preservação nas observações descrevem a execução histórica,
  não disponibilidade automática a partir de um novo checkout.
- **Preservação do raw fora do Git (decisão tomada em 2026-09-24):** a pasta
  `data/` de cada máquina usada no projeto está copiada no Google Drive do
  autor, em `tese-record/`, separada por origem para preservar proveniência
  (`data-raw-mac-m1-m3/` e `data-raw-windows-caminho-a/`, cada uma contendo a
  pasta `data/` completa dessa máquina). Contagens de ficheiros verificadas
  contra o esperado antes da cópia: Mac (`data/raw/texts/`) 13 ficheiros (11
  do M1 + 1 novo do M3 + `.gitkeep`); Windows (`data/raw/texts/`) 795 (794
  textos reais, 540 originais + 249 recuperados na retentativa, + `.gitkeep`).
  Isto resolve a proposta em aberto desde o início do projeto de definir como
  preservar os raw fora do Git; recuperar ou consultar essas cópias continua a
  ser uma tarefa manual e explícita, não automática a partir de um clone.
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

### Para a escrita da tese (2026-10-20)

- **Profundidade temporal por artigo: estudada, não uma lacuna.** No corpus
  de 125 artigos (941 capturas via `version_history`; mediana de 3 capturas
  por artigo, máximo 73), o Caminho D (variante c′, limiar 0,90) mostrou que
  a maioria dos artigos não muda entre capturas: dos 121 artigos com
  capturas comparáveis, 112 têm uma só versão distinta do corpo, 8 têm duas
  e 1 tem cinco. A variação entre capturas é sobretudo chrome. Por isso o
  corpus alargado regista uma captura por artigo (a mais antiga que a
  descoberta encontrou) e a Fase 2 foi parada (`docs/experiments.md`,
  2026-10-20): é uma escolha de âmbito do motor, não uma falha de recolha.
- **Wikidata, ontologia e cobertura desigual por modalidade.** O vocabulário
  fechado de entidades do Caminho B
  (`data/processed/caminho_b_vocabulario_wikidata.csv`) tem 1 091 entradas,
  **todas jogadores de futebol** dos plantéis da Primeira Liga 2015–16 a
  2019–20 (só 3 épocas com participantes na Wikidata, 23 clubes): a deteção
  de entidades só cobre futebol. A ontologia formaliza `sdh:Modalidade`
  (subclasse de `sdh:Tema`) para todas as modalidades, a partir do URL, mas
  `EntidadeMencionada` não tem subclasses por modalidade (fica para quando o
  vocabulário for alargado). No corpus alargado, a cobertura por modalidade
  é muito desigual: dos 83 320 Artigos, 36 869 têm `futebol` no URL e 28 079
  nenhuma modalidade no URL; as restantes vão de 1 558 (andebol) e
  1 522 (hóquei em patins) a menos de 10 (tiro, esgrima, xadrez, pólo
  aquático). Estes números refletem também o teto da descoberta (300
  resultados por termo e ano), não só o volume publicado pelo Record.

## Testes existentes

Suite completa: `python -m unittest discover -s tests -v`, após instalação do
pacote conforme o README. Existem 224 testes em dezassete módulos de `tests/`.
Cobrem processamento TextSearch/versionHistory, paginação (incluindo a não
dependência de `estimated_nr_results` como condição de paragem, corrigida em
2026-09-18), metadados do manifesto, IDs, `article_id` comum, ontologia,
relações/contagens RDF, ficheiros de texto, reutilização, preservação de
bytes, releitura de Turtle, a classificação Artigo/redirecionamento
(`test_corpus_classification.py`, incluindo a normalização http/https) e
o mapeamento RDF do corpus (`test_corpus_rdf.py`: reconstrução do raw,
normalização de `originalURL`, fusão de artigos, retoma sem repetir pedidos e
reconstrução offline com verificações) e a
retentativa de textos (`test_corpus_text_retry.py`: tentativas com espera crescente,
404 não retentado, retoma por captura) e a anotação de redundância do Caminho D
(`test_corpus_redundancy.py`: normalização, estratégias último representante e
consecutiva incluindo a cadeia A≈B, B≈C, A≉C, camadas, grupos de `digest`
anotados sem remoção, amostra de rotulagem e execução não destrutiva) e a
remoção do chrome (`test_corpus_chrome.py`: n-gramas partilhados por muitos
artigos removidos, específicos de um artigo intactos, contagem por artigo,
separação dos rótulos e execução não destrutiva) e os temas/entidades do Caminho B
(`test_corpus_entities.py`: normalização sem acentos, limites de palavra,
variantes, chrome do menu removido, persistência entre capturas, temas a
partir de URLs) e o vocabulário da Wikidata (`test_wikidata_vocabulary.py`:
sobreposição de datas, regras de variantes e homónimos, respostas guardadas
em bruto, com sessão simulada) e o protótipo de navegação
(`test_navigation_prototype.py`: contagens das queries sobre um grafo pequeno,
ordem e filtro do histórico, ligações entre páginas e escape de títulos) e o
HTML em bruto da captura mais antiga (`test_arquivo_client.py`: download,
reutilização de ficheiro existente, campo ausente e falha de rede; mais
testes em `test_history_pipeline.py` sobre a ligação a `TEXT_POLICY_FIRST`,
incluindo que `TEXT_POLICY_ALL` nunca pede HTML) e a Fase 1 alargada
(`test_corpus_phase1.py`: paragem só por página incompleta/vazia,
independente de `next_page`; lista de termos alargada).

Última validação em **2026-10-19**, com o Python 3.11.17 do ambiente virtual
(sessão remota Linux): `.venv/bin/python -m unittest discover -s tests` —
**224 testes, todos passaram (`OK`)**, sem chamadas à API real. (Anterior:
2026-10-15, Python 3.12.4 no ambiente virtual (macOS), 190 testes OK;
2026-09-20, Python 3.13.1 no Windows, 68 testes OK.)

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

   **Mapeamento RDF do corpus (passo final) concluído em 2026-09-19; retentativa
   dos textos e reconstrução do grafo concluídas em 2026-09-20 — Caminho A
   concluído.** `src/semantic_harvester/corpus_rdf.py` mapeia os 127 artigos
   retidos para `output/corpus_articles.ttl`, reconstruindo as capturas do raw
   de `version_history` já preservado (sem repetir esses pedidos). Depois da
   retentativa dos textos que tinham falhado por timeout ou ligação cortada
   (`corpus_text_retry.py`, corrida pelo autor fora do Claude Code: 249 das 324
   candidatas recuperadas, 75 falhas definitivas), o grafo foi reconstruído
   offline (`--rebuild-offline`, sem pedidos à API) e verificado. **Números
   finais: 127/127 artigos, 941 capturas, 789 textos disponíveis (83,8%) e 152
   indisponíveis (16,2%), 13 482 triplos** (127 `Artigo`, 1 `Jornal`, 127
   `RecursoWeb`, 941 `CapturaArquivada`, 789 `TextoExtraido`); 2 artigos sem
   nenhum texto e 77 com todos. Antes da retentativa eram 540 textos (57,4%),
   401 indisponíveis, 12 735 triplos, 32 artigos sem nenhum texto. Verificações
   (todas OK, também confirmadas contra o Turtle do commit anterior): 941
   capturas, textos = 540 + 249, todos os triplos antigos contidos no novo e a
   diferença só de `TextoExtraido` (747 = 249 × 3), ficheiros de texto
   existentes, Turtle relido. Causa das 152 sem texto: 128 HTTP 404 (77 da
   recolha original + 51 descobertos na retentativa) e 24 timeouts de leitura
   persistentes (os únicos que não são evidência de ausência); as 35 capturas
   com `statusCode` diferente de 200 continuam todas sem texto. Três bugs
   encontrados e corrigidos na descarga (variantes cosméticas de `originalURL`
   em 32 artigos, timeout excessivo, ausência de retoma por artigo).
   Ressalva: na reconstrução offline as colunas `texts_downloaded_now`/
   `texts_reused` do relatório perdem a divisão histórica (todos "reutilizados").
   Detalhe em `experiments.md`.

   **Correção da identidade dos artigos em 2026-10-04 (achado ao navegar no
   protótipo):** dois artigos eram o mesmo, porque os `originalURL` só
   diferiam em parâmetros de rastreio (`?ref=…`, `?utm_…&act=0&est=Aberto`).
   A classificação e o RDF passam a ignorar só `ref`, `utm_*`, `act` e `est`
   (`url_identity.py`); a query inteira não, porque no site antigo
   (`interior.aspx?content_id/…`) ela identifica o artigo. A reconstrução
   offline juntou as capturas das variantes e encontrou ainda 4 textos já em
   cache, guardados com o hash de URLs com barra dupla, que a procura só pelo
   URL canónico não via. **Números atuais do Caminho A: 125 artigos, 941
   capturas, 793 textos disponíveis (84,3%) e 148 indisponíveis, 13 482
   triplos.** D, B e o protótipo foram regenerados. Detalhe em
   `experiments.md` ("Correção da identidade dos artigos").

   O Caminho D foi concluído em 2026-10-02 e revisto em 2026-10-09 (passo 3
   abaixo).

   **Investigação do limite de resultados e das páginas de secção, e
   alargamento da descoberta (2026-10-19, `experiments.md`).** Confirmado
   (sessão local, com acesso à API): não há limite de 2000 resultados por
   pesquisa (~826 mil URLs alcançáveis para `futebol`, ~810 mil para
   `Benfica`); `next_page` e `estimated_nr_results` continuam não fiáveis
   mesmo a esta escala (o segundo é ~3× o valor real). As páginas de secção
   só cobrem bem 2018–meados de 2020 (crawl diário do site inteiro nessa
   janela, não uma recolha dedicada à secção) — não servem para alargar a
   1999–2026. Decisão: alargar a Fase 1 com 11 termos novos (5 modalidades,
   6 competições, a partir de valores reais do vocabulário do Caminho B) a
   somar aos 13 já usados, com `from=1999`/`to=2026`, e corrigir a paragem
   da paginação para não depender de `next_page`. Implementado em
   `corpus_phase1.py`; **ainda não corrido contra a API** (ambiente remoto
   sem acesso a `arquivo.pt`). Numa investigação relacionada (mesma sessão
   local), o HTML em bruto (`linkToOriginalFile`) mostrou conter
   marcação de corpo mais fiável do que a heurística atual em dois casos
   (deteção de Premium, recuperação de corpo sem texto em cache); decisão de
   design híbrida registada, **não implementada**. O que ficou implementado
   e testado offline dessa investigação é só o download/preservação do HTML
   em bruto da captura mais antiga de artigos novos, na mesma passagem que o
   texto (`ArquivoClient.download_original_html`, `data/raw/original_html/`,
   ligado a `history_pipeline.build_manifest_records` sob
   `TEXT_POLICY_FIRST`). Detalhe completo em `experiments.md`.
3. **D** — redução de redundância entre capturas do mesmo artigo. **Decisão de
   âmbito:** heurística de similaridade textual simples (não `digest` isolado,
   não embeddings), aplicada à escala do corpus produzido em A; comparação com
   trabalho relacionado (ver abaixo) sustenta que isto já é mais rigoroso do
   que o precedente conhecido. Deteção de equivalência semântica mais
   sofisticada (ex.: embeddings) fica como trabalho futuro, condicional a
   tempo disponível.

   **Resultado reportado desde 2026-10-09: variante (c′), corpo do artigo,
   com limiar 0,90** (decisão dos autores; `article_body.py`, 14 marcadores
   literais de chrome incluindo "Mais Premium"). Das 941 capturas: 775 na
   Camada 1 (com corpo), 18 com texto mas sem corpo, 144 sem texto e 4 não
   avaliáveis; **133 versões textuais distintas** e 642 redundantes, em 121
   artigos (112 com uma só versão). Na amostra rotulada os rótulos
   separam-se (0 erros a 0,90 nos 57 pares com corpo), **mas há um só par
   "texto alterado" de referência**; os 12 pares consecutivos abaixo de 0,90
   estão todos explicados (Premium vs. artigo completo, falhas da âncora de
   início, o par 29, contadores/embed em legendas curtas, bloco "Mais
   Fotogalerias"). Detalhe em `experiments.md` ("Adoção da variante (c′)").
   As variantes (a) e (b) ficam como histórico, testadas e não adotadas.

   *Histórico — fecho de 2026-10-02: variante (a) (texto completo, com
   chrome) com limiar 0,80*, decisão dos autores na altura. `output/corpus_redundancy.csv` final
   (sem `pendente_limiar`), após a correção de 2026-10-04: das 793 capturas
   da Camada 1 de 123 artigos, **666 versões textuais distintas** e 127
   redundantes; Camada 2 com 146 capturas (14 candidatas por `digest`, não
   verificadas) e 2 não avaliáveis (antes da correção: 789, 665, 124, 150); versões
   por artigo em `output/corpus_redundancy_versions.csv`. **Escolha
   pragmática, não calibração limpa:** nem a variante (a) nem a (b) separam os
   60 rótulos manuais com nenhum limiar de Jaccard de palavras testado. A
   0,80, nenhum dos 2 "texto alterado" fica classificado como igual (erro grave
   evitado na amostra), mas 28 dos 58 "mesma versão" ficam como versões
   distintas (erro conservador, aceite porque D é anotação não destrutiva).
   Esse erro concentra-se nos artigos muito capturados (por exemplo, um vídeo
   com 71 versões em 71 capturas), pelo que 666 é um limite superior. A
   variante (b) (remoção do chrome) fica testada e não adotada. Amostra de
   validação limitada: 34 artigos, um vídeo com 11 dos 60 pares, 2 pares
   "texto alterado".

   **Decisão em aberto (não tomada):** avaliar um modelo de similaridade
   semântica (embeddings) é trabalho futuro, condicional a (a) sobrar tempo
   depois do Caminho B e do protótipo de navegação e (b) confirmação do
   orientador de que o resultado atual não chega — ainda por validar em
   reunião.

   **Variante (c′), avaliada em 2026-10-04 (adotada em 2026-10-09):**
   corpo do artigo delimitado entre o título e o primeiro de 13 marcadores
   literais de chrome (`corpus_body.py`). Nos 57 pares rotulados com corpo,
   os rótulos **separam-se de forma limpa** (mín. "mesma versão" 0,975, máx.
   "texto alterado" 0,840; limiares 0,85–0,95), ao contrário de (a) e (b) —
   mas o lado "alterado" tem um só par comparável (o par 1 fica "sem corpo",
   como o rótulo previa). No B, as menções falsas dos casos Nike e
   Boavista-Moreirense desaparecem (pares persistentes 287 → 114; amostra de
   12 removidos: todos chrome). Limitações: bloco "Mais Premium" do layout
   de 2019 fora da lista, 3 falhas da âncora de início, 18 capturas sem
   corpo. Decidido em 2026-10-09: adotar (c′) em D (limiar 0,90) e em B, e
   acrescentar "Mais Premium" como 14.º marcador.

   **Histórico (2026-09-24 a 2026-10-02, antes do fecho).**
   `src/semantic_harvester/corpus_redundancy.py` aplica o desenho de
   `experiments.md` sem alterar o grafo nem o raw (checksums iguais antes e
   depois): Camada 1 (texto e `statusCode` 200) compara cada captura com o
   último representante retido, com a variante consecutiva como
   sensibilidade; Camada 2 mantém todas as capturas sem texto e só anota
   grupos `digest`+`contentLength`; Jaccard de palavras sobre texto
   normalizado, com chrome. Resultado real: **789 capturas na Camada 1, 150 na
   Camada 2, 2 não avaliáveis**; 664 pares consecutivos (mediana 0,655); na
   tabela de sensibilidade, 64 redundantes a 1,00, 81 a 0,90, 124 a 0,80 e
   210 a 0,70 (estratégia principal, em 789); Camada 2 com 9 grupos/14
   candidatas não verificadas e 0 grupos mistos. **Rotulagem manual feita em
   2026-10-02** (60 pares de `output/corpus_redundancy_label_sample.csv`): 58
   "mesma versão" e 2 "texto alterado" (0,434 e 0,780). Os rótulos não se
   separam por similaridade: há "mesma versão" desde 0,438, e um limiar ≥ 0,80
   (o mínimo que não funde os 2 "texto alterado") deixa de reconhecer 28 dos
   58 pares iguais; a causa é o chrome no texto completo. **Variante (b),
   remoção do chrome, implementada e avaliada em 2026-10-02**
   (`corpus_chrome.py`): n-gramas presentes em ≥ 10% dos artigos distintos
   (fração escolhida pela distribuição, antes dos rótulos) são retirados. Não
   separa os rótulos e piora a sobreposição (37 dos 58 pares iguais abaixo de
   0,80; 34 pares ambíguos entre 0,240 e 0,713), com o mesmo resultado em todas
   as frações (0,02–0,50) e n (3, 5, 8) testados: o que distingue capturas do
   mesmo artigo é chrome rotativo (manchetes do dia), raro entre artigos. A
   amostra rotulada cobre só 34 artigos (um vídeo com 11 dos 60 pares), o que
   limita a generalização. Detalhe em `experiments.md`.

   **Representação em RDF, 2026-10-10** (`corpus_redundancy_rdf.py`,
   `output/corpus_redundancy.ttl`, separado de `corpus_articles.ttl`, que não
   muda): a partir do CSV oficial (c′, limiar 0,90), **642 capturas
   redundantes** recebem `sdh:versaoDe` (para a representante) e
   `sdh:similaridade` (`xsd:float`) — **1 284 triplos**. As 133
   representantes, as 18 capturas `sem_corpo`, as 144 da Camada 2 e as 4 não
   avaliáveis não recebem triplos (sem comparação nem representante
   calculados; a Camada 2 é reconstituível por SPARQL a partir de
   `sdh:digest`/`sdh:contentLength`, já no grafo).
4. **B** — **O Caminho B foi concluído em 2026-10-03 e revisto em
   2026-10-09:** desde então o resultado reportado procura os jogadores só no
   corpo do artigo (variante c′): 113 pares artigo–jogador em 58 artigos pela
   regra de persistência (119 em 60 pela regra fraca); `clube_coerente` 34
   `sim`, 16 `nao`, 63 `sem_tema`, e dos 16 `nao` inspecionados 11 são
   menções legítimas e 5 falsos positivos (1 manchete, 4 de homonímia). Os
   números abaixo, sobre o texto sem chrome persistente, ficam como
   histórico. Povoamento de
   `EntidadeMencionada`/`Tema` (definidos na ontologia
   desde o início, nunca usados em código). **Decisão de âmbito:** caracterização
   descritiva/quantitativa (contagens, frequências), não uma avaliação formal
   de precisão do reconhecimento; a considerar um vocabulário fechado
   (clubes/competições/jogadores) em vez de um NER genérico em português.

   **Proposta escrita e script testado em 2026-10-02, não executado sobre o
   corpus** (secção "Caminho B" em `experiments.md`;
   `src/semantic_harvester/corpus_entities.py`). Tema = classificação
   editorial a partir do `originalURL` (secção, modalidade, competição,
   clube-secção); EntidadeMencionada = nome de um vocabulário fechado que ocorre
   no texto, procurado sem o chrome persistente e com regra de persistência
   entre capturas (os menus citam os três grandes em todas as páginas).
   Recomendação: temas pelo URL e entidades por lista fechada de fonte
   independente; os 13 termos da Fase 1 só como controlo, por serem
   circulares. **Fonte decidida pelo autor: Wikidata** (plantéis da
   Primeira Liga 2015–16 a 2019–20; `wikidata_vocabulary.py`): 1 094
   futebolistas, 1 091 rótulos em
   `data/processed/caminho_b_vocabulario_wikidata.csv`. **Primeira execução
   real em 2026-10-02:** temas pelo URL em todos os 127 artigos (clube-secção
   em 50, modalidade em 71); jogadores no texto em 93 artigos pela regra de
   persistência (291 pares artigo–jogador, 119 jogadores distintos) e em 118
   pela regra fraca (1 424 pares). Ressalvas: 163 dos 291 pares vêm de artigos
   com uma só captura (sem proteção de persistência); 62 de rótulos de uma
   palavra; a remoção do chrome quase não afeta os jogadores (estão nas
   manchetes rotativas, não nos menus); cobertura limitada pela Wikidata.
   Contagens de correspondências, sem avaliação de precisão (decisão de
   âmbito). *Após a correção de 2026-10-04 (125 artigos, 793 textos):*
   persistência 287 pares em 91 artigos (118 jogadores), regra fraca 1 427
   pares em 116 artigos; 158 dos 287 de artigos com uma só captura. **Contaminação por chrome investigada em 2026-10-03:** os falsos
   positivos vêm de manchetes rotativas (blocos "Últimas Notícias", "Mais
   notícias", "Notícias MAIS", faixa sob o menu), confirmado em dois casos
   reais (artigo Nike AMP; crónica Premium Boavista-Moreirense com 49 jogadores
   pela regra fraca e só 1, legítimo, pela persistência); a persistência falha
   com capturas próximas no tempo. **Sinal `clube_coerente`** (só sinal, nada
   removido; tabela slug → clube em `data/processed/caminho_b_clubes_url.csv`):
   pela regra fraca 189 `sim`, 333 `nao`, 902 `sem_tema`; pela persistência 82
   `sim`, 41 `nao`, 168 `sem_tema` (após a correção de 2026-10-04: fraca 189 /
   333 / 905, persistência 82 / 41 / 164). Só 50 artigos têm clube no URL, por isso os
   dois casos investigados ficam `sem_tema`.

   **Representação em RDF, 2026-10-10** (`corpus_entities_rdf.py`,
   `output/corpus_entities.ttl`, separado de `corpus_articles.ttl`, que não
   muda), a partir do CSV oficial (c′): **1 703 triplos**; **40 nós `Tema`**
   partilhados por (categoria, valor), ligados por `sdh:temTema` aos 125
   artigos (308 linhas de tema); **82 nós `EntidadeMencionada`** partilhados
   por entidade, 81 com o URI da Wikidata e 1 com URI próprio (homónimo);
   **119 nós `Mencao`** (`sdh:temMencao`/`sdh:sobreEntidade`, com as
   métricas do CSV) em 60 artigos, em paralelo com `sdh:mencionaEntidade`.
   Homónimos do vocabulário: 3 rótulos (André Silva, Chico, Pedro Mendes);
   no corpus atual só "Pedro Mendes" ocorre, 1 linha. Os três Turtle (corpus,
   D, B) combinados dão 16 469 triplos com URIs comuns. Detalhe em
   `experiments.md` ("RDF dos Caminhos D e B").
5. **Protótipo de navegação** — objetivo do RPD ainda sem nenhuma implementação.
   **Decisão:** versão mínima baseada em SPARQL sobre o grafo já existente,
   construída cedo (não deixada para o fim) para reduzir o risco de ficar sem
   este entregável; uma interface mais interativa fica condicional a sobrar tempo.

   **Versão mínima implementada e gerada em 2026-10-03**
   (`src/semantic_harvester/navigation_prototype.py`, queries em `queries/`):
   páginas HTML estáticas em `output/prototipo/` (abrir `index.html`), geradas
   com `rdflib` a partir de 5 queries SPARQL sobre `output/corpus_articles.ttl`
   — artigos com RecursoWeb e nº de capturas, histórico cronológico de cada
   artigo (ligado ao Arquivo.pt), artigos mais capturados, capturas por ano e
   texto por `statusCode`. Sem servidor nem dependências novas. Resultado real:
   125 páginas de artigo (127 antes da correção de 2026-10-04), 941 linhas de
   histórico, totais iguais aos do
   Caminho A; tornou visível que as capturas vão de 2017 a 2023 (nenhuma de
   2015–2016) e que as 24 de 2020–2023 não têm texto. A lista de artigos tem
   pesquisa por título/URL e filtro por secção (JavaScript embutido, sem
   dependências).

   **Ligado a D e B em 2026-10-15** (`docs/experiments.md`, "Protótipo
   ligado aos Caminhos D e B"): quando `output/corpus_redundancy.ttl` e
   `output/corpus_entities.ttl` existem, juntam-se ao mesmo grafo; o
   histórico de cada artigo assinala capturas redundantes, a página do
   artigo mostra Temas/Entidades, e há páginas novas `temas.html`/
   `entidades.html`. Sem esses ficheiros, gera-se só com o Caminho A, como
   antes.

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
