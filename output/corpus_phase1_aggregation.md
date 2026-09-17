# Fase 1 — descoberta via TextSearch (Opção 2, corpus do Caminho A)

Execução real. Parâmetros comuns: `siteSearch=record.pt`, `from=2015`, `to=2020`, `maxItems=50`, `dedupField=url`/`dedupValue=1` explícitos. 13 termos (4 modalidades, 4 clubes, 5 atletas), 2 repetições por termo, offset só quando a página anterior veio cheia.

## Resumo

- Pedidos reais efetuados: 26
- Itens brutos recebidos (antes de deduplicar): 400
- Capturas únicas por `(originalURL, tstamp)`: 160
- **N (artigos únicos por `originalURL`): 159**
- Capturas encontradas por mais do que uma query: 20
- Divergências de metadados para a mesma `(originalURL, tstamp)`: 20

## Pedidos e resultados por termo

| Faceta | Termo | Repetição | Pedidos | Resultados |
| --- | --- | ---: | ---: | ---: |
| modalidade | futebol | 1 | 1 | 21 |
| modalidade | futebol | 2 | 1 | 21 |
| modalidade | basquetebol | 1 | 1 | 20 |
| modalidade | basquetebol | 2 | 1 | 20 |
| modalidade | andebol | 1 | 1 | 21 |
| modalidade | andebol | 2 | 1 | 21 |
| modalidade | voleibol | 1 | 1 | 19 |
| modalidade | voleibol | 2 | 1 | 19 |
| clube | Benfica | 1 | 1 | 19 |
| clube | Benfica | 2 | 1 | 19 |
| clube | Sporting | 1 | 1 | 20 |
| clube | Sporting | 2 | 1 | 20 |
| clube | Porto | 1 | 1 | 16 |
| clube | Porto | 2 | 1 | 16 |
| clube | SC Braga | 1 | 1 | 3 |
| clube | SC Braga | 2 | 1 | 3 |
| atleta | Cristiano Ronaldo | 1 | 1 | 20 |
| atleta | Cristiano Ronaldo | 2 | 1 | 20 |
| atleta | Bruno Fernandes | 1 | 1 | 15 |
| atleta | Bruno Fernandes | 2 | 1 | 15 |
| atleta | Telma Monteiro | 1 | 1 | 6 |
| atleta | Telma Monteiro | 2 | 1 | 6 |
| atleta | João Félix | 1 | 1 | 12 |
| atleta | João Félix | 2 | 1 | 12 |
| atleta | Nelson Évora | 1 | 1 | 8 |
| atleta | Nelson Évora | 2 | 1 | 8 |

## Divergências de metadados

| originalURL | tstamp |
| --- | --- |
| http://www.record.pt/internacional/detalhe/danny-deixa-zenit-respeito-a-decisao-de-nao-renovarem-comigo.html | 20170606020833 |
| http://www.record.pt/internacional/paises/inglaterra/detalhe/pep-guadiola-eu-e-o-zidane-somos-parecidos-no-cabelo.html | 20170606020822 |
| https://www.record.pt/futebol/futebol-de-praia/amp/sporting-entre-as-equipas-presentes-na-madjer-youth-cup | 20190424111034 |
| https://www.record.pt/modalidades/ciclismo/amp/alaphilippe-vence-segunda-etapa-e-yates-sobe-a-lideranca-da-tirreno-adriatico | 20190314190118 |
| http://www.record.pt/multimedia/videos/detalhe/zainadine-cortou-mal-a-bola-e-otavio-abriu-o-marcador.html | 20170807090457 |
| http://www.record.pt/multimedia/videos/detalhe/zungu-aproveitou-distracao-da-defesa-do-benfica-para-marcar.html | 20170807102925 |
| https://www.record.pt/sabermais/yebda | 20171227020719 |
| https://www.record.pt/sabermais/ze-pedro | 20171227023119 |
| https://www.record.pt/multimedia/fotogalerias/detalhe/zagreb-foi-abaixo-com-a-chegada-dos-vice-campeoes-do-mundo.html | 20180720050020 |
| https://www.record.pt/multimedia/fotogalerias/detalhe/AMP/benfica-e-uma-lesao-que-ainda-nao-foi-curada-assim-foi-o-aniversario-de-zivkovic.html | 20180720051618 |
| http://www.record.pt/multimedia/videos/detalhe/video-arbitro-e-o-arbitro-principal-viveram-momentos-dificeis-no-mexico-nova-zelandia.html | 20180413212306 |
| http://www.record.pt/multimedia/fotogalerias/detalhe/esta-falta-tirou-zeegelaar-do-derbi-com-o-benfica.html | 20170807104012 |
| http://www.record.pt/opiniao/detalhe/hora-zero-hora-de-recomecar-ou-de-continuar.html | 20170105190704 |
| https://www.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/yohan-boli-observado | 20190405043020 |
| https://www.record.pt/futebol/detalhe/carlos-xistra-castigado-por-erro-no-golo-do-p-ferreira-frente-ao-sporting | 20191104200433 |
| https://www.record.pt/futebol/futebol-nacional/liga-nos/sporting/detalhe/AMP/leao-sem-joqueres-tenta-xeque-mate.html | 20180421014625 |
| https://www.record.pt/multimedia/videos/detalhe/zlobin-fez-de-paulo-lopes-e-subiu-a-baliza-para-erguer-a-taca-de-campeao | 20190522132120 |
| https://www.record.pt/modalidades/ciclismo/detalhe/alaphilippe-vence-segunda-etapa-e-yates-sobe-a-lideranca-da-tirreno-adriatico | 20190314190114 |
| http://www.record.pt/futebol/futebol-nacional/liga-nos/sporting/detalhe/zeegelaar-na-lista-de-dispensaveis.html/ | 20170302185303 |
| http://www.record.pt/modalidades/atletismo/detalhe/zach-miller-vence-oitava-edicao-do-madeira-island-ultra-trail.html | 20180720075135 |

Ambas as versões do item ficam preservadas no raw de origem; esta tabela só sinaliza a divergência, não a resolve.

Estes valores são o resultado real desta execução, não uma estimativa. Corpus agregado em `output/corpus_phase1_captures.csv` (uma linha por captura única, com proveniência de faceta/termo).
