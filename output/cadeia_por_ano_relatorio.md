# Cadeia do Caminho B no corpus alargado (por_ano) — segunda corrida, depois das correções

Correções `81e46e3` e `3d6bf30`; tabela de clubes `2c9e032` + `73e4e2a`; limiar do `wikidata_candidates`: ≥ 10 artigos, só com respostas guardadas (0 pedidos novos). Corrida de 2026-10-23, 09:17 → 11:07.

## Tabela de resumo (primeira corrida → segunda corrida)

| Medida | Antes das correções | Depois das correções |
| --- | ---: | ---: |
| Artigos com ≥ 1 entidade, passagem 1 (lista fechada) | 91 631 (70,9 %) | 88 467 (68,4 %) |
| Artigos com ≥ 1 entidade, passagem 2 (híbrida ≥ 10) | 104 227 (80,6 %) | 102 372 (79,2 %) |
| Aceites + variantes novas no `wikidata_candidates` | 3 344 | 2 918 |
| … dos quais pela pesquisa | 747 | 333 |
| `forma_rejeitada` / `item_rejeitado` | — / — | 1 243 / 498 |
| Ambíguos | 374 | 164 |
| Artigos com "Nem" / "Carlos" / "Ricardo" (passagem 2) | 8 066 / 6 486 / 5 015 | 1 467 / 1 / 0 |
| Slugs de clube sem mapa (artigos) | 49 (10 823) | 0 (0) |
| Benfica, Sporting e Braga com QID no RDF | não | sim (Q131499, Q75729, Q75684) |
| Triplos RDF, passagem 1 / passagem 2 | 4 592 612 / 7 216 287 | 4 154 470 / 6 265 122 |
| Entidades distintas no RDF, passagem 2 | 7 414 | 7 078 |
| Erros evidentes nas 30 entidades mais mencionadas | 4 | 1 ("Speedway 2. Ekstraliga" ← "I Liga") |
| Amostra de aceites revista à mão | 30 (10–49): 2 errados, 2 duvidosos | 50: 3 errados, 5 duvidosos (abaixo) |
| `data.js` da passagem 2 | 31,8 MB | 31,2 MB |

Tempos e memória máxima: 1a 41 min 29 s (1,84 GB); 1b 4 min 51 s (2,58 GB); 1d 46 s (0,90 GB); 2 4,3 s (69 MB); 3a 43 min 32 s (2,07 GB); 3b 11 min 56 s (2,35 GB); 3c 47 s (0,93 GB).

## Amostra de 50 aceites revista à mão (25 com ≥ 50 artigos, 25 com 10–49; semente 20261023)

Avaliação pela identidade do item (descrição na Wikidata e URL do artigo de exemplo); "duvidosa" quando o contexto disponível não chega para decidir.

| Candidato | Artigos | Tipo | Item | Avaliação |
| --- | ---: | --- | --- | --- |
| Estádio do Dragão | 785 | estadio | Q271454 | certa |
| Segunda Liga | 601 | competicao | Q754488 | certa |
| José Couceiro | 311 | treinador | Q2422828 | certa |
| Camp Nou | 277 | estadio | Q159848 | certa |
| Novak Djokovic | 227 | jogador | Q5812 | certa |
| Rúben Ribeiro | 138 | jogador | Q91018787 Ruben Ribeiro | **errada**: cavaleiro brasileiro; no Record é o futebolista (exemplo: Gil Vicente–Aves) |
| Jogos Paralímpicos | 132 | competicao | Q73633 | certa |
| Kanoa Igarashi | 109 | jogador | Q27757444 | certa (surfista) |
| Estádio Capital do Móvel | 108 | estadio | Q1370763 | certa |
| Leonardo Ruiz | 94 | jogador | Q93892105 Leonardo Ruíz | duvidosa: futebolista peruano escolhido por proeminência; exemplo num artigo do Varzim |
| Kobe Bryant | 90 | jogador | Q25369 | certa |
| Standard Liège | 90 | clube | Q190561 | certa |
| Hertha Berlim | 89 | clube | Q102720 | certa |
| Inter Miami | 81 | clube | Q16844931 | certa |
| Pavilhão Atlântico | 79 | estadio | Q1463929 MEO Arena | certa |
| The Athletic | 74 | estadio | Q16632730 The Athletic Grounds | **errada**: é o jornal; o item é um estádio do Millwall (1890–1901) |
| Octávio Machado | 68 | treinador | Q7077130 | certa |
| David Nalbandian | 66 | jogador | Q181501 | certa |
| Andy Roddick | 66 | jogador | Q54584 | certa |
| Paul Pogba | 65 | jogador | Q129027 | certa |
| Dínamo de Kiev | 62 | clube | Q179075 | certa |
| Major League Soccer | 59 | competicao | Q18543 | certa |
| Caroline Marks | 58 | jogador | Q52746885 | certa (surfista) |
| Maverick Viñales | 58 | jogador | Q925691 | certa |
| Frank Lampard | 53 | treinador | Q41533 | certa |
| Estádio Municipal de Mafra | 44 | estadio | Q10277329 | certa |
| Tommy Haas | 41 | jogador | Q53560 | certa |
| Fed Cup | 39 | competicao | Q206984 | certa |
| Matthijs de Ligt | 24 | jogador | Q26259982 | certa |
| Copa João Havelange | 24 | competicao | Q2453542 | certa |
| Bernardo Manuel | 19 | jogador | Q42890123 | duvidosa: atleta angolano; exemplo `noticia.asp` sem contexto no URL |
| Al Nasr | 18 | clube | Q812723 Al-Nasr (Dubai) | duvidosa: pode ser o Al-Nassr saudita (exemplo: mercado de transferências) |
| Jorge Correa | 18 | jogador | Q5934800 | certa (avançado argentino do Marítimo) |
| Alexandre Nobre | 17 | jogador | Q126999155 | certa (triatleta) |
| Rigoberto Urán | 17 | jogador | Q362185 | certa |
| Vissel Kobe | 17 | clube | Q844271 | certa |
| Marco Materazzi | 17 | treinador | Q185081 | certa; tipo discutível (no Record sobretudo jogador) |
| Luís Torres | 17 | jogador | Q16573201 Luis Torres | **errada**: futebolista do Belize, pela pesquisa e por proeminência (exemplo: Campeonato de Portugal) |
| Sara Ferreira | 16 | jogador | Q98074809 | certa (futebolista portuguesa; exemplo: Torreense feminino) |
| Lionel Scaloni | 16 | treinador | Q311586 | certa |
| Mário Coluna | 15 | treinador | Q705585 | certa; tipo discutível (sobretudo jogador) |
| Rafael Gava | 15 | jogador | Q62081707 | duvidosa: futebolista brasileiro; exemplo Louletano–Paços de Ferreira |
| Nou Camp | 14 | estadio | Q159848 | certa |
| Raphael Silva | 14 | jogador | Q23639449 Raphael da Silva Arruda | duvidosa: exemplo num artigo do Boavista |
| Dimitar Berbatov | 13 | jogador | Q170235 | certa |
| Jude Bellingham | 11 | jogador | Q66241169 | certa |
| Sébastien Bourdais | 10 | jogador | Q171307 | certa |
| Marco Marzano | 10 | treinador | Q726502 | certa; tipo errado (ciclista) |
| Eddie Ekiyor | 10 | jogador | Q135268062 | certa (basquetebolista; Sporting–V. Guimarães) |
| Greg Rusedski | 10 | jogador | Q335209 | certa |

Resultado: **42 certas** (3 com tipo discutível ou errado), **3 erradas**, **5 duvidosas**. Com ≥ 50 artigos: 22 certas, 2 erradas, 1 duvidosa. Com 10–49: 20 certas, 1 errada, 4 duvidosas.

Erros que continuam: "Speedway 2. Ekstraliga" (2 462 artigos) vem de "I Liga" pelo nome exato; "Nem" ainda conta em 1 467 artigos (início de frase com maiúscula — limitação já registada).

## Detalhe


## Origem do corpo por esquema de URL

| esquema | c′ | html:apreto12n | html:aux | html:bodybox | html:readerBody | html:td480 | html:text_container | premium | sem_corpo | sem_texto | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| detalhe | 53102 | 0 | 0 | 5348 | 38 | 0 | 864 | 9714 | 1723 | 1381 | 72170 |
| amp | 7406 | 0 | 0 | 175 | 0 | 0 | 0 | 1179 | 12 | 18 | 8790 |
| noticia.aspx?id | 1704 | 1971 | 76 | 0 | 0 | 0 | 0 | 0 | 29 | 34 | 3814 |
| noticia.asp?id | 28 | 23 | 27500 | 0 | 0 | 0 | 0 | 0 | 5206 | 1016 | 33773 |
| shownews.asp?id | 0 | 0 | 8284 | 0 | 0 | 0 | 0 | 0 | 56 | 70 | 8410 |
| tn0cs.asp?nid | 0 | 0 | 0 | 0 | 0 | 1690 | 0 | 0 | 5 | 0 | 1695 |
| tn1cs.asp?nid | 0 | 0 | 0 | 0 | 0 | 662 | 0 | 0 | 3 | 0 | 665 |
| **total** | 62240 | 1994 | 35860 | 5523 | 38 | 2352 | 864 | 10893 | 7034 | 2519 | 129317 |

## Artigos com ≥ 1 entidade, por década

| década | artigos | passagem 1 (lista fechada) | % | passagem 2 (híbrido ≥ 10) | % |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1990s | 294 | 267 | 90.8 | 285 | 96.9 |
| 2000s | 48063 | 33686 | 70.1 | 39430 | 82.0 |
| 2010s | 43442 | 31273 | 72.0 | 35473 | 81.7 |
| 2020s | 37518 | 23241 | 61.9 | 27184 | 72.5 |
| **total** | 129317 | 88467 | 68.4 | 102372 | 79.2 |

## Artigos com ≥ 1 entidade, por esquema

| esquema | artigos | passagem 1 (lista fechada) | % | passagem 2 (híbrido ≥ 10) | % |
| --- | ---: | ---: | ---: | ---: | ---: |
| detalhe | 72170 | 48906 | 67.8 | 55998 | 77.6 |
| amp | 8790 | 5608 | 63.8 | 6659 | 75.8 |
| noticia.aspx?id | 3814 | 3259 | 85.4 | 3576 | 93.8 |
| noticia.asp?id | 33773 | 22160 | 65.6 | 26058 | 77.2 |
| shownews.asp?id | 8410 | 6410 | 76.2 | 7785 | 92.6 |
| tn0cs.asp?nid | 1695 | 1501 | 88.6 | 1644 | 97.0 |
| tn1cs.asp?nid | 665 | 623 | 93.7 | 652 | 98.0 |
| **total** | 129317 | 88467 | 68.4 | 102372 | 79.2 |

## Artigos com ≥ 1 entidade, década × esquema (passagem 1 → passagem 2)

| década | detalhe | amp | noticia.aspx?id | noticia.asp?id | shownews.asp?id | tn0cs.asp?nid | tn1cs.asp?nid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1990s |  |  |  |  |  | 150 → 162 / 168 | 117 → 123 / 126 |
| 2000s |  |  | 3259 → 3576 / 3814 | 22160 → 26058 / 33773 | 6410 → 7785 / 8410 | 1351 → 1482 / 1527 | 506 → 529 / 539 |
| 2010s | 27506 → 31079 / 38129 | 3767 → 4394 / 5313 |  |  |  |  |  |
| 2020s | 21400 → 24919 / 34041 | 1841 → 2265 / 3477 |  |  |  |  |  |

## As 30 entidades mais mencionadas (passagem 2, por artigos)

| # | entidade | categoria | artigos | ocorrências | origem | Portugal | QID |
| ---: | --- | --- | ---: | ---: | --- | --- | --- |
| 1 | Sport Lisboa e Benfica | clube | 30996 | 119568 | lista_fechada | sim | Q131499|Q136823040|Q19060544|Q2029819 |
| 2 | Sporting Clube de Portugal | clube | 27960 | 107364 | lista_fechada | sim | Q112176117|Q75729 |
| 3 | Futebol Clube do Porto | clube | 23840 | 76085 | lista_fechada+candidato | sim | Q128446 |
| 4 | Sporting Clube de Braga | clube | 11442 | 28826 | lista_fechada | sim | Q138721732|Q75684 |
| 5 | Clube de Futebol Os Belenenses | clube | 10290 | 29008 | lista_fechada | sim | Q216510 |
| 6 | Club Sport Marítimo | clube | 9895 | 29379 | lista_fechada | sim | Q216503 |
| 7 | Vitória Futebol Clube | clube | 8917 | 25268 | lista_fechada | sim | Q208585 |
| 8 | Gil Vicente Futebol Clube | clube | 8388 | 22912 | lista_fechada+candidato | sim | Q926438 |
| 9 | Taça de Portugal | competicao | 8084 | 15480 | candidato | sim | Q29224 |
| 10 | União Desportiva de Leiria | clube | 7596 | 21643 | lista_fechada | sim | Q211401 |
| 11 | Varzim Sport Club | clube | 7344 | 21444 | lista_fechada | sim | Q1429473 |
| 12 | Sporting Clube Farense | clube | 7135 | 21172 | lista_fechada | sim | Q744353 |
| 13 | Sport Clube Beira-Mar | clube | 6364 | 22027 | lista_fechada | sim | Q688300 |
| 14 | Liga dos Campeões da UEFA | competicao | 4906 | 7781 | candidato | sim | Q18756 |
| 15 | Hugo Henrique | jogador | 4646 | 4701 | lista_fechada | sim | Q10298763 |
| 16 | Derlei | jogador | 4452 | 4720 | lista_fechada | sim | Q703983 |
| 17 | Rio Ave Futebol Clube | clube | 4163 | 10550 | lista_fechada+candidato | sim | Q622432 |
| 18 | Associação Académica de Coimbra – O.A.F. | clube | 4097 | 11441 | lista_fechada | sim | Q243235 |
| 19 | Cristiano Ronaldo | jogador | 4086 | 10512 | lista_fechada | sim | Q11571 |
| 20 | João Carlos Rodrigues da Costa | jogador | 4019 | 7810 | lista_fechada | sim | Q30122631 |
| 21 | Grupo Desportivo Estoril Praia | clube | 3909 | 8770 | lista_fechada | sim | Q634829 |
| 22 | Real Madrid Club de Fútbol | clube | 3584 | 7216 | candidato | nao | Q8682 |
| 23 | Jogos Olímpicos | competicao | 3356 | 6732 | candidato | sim | Q5389 |
| 24 | Leixões Sport Club | clube | 3121 | 8645 | lista_fechada | sim | Q623730 |
| 25 | Futebol Clube Paços de Ferreira | clube | 2911 | 5863 | lista_fechada | sim | Q371136 |
| 26 | Manchester United Football Club | clube | 2642 | 5117 | candidato | nao | Q18656 |
| 27 | Moreirense Futebol Clube | clube | 2618 | 6479 | lista_fechada | sim | Q1346314 |
| 28 | Clube Desportivo Feirense | clube | 2538 | 6744 | lista_fechada | sim | Q671042 |
| 29 | Pedro Mantorras | jogador | 2496 | 3057 | lista_fechada | sim | Q464815 |
| 30 | Speedway 2. Ekstraliga | competicao | 2462 | 3549 | candidato | nao | Q11710778 |

## Artigos com "Nem", "Carlos" e "Ricardo" (antes e depois das correções)

| entidade | passagem 1 antes | passagem 1 agora | passagem 2 antes | passagem 2 agora |
| --- | ---: | ---: | ---: | ---: |
| Nem | 8066 | 1467 | 8066 | 1467 |
| Carlos | 6492 | 1 | 6486 | 1 |
| Ricardo | 5015 | 0 | 5015 | 0 |

## URI de Benfica, Sporting e Braga no RDF (passagem 2)

| clube | sujeito no RDF |
| --- | --- |
| Sport Lisboa e Benfica | wd:Q131499 |
| Sporting Clube de Braga | wd:Q75684 |
| Sporting Clube de Portugal | wd:Q75729 |

Entidades distintas mencionadas, por categoria e origem: {('clube', 'candidato'): 293, ('clube', 'lista_fechada'): 93, ('clube', 'lista_fechada+candidato'): 7, ('competicao', 'candidato'): 219, ('estadio', 'candidato'): 108, ('jogador', 'candidato'): 1773, ('jogador', 'lista_fechada'): 4166, ('jogador', 'lista_fechada+candidato'): 31, ('treinador', 'candidato'): 388}

## Slugs de clube sem mapa: 0 slugs, 0 artigos



## Decisões do wikidata_candidates (≥ 10)

| decisão | candidatos |
| --- | ---: |
| sem_correspondencia | 3315 |
| aceite | 2880 |
| tipo_nao_aceite | 1335 |
| forma_rejeitada | 1243 |
| item_rejeitado | 498 |
| ambiguo | 164 |
| variante_nova | 38 |

Decisão × tipo:

| decisão | (sem) | clube | competicao | estadio | jogador | treinador | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sem_correspondencia | 3315 | 0 | 0 | 0 | 0 | 0 | 3315 |
| aceite | 0 | 319 | 256 | 122 | 1786 | 397 | 2880 |
| tipo_nao_aceite | 1335 | 0 | 0 | 0 | 0 | 0 | 1335 |
| forma_rejeitada | 1243 | 0 | 0 | 0 | 0 | 0 | 1243 |
| item_rejeitado | 498 | 0 | 0 | 0 | 0 | 0 | 498 |
| ambiguo | 164 | 0 | 0 | 0 | 0 | 0 | 164 |
| variante_nova | 0 | 7 | 0 | 0 | 28 | 3 | 38 |

Aceites + variantes novas, por tipo × Portugal:

| tipo | Portugal sim | Portugal não | total |
| --- | ---: | ---: | ---: |
| clube | 40 | 286 | 326 |
| competicao | 67 | 189 | 256 |
| estadio | 73 | 49 | 122 |
| jogador | 309 | 1505 | 1814 |
| treinador | 117 | 283 | 400 |
| **total** | 606 | 2312 | 2918 |

método (aceites + variantes): {'nome_exato': 2585, 'pesquisa': 333} | desempate: {'proeminencia': 394, 'unico': 2524}

ambíguos mais frequentes: João Pedro (698), Estádio Nacional (418), Taça do Mundo (370), Liga Europeia (349), Roland Garros (294), Roger Federer (274), Paulo Pereira (223), Challenge Tour (208), Los Angeles (185), Hugo Miguel (178), Bruno Santos (170), Celta de Vigo (164)

forma_rejeitada (1243), mais frequentes: RTP1 SIC TVI (3197), Por Lusa Temas (2177), Por Record Temas (1743), O FC Porto (980), CARTÃO AMARELO (917), Grupo A (660), S A (630), Gil Vicente P (590), INÍCIO DA PARTIDA (575), Serie A (547), Grupo B (490), FC Porto V (486), AS NOTÍCIAS Sábado (400), FC Porto U (398), Boavista P (392)

item_rejeitado (498), mais frequentes: Liga NOS (3660), Taça UEFA (1178), Selecção Nacional (679), Liga Bwin (645), Di María (479), Sá Pinto (364), Paris Saint Germain (359), Taça CTT (351), Rio Maior (329), I Divisão (311), Vila Franca de Xira (292), Pedro Henriques (262), OC Barcelos (257), Jorge Sousa (246), Van Hooijdonk (239)

## 25 aceites ao acaso com ≥ 50 artigos (de 518)

| candidato | artigos | tipo | QID | rótulo Wikidata | Portugal | método | desempate |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Estádio do Dragão | 785 | estadio | Q271454 | Estádio do Dragão | sim | nome_exato | unico |
| Segunda Liga | 601 | competicao | Q754488 | Segunda Liga | sim | nome_exato | unico |
| José Couceiro | 311 | treinador | Q2422828 | José Couceiro | sim | nome_exato | unico |
| Camp Nou | 277 | estadio | Q159848 | Camp Nou | nao | nome_exato | unico |
| Novak Djokovic | 227 | jogador | Q5812 | Novak Đoković | nao | nome_exato | unico |
| Rúben Ribeiro | 138 | jogador | Q91018787 | Ruben Ribeiro | nao | pesquisa | unico |
| Jogos Paralímpicos | 132 | competicao | Q73633 | Jogos Paralímpicos | nao | nome_exato | unico |
| Kanoa Igarashi | 109 | jogador | Q27757444 | Kanoa Igarashi | nao | nome_exato | unico |
| Estádio Capital do Móvel | 108 | estadio | Q1370763 | Estádio Capital do Móvel | sim | nome_exato | unico |
| Leonardo Ruiz | 94 | jogador | Q93892105 | Leonardo Ruíz | nao | nome_exato | proeminencia |
| Kobe Bryant | 90 | jogador | Q25369 | Kobe Bryant | nao | nome_exato | unico |
| Standard Liège | 90 | clube | Q190561 | Standard de Liège | nao | nome_exato | unico |
| Hertha Berlim | 89 | clube | Q102720 | Hertha BSC | nao | nome_exato | unico |
| Inter Miami | 81 | clube | Q16844931 | Club Internacional de Fútbol Miami | nao | nome_exato | unico |
| Pavilhão Atlântico | 79 | estadio | Q1463929 | MEO Arena | sim | nome_exato | unico |
| The Athletic | 74 | estadio | Q16632730 | The Athletic Grounds | nao | pesquisa | unico |
| Octávio Machado | 68 | treinador | Q7077130 | Octávio Machado | sim | nome_exato | unico |
| David Nalbandian | 66 | jogador | Q181501 | David Nalbandian | nao | nome_exato | unico |
| Andy Roddick | 66 | jogador | Q54584 | Andy Roddick | nao | nome_exato | unico |
| Paul Pogba | 65 | jogador | Q129027 | Paul Pogba | nao | nome_exato | unico |
| Dínamo de Kiev | 62 | clube | Q179075 | Futbolniy Klub Dynamo Kyiv | nao | nome_exato | unico |
| Major League Soccer | 59 | competicao | Q18543 | Major League Soccer | nao | nome_exato | unico |
| Caroline Marks | 58 | jogador | Q52746885 | Caroline Marks | nao | nome_exato | unico |
| Maverick Viñales | 58 | jogador | Q925691 | Maverick Viñales | nao | nome_exato | unico |
| Frank Lampard | 53 | treinador | Q41533 | Frank Lampard | nao | nome_exato | proeminencia |

## 25 aceites ao acaso com 10–49 artigos (de 2362)

| candidato | artigos | tipo | QID | rótulo Wikidata | Portugal | método | desempate |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Estádio Municipal de Mafra | 44 | estadio | Q10277329 | Estádio Municipal de Mafra | sim | nome_exato | unico |
| Tommy Haas | 41 | jogador | Q53560 | Tommy Haas | nao | nome_exato | unico |
| Fed Cup | 39 | competicao | Q206984 | Fed Cup | nao | nome_exato | unico |
| Matthijs de Ligt | 24 | jogador | Q26259982 | Matthijs de Ligt | nao | nome_exato | unico |
| Copa João Havelange | 24 | competicao | Q2453542 | Copa João Havelange | nao | nome_exato | unico |
| Bernardo Manuel | 19 | jogador | Q42890123 | Bernardo Manuel | nao | nome_exato | unico |
| Al Nasr | 18 | clube | Q812723 | Al-Nasr Sports Club | nao | nome_exato | unico |
| Jorge Correa | 18 | jogador | Q5934800 | Jorge Correa | nao | nome_exato | proeminencia |
| Alexandre Nobre | 17 | jogador | Q126999155 | Alexandre Nobre | sim | nome_exato | unico |
| Rigoberto Urán | 17 | jogador | Q362185 | Rigoberto Urán | nao | nome_exato | unico |
| Vissel Kobe | 17 | clube | Q844271 | Vissel Kobe | nao | nome_exato | unico |
| Marco Materazzi | 17 | treinador | Q185081 | Marco Materazzi | nao | nome_exato | unico |
| Luís Torres | 17 | jogador | Q16573201 | Luis Torres | nao | pesquisa | proeminencia |
| Sara Ferreira | 16 | jogador | Q98074809 | Sara Ferreira | sim | nome_exato | unico |
| Lionel Scaloni | 16 | treinador | Q311586 | Lionel Scaloni | nao | nome_exato | unico |
| Mário Coluna | 15 | treinador | Q705585 | Mário Coluna | sim | nome_exato | unico |
| Rafael Gava | 15 | jogador | Q62081707 | Rafael Gustavo Meneghel Gava | nao | nome_exato | unico |
| Nou Camp | 14 | estadio | Q159848 | Camp Nou | nao | nome_exato | proeminencia |
| Raphael Silva | 14 | jogador | Q23639449 | Raphael da Silva Arruda | nao | nome_exato | unico |
| Dimitar Berbatov | 13 | jogador | Q170235 | Dimitar Berbatov | nao | nome_exato | unico |
| Jude Bellingham | 11 | jogador | Q66241169 | Jude Bellingham | nao | nome_exato | unico |
| Sébastien Bourdais | 10 | jogador | Q171307 | Sébastien Bourdais | nao | nome_exato | unico |
| Marco Marzano | 10 | treinador | Q726502 | Marco Marzano | nao | nome_exato | unico |
| Eddie Ekiyor | 10 | jogador | Q135268062 | Eddie Ekiyor | nao | nome_exato | unico |
| Greg Rusedski | 10 | jogador | Q335209 | Greg Rusedski | nao | nome_exato | unico |
