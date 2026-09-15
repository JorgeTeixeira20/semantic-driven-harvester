# Fixtures sintéticas para testes unitários

Todos os valores nestes ficheiros são fictícios. Não são respostas recolhidas
do Arquivo.pt nem dados empíricos do corpus.

- `textsearch/sample_search.json`: uma resposta TextSearch com uma captura.
- `version_history/sample_history.json`: duas capturas do mesmo URL fictício,
  com datas diferentes e digest repetido para verificar a preservação de versões.
- `texts/sample_text.txt`: texto UTF-8 sintético reutilizado nas capturas.

Os testes passam estes bytes a uma sessão HTTP simulada e usam apenas diretórios
temporários para JSON raw, textos, manifestos e Turtle gerados. O transporte
HTTP real e as ligações de sockets estão bloqueados durante cada teste.
A ontologia versionada em `ontology/` é o único recurso lido fora das fixtures.

O mapper do sample M2 restringe a entrada a um URL e timestamp específicos.
Os testes substituem essas duas constantes temporariamente pelos valores desta
fixture, mantendo as validações e o mapeamento de produção em execução.

Na raiz do repositório, com o ambiente instalado e ativo:

```sh
python -m unittest discover -s tests -v
```

Não é necessário executar a pipeline, dispor de `data/raw/`, de manifestos ou
de ficheiros em `output/`. O smoke test real descrito no README principal é uma
execução manual separada e não pertence a esta suite unitária.
