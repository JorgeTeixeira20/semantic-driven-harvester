# Observações experimentais

## Execução do M1

Pesquisa realizada contra a API TextSearch do Arquivo.pt:

```text
query = Benfica
siteSearch = record.pt
from = 2018
to = 2020
maxItems = 20
```

Resultados observados:

- resultados recebidos: 11;
- textos descarregados: 11;
- falhas: 0;
- total de texto: 86 151 bytes.

## Observações

- `maxItems=20` resultou em apenas 11 itens;
- foi devolvida pelo menos uma captura de dezembro de 2017 apesar de
  `from=2018`;
- `encoding` estava presente nos 11 resultados;
- `status` não estava presente nesta resposta;
- pelo menos um resultado observado corresponde a uma página temática ou de
  secção do Record e não deve ser automaticamente classificado como `Artigo`.

Estas são observações experimentais desta execução, não conclusões sobre o
comportamento geral do Arquivo.pt.

## Execução do M3 — histórico temporal do artigo

Foi consultado, sem restrição temporal, o `versionHistory` do artigo:

```text
https://www.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/yony-gonzalez-e-reforco-para-o-benfica
```

Resultados observados em 25 de agosto de 2026:

- total estimado pela API: 3 capturas;
- capturas efetivamente devolvidas: 3;
- intervalo observado: `20191114000138` a `20200101205547`;
- textos obtidos: 2, incluindo 1 ficheiro já existente do M1;
- falhas de texto: 1;
- digests distintos: 3;
- digests repetidos: 0 ocorrências além da primeira;
- tamanho dos textos disponíveis: mínimo 10 372 bytes, média 10 901,50 bytes
  e máximo 11 431 bytes.

### Qualidade e anomalias observadas no M3

- Os três resultados não incluem `encoding`, `snippet`, `date` nem
  `linkToExtractedText`.
- Não foi possível observar diferenças de encoding, porque o campo estava
  ausente nas três capturas.
- Os três resultados incluem `statusCode=200`.
- Apesar de `estimated_nr_results=3` e de a primeira página conter os três
  resultados com `maxItems=50`, a resposta inclui um `next_page` com
  `offset=50`. O URL foi preservado no JSON raw; não foi pedida uma página
  adicional porque o total estimado já tinha sido atingido.
- Como `linkToExtractedText` estava ausente, foi tentado o endpoint de texto
  extraído com URL e `tstamp`, seguindo a convenção já observada no M1. O texto
  de `20191114000138` estava disponível; o de `20200101205547` devolveu HTTP
  404. O texto de `20191120040251` já existia e não foi descarregado novamente.
- Para a captura `20191120040251`, os valores de `digest`, `contentLength` e
  `title` devolvidos por `versionHistory` diferem dos valores devolvidos pela
  pesquisa TextSearch do M1 para o mesmo URL e `tstamp`. Ambas as respostas raw
  foram preservadas sem alteração.
- Não foram encontrados digests repetidos nesta amostra. Este resultado é
  apenas descritivo e não é usado como critério de equivalência semântica.

Estas observações descrevem somente esta execução e não constituem uma
caracterização geral das APIs do Arquivo.pt.
