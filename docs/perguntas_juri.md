# Perguntas difíceis do júri

Material de estudo para a defesa (não entra na dissertação). As perguntas vêm da revisão
da tese feita por quatro agentes em 2026-10-28; as respostas são pontos de partida, a
confirmar e a dizer por palavras próprias. Os números são os da dissertação e do
`experiments.md`.

## 1. Cobertura: que número representa o corpus todo?

"Os 28,9 % de cobertura vêm de 30 notícias de `record.pt`; em 2010–2016 são 48,8 %. Que
número representa as 200 101 notícias?"

- Nenhum dos dois, sozinho: são amostras pequenas, de períodos diferentes, e a cobertura
  varia muito de notícia para notícia.
- O que é estável nas duas amostras é o motivo: a maior parte das falhas vem de entidades
  fora do vocabulário e de notícias sem corpo. Dentro do vocabulário, o método encontra
  55,5 % (30 notícias) e 60,8 % (2010–2016).
- Por isso apresento a cobertura por período e não um valor único para o corpus.

## 2. Independência da anotação

"A ferramenta de IA fez a anotação inicial e o autor fez a segunda. Em que sentido a
referência é independente, e porque é que a concordância inicial de 60 % não aparece?"

- A segunda anotação foi feita às cegas, sem ver a primeira nem os resultados do sistema.
- Nas 30 notícias, todas as diferenças estavam numa notícia de 2002 cujo texto só estava
  no HTML; em 2010–2016, uma página mostrava um erro do Arquivo.pt e só abria pela versão
  original da captura. A concordância de 60 % (9/15) mede esse acesso à página, não o
  critério: com a mesma página, 14/15.
- Limitação assumida: só 8 de 30 e 3 de 15 notícias tiveram segunda anotação, e o segundo
  anotador sou eu.

## 3. Regras corrigidas com as mesmas notícias que as avaliam

"As regras das siglas foram corrigidas olhando para as mesmas 30 notícias que as avaliam.
Como garante que a cobertura da passagem inicial não está inflacionada?"

- A correção das siglas mudou 4 entidades nas 30 notícias (o "FC Porto" passou a ser
  reconhecido pelo vocabulário inicial, 43 → 47 certas); a passagem híbrida não mudou.
- A anotação não foi alterada depois da correção.
- Concordo que, em rigor, as 30 notícias serviram também de diagnóstico; uma amostra nova
  depois da última correção seria o ideal. As amostras de 2010–2016 foram retiradas depois
  e não motivaram nenhuma regra.

## 4. O "ano" é o da captura

"O ano é o da captura mais antiga. Que conclusões temporais se podem tirar das contagens
por ano?"

- Nenhuma sobre a produção do jornal: as contagens refletem o que o arquivo guardou, o
  que as pesquisas alcançaram e o limite de 300 resultados por termo e ano.
- A captura mais antiga é uma aproximação da data de publicação, dita como tal no
  Capítulo 6 e na legenda da Tabela 5.
- O protótipo serve para explorar o que está no corpus, não para medir tendências.

## 5. "Custo moderado" da abordagem híbrida

"A abordagem híbrida duplica os erros (12 → 25) para ganhar 24 certas. Porque lhe chama
custo moderado?"

- A precisão global desce de 79,7 % para 74,0 % e a cobertura sobe de 19,1 % para 28,9 %;
  em 2010–2016, de 95,7 % para 94,0 % e de 27,8 % para 48,8 %.
- 14 dos 25 erros são de uma única notícia (lista lateral no corpo); sem ela, 86,4 %.
- Para explorar o corpus, encontrar mais notícias de uma entidade compensa alguns erros a
  mais; para outro uso (por exemplo, estatísticas), o vocabulário inicial seria a escolha
  mais segura. A origem de cada entidade está no grafo, por isso é possível filtrar.

## 6. A verificação do RDF é circular?

"A verificação compara os ficheiros com eles próprios convertidos em RDF. O que mostra
sobre a ontologia, sem perguntas de competência nem avaliação com utilizadores?"

- Mostra a integridade da conversão: o grafo guarda tudo o que o protótipo usa dos
  artigos, temas e menções, e as consultas SPARQL recuperam-no sem perdas.
- Não mostra que a ontologia é a melhor possível nem a usabilidade do protótipo: não houve
  perguntas de competência formais nem testes com utilizadores (trabalho futuro).
- As cinco consultas de validação funcionam, na prática, como perguntas de competência:
  são as perguntas a que o protótipo responde.

## 7. Uma só captura por notícia

"A estabilidade do texto entre capturas (112 de 121) assenta em 125 artigos exploratórios,
e no corpus alargado há uma captura por artigo. Como justifica esta escolha?"

- Foi uma decisão de âmbito, pelo tempo de recolha (cada captura exige dois pedidos), e
  está dita como tal no Capítulo 4.
- Os 125 artigos mostraram que a maior parte das diferenças entre capturas era nos
  elementos da página e não no texto da notícia; não afirmo que as notícias não mudam.
- A ontologia continua a representar várias capturas por artigo, e o primeiro protótipo
  mostra o histórico de capturas: a recolha completa fica como trabalho futuro.

## 8. Classificação dos recursos avaliada só em `record.xl.pt`

"Porque é que a classificação das páginas como notícias só foi avaliada em `record.xl.pt`?"

- O `record.xl.pt` foi acrescentado no fim, com esquemas de endereço que nunca tinham sido
  vistos (`interior.aspx`, `interior_premium.aspx`, secções de vídeos e fotogalerias); era
  aí que o risco de erro era maior, e a amostra serviu para validar as regras novas antes
  de as usar. Deu 136 certas em 140 (97,1 %), e os 4 erros levaram a excluir vídeos e
  fotogalerias nesse domínio.
- Em `record.pt`, as regras vieram da exploração da fonte (o padrão `/detalhe/` e os
  esquemas antigos foram vistos página a página no corpus exploratório) e foram ajustadas
  ao longo do trabalho, mas não foram medidas com uma amostra. É uma limitação declarada
  na tese, a par das páginas que não são notícias identificadas por padrões evidentes.
- A regra dos vídeos e fotogalerias não foi aplicada a `record.pt` para não mudar o
  corpus já fechado e avaliado; essas páginas têm, na maior parte, pouco ou nenhum texto,
  pelo que contribuem pouco para as entidades.

## 9. Intervalos de Wilson com notícias agrupadas

"Os intervalos tratam cada entidade como independente, mas as entidades estão agrupadas
por notícia. Os intervalos não subestimam a incerteza?"

- Sim, subestimam: uma notícia concentra 14 dos 25 erros. Por isso apresento também o
  valor sem essa notícia (86,4 %) e não tiro conclusões de diferenças pequenas.
- Os intervalos servem para mostrar a ordem de grandeza da incerteza, não para testes
  estatísticos; uma análise por notícia (média e intervalo por notícia) seria mais correta.

## 10. Viés dos termos de pesquisa

"Os 108 termos (só 5 atletas) e o limite de 300 por termo e ano condicionam o corpus. As
frequências do protótipo dizem algo sobre o jornal?"

- Não diretamente: dizem algo sobre o corpus recolhido. Os termos vieram da organização
  editorial do Record (modalidades, clubes e competições dos endereços), e os 5 atletas
  vêm da fase exploratória.
- Uma recolha exaustiva, por exemplo listando as capturas de cada domínio, está no
  trabalho futuro.
