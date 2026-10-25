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
   Os dois usam listas fechadas ou dicionários e ontologias/RDF; o Politiquices usa
   um subconjunto da Wikidata num servidor SPARQL e uma tabela manual de nomes da
   imprensa. A abordagem desta dissertação está na mesma família (lista fechada da
   Wikidata), acrescenta a abordagem híbrida e **tem avaliação documentada**, que
   não foi encontrada publicada para nenhum dos dois. Fonte: `experiments.md`,
   "Trabalho relacionado: Politiquices" e "Trabalho relacionado: Major Minors".

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
| Arquivo.pt | Caracterização dos Conteúdos Arquivados | "não foram identificados artigos … entre 2010 e 2016" + frase sobre a estratégia de pesquisa | completo; acrescentar a explicação do domínio `record.xl.pt` (nota 6) em qualquer caso |
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
