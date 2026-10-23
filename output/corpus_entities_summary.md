# Caminho B — temas e entidades mencionadas

Sem pedidos à API; não altera o grafo nem o raw. Anotação por artigo. Vocabulário: `data/processed/caminho_b_vocabulario_wikidata.csv`. Texto pesquisado: só o **corpo do artigo** (variante c′, `article_body.py`; capturas sem corpo não contam).

- Artigos: 125; com texto (Camada 1): 121; com uma só captura com texto (sem proteção de persistência): 37.
- Regras dos nomes de pessoas (2026-10-23): um nome de uma só palavra só conta com maiúscula no texto; nomes próprios comuns (primeira palavra de 2+ outras pessoas do vocabulário) não contam sozinhos — 4 retirados: adilson, danilo, gustavo, rodrigo.

## Temas (a partir do `originalURL`)

| Categoria | Artigos com tema | Valores distintos |
| --- | ---: | ---: |
| secao | 125 | 14 |
| modalidade | 71 | 9 |
| competicao | 62 | 7 |
| clube | 50 | 10 |

### modalidade

| modalidade | Artigos |
| --- | ---: |
| futebol | 59 |
| atletismo | 2 |
| ciclismo | 2 |
| judo | 2 |
| motores | 2 |
| andebol | 1 |
| desporto-universitario | 1 |
| jogos-europeus | 1 |
| natacao | 1 |

### competicao

| competicao | Artigos |
| --- | ---: |
| liga-nos | 52 |
| europeu | 4 |
| 2--liga | 2 |
| can | 1 |
| liga-jovem-da-uefa | 1 |
| taca-das-confederacoes | 1 |
| taca-de-portugal | 1 |

### clube

| clube | Artigos |
| --- | ---: |
| sporting | 17 |
| benfica | 16 |
| fc-porto | 5 |
| v--guimaraes | 3 |
| boavista | 2 |
| moreirense | 2 |
| sp--braga | 2 |
| aves | 1 |
| maritimo | 1 |
| portimonense | 1 |

## Entidades mencionadas (vocabulário fechado, no texto)

- Artigos com pelo menos uma entidade, regra de persistência (todas as capturas com texto): 56
- Artigos com pelo menos uma entidade, regra fraca (≥ 1 captura): 58
- Pares artigo–entidade: 115 pela regra fraca, 109 pela regra de persistência; destes, 28 são de artigos com uma só captura com texto, onde a persistência não filtra nada.

### Coerência de clube (sinal, não filtro)

Para cada par artigo–jogador: `sim` se um clube do jogador no vocabulário coincide com o tema `clube` do URL do artigo; `nao` se não coincide (possível falso positivo, por exemplo uma manchete do chrome); `sem_tema` se o URL não tem clube. Uma entidade clube compara-se pelo próprio rótulo. `sem_mapa`: o clube do URL não está na tabela slug → clube. `nao_aplicavel`: treinador, estádio ou competição. Nenhuma menção é removida.

| clube_coerente | Pares (regra fraca) | Pares (persistência) |
| --- | ---: | ---: |
| sim | 34 | 34 |
| nao | 16 | 16 |
| sem_tema | 65 | 59 |

| Entidade | Artigos (persistência) | Artigos (≥ 1 captura) |
| --- | ---: | ---: |
| João Félix | 6 | 6 |
| Bruno Fernandes | 5 | 5 |
| Pepe | 5 | 5 |
| Marvin Zeegelaar | 4 | 4 |
| Rodrigo José Lima dos Santos | 3 | 4 |
| Bas Dost | 3 | 3 |
| Bernardo Silva | 3 | 3 |
| José Pedro Costa Amorim Cerqueira | 3 | 3 |
| Andrija Živković | 2 | 2 |
| Douglas Pereira dos Santos | 2 | 2 |
| Gonçalo Guedes | 2 | 2 |
| Jonas | 2 | 2 |
| José Gomes da Silva | 2 | 2 |
| Moreira | 2 | 2 |
| Nuno Santos | 2 | 2 |
| Nélson Oliveira | 2 | 2 |
| Paulo Sérgio Mota | 2 | 2 |
| Éderzito António Macedo Lopes | 2 | 2 |
| Adrien Silva | 1 | 1 |
| Ahmed Sayed | 1 | 1 |
| Alan Ruiz | 1 | 1 |
| Alejandro Grimaldo | 1 | 1 |
| Alex Telles | 1 | 1 |
| André Fontes | 1 | 1 |
| André Micael | 1 | 1 |
| André Sousa | 1 | 1 |
| Bruno Gaspar | 1 | 1 |
| Bryan Ruiz | 1 | 1 |
| Carlos Mané | 1 | 1 |
| Carraça | 1 | 1 |
| Casemiro | 1 | 1 |
| Cristian Ponde | 1 | 1 |
| Danilo Luís Hélio Pereira | 1 | 1 |
| David Martins Simão | 1 | 1 |
| Diogo Gonçalves | 1 | 1 |
| Diogo Queirós | 1 | 1 |
| Ederson Moraes | 1 | 1 |
| Edinaldo Gomes Pereira | 1 | 1 |
| Ezequiel Schelotto | 1 | 1 |
| Fabinho | 1 | 1 |
| Filipe Chaby | 1 | 1 |
| Fransérgio | 1 | 1 |
| Fredy Montero | 1 | 1 |
| Fábio Daniel Soares Silva | 1 | 1 |
| Fábio Fortes | 1 | 1 |
| Fábio Vieira | 1 | 1 |
| Gonçalo Abreu | 1 | 1 |
| Hildeberto Pereira | 1 | 1 |
| Hugo Rogério Ferreira Monteiro | 1 | 1 |
| Hélder Postiga | 1 | 1 |
| Jonathan Silva | 1 | 1 |
| João Mário | 1 | 1 |
| Júlio César Oliveira Martins | 1 | 1 |
| Luisão | 1 | 1 |
| Luís Pinto | 1 | 1 |
| Luíz Carlos | 1 | 1 |
| Miguel Oliveira | 1 | 1 |
| Nani | 1 | 1 |
| Paulo Jorge Pedro Lopes | 1 | 1 |
| Pedro Mendes | 1 | 1 |
| Pintassilgo | 1 | 1 |
| Piqueti | 1 | 1 |
| Raphael Guzzo | 1 | 1 |
| Raphinha | 1 | 1 |
| Renato Sanches | 1 | 1 |
| Ricardo Costa | 1 | 1 |
| Ricardo Quaresma | 1 | 1 |
| Rodrigo Pinho | 1 | 1 |
| Romário Baldé | 1 | 1 |
| Rui Daniel Morais Gomes | 1 | 1 |
| Tomás Tavares | 1 | 1 |
| Vítor Bruno | 1 | 1 |
| Vítor Ferreira | 1 | 1 |
| Wilson Eduardo | 1 | 1 |
| Yony Andrés González Copete | 1 | 1 |
| Raúl Jiménez | 0 | 2 |
| Diego Reyes | 0 | 1 |
| Luís Miguel Afonso Fernandes | 0 | 1 |
| Nélson Semedo | 0 | 1 |

Detalhe por artigo em `output/corpus_entities.csv`. Contagens descritivas desta amostra; não são uma avaliação de precisão.
