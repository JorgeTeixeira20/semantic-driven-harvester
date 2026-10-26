# Notas para a escrita da dissertação

Lista de observações que **devem aparecer no texto** e que podem perder-se entre
as secções do `experiments.md`. Usar na revisão dos capítulos: para cada nota,
confirmar que o texto a inclui (ou decidir conscientemente deixá-la de fora).
Cada nota indica a fonte; os números vêm só dessas fontes.

## Discussão

1. **Páginas antigas que não mostram a notícia no ecrã** (2026-10-26). Na anotação
   de verificação feita pelo autor (8 páginas), em **3 delas** (n.º 1 de 2002,
   n.º 5 de 2008 e n.º 16 de 2019) a notícia não se via na página do Arquivo.pt
   com a moldura e só foi encontrada no HTML ou na versão sem moldura (`noFrame`);
   na n.º 1 estava abaixo do marcador lateral. Leitura: para quem consulta o
   arquivo, o conteúdo das páginas antigas nem sempre é visível; o sistema extrai o
   texto diretamente do HTML e do texto extraído, o que é uma vantagem prática.
   Fonte: `docs/protocolo_cobertura_30.md` ("Notas da execução") e a secção
   "Precisão e cobertura em 30 notícias anotadas" do `experiments.md`. Ressalva:
   8 páginas, observação qualitativa, não uma taxa.

2. **Concordância da anotação** (2026-10-26). Nas notícias em que o autor e a sessão
   local leram o texto, a concordância foi total (31 de 31 entidades nas n.º 2–5); a
   única divergência inicial (n.º 1) foi de leitura da página, não de critério:
   concordância inicial 31/39 (79,5 %), final 39/39 depois de resolvida. A revisão
   da n.º 1 pelo autor já não foi às cegas. N.º 16–18 (2017–2024, às cegas):
   10/10. **Total: 41/49 (83,7 %) inicial, 49/49 final**, em 8 das 30 notícias
   (49 das 246 entidades anotadas); as outras 22 foram anotadas só pela sessão
   local. Mede a fiabilidade da anotação, não a do sistema. Mostra que as regras
   de anotação são claras.

3. **Trabalho relacionado: Politiquices e Major Minors** (Prémio Arquivo.pt 2021).
   O Major Minors (artigo SLATE 2021) organiza notícias sobre minorias numa ontologia em
   RDF. O Politiquices identifica personalidades políticas nos títulos com **classificadores
   de aprendizagem automática** e liga-as à **Wikidata** (página "Sobre"). Contraste útil
   com esta dissertação: mesma base de conhecimento (Wikidata), **método diferente** de
   identificação (vocabulário fechado em vez de classificadores treinados), o que ilustra
   as duas famílias da secção "Reconhecimento e Ligação de Entidades". Não afirmar que
   os três usam dicionários; não afirmar que os outros não avaliaram (dizer só que esta
   dissertação inclui uma avaliação explícita). Fonte: `experiments.md`, "Trabalho
   relacionado: Politiquices" e "Trabalho relacionado: Major Minors".

4. **Método por regras refinado por análise de erros.** Escrever como tal:
   regras e listas fechadas (como os projetos de 2021), refinadas em rondas
   sucessivas a partir de amostras de erros, cada ronda avaliada com uma amostra
   nova (sementes diferentes); limitação de generalização declarada (as regras são
   específicas do Record e do português); alternativa geral (NER + ligação de
   entidades) como trabalho futuro. Fonte: secções "Diagnóstico de falhas no
   painel" a "Erros de nome evidentes" do `experiments.md`.

## Limitações

5. **Modalidade só pelo URL**: 57,3 % dos artigos sem modalidade (terceira
   corrida), quase todos de 1999–2009; conclusões por modalidade valem só para os
   artigos com modalidade. Classificador treinado nas modalidades do URL como
   trabalho futuro. Fonte: `experiments.md`, "Modalidades: o que se pode concluir".

6. **Lacuna de 2010–2016**: deve-se ao domínio `record.xl.pt`, não à falta de
   notícias no arquivo. Fonte: `experiments.md`, "Lacuna de 2010–2016".

7. **Teto de 300 resultados por termo e ano**: um só termo ("futebol") alcança
   cerca de 826 mil URLs sem o teto. Fonte: `experiments.md`, paginação contínua.

7b. **TextSearch vs CDX** (2026-10-26). A descoberta usou a TextSearch (pesquisa por
   termos, com título, limitada a 300 resultados por termo e ano). O CDX lista todas as
   capturas sob um prefixo de endereço, sem depender dos termos — alternativa para uma
   recolha mais exaustiva (o Politiquices usa os dois) —, mas devolve também páginas que
   não são notícias, não traz o título e, nos testes, cortava o resultado por ordem de
   endereço e dava timeouts nos filtros (`experiments.md`, "Lacuna de 2010–2016"). Não
   acelera o download: o texto e o HTML continuam a ser pedidos um a um. Trabalho futuro.

8. **Ordem c′ antes do HTML** na extração do corpo: escolha medida (HTML mais
   limpo em 25 e pior em 12 dos 37 casos de discordância), não esquecimento.
   Fonte: `experiments.md`, "Corpo do artigo pelo contentor do HTML".

## Números a atualizar quando forem finais

Os números finais dependem de duas coisas ainda em curso: a **quarta corrida** do
`por_ano` (números do Caminho B e do painel) e a decisão sobre o corpus **completo**
(`por_ano` + 2010–2016 de `record.xl.pt`; muda o número de artigos, os anos e a
lacuna). Quando estiverem fechados, voltar a cada um destes sítios. Verificado
em 2026-10-26: os valores atuais conferem com o `experiments.md`.

| Capítulo (ficheiro) | Secção | O que está escrito agora | Depende de |
| --- | --- | --- | --- |
| Introdução (`introducao.typ`) | Contributos da Dissertação | "[N] artigos do Record entre 1999 e 2024" (por preencher) | completo |
| Arquivo.pt (`arquivopt.typ`) | Caracterização dos Conteúdos Arquivados | "129 317 artigos", "entre 1999 e 2024" | completo |
| Arquivo.pt | Caracterização dos Conteúdos Arquivados | "não foram identificados artigos … entre 2010 e 2016" + explicação pelo domínio `record.xl.pt` e números da descoberta (feito em 2026-10-26) | completo: se entrar, reescrever o parágrafo pela ordem recolha → lacuna → investigação → pesquisas sobre `record.xl.pt` → "acrescentaram [N] artigos, corpus de [N total]" (versão do autor de 2026-10-26, com os números); se não entrar, manter e remeter a integração para trabalho futuro |
| Arquivo.pt | Caracterização dos Conteúdos Arquivados | "126 798 possuem texto extraído", "123 844 possuem HTML" | completo |
| Arquivo.pt | Limitações e Desafios | lista de códigos HTTP "404, 429, 503" | rever: o `experiments.md` regista também 500 (HTML) e os 400 por acumulação de cookies, já resolvidos |
| Motor de colheita (`motorcolheita.typ`) | Estratégia de Pesquisa e Recolha | "108 termos (39/57/5/7)", "826 mil URLs" | não muda; se o completo entrar, acrescentar a pesquisa com `siteSearch=record.xl.pt` |
| Motor de colheita | Extração e Processamento | origem do corpo (c′ / HTML / sem corpo) — ainda sem números | quarta corrida (a correção da tabela do `<aux>` mudou `html:aux` e `sem_corpo`) |
| Motor de colheita | Tratamento da Redundância | "121 artigos … 112 com uma versão" | não muda (corpus de 125 artigos) |
| Ontologia (`ontologia.typ`) | Identificação e Enriquecimento Semântico (por escrever) | — | quarta corrida: artigos com ≥ 1 entidade, entidades aceites na híbrida, precisão (40 pares), precisão e cobertura (30 notícias), concordância |
| Protótipo (por escrever) | — | — | quarta corrida: modalidades (com e sem), top de entidades, tamanho do `data.js`; completo: anos |
| Avaliação (por escrever) | — | — | quarta corrida e 30 notícias |

## Perguntas de investigação (decididas em 2026-10-26)

Ficam no fim da secção "Problema de Investigação" da Introdução, antes dos Objetivos:
QI1 (características do Arquivo.pt que condicionam a recolha), QI2 (isolar o conteúdo
editorial e identificar entidades, e com que qualidade), QI3 (como uma ontologia organiza
os conteúdos preservando a proveniência e suportando a exploração). **A revisitar:** nas
Conclusões, uma subsecção "Resposta às questões de investigação"; na Avaliação, indicar que
resultado responde a cada pergunta (QI1 → capítulo do Arquivo.pt; QI2 → precisão e cobertura;
QI3 → ontologia e protótipo).

## Como ler os resultados das entidades (quarta corrida e 30 notícias, 2026-10-26)

Fonte: `experiments.md`, "Quarta corrida do `por_ano` e avaliação" e "Precisão e cobertura
em 30 notícias anotadas"; dados em `data/processed/avaliacao_cobertura_30.csv`.

- **Precisão alta, cobertura baixa, e porquê.** Passagem 2: precisão 74,0 % (64–82),
  cobertura 28,9 % (24–35). A cobertura baixa vem sobretudo do **âmbito do vocabulário**
  (desporto português, 1999–2024): 67,4 % das menções falhadas são de entidades fora do
  vocabulário (atletas estrangeiros, escalões, modalidades menores), concentradas em
  poucas notícias com listas longas. **Medida só sobre as entidades que existem no
  vocabulário, a cobertura é 55,5 % (47–64), e 75,5 % (66–83) sem as notícias sem corpo.**
  Escrever as três, por esta ordem, e explicar: o método funciona dentro do vocabulário;
  o limite principal é o vocabulário (trabalho futuro: alargá-lo ou NER).
- **Um artigo concentra 14 dos 25 erros** (lista lateral "Todas as notícias" dentro do
  corpo); sem ele, precisão 86,4 % (77–92). Dizer as duas, não só a melhor.
- **Precisão dos 40 pares:** 80,0 % (65–90) na quarta, 72,5 % (57–84) na terceira, com
  sementes diferentes e intervalos sobrepostos: **não afirmar que a precisão subiu**, só
  que os tipos de erro mudaram (tabelas e manchetes deram lugar a homónimos e nomes).
- **Erros de vocabulário conhecidos** (para a análise de erros): "João Carlos Rodrigues da
  Costa" tem a variante "Costa" e apanha Pinto da Costa, António Costa e outros (8 de 8
  menções da amostra erradas; está no top 30); "Rui Costa" junta três pessoas; a lista
  fechada não tem a variante "FC Porto" (só a abordagem híbrida a acrescenta).
- **Modalidades:** 39/40 certas (97,5 %) pelo URL; nenhum artigo de 1999–2009 tem
  modalidade; 68,2 % em 2017–2024; 42,7 % no corpus inteiro.
- **Limpeza do texto:** 38 de 40 trechos retirados estavam certos (os 2 falsos negativos
  sem entidade); nenhuma menção falhada nas 30 notícias se deve à limpeza.
- **Classificação dos motivos** feita por um só anotador (a sessão local); a concordância
  medida (41/49 às cegas, 49/49 final) é sobre as entidades, não sobre os motivos.
