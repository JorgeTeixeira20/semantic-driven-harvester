# Semantic Driven Harvester — guia para agentes

Instruções canónicas do projeto, independentes da ferramenta de IA utilizada.
Protótipo de uma dissertação de Mestrado para recolher metadados e textos do
Arquivo.pt e representar recursos Web e capturas temporais em RDF.

## Antes de trabalhar

1. Inspecionar `git status --short`, `git log -5 --oneline` e o diff existente.
2. Ler [README.md](README.md) e [estado do projeto](docs/PROJECT_STATUS.md).
3. Para dados/experiências, ler [observações](docs/observations.md) e
   [experiências e decisões](docs/experiments.md).
4. Para testes, ler [política das fixtures](tests/fixtures/README.md).
5. Ler o código e testes afetados; para RDF, também a ontologia abaixo.

Não afirmar comportamento, resultados ou decisões sem verificar as fontes.

## Mapa e arquitetura atual

- `src/semantic_harvester/arquivo_client.py`: HTTP, TextSearch, versionHistory
  e preservação dos bytes de JSON/texto.
- `history_pipeline.py`: paginação, textos, manifesto JSONL e métricas.
- `rdf_mapper.py`: IDs determinísticos, grafos de sample/histórico e Turtle.
- `smoke_test.py`, `api_profiling.py`, `api_diagnostics.py`,
  `api_diagnostics_offset.py`, `api_diagnostics_site_volume.py`,
  `corpus_phase1.py`, `corpus_phase2.py`: execuções reais manuais; estes
  módulos também estão em `src/semantic_harvester/`. `corpus_phase1.py`
  implementa a Fase 1 (descoberta via TextSearch) e `corpus_phase2.py` a
  Fase 2 (profundidade temporal via `version_history`, um artigo de cada
  vez) do protocolo de queries do Caminho A descrito em
  `docs/experiments.md`.
- `corpus_classification.py`: passo 6 do protocolo (classificação
  Artigo/redirecionamento), trabalha só sobre os CSV já gerados pelas
  Fases 1–2; não faz pedidos à API, corre offline.
- `corpus_text_retry.py`: retentativa isolada, resumível por captura, dos
  textos que falharam por timeout/ligação cortada (lista em
  `output/corpus_text_retry_candidates.csv`); não toca no grafo nem em
  `corpus_rdf_report.csv`.
- `corpus_rdf.py`: passo final do Caminho A — grafo RDF único dos artigos
  retidos, reconstruindo capturas do raw já preservado pela Fase 2 (sem
  repetir pedidos de `version_history`) e descarregando/reutilizando só os
  textos extraídos.
- `corpus_redundancy.py`: Caminho D — anotação (não destrutiva) de redundância
  entre capturas do mesmo artigo por similaridade textual; lê o Turtle do
  corpus e a cache de textos, sem rede; o limiar depende de rotulagem manual.
- `corpus_chrome.py`: variante (b) do Caminho D — remoção do chrome por
  n-gramas frequentes entre artigos distintos e avaliação contra os 60 pares
  rotulados; sem rede, não altera grafo, raw nem as saídas da variante (a).
- `corpus_entities.py`: Caminho B — temas pelo `originalURL` e entidades por
  vocabulário fechado no texto sem chrome; sem rede.
- `corpus_candidate_entities.py`: teste exploratório (não o Caminho B) —
  candidatos a entidade por heurística (sequências de palavras
  capitalizadas, sem NER) que o vocabulário fechado não cobre; sem rede.
- `wikidata_vocabulary.py`: vocabulário de jogadores do Caminho B a partir da
  Wikidata (rede: endpoint SPARQL); raw em `data/raw/wikidata/`.
- `wikidata_vocabulary_alargado.py`: vocabulário alargado (1999–2024, 39
  modalidades, clubes e atletas) a partir da Wikidata, noutros caminhos; não
  altera o vocabulário original; raw em `data/raw/wikidata/alargado/`.
- `article_body.py`: corpo do artigo entre o título e 14 marcadores literais
  de chrome (variante c′, adotada em D e B); sem dependências.
- `corpus_body.py`: avaliação da variante (c′) contra D e B, sem rede.
- `corpus_redundancy_rdf.py`, `corpus_entities_rdf.py`: RDF dos Caminhos D e
  B a partir dos CSV oficiais, em Turtle separado do grafo do corpus (que não
  alteram); sem rede.
- `navigation_prototype.py`: protótipo de navegação — corre `queries/*.rq`
  (SPARQL, `rdflib`) sobre o Turtle do corpus e gera HTML estático em
  `output/prototipo/`; sem rede nem servidor.
- [ontology/semantic_harvester.ttl](ontology/semantic_harvester.ttl): vocabulário.
- `tests/`: suite offline, transporte simulado e fixtures sintéticas.
- `data/raw/`: artefactos locais ignorados pelo Git, salvo `.gitkeep`.
- `data/processed/`: manifesto; `output/`: RDF e relatórios, alguns versionados.
- `docs/`: estado, observações e decisões; não duplicar resultados dos relatórios.

Fluxo: API → bytes raw → registos/manifesto → RDF; profiling e diagnóstico
produzem relatórios separados. Não existe serviço Web nem base de dados.

## Ambiente e comandos

Python >=3.11; dependências em `pyproject.toml`: RDFLib >=7.6,<8 e
requests >=2.31,<3; empacotamento setuptools com layout `src/`.
Na raiz, criar `.venv` com `python -m venv .venv` (`python3` em sistemas que
assim designam o Python). Ativar com `.venv\Scripts\Activate.ps1` no PowerShell
ou `source .venv/bin/activate` em shells POSIX. Depois:

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

No Windows também é possível usar `.venv\Scripts\python.exe` sem ativar.
Comandos de execução, apenas quando a tarefa pedir essa operação:

| Comando | Pré-requisitos / efeito |
| --- | --- |
| `python -m semantic_harvester.smoke_test` | Rede; pesquisa e grava raw/textos. |
| `python -m semantic_harvester.rdf_mapper` | Raw M1 e texto da captura selecionada; grava Turtle. |
| `python -m semantic_harvester.history_pipeline` | Rede; recolhe histórico; a geração RDF final também exige o JSON M1 selecionado. |
| `python -m semantic_harvester.api_profiling` | Rede; grava raw e relatórios. |
| `python -m semantic_harvester.api_diagnostics` | Rede; grava raw e relatórios. |
| `python -m semantic_harvester.api_diagnostics_offset` | Rede; grava raw e relatórios. |
| `python -m semantic_harvester.api_diagnostics_site_volume` | Rede; 9 pedidos; grava raw e relatórios. |
| `python -m semantic_harvester.corpus_phase1` | Rede; ~26 pedidos (Fase 1 do Caminho A); grava raw e relatórios. |
| `python -m semantic_harvester.corpus_phase2` | Rede; ~159+ pedidos (Fase 2 do Caminho A, um artigo de cada vez); execução longa; retoma automaticamente se interrompida. |
| `python -m semantic_harvester.corpus_classification` | Sem rede; lê os CSV das Fases 1–2 e classifica Artigo/redirecionamento (passo 6). |
| `python -m semantic_harvester.corpus_text_retry` | Rede (até 324 capturas, várias tentativas cada); resumível por captura; grava textos em `data/raw/texts/` e `output/corpus_text_retry_report.csv`. |
| `python -m semantic_harvester.corpus_rdf --rebuild-offline [--check-only]` | Sem rede; reconstrói o grafo dos artigos retidos a partir do raw e da cache de textos, verifica e só então substitui os outputs. |
| `python -m semantic_harvester.corpus_rdf` | Rede só para textos (~centenas de pedidos); lê o raw de version_history já preservado; grava `output/corpus_articles.ttl` e relatórios. |
| `python -m semantic_harvester.corpus_redundancy [--limiar X] [--texto corpo\|completo]` | Sem rede; lê `output/corpus_articles.ttl` e `data/raw/texts/`; grava `output/corpus_redundancy*`; não altera grafo nem raw; por omissão só o corpo do artigo (c′). |
| `python -m semantic_harvester.corpus_chrome --so-distribuicao \| --fracao F [--n 5]` | Sem rede; lê o Turtle, `data/raw/texts/` e a amostra rotulada; grava `output/corpus_chrome_*`. |
| `python -m semantic_harvester.corpus_entities --vocabulario CSV [--texto corpo\|sem-chrome\|completo] [--correspondencia-simples]` | Sem rede; lê o Turtle e `data/raw/texts/`; grava `output/corpus_entities*`; por omissão só o corpo do artigo (c′). |
| `python -m semantic_harvester.corpus_candidate_entities --vocabulario CSV [--texto corpo\|completo]` | Sem rede; lê o Turtle e `data/raw/texts/`; teste exploratório (candidatos fora do vocabulário fechado, sem NER); grava `output/corpus_candidate_entities*`; por omissão só o corpo do artigo (c′). |
| `python -m semantic_harvester.wikidata_vocabulary` | Rede (28 pedidos SPARQL à Wikidata); grava raw em `data/raw/wikidata/` e `data/processed/caminho_b_vocabulario_wikidata.csv`. |
| `python -m semantic_harvester.wikidata_vocabulary_alargado [--reutilizar-raw]` | Rede (~115 pedidos SPARQL à Wikidata, um de cada vez); grava raw em `data/raw/wikidata/alargado/`, `data/processed/caminho_b_vocabulario_wikidata_alargado.csv` e `output/wikidata_vocabulario_alargado.md`; com `--reutilizar-raw` só pede o que mudou. |
| `python -m semantic_harvester.corpus_body [--vocabulario CSV]` | Sem rede; lê o Turtle, os textos e a amostra rotulada; grava `output/corpus_body_*`. |
| `python -m semantic_harvester.corpus_redundancy_rdf` / `corpus_entities_rdf` | Sem rede; leem os CSV oficiais de D/B (e o vocabulário); gravam `output/corpus_redundancy.ttl` / `output/corpus_entities.ttl`; não alteram `corpus_articles.ttl`. |
| `python -m semantic_harvester.navigation_prototype` | Sem rede; lê `output/corpus_articles.ttl` e `queries/`; regenera `output/prototipo/`. |

Os detalhes e parâmetros estão no README e nos módulos. Estes comandos reais
não são pré-requisitos da suite unitária nem devem ser executados para a reparar.

## Regras de trabalho e dados

- Preferir alterações pequenas, justificadas e testáveis; preservar comportamento
  já testado. Não fazer refactors nem acrescentar funcionalidades fora do pedido.
- Distinguir implementação observada, hipótese, resultado histórico e proposta.
  Não inventar resultados científicos, medições, arquitetura ou decisões.
- Não editar, fabricar ou substituir raw para fazer testes passar. Preservar
  os bytes originais e a proveniência; fixtures são sintéticas e ficam em `tests/fixtures/`.
- Raw não acompanha um clone. Relatórios e caminhos no manifesto não provam
  que os ficheiros referenciados existem localmente; verificar antes de os usar.
- Não repetir recolhas live sem isso fazer parte do pedido. Novas execuções
  podem sobrescrever artefactos: preservar a evidência anterior antes de repetir.
- Não generalizar conclusões de uma amostra para toda a API. Consultar as
  decisões de `docs/experiments.md` sobre estimativas, offsets e deduplicação.
- Registar decisões importantes com motivo e evidência na documentação existente:
  método em `docs/experiments.md`, observações em `docs/observations.md`,
  estado/limitações em `docs/PROJECT_STATUS.md`; evitar fontes paralelas.

## Ontologia e RDF

- Distinguir `Artigo`, `RecursoWeb`, `CapturaArquivada` e `TextoExtraido`.
  Uma página devolvida pela pesquisa não é automaticamente um artigo.
- Preservar IDs com SHA-256 do URL e `tstamp` nas URIs de captura/texto;
  capturas do mesmo URL partilham `article_id`. Digest não prova equivalência semântica.
- Explicar alterações de classes, propriedades, datatypes, relações ou IDs e
  o impacto em dados/consumidores antes de as implementar como mudanças triviais.
- Manter ontologia, mapper e testes coerentes; verificar relações, ficheiros
  referenciados e releitura do Turtle. Não corrigir outputs históricos à mão.

## Testes, Git e conclusão

- Testes automatizados usam fixtures determinísticas e diretórios temporários;
  sem rede, `data/raw/`, outputs históricos ou pipeline prévia. Usar o suporte offline existente.
- Manter assertions relevantes; acrescentar testes proporcionais às mudanças.
  Integrações reais devem ser opcionais e separadas da descoberta unitária.
- Correr a suite relevante após alterações e a suite completa acima antes de concluir.
  Informar comando, contagem, resultado e limitações; não declarar sucesso sem execução.
- Preservar alterações alheias; não adicionar raw, `.venv/` ou segredos ao Git.
  Não fazer commit, push ou reescrever histórico sem pedido explícito.
- Concluir quando o âmbito pedido estiver resolvido, testes passarem, documentação
  estiver coerente e `git diff --check` estiver limpo. Rever o diff e apresentar
  ficheiros alterados, motivo e `git diff --stat`; explicar bloqueios se existirem.
