# Protocolo: precisão e cobertura das entidades em 30 notícias anotadas

Escrito em 2026-10-25. Corre-se **depois da quarta corrida** do `por_ano` e
sobre os outputs dela. Objetivo: medir, além da precisão (das menções que o
sistema encontra, quantas estão certas), a **cobertura** (das menções que
existem nas notícias, quantas o sistema encontra), e explicar cada falha.

## Amostra

- 30 Artigos do `por_ano`, ao acaso com semente `20261026`, **estratificados**:
  15 do site de 1999–2009 (épocas "1999–2000" e "2000–2015 (ASP.NET)" com
  captura até 2009) e 15 do site de 2017–2024. Se o corpus `completo` já
  existir, 10 + 10 + 10 (a terceira parte de 2010–2016), com a mesma semente.
- **Não** excluir artigos sem corpo, Premium ou com poucas palavras: a medida é
  de ponta a ponta. Um artigo cujo corpo não foi extraído conta as suas menções
  como falhadas, com o motivo `sem_corpo`.
- Registar a lista dos 30 URLs antes de anotar (para não escolher depois).

## Anotação ("resposta certa")

Para cada Artigo, ler **a notícia na página arquivada** (título e texto da
notícia, sem menus, destaques, comentários, legendas de outras notícias) e
listar cada **entidade distinta** mencionada, de uma destas categorias (as do
âmbito do Caminho B):

- clube (de qualquer modalidade);
- pessoa do desporto: atleta ou treinador;
- estádio ou pavilhão;
- competição.

Fora do âmbito, não se anotam: dirigentes, árbitros, jornalistas, políticos,
seleções nacionais genéricas, empresas e marcas. Conta-se a **entidade**, não
cada ocorrência (o sistema regista presença por artigo). Para cada uma, anotar
o QID da Wikidata quando for claro; se não for, deixar vazio e anotar o nome.

A anotação faz-se **antes** de olhar para o que o sistema encontrou.

## Comparação

Com o CSV de entidades da quarta corrida (passagem 2, híbrida; e também a
passagem 1, só a lista fechada, para comparar), por Artigo:

- **certa**: o sistema encontrou a entidade e ela está na anotação (mesmo
  QID, ou mesmo nome quando não há QID);
- **errada**: o sistema encontrou-a e ela não está na anotação (falso
  positivo); motivo como no diagnóstico (widget, manchete, nome truncado,
  homónimo, genérico, outro);
- **falhada**: está na anotação e o sistema não a encontrou; motivo:
  - `fora_do_vocabulario`: a entidade não existe no vocabulário (nem na
    lista fechada nem na híbrida) — **limite do vocabulário**;
  - `forma_nao_prevista`: existe, mas o texto usa uma forma de nome que não
    está nas variantes (alcunha, só apelido, grafia diferente) — **limite do
    método**;
  - `regra_de_nomes`: existe e a forma está prevista, mas uma regra a retirou
    (nome de uma palavra em minúscula, nome próprio comum, nome truncado);
  - `retirada_pela_limpeza`: estava num trecho retirado por `--sem-repetidas`;
  - `homonimo_sem_qid`: encontrada, mas sem QID por ser homónima;
  - `sem_corpo`: o corpo do artigo não foi extraído;
  - `outro` (descrever).

## Saídas

- `data/processed/avaliacao_cobertura_30.csv` (pequeno, versionado): uma linha
  por entidade, com `artigo`, `epoca`, `entidade`, `categoria`, `qid`,
  `resultado` (`certa`/`errada`/`falhada`), `passagem` (1 ou 2), `motivo`.
- No `docs/experiments.md`, secção "Precisão e cobertura em 30 notícias
  anotadas":
  - por passagem e por época: certas, erradas, falhadas; **precisão**,
    **cobertura** e F1, com intervalo de Wilson a 95 %;
  - a tabela dos motivos das falhadas, separando **limite do vocabulário**
    (`fora_do_vocabulario`) de **limite do método** (os outros);
  - a cobertura **só sobre as entidades que existem no vocabulário**, que mede
    o método sem o limite do vocabulário.

## Verificação pelo autor

A anotação é feita pela sessão local. Para medir a sua fiabilidade, o autor
anota **5 dos 30 artigos** por conta própria (os 5 primeiros da lista), sem ver
a anotação da sessão, e regista-se a concordância (entidades em comum / total
de entidades distintas das duas anotações). Diferenças resolvidas pelo autor.

## Notas da execução (2026-10-26)

- **Sorteio:** `data/processed/amostra_cobertura_30.csv` (commit `c00ef3e`, antes
  da anotação), semente `20261026`: 15 Artigos de 1999–2009 (n.º 1–15) e 15 de
  2017–2024 (n.º 16–30), ao acaso dentro de cada estrato, de todos os Artigos
  retidos do `por_ano` (incluindo sem corpo e Premium). O corpus `completo` ainda
  não existia, por isso não há estrato de 2010–2016. Anotação da sessão local:
  commit `0f80db5`.
- **Viés na verificação do autor:** "os 5 primeiros da lista" ficaram **todos do
  estrato 1999–2009**, porque a lista está ordenada por estrato. A concordância
  medida nesses 5 vale para as páginas antigas (as mais difíceis), não para as
  recentes. Correção: o autor anota também **3 artigos do estrato 2017–2024 (n.º
  16, 17 e 18)**, e a concordância regista-se por estrato.
- **Páginas antigas e versão noFrame:** com a moldura do Arquivo.pt, a página n.º 5
  (2008) parecia não ter notícia (coluna central vazia); na versão
  `arquivo.pt/noFrame/replay/<tstamp>/<url>` a notícia existe, desformatada. A n.º 1
  (2002) continua sem notícia também na versão noFrame (só o marcador lateral da
  jornada). Regra: **anotar sempre na versão noFrame** e copiar o texto (Ctrl+A)
  quando a página está desformatada; só o texto entre o título e a linha "Data:".
- **Decisões de âmbito tomadas pelo autor na anotação:** seleções nacionais (ex.:
  "Selecção de Malta") e o nome de um estádio usado como sinónimo do clube
  ("ficar no Restelo") ficam como **duvidosos, não contados**; uma entidade só no
  caminho de navegação ("Futebol > Nacional > BWIN LIGA > Leixões") não conta;
  "M. Cláudio" e "Marco Cláudio" são a mesma entidade.
