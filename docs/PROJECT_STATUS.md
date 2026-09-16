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

`docs/experiments.md` já contém hipóteses, interpretação, questões abertas e
decisões metodológicas. Não existe um ADR ou documento de arquitetura separado;
este resumo, o mapa em AGENTS.md, o código e a ontologia cumprem essas funções.

## Limitações e problemas conhecidos

- Em 2026-09-16, `data/raw/` contém apenas `.gitkeep`. O Git ignora as respostas
  e textos reais; o clone não inclui esses artefactos. As afirmações de
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
pacote conforme o README. Existem 23 testes nos dois módulos de `tests/`.
Cobrem processamento TextSearch/versionHistory, paginação, metadados do manifesto,
IDs, `article_id` comum, ontologia, relações/contagens RDF, ficheiros de texto,
reutilização, preservação de bytes e releitura de Turtle.

Última validação em **2026-09-16**, com o Python 3.13.1 do ambiente virtual:
`.venv/Scripts/python.exe -m unittest discover -s tests -v` — **23 testes,
todos passaram (`OK`)**, sem chamadas à API real.

[tests/support.py](../tests/support.py) fornece respostas simuladas, temporários
e bloqueio de rede. As [fixtures](../tests/fixtures/README.md) são sintéticas.
Passar esta suite verifica o comportamento local testado, não reproduz as
experiências reais nem valida disponibilidade/completude do Arquivo.pt.

## Trabalho em aberto e próximo passo provável

Não há um roadmap posterior formalizado nos ficheiros versionados. Permanecem
as questões de recuperação listadas em `experiments.md` e a ausência dos raw
necessários para reproduzir os artefactos históricos.

**Proposta, não decisão já tomada:** antes de ampliar o corpus, definir o âmbito
e protocolo da próxima experiência, usando as decisões existentes sobre
parâmetros e comparação de conjuntos, e definir como preservar os raw fora do
Git. Recuperar artefactos ou realizar novas recolhas deve ser uma tarefa explícita;
não é necessário para desenvolver ou executar a suite unitária.

Atualizar este documento quando mudar o estado implementado, a validação ou
as limitações; manter resultados detalhados e decisões nas fontes acima.
