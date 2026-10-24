# Plano: extensão do corpus a 2010–2016 (`record.xl.pt`)

Instruções para a sessão local executar **do princípio ao fim sem pedir
confirmações**. Escrito em 2026-10-24, depois da medição registada em
`docs/experiments.md` ("Lacuna de 2010–2016"): 103 178 `originalURL` distintos
em `record.xl.pt` (66 696 com cara de notícia), mínimos por causa do teto de
300 resultados por termo e ano.

O autor está a escrever a dissertação em paralelo. Os números finais atuais
(corpus `por_ano`, segunda corrida) **continuam a ser os oficiais** até o autor
decidir o contrário. Esta extensão produz um corpus **novo e separado**; não
substitui nem altera nada do `por_ano`.

## Regras gerais

1. **Não tocar no `por_ano`.** Nenhum ficheiro de `output/*por_ano*`,
   `data/processed/*por_ano*` ou das pastas raw já existentes é alterado ou
   apagado. As novas etiquetas são:
   - `xl` — só os artigos de `record.xl.pt` de 2010–2016;
   - `completo` — `por_ano` + `xl`, sem duplicados.
2. **Retomável.** Cada passo longo tem de poder ser interrompido e retomado
   sem repetir pedidos já feitos (reutilizar o raw guardado).
3. **Respeito pelo Arquivo.pt.** Um pedido de cada vez, com a mesma pausa da
   recolha do `por_ano`. Aplicar as soluções já documentadas: renovar a sessão
   HTTP (sem cookies acumulados) para evitar os 400, e esperar e retomar nos 503.
   Se o Arquivo.pt devolver erros seguidos durante mais de 2 horas, parar a
   recolha, registar onde ficou e continuar com o que houver (ver "Paragens").
4. **Decisões sem perguntar.** Quando surgir uma escolha não prevista aqui,
   escolher a opção **mais conservadora** (a que não mete erros novos nos
   dados, mesmo que perca cobertura), registar a escolha e o motivo no
   `experiments.md` e continuar.
5. **Números.** Só se registam números medidos. Nada de estimativas
   apresentadas como resultados.
6. **Testes.** Toda a alteração de código leva testes offline no estilo dos
   existentes; `python -m unittest discover -s tests` tem de passar antes de
   cada commit.
7. **Git.** Começar com `git fetch origin && git merge
   origin/claude/affectionate-gates-wtftgh`. Commits pequenos, por passo, com
   push para `main`. Nunca versionar ficheiros grandes (CSV de entidades, RDF,
   `data.js`, raw, textos, HTML); registar no `experiments.md` o nome, o
   tamanho e o comando que os gera.

## Passos

### 0. Preparação

- Correr os testes. Anotar a hora de início.
- Abrir no `docs/experiments.md` uma secção nova "Extensão do corpus a
  2010–2016 (`record.xl.pt`)", onde se regista cada passo (comando, duração,
  contagens, decisões).

### 1. Descoberta

- **Reutilizar** as respostas já guardadas em
  `data/raw/corpus_queries/lacuna_xl_2010_2016/`: não repetir a pesquisa.
- Produzir o CSV de capturas da etiqueta `xl` no mesmo formato do
  `output/corpus_phase1_por_ano_captures.csv` (termo, modalidade/faceta, URL,
  timestamp, …), para o painel e o Caminho B o poderem ler.

### 2. Identidade dos URLs (código)

O agrupamento atual (`url_identity.normalize_for_grouping`,
`corpus_classification.canonical_key`) não junta domínios diferentes.

- Para **agrupar**, tratar `record.xl.pt`, `www.record.xl.pt`, `record.pt` e
  `www.record.pt` como o mesmo site (o mesmo `interior.aspx?content_id=N` nos
  dois domínios é o mesmo artigo). Os **identificadores** continuam a ser o
  `originalURL` canónico, como hoje.
- Testes: os quatro hosts dão a mesma chave; caminhos diferentes continuam
  diferentes; os casos já testados não mudam.
- Confirmar que o `por_ano` **não muda** com esta alteração: correr só a
  agregação/classificação do `por_ano` para uma pasta temporária e comparar as
  contagens com as oficiais. Se mudarem, a alteração só se aplica com uma
  opção nova (por exemplo `--juntar-dominios`), ligada apenas para `xl` e
  `completo`.

### 3. Classificação (Artigo vs. outras páginas)

- Correr a classificação para `xl`. Ajustar as regras só se for preciso para
  os esquemas novos (`interior.aspx?content_id=`, `noticia.aspx?id=`,
  `interior*.aspx`, `/detalhe/…html` em `record.xl.pt`). Calendários, jogos em
  direto, páginas com GUID, capas e URLs numéricos (`/1.15384615385`) **não**
  são Artigos.
- Validar a classificação numa amostra de **20 URLs por ano**, 140 no total,
  abrindo a página arquivada. Registar a precisão. Se a precisão for
  **< 90 %**, corrigir as regras e repetir a amostra (uma vez). Se continuar
  < 90 %, seguir com a regra mais restritiva e registar.
- Uma captura por artigo: a **mais antiga** conhecida, como no `por_ano`.

### 4. Recuperação dos conteúdos

- Descarregar o texto extraído e o HTML arquivado de cada Artigo de `xl`, para
  as mesmas pastas (`data/raw/texts/` e `data/raw/original_html/`), com o
  mesmo esquema de nomes. Não sobrescrever ficheiros existentes.
- Esperado: dezenas de milhares de pedidos, várias horas, possivelmente mais
  de um dia. Correr em segundo plano e guardar o progresso.
- No fim, contar: artigos com texto, com HTML, sem nenhum dos dois, e
  falhas (por código HTTP).

### 5. Corpo editorial (extrator)

- Medir, para `xl`, quantos artigos têm corpo pela c′, pelo contentor do HTML
  e sem corpo (como no `por_ano`).
- Se a fração sem corpo for **> 10 %**, abrir 10 HTML sem corpo (de anos
  diferentes) com `python -m semantic_harvester.html_body`, identificar o
  contentor do corpo e acrescentá-lo ao `html_body.CONTAINERS` com testes
  (HTML mínimo, como nos testes existentes). Validar com 20 artigos: o corpo
  extraído começa no início da notícia e não traz menus, "ler mais",
  publicidade nem a assinatura. Repetir no máximo **duas vezes**; o que
  ficar sem corpo fica registado como limitação.
- Premium fica sem corpo, como no `por_ano`.

### 6. Grafo RDF

- Gerar o N-Triples de `xl` e de `completo` pelo mesmo caminho do `por_ano`
  (mesma ontologia, mesmas propriedades). Em `completo`, um artigo presente
  nos dois corpora fica **uma vez**, com a captura mais antiga.
- Época do site (`navigation_corpus.ERAS`): o rótulo "2000–2009" deixa de
  servir para `interior.aspx` em 2010–2015. Renomear para algo que descreva
  o esquema sem afirmar anos errados (por exemplo "2000–2015 (ASP.NET)") e
  acrescentar `/detalhe/` de 2016 ao site atual, com testes. Não altera os
  dados do `por_ano`; o painel do `por_ano` só muda o rótulo, se for
  regenerado.

### 7. Tabela de clubes do URL

- `python -m semantic_harvester.club_url_map --corpus completo`; aplicar as
  sugestões `unico` com `--aplicar`.
- Para `ambiguo` e `sem`, seguir as mesmas regras de 2026-10-23: equipas B
  pelo nome com "B"; abreviaturas (`sp`, `ac`, `lnk`…) pelo clube do
  vocabulário alargado; clubes refundados ficam com o QID histórico (limitação
  registada). Se continuar duvidoso, fica **sem mapa**.

### 8. Cadeia (Caminho B, híbrida, painel) para `completo`

Os mesmos passos e opções da segunda corrida do `por_ano`, com
`--corpus completo`:

- 1a `corpus_entities --texto corpo-html` (lista fechada);
- 1b `corpus_candidate_entities --texto corpo-html`;
- 1d `corpus_entities_rdf`;
- 2 `wikidata_candidates --min-artigos 10 --reutilizar`. Aqui **pode haver
  pedidos novos** à Wikidata (candidatos novos); são permitidos. Um de cada
  vez, com a pausa por omissão;
- 3a, 3b e 3c com o vocabulário híbrido de `completo`.

Registar tempos e memória máxima por passo, como no relatório da segunda
corrida.

### 9. Avaliação

- Amostra de **50 entidades aceites novas** da abordagem híbrida (só as que
  não estavam no vocabulário híbrido do `por_ano`): 25 com ≥ 50 artigos e
  25 com 10–49, avaliadas como na segunda corrida (certa / errada / duvidosa,
  pela descrição na Wikidata e pelo artigo de exemplo).
- As 30 entidades mais mencionadas em `completo`: quantos erros evidentes.

### 10. Painel

- `navigation_corpus --corpus completo --vocabulario <híbrido de completo>`,
  a gerar `output/prototipo_completo/`. Verificar com o Playwright: sem
  erros na consola, tempo de carregamento, pesquisa "Braga", separador
  Estatísticas e o gráfico por ano **sem a lacuna 2010–2016**. Captura em
  `output/prototipo_completo_captura.png` (pode ser versionada, como a
  anterior).
- Se o `data.js` passar de **60 MB** ou a página demorar mais de **10 s** a
  carregar, registar e continuar; não dividir o ficheiro sem decisão do
  autor.

### 11. Documentação final

- Na secção nova do `experiments.md`: uma tabela **`por_ano` vs `completo`**
  com Artigos, Artigos por ano (2010–2016), com corpo, com ≥ 1 entidade
  (lista fechada e híbrida), entidades aceites, amostra de 50 e erros no top
  30, mais os tempos.
- No `docs/PROJECT_STATUS.md`, no índice "Para a escrita da tese", **só**
  uma frase: a extensão existe, onde estão os números, e que os oficiais
  continuam a ser os do `por_ano` até decisão do autor.
- `AGENTS.md`: acrescentar as opções novas, se as houver.

## Paragens

Parar **só** nestes casos (registando o motivo e o ponto exato):

- algum ficheiro do `por_ano` foi alterado (comparar tamanhos e somas antes
  e depois);
- testes a falhar que não se conseguem corrigir em 30 minutos;
- o Arquivo.pt a recusar pedidos durante mais de 2 horas seguidas.

Neste último caso, seguir com os artigos já recolhidos: fazer os passos
5–11 sobre eles e registar a cobertura parcial.

## Relatório final ao autor

No fim, devolver **só** isto, em markdown simples (tabelas estreitas):

1. a tabela `por_ano` vs `completo` do passo 11;
2. a precisão da classificação (passo 3) e a origem do corpo (passo 5);
3. a amostra de 50: certas / erradas / duvidosas, e os erros listados;
4. as decisões tomadas pela regra 4 (uma linha cada);
5. os commits feitos e o caminho do `index.html` de `completo`.
