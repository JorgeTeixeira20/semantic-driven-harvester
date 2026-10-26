# Referências: o que cada uma sustenta e como defendê-la

Material de estudo para a defesa (não entra na dissertação). Uma linha por referência do
`bibliography.yml`: onde é citada, que afirmação do texto sustenta, o mínimo a ler e uma
resposta possível a "porque escolheu este documento?". Atualizado em 2026-10-26 a partir
dos capítulos `introducao`, `estadoarte`, `arquivopt`, `motorcolheita` e `ontologia`.

**Regra:** antes da entrega, ler pelo menos o indicado em "O que ler" de cada referência
citada. Se não houver tempo para ler uma, é preferível retirar a citação do que mantê-la.

## Citadas no texto

| Chave | Onde é citada | Afirmação que sustenta | O que ler | "Porque este documento?" |
| --- | --- | --- | --- | --- |
| `koehler2004` | Estado da Arte, Preservação da Web | 361 páginas acompanhadas do final de 1996 a maio de 2003; restavam 122 (cerca de um terço); meia-vida de cerca de dois anos. **Por confirmar no artigo** antes da entrega; os "65 % de sítios ativos" (de um resumo de outra IA) **não foram confirmados**: não usar sem os ver no artigo | Resumo e resultados (as contagens por ano) | "É um estudo longitudinal clássico, que acompanhou o mesmo conjunto de páginas durante seis anos: em 2003 só restava cerca de um terço; dá evidência empírica da instabilidade da Web, que justifica os arquivos Web." |
| `klein2014` | Estado da Arte, Preservação da Web | *Reference rot* = *link rot* + *content drift*; nas publicações científicas, cerca de um em cada cinco artigos tem referências afetadas | Resumo e introdução (definições); o resultado está no próprio título | "Define com precisão *link rot*, *content drift* e *reference rot* e mostra a dimensão do problema num domínio onde as referências deviam ser estáveis." |
| `brugger2018` | Estado da Arte, Preservação da Web | A Web arquivada é uma fonte histórica com particularidades: proveniência, versões, momento da recolha | Introdução e o capítulo sobre a natureza da Web arquivada | "Trata a Web arquivada como fonte de investigação, não como cópia da Web; é o enquadramento para eu guardar a proveniência de cada captura (data, endereço) na ontologia." |
| `kohlschuetter2010` | Estado da Arte, Extração | O *boilerplate* (menus, publicidade, rodapés) pode ser distinguido do conteúdo principal com características textuais simples (por exemplo, número de palavras e densidade de ligações por bloco) | Resumo, introdução e a secção das características usadas | "É uma referência de base na deteção de *boilerplate*; mostra que o problema que encontrei no Record é geral, e que há métodos que não dependem de regras para cada sítio." |
| `broder1997` | Estado da Arte, Extração | É possível identificar documentos quase iguais comparando conjuntos de sequências de palavras (*shingles*) e medidas de semelhança | Resumo e a secção sobre semelhança (*resemblance*) | "Introduz a comparação de documentos por semelhança de conjuntos, que é o princípio da medida de Jaccard que usei para comparar capturas do mesmo artigo." |
| `weigle2023` | Estado da Arte, Extração | Páginas que carregam conteúdo por pedidos adicionais podem ser reproduzidas de forma incompleta ou incoerente no arquivo | Resumo e introdução | "Explica porque uma captura pode não mostrar o conteúdo original; observei isso nas páginas antigas do Record em que a notícia não aparece no ecrã e só está no HTML." |
| `w3cRdfPrimer2014` | Estado da Arte, Web Semântica | O RDF representa informação como triplos sujeito–predicado–objeto, formando um grafo | Secções iniciais (triplos, IRIs, grafos) | "É a especificação oficial do W3C; descreve o modelo de dados em que o meu grafo está escrito." |
| `w3cOwlOverview2012` | Estado da Arte, Web Semântica | A OWL define classes, propriedades e relações com mais expressividade, e suporta raciocínio | A visão geral (é curta) | "É a especificação oficial da linguagem em que a minha ontologia está definida (classes, subclasses de `Tema`, propriedades)." |
| `heath2011` | Estado da Arte, Web Semântica | Princípios de *Linked Data*: identificadores e representações normalizadas para ligar dados entre fontes | Capítulo 2 (os princípios de Linked Data) | "Justifica ligar as minhas entidades a identificadores externos (os QIDs da Wikidata) em vez de criar identificadores isolados." |
| `majorminors2021` | Estado da Arte, Trabalhos Relacionados | O Major Minors organiza notícias sobre minorias numa ontologia (RDF, triplestores) | O artigo SLATE 2021 (13 páginas; DOI 10.4230/OASIcs.SLATE.2021.3): resumo, introdução e a secção da ontologia. O sítio do projeto já não está acessível | "É o trabalho mais próximo do meu: usa o Arquivo.pt e uma ontologia para organizar notícias." |
| `politiquices2021` | Estado da Arte, Trabalhos Relacionados | Títulos de notícias do Arquivo.pt e do Público; classificadores de aprendizagem automática identificam as personalidades; ligação à Wikidata. **A página não refere RDF**: não o atribuir a esta citação | A página "Sobre" (lida pelo autor em 2026-10-26) | "Liga as personalidades à Wikidata, tal como eu, mas identifica-as com classificadores treinados; eu uso um vocabulário fechado da Wikidata. São as duas abordagens que descrevo no Estado da Arte." |
| `premioArquivo2021` | Estado da Arte, Trabalhos Relacionados | O Major Minors teve o 1.º prémio e o Politiquices o 2.º no Prémio Arquivo.pt 2021 | A notícia (curta) | "É a fonte oficial dos prémios; mostra que os dois projetos são reconhecidos pelo próprio Arquivo.pt." |
| `w3cSparql2013` | Estado da Arte, Web Semântica | O SPARQL consulta dados RDF através de padrões de triplos | A introdução da especificação | "É a especificação oficial da linguagem de consulta que usei sobre a Wikidata e no protótipo dos 125 artigos." |
| `arquivoSobre` | Arquivo.pt (3 vezes) | O que é o Arquivo.pt, quem o gere, desde quando preserva, que serviços oferece | A página toda | "É a descrição oficial do serviço." Ponderar juntar uma referência científica sobre o Arquivo.pt (ver abaixo). |

## Novas (a acrescentar com a secção "Reconhecimento e Ligação de Entidades")

| Chave | Onde é citada | Afirmação que sustenta | O que ler | "Porque este documento?" |
| --- | --- | --- | --- | --- |
| `nadeau2007` | Estado da Arte, Reconhecimento e Ligação de Entidades | Definição de NER; abordagens por regras/dicionários e por aprendizagem; avaliação por precisão e cobertura | Resumo, introdução e as secções sobre técnicas por regras/dicionários e sobre avaliação | "É o levantamento de referência sobre NER; situa a minha escolha (um dicionário) e justifica as métricas que usei." |
| `shen2015` | Idem | Definição de ligação de entidades; três passos: gerar candidatos, escolher o candidato, identificar menções sem entrada na base de conhecimento; dificuldades: variantes de nome e homónimos | Resumo e introdução | "Descreve a ligação a uma base de conhecimento, que é o que faço com a Wikidata; os problemas que aponta são os que encontrei e medi." |
| `vrandecic2014` | Idem | A Wikidata é colaborativa, livre, com identificadores estáveis e dados estruturados (o SPARQL **não** vem deste artigo, que é anterior ao serviço) | O artigo todo (8 páginas) | "É o artigo dos criadores da Wikidata; justifica a escolha da Wikidata como base de identificadores." |

## No `bibliography.yml`, mas não citadas

| Chave | Situação | Sugestão |
| --- | --- | --- |
| `costa2017` | Não citada em nenhum capítulo | Se a leste: citá-la no capítulo do Arquivo.pt ou no Estado da Arte (evolução do arquivamento da Web). Senão, deixá-la sem citar (não aparece na lista final). |
| `gomes2016` | Não citada em nenhum capítulo | Seria a referência científica para o Arquivo.pt, a juntar ao `arquivoSobre`. **Confirmar o título e os autores antes de citar** (não foi possível verificar esta entrada desta sessão). |
