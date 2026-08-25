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

Depois de gerar o sample:

```bash
python -m unittest discover -s tests -v
```

Os testes carregam a ontologia e o sample com RDFLib, verificam as relações
principais e confirmam que o ficheiro de texto referenciado existe.
