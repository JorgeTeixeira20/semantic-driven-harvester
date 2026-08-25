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
