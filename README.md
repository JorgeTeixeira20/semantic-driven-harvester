# Semantic Driven Harvester

Primeiro vertical slice do protótipo da dissertação: pesquisar a API
TextSearch do Arquivo.pt, guardar a resposta JSON original e descarregar o
texto extraído de cada captura.

Nesta fase o projeto não inclui RDF, ontologias, NER, deduplicação, bases de
dados, frontend ou LLMs.

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
