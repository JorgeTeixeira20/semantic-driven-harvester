# Semantic Driven Harvester

Protótipo de uma dissertação de Mestrado para obter dados preservados pelo
Arquivo.pt e representar recursos Web e capturas temporais em RDF.

Estão implementados o M1 (pesquisa e texto real), o M2 (ontologia base e
mapeamento RDF de uma captura) e o M3 (histórico temporal de um artigo), além
do profiling e diagnóstico da TextSearch. O projeto ainda não inclui NER,
deduplicação local/semântica, bases de dados, frontend ou LLMs; o cliente permite
configurar os parâmetros de deduplicação da API.

## Contexto e colaboração

- [AGENTS.md](AGENTS.md): instruções canónicas e mapa para qualquer agente de IA.
- [Estado do projeto](docs/PROJECT_STATUS.md): marcos, implementação, limitações e próximos passos propostos.
- [Observações](docs/observations.md): resultados históricos de M1/M3.
- [Experiências](docs/experiments.md): diagnóstico, interpretação e decisões metodológicas.
- [Fixtures de teste](tests/fixtures/README.md): dados sintéticos e isolamento offline.

## Requisitos

- Python 3.11 ou superior
- acesso à Internet para instalar dependências e executar recolhas reais;
  a suite unitária funciona offline após a instalação

## Instalação

Na raiz do repositório, criar e ativar um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

No Windows PowerShell, o comando de ativação equivalente é:

```powershell
.venv\Scripts\Activate.ps1
```

## Executar o smoke test real

Com o ambiente virtual ativo, na raiz do repositório:

```bash
python -m semantic_harvester.smoke_test
```

O teste pesquisa `Benfica` no domínio `record.pt`, entre 2018 e 2020, com um
máximo de 20 resultados. Como o Arquivo.pt trata os hosts de forma exata, o
cliente inclui também `www.record.pt` quando recebe um domínio simples. Assim,
a pesquisa abrange tanto o domínio raiz como o host `www`.

No fim são apresentados os resultados recebidos, downloads bem-sucedidos,
falhas e localizações dos ficheiros.

## Ficheiros produzidos

- `data/raw/searches/`: resposta JSON original de cada pesquisa.
- `data/raw/texts/`: um ficheiro `.txt` por captura, com nome formado pelo
  `tstamp` e por um hash curto do URL original.

Estes artefactos são dados de execução e estão ignorados pelo Git. Os ficheiros
`.gitkeep` mantêm a estrutura de diretórios no repositório. Um clone não inclui
os raw; os relatórios, manifesto e RDF versionados descrevem execuções históricas
e podem referenciar textos ausentes. Ver o [estado do projeto](docs/PROJECT_STATUS.md).

## Utilização do cliente

```python
from pathlib import Path

from semantic_harvester import ArquivoClient

client = ArquivoClient(data_dir=Path("data/raw"))
search = client.search(
    query="Benfica",
    site_search="record.pt",
    from_date="2018",
    to_date="2020",
    max_items=20,
)
downloads = client.download_extracted_texts(search.results)
```

`search.results` contém os itens devolvidos pela API sem remover campos. A
resposta completa e original fica disponível em `search.raw_response` e no
ficheiro indicado por `search.raw_path`.

## Gerar o sample RDF do M2

O sample usa a captura real `20191120040251` da execução histórica M1. Este
comando exige localmente o JSON dessa captura em `data/raw/searches/` e o
respetivo texto em `data/raw/texts/`; os raw não acompanham o clone:

```bash
python -m semantic_harvester.rdf_mapper
```

O grafo é guardado em `output/sample_capture.ttl`. Os seus identificadores são
determinísticos e derivados do URL original e do `tstamp`.

## Executar os testes

Com o ambiente instalado e ativo, sem executar previamente a pipeline:

```bash
python -m unittest discover -s tests -v
```

Os testes unitários funcionam offline e usam apenas a ontologia versionada e
fixtures sintéticas em `tests/fixtures/`. Geram JSON raw, textos, manifestos e
Turtle em diretórios temporários, sem depender de `data/raw/`, `data/processed/`
ou `output/`. As chamadas HTTP são simuladas e as ligações de rede bloqueadas.
Os valores das fixtures são fictícios, não são dados empíricos do Arquivo.pt.
O smoke test real acima é uma execução manual separada desta suite.

## Recolher o histórico temporal do artigo (M3)

Para recolher o histórico devolvido por versionHistory para o artigo usado no
M2, reutilizar textos existentes, criar o manifesto e gerar o RDF temporal:

```bash
python -m semantic_harvester.history_pipeline
```

Este comando faz chamadas reais à API. A etapa final de geração RDF também
exige o JSON M1 da captura selecionada, usado para obter o título do artigo.
Não executar este comando para satisfazer os testes unitários.

O comando produz:

- JSON original em `data/raw/version_history/`;
- textos disponíveis em `data/raw/texts/`;
- `data/processed/captures_manifest.jsonl`;
- `output/article_history.ttl`.

O parâmetro `maxItems` é tratado como tamanho de página, não como indicação do
total. As páginas seguintes são consultadas através de `offset` quando
necessário.

## Executar o profiling rápido da TextSearch

Para repetir as seis pesquisas exploratórias sem descarregar textos nem gerar
RDF:

```bash
python -m semantic_harvester.api_profiling
```

As respostas originais são guardadas em `data/raw/profiling/` e o resumo é
escrito em `output/api_profiling.csv` e `output/api_profiling.md`.

## Repetir a experiência de diagnóstico da API

Para executar as variantes controladas de `maxItems`, `offset` e dedup:

```bash
python -m semantic_harvester.api_diagnostics
```

Os JSON raw são guardados em `data/raw/api_diagnostics/`; os resultados ficam
em `output/api_diagnostics.csv`, `output/api_diagnostics.md` e são discutidos
em `docs/experiments.md`.

## Repetir a Experiência 2 (offset com página cheia)

Para repetir o teste de paginação por `offset` quando a primeira página vem
efetivamente cheia:

```bash
python -m semantic_harvester.api_diagnostics_offset
```

Os JSON raw são guardados em `data/raw/api_diagnostics_offset/`; os
resultados ficam em `output/api_diagnostics_offset.csv`,
`output/api_diagnostics_offset.md` e são discutidos em `docs/experiments.md`.
Este comando pode demorar por chamada (a query não usa `siteSearch`); em caso
de timeout ou erro 500 pontual da API, repetir a execução.

## Repetir a Experiência 3 (volume de queries genéricas em record.pt)

Para repetir o teste de volume — queries específicas vs. genéricas dentro de
`siteSearch=record.pt`, com repetições por query para observar variação
entre pedidos idênticos:

```bash
python -m semantic_harvester.api_diagnostics_site_volume
```

Os JSON raw são guardados em `data/raw/api_diagnostics_site_volume/`; os
resultados ficam em `output/api_diagnostics_site_volume.csv`,
`output/api_diagnostics_site_volume.md` e são discutidos em
`docs/experiments.md`. Este comando faz 9 pedidos reais e pode demorar
vários minutos; em caso de timeout ou erro 500 pontual da API, repetir a
execução.

## Fase 1 do corpus do Caminho A (descoberta via TextSearch)

Para correr a Fase 1 ano a ano (decisões de âmbito de 2026-10-19 em
`docs/experiments.md`: 108 termos — 39 modalidades, 57 clubes, 5 atletas,
7 competições —, um intervalo por ano de 1999 a 2026 com datas de 14
dígitos, 1 repetição, paragem só em página vazia):

```bash
python -m semantic_harvester.corpus_phase1
```

Os JSON raw são guardados em `data/raw/corpus_queries/por_ano/` (o ano
entra no nome de cada ficheiro); os resultados (estatísticas por termo e ano,
capturas agregadas/deduplicadas por `(originalURL, tstamp)` e o resumo com
`N` e a distribuição por ano) ficam em
`output/corpus_phase1_por_ano_per_term.csv`,
`output/corpus_phase1_por_ano_captures.csv` e
`output/corpus_phase1_por_ano_aggregation.md`. As execuções anteriores — a
original (13 termos, 2015–2020, que deu o corpus atual de 125 artigos, em
`data/raw/corpus_queries/` e `output/corpus_phase1_*`) e a alargada (108
termos num só intervalo, `.../alargada/` e `output/corpus_phase1_alargada_*`)
— não são reescritas; a Fase 2 e a classificação continuam a ler a original
por omissão. O comando faz no máximo 18 144 pedidos (108 termos × 28 anos ×
até 6 páginas) e retoma a partir do raw já gravado se for interrompido.
**Não avança para a Fase 2 (`version_history`)** — essa etapa exige
confirmação explícita do valor de `N` (ver `docs/experiments.md`).

## Fase 2 do corpus do Caminho A (profundidade temporal via version_history)

Depois de confirmado o valor de `N` (artigos únicos) da Fase 1, para correr
a Fase 2 — o histórico completo de cada artigo, sem restrição de datas:

```bash
python -m semantic_harvester.corpus_phase2
```

Lê os `originalURL` únicos de `output/corpus_phase1_captures.csv` e chama
`version_history()` (via `collect_all_captures()`, já corrigida para não
depender de `estimated_nr_results`) uma vez por artigo, com paginação por
offset só quando a página anterior vier cheia. O JSON raw é guardado em
`data/raw/version_history/` (convenção já usada pelo M3); os resultados
ficam em `output/corpus_phase2_history.csv` (uma linha por artigo, escrita
incrementalmente) e `output/corpus_phase2_summary.md`. Regista progresso a
cada 10 artigos em `output/corpus_phase2_progress.log` e no terminal. Esta é
a execução mais longa do projeto (potencialmente 159+ pedidos, um por
artigo, mais paginação onde houver histórico); se for interrompida, correr
o comando outra vez retoma automaticamente a partir dos artigos ainda não
presentes em `output/corpus_phase2_history.csv`. Não descarrega textos nem
gera RDF — isso fica para depois da classificação Artigo/redirecionamento
(ver `docs/experiments.md`).

Para a Fase 1 ano a ano (corrigir antes a agregação a partir do raw, com
`originalURL` normalizado, e depois correr a Fase 2 separada da original):

```bash
python -m semantic_harvester.corpus_phase1 --rebuild-offline
nohup python -m semantic_harvester.corpus_phase2 \
    --captures-csv output/corpus_phase1_por_ano_captures.csv --label por_ano \
    > output/phase2.log 2>&1 &
```

Com `--label por_ano`, os resultados ficam em
`output/corpus_phase2_por_ano_{history.csv,summary.md,progress.log}` e o raw
em `data/raw/phase2_por_ano/version_history/`, sem tocar na Fase 2 original
nem no raw do corpus de 125 artigos. É retomável por artigo.

## Classificação Artigo/redirecionamento (passo 6 do Caminho A)

Depois da Fase 2, para classificar os artigos descobertos como `Artigo` ou
excluí-los por serem páginas de referência/secção/redirecionamento:

```bash
python -m semantic_harvester.corpus_classification
```

Não faz pedidos à API — lê `output/corpus_phase1_captures.csv` e
`output/corpus_phase2_history.csv`, normaliza `originalURL` que só diferem
no esquema (`http://`/`https://`), aplica a regra documentada em
`docs/experiments.md` ("Classificação Artigo vs. redirecionamento/não-
artigo") e escreve `output/corpus_classification.csv` (uma linha por
recurso, com a razão da classificação) e
`output/corpus_classification_summary.md`.

## Grafo RDF do corpus (passo final do Caminho A)

Depois da classificação, para mapear os artigos retidos para um único
grafo RDF, com as suas capturas históricas e textos extraídos:

```bash
python -m semantic_harvester.corpus_rdf
```

Não repete pedidos de `version_history` — reconstrói as capturas de cada
artigo a partir do raw já preservado pela Fase 2
(`data/raw/version_history/`). Só faz pedidos novos à API para descarregar
os textos extraídos de cada captura, reutilizando os que já existirem em
`data/raw/texts/`. Regista progresso a cada 10 artigos em
`output/corpus_rdf_progress.log` e no terminal. Grava o grafo combinado em
`output/corpus_articles.ttl` (não sobrescreve `output/sample_capture.ttl`
nem `output/article_history.ttl`, do M2/M3) e relatórios em
`output/corpus_rdf_report.csv`/`output/corpus_rdf_summary.md`.

**Política de texto para artigos novos** (desde 2026-10-15; ver
`docs/experiments.md`): para os artigos ainda não presentes em
`output/corpus_rdf_report.csv`, o `version_history` continua a ser lido até
ao fim (sem usar `estimated_nr_results`), mas só se pede o texto extraído da
captura **mais antiga** (menor `tstamp`) de cada artigo. As restantes
capturas entram no grafo sem texto e contam como "não pedido", não como
falha (sem tentativa alternativa noutra captura se o texto da mais antiga
falhar). Os 125 artigos já processados são saltados e não mudam; a
reconstrução offline (`--rebuild-offline`) e o M3 continuam a usar o texto de
todas as capturas. A descoberta de artigos continua a ser a pesquisa por
palavra-chave com `siteSearch=record.pt` (sem RSS). Esta política **não foi
ainda corrida contra a API real**.

## Retentar os textos que falharam por timeout (antes do Caminho D)

Para retentar as 324 capturas cuja última falha foi timeout ou ligação
cortada (lista em `output/corpus_text_retry_candidates.csv`):

```bash
python -m semantic_harvester.corpus_text_retry
```

Faz até 3 tentativas por captura com espera crescente (um 404 não é
retentado), é resumível por captura e regista o resultado em
`output/corpus_text_retry_report.csv` (e um resumo em
`output/corpus_text_retry_summary.md`). Só acrescenta textos a
`data/raw/texts/`: **não altera** `output/corpus_rdf_report.csv` nem o grafo;
a integração dos textos recuperados no grafo é um passo separado (ver
`docs/experiments.md`). Para retentar uma falha definitiva, apagar a sua
linha do relatório.

## Reconstruir o grafo do corpus offline (depois da retentativa)

Depois de `corpus_text_retry`, os textos recuperados só estão em cache;
`corpus_rdf` salta os artigos já concluídos. Para os incorporar no grafo sem
qualquer pedido à API:

```bash
python -m semantic_harvester.corpus_rdf --rebuild-offline --check-only   # só verifica
python -m semantic_harvester.corpus_rdf --rebuild-offline                # verifica e substitui
```

Reconstrói os artigos retidos a partir do raw de `version_history`, da
classificação e da cache de textos (`data/raw/texts/`), corre as verificações
(artigos, capturas, contagem de textos face à retentativa, grafo antigo
contido no novo, diferença só de `TextoExtraido`, ficheiros existentes,
Turtle relido) e **só substitui** `output/corpus_articles.ttl`,
`output/corpus_rdf_report.csv`, `output/corpus_rdf_summary.md` e
`data/processed/corpus_articles_triples.nt` se todas passarem (cópia prévia do
`.nt` em `data/processed/corpus_articles_triples.nt.pre-rebuild`).

## Caminho D — anotação de redundância entre capturas

Sem rede e sem alterar o grafo nem o raw: lê `output/corpus_articles.ttl` e os
textos referenciados em `data/raw/texts/`.

```bash
python -m semantic_harvester.corpus_redundancy --limiar 0.90                    # resultado oficial (corpo, variante c′)
python -m semantic_harvester.corpus_redundancy --limiar 0.80 --texto completo   # variante (a), histórica
```

Escreve `output/corpus_redundancy.csv` (uma linha por captura: camada,
representante, similaridade, rótulo), `output/corpus_redundancy_summary.md`
(contagens por camada, distribuição e tabela de sensibilidade ao limiar) e
`output/corpus_redundancy_label_sample.csv` (amostra de pares para rotulagem
manual, nunca reescrita depois de rotulada). Por omissão a similaridade usa só
o corpo do artigo (`--texto corpo`, variante c′, `article_body.py`); as
capturas sem corpo ficam numa camada própria (`sem_corpo`). Sem `--limiar`, a
Camada 1 fica `pendente_limiar`. Desenho e decisões em `docs/experiments.md`.

### Título exato vs. digest: estratégia de deduplicação antes do download

```bash
python -m semantic_harvester.dedup_strategy_check
```

Sem rede: lê `output/corpus_classification.csv`, `output/corpus_redundancy.csv`
e o raw de `version_history` já em cache (`data/raw/version_history/`).
Mede, contra os rótulos reais já calculados por Jaccard (Camada 1), se
dedupicar por título exato (como o "Major Minors", Martins & Costa, Prémio
Arquivo.pt 2021) ou por `digest` apanharia os mesmos duplicados sem
descarregar o texto. Escreve `output/corpus_dedup_strategy_check.md`.
Requer o raw e as saídas de classificação/redundância já presentes — não
corre nesta sandbox (sem `data/raw/version_history/`), só numa sessão local
com o corpus real.

### Variante (b): remoção do chrome

```bash
python -m semantic_harvester.corpus_chrome --so-distribuicao      # só a distribuição dos n-gramas
python -m semantic_harvester.corpus_chrome --fracao F [--n 5]     # avaliação com a fração escolhida
```

Sem rede e sem alterar grafo, raw ou saídas da variante (a). Considera chrome
os n-gramas de palavras presentes numa fração alta dos artigos distintos, retira
as palavras que eles cobrem e recalcula a Jaccard na Camada 1 e nos 60 pares
rotulados. Escreve `output/corpus_chrome_summary.md` e
`output/corpus_chrome_label_eval.csv`.

## Caminho B — temas e entidades mencionadas

```bash
python -m semantic_harvester.corpus_entities --vocabulario CAMINHO.csv [--texto corpo|sem-chrome|completo] [--correspondencia-simples]
```

Sem rede e sem alterar grafo nem raw. Temas a partir do `originalURL`
(secção, modalidade, competição, clube) e entidades por correspondência exata
de um vocabulário fechado (CSV `tipo,categoria,rotulo,variantes`) só no corpo
do artigo (`--texto corpo`, por omissão; `sem-chrome` é a configuração
histórica com remoção de n-gramas frequentes), com regra de persistência
entre capturas. Escreve
`output/corpus_entities.csv` e `output/corpus_entities_summary.md`.

O vocabulário de jogadores (plantéis da Primeira Liga 2015–2020, Wikidata) é
construído com rede (28 pedidos SPARQL, respostas em bruto em
`data/raw/wikidata/`):

```bash
python -m semantic_harvester.wikidata_vocabulary
```

Escreve `data/processed/caminho_b_vocabulario_wikidata.csv`.

## Protótipo de navegação

```bash
python -m semantic_harvester.navigation_prototype
```

Sem rede e sem servidor: corre as queries SPARQL de `queries/*.rq` com `rdflib`
sobre `output/corpus_articles.ttl` e gera páginas HTML estáticas em
`output/prototipo/` (abrir `output/prototipo/index.html` no browser): agregados
por ano e por `statusCode`, artigos mais capturados, lista de artigos e o
histórico cronológico de capturas de cada artigo, com ligação ao Arquivo.pt.

Se `output/corpus_redundancy.ttl` (Caminho D) e `output/corpus_entities.ttl`
(Caminho B) existirem, juntam-se ao mesmo grafo (os URIs já são partilhados,
sem conversão): o histórico de cada artigo passa a assinalar as capturas
redundantes (`sdh:versaoDe`, com a similaridade), a página do artigo mostra os
seus Temas e Entidades mencionadas, e o índice e as páginas `temas.html`/
`entidades.html` resumem isso para o corpus todo. Sem esses dois ficheiros, o
protótipo gera-se só com o Caminho A, como antes.

### Variante (c′): corpo do artigo por âncoras literais

```bash
python -m semantic_harvester.corpus_body [--vocabulario data/processed/caminho_b_vocabulario_wikidata.csv]
```

Sem rede e sem alterar as saídas fechadas de D e B. Isola o corpo de cada
captura entre o título do artigo e o primeiro de 13 marcadores de bloco de
chrome, e compara com os 60 pares rotulados (D) e, com `--vocabulario`, os
pares artigo–jogador (B). Escreve `output/corpus_body_summary.md`,
`output/corpus_body_label_eval.csv` e `output/corpus_body_entities.csv`.

## RDF dos Caminhos D e B

```bash
python -m semantic_harvester.corpus_redundancy_rdf   # output/corpus_redundancy.ttl
python -m semantic_harvester.corpus_entities_rdf     # output/corpus_entities.ttl
```

Sem rede. Leem os CSV oficiais (`output/corpus_redundancy.csv`,
`output/corpus_entities.csv`) e o vocabulário da Wikidata, e escrevem Turtle
separado de `output/corpus_articles.ttl` (não alterado; checksum verificado),
com os mesmos URIs de `Artigo` e `CapturaArquivada`: carregar os três ficheiros
juntos dá o grafo completo. Termos novos da ontologia: `sdh:versaoDe`,
`sdh:similaridade`, `sdh:Mencao`, `sdh:temMencao`, `sdh:sobreEntidade`,
`sdh:capturasComMencao`, `sdh:capturasComTexto`, `sdh:ocorrencias`,
`sdh:persistente`, `sdh:clubeCoerente`, `sdh:categoriaTema`, `sdh:valorTema`.

## Dados e protótipo do corpus completo

Os dados do corpus completo (200 101 notícias do Record, 2001–2021) estão na
[página de releases](https://github.com/JorgeTeixeira20/semantic-driven-harvester/releases)
(versão `v1.0-tese`), em dois ZIP:

- `prototipo_completo.zip`: o protótipo já gerado. Descomprimir e abrir
  `prototipo_completo/index.html` no browser (sem servidor nem rede).
- `dados_completo.zip`: o grafo RDF e as tabelas de entidades de que o painel
  precisa, com o caminho relativo à raiz do repositório.

Para gerar o protótipo a partir dos dados, num clone limpo:

```bash
git clone https://github.com/JorgeTeixeira20/semantic-driven-harvester.git
cd semantic-driven-harvester
python3 -m venv .venv
.venv/bin/pip install -e ".[sparql]"
unzip /caminho/para/dados_completo.zip   # na raiz do clone
.venv/bin/python -m semantic_harvester.navigation_corpus --corpus completo \
  --vocabulario data/processed/caminho_b_vocabulario_hibrido_completo.csv \
  --fonte sparql --destino prototipo_verificacao
```

O resultado fica em `output/prototipo_verificacao/` (cerca de 4 minutos; o
`data.js` é idêntico, byte a byte, ao de `prototipo_completo.zip`).

Os textos e o HTML descarregados do Arquivo.pt não são publicados: para refazer
todo o processo, desde a recolha, é preciso voltar a descarregá-los (muitas
horas de pedidos).
