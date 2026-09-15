# Semantic Driven Harvester

Protótipo da dissertação para obter dados preservados pelo Arquivo.pt e
representar uma captura real num pequeno grafo RDF.

Estão implementados o M1 (pesquisa e texto real) e o M2 (ontologia base e
mapeamento RDF de uma captura). O projeto ainda não inclui NER, deduplicação,
bases de dados, frontend ou LLMs.

## Requisitos

- Python 3.11 ou superior
- acesso à Internet

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
`.gitkeep` mantêm a estrutura de diretórios no repositório.

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

O sample usa a captura real `20191120040251`, já obtida no M1:

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

Para consultar todas as capturas conhecidas do artigo usado no M2, reutilizar
textos existentes, criar o manifesto e gerar o RDF temporal:

```bash
python -m semantic_harvester.history_pipeline
```

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
