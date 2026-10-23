# Candidatos a entidade fora do vocabulário fechado (teste exploratório)

Heurística (sequências de palavras capitalizadas fora do início de frase), não NER; descarta candidatos já cobertos pelo vocabulário fechado indicado. Não avalia se os candidatos são entidades reais — isso é inspeção manual de uma amostra, fora deste script. Vocabulário: `data/processed/caminho_b_vocabulario_wikidata_alargado.csv`. Texto pesquisado: só o corpo do artigo (variante c′).

- Artigos no corpus: 129317
- Candidatos distintos fora do vocabulário: 220933

| Candidato | Artigos | Ocorrências | Exemplo de artigo |
| --- | ---: | ---: | --- |
| Comentários Destinatários | 27848 | 35080 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/carlos-brito-bruno-lage-tambem-nao-foi-promovido-para-ser-campeao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| Enviar Para | 27180 | 27180 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/carlos-brito-bruno-lage-tambem-nao-foi-promovido-para-ser-campeao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| FC Porto | 20361 | 47468 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/carlos-brito-bruno-lage-tambem-nao-foi-promovido-para-ser-campeao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| Record Premium Assine | 16984 | 16984 | https://record.pt/aposta-na-desportiva/detalhe/atalanta-juventus-visitantes-num-grande-momento?ref=fotogalerias_ultimas |
| Gil Vicente | 7575 | 14059 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/carlos-brito-bruno-lage-tambem-nao-foi-promovido-para-ser-campeao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| Enviar Enviar | 7232 | 7232 | https://record.pt/comunicados-de-imprensa/detalhe/cerveja-quinas-vai-a-europa-com-o-gil-vicente-fc?ref=hp_blococomunicadosdeimprensa |
| Lusa Temas | 6957 | 6957 | https://liga.record.pt/fora-de-campo/detalhe/coronavirus-governo-autoriza-liga-nos-taca-e-desportos-individuais-ao-ar-livre?ref=ta%c3%a7a%20de%20portugal_destaquesprincipais |
| Taça de Portugal | 5804 | 8840 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/ze-nuno-azevedo-e-o-inedito-no-famalicao-quando-iamos-jogar-contra-o-maritimo-fomos-para-a-3-divisao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| Liga dos Campeões | 4120 | 5571 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/maritimo/detalhe/20200602-0029-presidente-do-maritimo-defende-que-liga-so-recomecava-com-regulamentos-aprovados?ref=mar%c3%adtimo_destaquesprincipais |
| Record Temas | 3823 | 3823 | https://liga.record.pt/futebol/futebol-de-praia/detalhe/sporting-celebra-titulo-com-pleno-na-nazare?ref=futebol%20de%20praia_destaquesprincipais |
| Liga NOS | 3660 | 4804 | https://liga.record.pt/fora-de-campo/detalhe/coronavirus-governo-autoriza-liga-nos-taca-e-desportos-individuais-ao-ar-livre?ref=ta%c3%a7a%20de%20portugal_destaquesprincipais |
| RTP1 SIC TVI | 3197 | 4298 | https://record.pt/noticia.asp?id=100437&idcanal=123 |
| Rio Ave | 3119 | 5950 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/carlos-brito-bruno-lage-tambem-nao-foi-promovido-para-ser-campeao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| Real Madrid | 2857 | 4902 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/tiago-araujo-incredulo-com-o-fc-porto-por-isso-e-que-somos-bem-mais-superiores?ref=liga%20jovem%20da%20uefa_destaquesprincipais |
| Santa Clara | 2537 | 5252 | https://liga.record.pt/entrevistas/detalhe/rodolfo-frutuoso-assino-por-cinco-anos-pelo-sporting-logo-apos-o-primeiro-treino?ref=vilafranquense_destaquesprincipais |
| I Liga | 2290 | 3198 | https://liga.record.pt/futebol/arbitragem/detalhe/pedro-henriques-e-o-ambiente-estranho-como-sera-decidir-um-titulo-sem-barulho-na-bancada?ref=arbitragem_destaquesprincipais |
| Manchester United | 2201 | 3529 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/boavista/detalhe/bruno-fernandes-treina-no-bessa-e-agradece-ao-boavista-treinar-onde-cresci-e-sempre-melhor?ref=boavista_destaquesprincipais |
| Por Lusa Temas | 2177 | 2177 | https://liga.record.pt/futebol/futebol-de-praia/detalhe/sporting-isolado-na-frente-da-fase-final-do-futebol-de-praia-na-nazare?ref=futebol%20de%20praia_destaquesprincipais |
| Jogos Olímpicos | 1825 | 3086 | https://liga.record.pt/fazemos-campeoes/detalhe/teresa-portela-orgulho-em-dizer-faco-parte-da-evolucao?ref=hp_3blocoareasemdestaques |
| Por Record Temas | 1743 | 1743 | https://liga.record.pt/futebol/futebol-feminino/detalhe/nove-jogadoras-deixam-o-sporting?ref=hp_2bucketdestaquesprincipais |
| Estádio da Luz | 1707 | 2255 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/weigl-constatou-loucura-dos-adeptos-do-benfica-e-comecou-logo-a-ver-jogos-das-aguias?ref=nata%c3%a7%c3%a3o_2blocoareasemdestaques |
| Campeonato de Portugal | 1689 | 2703 | https://liga.record.pt/entrevistas/detalhe/rodolfo-frutuoso-e-muito-dificil-ter-lucro-em-campeonatos-secundarios?ref=vilafranquense_destaquesprincipais |
| Comentar Enviar | 1686 | 1686 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| Imprimir Classificados Alertas Rec Pesquisa Blog Facebook Digg Delicio | 1686 | 1686 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| Jorge Jesus | 1608 | 2799 | https://liga.record.pt/futebol/futebol-nacional/2--liga/leixoes/detalhe/matheus-alves-dos-sub-20-do-flamengo-e-reforco?ref=2%c2%aa%20liga_destaquesprincipais |
| Taça da Liga | 1517 | 1970 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/joao-oliveira-e-o-nono-reforco-do-academico-de-viseu?ref=ac%20viseu_bucketdestaquesprincipais |
| Estados Unidos | 1408 | 2034 | https://liga.record.pt/fora-de-campo/detalhe/eua-recomenda-aos-norte-americanos-que-nao-viagem-para-portugal-devido-a-covid-19?ref=hp_blococoloridosec%c3%a7%c3%a3odestaque |
| Seleção Nacional | 1360 | 1966 | https://liga.record.pt/futebol/futebol-nacional/2--liga/estoril/detalhe/hugo-basto-reforca-o-estoril?ref=estoril_destaquesprincipais |
| Liga Europa | 1344 | 1915 | https://liga.record.pt/futebol/detalhe/pedro-macieirinha-querem-clubes-cumpridores-ou-que-adiam-pagamentos-ad-eternum?ref=detalhe_comentadas |
| Federação Portuguesa de Futebol | 1329 | 1477 | https://liga.record.pt/futebol/arbitragem/detalhe/pedro-henriques-e-o-ambiente-estranho-como-sera-decidir-um-titulo-sem-barulho-na-bancada?ref=arbitragem_destaquesprincipais |
| Atlético Madrid | 1212 | 2178 | https://liga.record.pt/futebol/futebol-nacional/2--liga/academica/detalhe/ze-castro-renova-por-mais-uma-temporada-pela-academica?ref=acad%c3%a9mica_bucketdestaquesprincipais |
| Taça UEFA | 1178 | 1490 | https://liga.record.pt/noticia.asp?id=729414&idcanal=128 |
| Lusa Deixe | 1174 | 1174 | https://record.pt/fora-de-campo/amp/aviao-fica-sem-instrumentos-durante-o-voo-e-sobrevoa-lisboa |
| Dias Ferreira | 1170 | 1241 | https://record.pt/futebol/futebol-nacional/liga-bwin/sporting/detalhe/ricardo-oliveira-admite-candidatura-a-presidencia-do-sporting?ref=detalhe_comentadas |
| Fernando Santos | 1169 | 1840 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/espanha-portugal-selecao-lusa-no-primeiro-teste-para-a-fase-final-do-euro2020?ref=europeu_bucketdestaquesprincipais |
| Premier League | 1049 | 1450 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/boavista/detalhe/da-premier-league-para-o-bessa-angel-gomes-reforca-boavista?ref=inglaterra_bucketdestaquesprincipais |
| II Liga | 1016 | 1299 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/ac-viseu-diz-que-tad-aceitou-suspensao-da-exclusao-das-competicoes-profissionais?ref=ac%20viseu_destaquesprincipais |
| Campeonato da Europa | 991 | 1155 | https://liga.record.pt/fazemos-campeoes/detalhe/teodoro-candido-na-cadeira-esqueco-tudo?ref=hp_2blocoareasemdestaques |
| O FC Porto | 980 | 1181 | https://liga.record.pt/modalidades/basquetebol/detalhe/20210528-2012-fc-porto-sporting-em-direto?ref=basquetebol_bucketdestaquesprincipais |
| José Mourinho | 967 | 1389 | https://liga.record.pt/futebol/futebol-nacional/campeonato-de-portugal/detalhe/v-setubal-contrata-de-zlatan-ibrahimovic-com-a-ajuda-de-jose-mourinho?ref=coluna%20distrital_destaquesprincipais |
| Cova da Piedade | 942 | 2006 | https://liga.record.pt/futebol/detalhe/farense-sp-covilha-0-0-empate-em-jogo-com-pouca-emocao?ref=sp.%20covilh%c3%a3_destaquesprincipais |
| CARTÃO AMARELO | 917 | 3869 | https://record.pt/futebol/detalhe/20170723_1908_v-guimaraes-fc-porto-em-direto.html |
| Sport TV | 870 | 1210 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/moreirense/detalhe/jogo-com-gil-vicente-deve-ter-var?ref=moreirense_bucketdestaquesprincipais |
| Campeonato do Mundo | 857 | 1030 | https://liga.record.pt/fazemos-campeoes/detalhe/teodoro-candido-na-cadeira-esqueco-tudo?ref=hp_2blocoareasemdestaques |
| Manchester City | 841 | 1276 | https://liga.record.pt/futebol/futebol-nacional/2--liga/varzim/detalhe/pedro-ferreira-o-maior-desafio-foi-mesmo-vir-para-o-norte?ref=varzim_destaquesprincipais |
| Casa Pia | 831 | 1736 | https://liga.record.pt/entrevistas/detalhe/rodolfo-frutuoso-assino-por-cinco-anos-pelo-sporting-logo-apos-o-primeiro-treino?ref=vilafranquense_destaquesprincipais |
| Estádio do Dragão | 785 | 943 | https://liga.record.pt/futebol/futebol-nacional/2--liga/varzim/detalhe/rui-moreira-ninguem-queria-que-a-2-liga-acabasse?ref=varzim_destaquesprincipais |
| Vila do Conde | 719 | 868 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/aves/detalhe/mahmoud-kahraba-estreia-se-nos-convocados-do-aves?ref=detalhe_relacionadas |
| Liga de Honra | 712 | 821 | https://record.pt/futebol/detalhe/vitor-oliveira-rejeita-reencontro-especial-entre-gil-vicente-e-belenenses-sad |
| Bruno de Carvalho | 707 | 1429 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/rui-gomes-da-silva-responde-a-vieira-nunca-fui-visita-de-casa-do-presidente-do-fc-porto?ref=canoagem_2blocoareasemdestaques |
| João Pedro | 698 | 1080 | https://liga.record.pt/futebol/futebol-nacional/2--liga/detalhe/varzim-vizela-0-3-bis-de-cassiano-embala-para-triunfo?ref=varzim_destaquesprincipais |
| Selecção Nacional | 679 | 786 | https://record.pt/comunicados-de-imprensa/amp/-aquapaper-convida-a-descobrir-a-albufeira-de-castelo-do-bode-de-canoa |
| Sexta Feira | 677 | 906 | https://record.pt/noticia.aspx?id=00129317-3333-3333-3333-000000129317&idcanal=00000011-0000-0000-0000-000000000011 |
| República Checa | 668 | 972 | https://liga.record.pt/internacional/competicoes-de-clubes/liga-europa/detalhe/sorteio-da-2-pre-eliminatoria-da-liga-europa-em-direto?ref=liga%20dos%20campe%c3%b5es_destaquesprincipais |
| Grupo A | 660 | 814 | https://record.pt//aposta-na-desportiva/detalhe/sevilha-manchester-united-mourinho-tenta-adiantar-se-em-espanha.html |
| Bayern Munique | 650 | 1009 | https://liga.record.pt/internacional/paises/alemanha/bayern-munique/detalhe/nagelsmann-promete-nao-levar-os-melhores-jogadores-para-o-bayern-e-enfraquecer-o-leipzig?ref=alemanha_destaquesprincipais |
| Liga Bwin | 645 | 783 | https://liga.record.pt/noticia.asp?id=737116&idcanal=128 |
| Liga Betclic | 641 | 832 | https://record.pt/futebol/arbitragem/detalhe/apaf-avanca-com-queixa-contra-banza-apos-publicacao-nas-redes-sociais?ref=arbitragem_destaquesprincipais |
| S A | 630 | 731 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/20210526-1709-hungria?ref=europeu_destaquesprincipais |
| Jesualdo Ferreira | 618 | 776 | https://record.pt//futebol/futebol-nacional/detalhe/100-produto-nacional.html |
| Salgueiros Guimarães | 618 | 618 | https://record.pt/noticia.asp?id=100532&idcanal=113 |
| África do Sul | 605 | 795 | https://liga.record.pt/modalidades/raguebi/detalhe/campeonato-de-raguebi-da-nova-zelandia-arranca-em-13-de-junho?ref=r%c3%a2guebi_destaquesprincipais |
| Política de Privacidade Cofina | 602 | 715 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/20210526-1709-hungria?ref=europeu_destaquesprincipais |
| Segunda Liga | 601 | 727 | https://liga.record.pt/futebol/futebol-nacional/2--liga/chaves/detalhe/kevin-pina-esta-infetado-com-a-covid-19?ref=chaves_bucketdestaquesprincipais |
| Gil Vicente P | 590 | 590 | https://record.pt/futebol/futebol-nacional/liga-bwin/detalhe/benfica-arouca-abre-liga-bwin-202223-conheca-os-horarios-da-1-e-2-jornadas?ref=detalhe_ultimas |
| Bruno Lage | 585 | 1010 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/carlos-brito-bruno-lage-tambem-nao-foi-promovido-para-ser-campeao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| SIC Sport TV RTPi Jornada | 584 | 584 | https://record.pt/noticia.asp?id=100532&idcanal=113 |
| INÍCIO DA PARTIDA | 575 | 575 | https://record.pt/futebol/detalhe/20170723_1908_v-guimaraes-fc-porto-em-direto.html |
| Oliveira de Azeméis | 572 | 731 | https://liga.record.pt/futebol/futebol-nacional/2--liga/benfica-b/detalhe/nelson-verissimo-controlamos-um-jogo-que-nem-sempre-foi-jogado-com-muita-intensidade?ref=benfica%20b_destaquesprincipais |
| Quarta Feira | 556 | 773 | https://ligabppremierplus.record.pt/noticia.asp?id=318639&idcanal=128 |
| Cofina Media | 555 | 653 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/20210526-1709-hungria?ref=europeu_destaquesprincipais |
| Serie A | 547 | 717 | https://liga.record.pt/internacional/paises/italia/ac-milan/detalhe/maldini-e-a-saida-de-donnarumma-do-milan-ele-nunca-nos-desrespeitou?ref=it%c3%a1lia_destaquesprincipais |
| Paulo Calado | 546 | 546 | https://liga.record.pt/futebol/futebol-nacional/2--liga/detalhe/casa-pia-arouca-1-1-igualdade-amplia-serie-sem-vencer-dos-gansos?ref=casa%20pia_destaquesprincipais |
| AC Milan | 538 | 819 | https://liga.record.pt/internacional/competicoes-de-clubes/liga-europa/detalhe/sorteio-da-2-pre-eliminatoria-da-liga-europa-em-direto?ref=liga%20dos%20campe%c3%b5es_destaquesprincipais |
| Comité Olímpico Internacional | 537 | 688 | https://liga.record.pt/modalidades/canoagem/detalhe/coronavirus-federacao-de-canoagem-quer-adiamento-dos-jogos-toquio2020-para-outono?ref=canoagem_destaquesprincipais |
| Quinta Feira | 533 | 680 | https://ligabppremierplus.record.pt/noticia.asp?id=314613&idcanal=128 |
| José Gageiro Movephoto | 532 | 532 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/ze-gomes-se-ate-ganhassemos-o-jogo-nao-era-nada-de-outro-mundo?ref=ac%20viseu_destaquesprincipais |
| Alverca Boavista | 525 | 526 | https://record.pt/noticia.asp?id=100532&idcanal=113 |
| Arábia Saudita | 524 | 755 | https://liga.record.pt/internacional/detalhe/sporting-foi-o-emblema-portugues-que-mais-arrecadou-com-a-ida-de-jogadores-ao-mundial-2018?ref=mundial%202018_destaquesprincipais |
| Paulo Sérgio | 519 | 900 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/portimonense/detalhe/paulo-sergio-posso-ter-desequilibrado-a-equipa-com-as-alteracoes-mas-tinhamosde-arriscar?ref=moreirense_bucketdestaquesprincipais |
| Twitter Orkut Google MySpace Windows Live EXCLUSIVOS JORNAL RECORD | 518 | 518 | https://record.pt/noticia.aspx?id=0014f0b6-5e7c-4786-a84c-0fc6435b7dd5&idcanal=00000004-0000-0000-0000-000000000004 |
| Guimarães Sp | 513 | 513 | https://record.pt/noticia.asp?id=100532&idcanal=113 |
| Serginho e Duda | 513 | 513 | https://record.pt/noticia.asp?id=100532&idcanal=113 |
| Assembleia Geral | 511 | 656 | https://liga.record.pt/futebol/futebol-nacional/2--liga/estoril/detalhe/estoril-critica-tratamento-desigual-que-ditou-suspensao-da-2-liga?ref=cova%20da%20piedade_destaquesprincipais |
| Lusa EPA | 510 | 511 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/rio-ave/detalhe/miguel-cardoso-partimos-com-a-responsabilidade-de-honrar-os-pergaminhos-do-rio-ave?ref=rio%20ave_bucketdestaquesprincipais |
| Alverca Salgueiros | 510 | 510 | https://record.pt/noticia.asp?id=100516&idcanal=306 |
| Rio de Janeiro | 508 | 637 | https://record.pt//modalidades/jogos-olimpicos/rio2016/futebol/detalhe/alemanha-vence-nigeria-e-disputa-final-com-o-brasil.html |
| Desportivo de Chaves | 504 | 809 | https://liga.record.pt/futebol/futebol-de-praia/detalhe/sporting-isolado-na-frente-da-fase-final-do-futebol-de-praia-na-nazare?ref=futebol%20de%20praia_destaquesprincipais |
| Jaime Pacheco | 503 | 765 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/boavista/detalhe/xadrez-foi-rei-ha-19-anos?ref=boavista_bucketdestaquesprincipais |
| São Paulo | 498 | 657 | https://liga.record.pt/futebol/futebol-nacional/2--liga/chaves/detalhe/nicolas-reis-apresentado-como-reforco-do-chaves?ref=chaves_destaquesprincipais |
| Campeonato Nacional | 496 | 539 | https://record.pt//futebol/futebol-nacional/juniores/detalhe/fc-porto-cumpre-com-goleada.html |
| Terça Feira | 493 | 649 | https://ligabppremierplus.record.pt/noticia.asp?id=318049&idcanal=128 |
| Grupo B | 490 | 614 | https://record.pt//internacional/detalhe/argelia-bate-3-1-mauritania-gracas-a-reviravolta.html |
| FC Porto V | 486 | 509 | https://record.pt/futebol/futebol-nacional/2--liga/academica/detalhe/academica-benfica-e-sporting-belenenses-na-abertura-da-liga.html |
| Enviar Siga | 485 | 485 | https://record.pt/futebol/futebol-nacional/liga-betclic/benfica/detalhe/20240418-1847-o-onze-do-benfica-para-o-jogo-com-o-marselha?ref=detalhe_comentadas |
| Grand Slam | 483 | 658 | https://liga.record.pt/modalidades/tenis/detalhe/cabecas-de-serie-de-wimbledon-passam-a-ser-definidos-apenas-pelo-ranking?ref=wimbledon_destaquesprincipais |
| Di María | 479 | 932 | https://liga.record.pt/internacional/paises/espanha/barcelona/detalhe/koeman-reage-as-palavras-de-di-maria-sobre-messi-e-uma-falta-de-respeito?ref=fran%c3%a7a_destaquesprincipais |
| Segunda Feira | 479 | 676 | https://record.pt/noticia.asp?id=761846&idcanal=11 |
| Getty Images | 478 | 478 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/fc-porto/detalhe/fc-porto-deixa-bicada-ao-benfica-apos-derrota-na-youth-league?ref=liga%20jovem%20da%20uefa_destaquesprincipais |
| Coreia do Sul | 476 | 713 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/v--guimaraes/detalhe/de-regresso-para-preparar-sporting?ref=v.%20guimar%c3%a3es_destaquesprincipais |
| Santa Maria da Feira | 473 | 565 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/ze-gomes-se-ate-ganhassemos-o-jogo-nao-era-nada-de-outro-mundo?ref=ac%20viseu_destaquesprincipais |
| Luís Castro | 464 | 845 | https://record.pt//futebol/futebol-nacional/2--liga/fc-porto-b/detalhe/luis-castro-apontado-para-orientar-o-troyes.html |
| Lusa PUB | 462 | 462 | https://record.pt/fora-de-campo/amp/20200131-1751-adiada-para-28-de-fevereiro-leitura-do-acordao-do-processo-jogo-duplo |
| Luís Manuel Neves | 451 | 452 | https://liga.record.pt/futebol/futebol-nacional/2--liga/academica/detalhe/mika-renova-com-a-academica?ref=ac%20viseu_destaquesprincipais |
| Pub Deixe | 441 | 441 | https://liga.record.pt/multimedia/fotogalerias/detalhe/treino-conjunto-do-fc-porto-com-a-equipa-b-ate-teve-direito-a-equipamentos-oficiais?ref=fc%20porto_1bucketdestaqueprincipal |
| Atlético de Madrid | 440 | 597 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/espanha-portugal-selecao-lusa-no-primeiro-teste-para-a-fase-final-do-euro2020?ref=europeu_bucketdestaquesprincipais |
| AF Porto | 432 | 521 | https://liga.record.pt/futebol-ao-vivo/detalhe/transmissao-em-direto-do-vila-fc-infesta-af-porto?ref=coluna%20distrital_bucketdestaquesprincipais |
| Estádio Nacional | 418 | 585 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/belenenses-sad/detalhe/coronavirus-belenenses-sad-com-testes-negativos-e-futebolista-recuperado?ref=belenenses%20sad_destaquesprincipais |
| Record Premium Assine Já Se | 415 | 415 | https://liga.record.pt/multimedia/fotogalerias/detalhe/as-camisolas-das-24-selecoes-que-jogarao-o-euro2020?ref=alemanha_blocofotos |
| Direção Geral da Saúde | 414 | 456 | https://liga.record.pt/fora-de-campo/detalhe/eua-recomenda-aos-norte-americanos-que-nao-viagem-para-portugal-devido-a-covid-19?ref=hp_blococoloridosec%c3%a7%c3%a3odestaque |
| Liga Portuguesa de Futebol Profissional | 400 | 459 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/antonio-albino-garante-o-ac-viseu-tem-a-sua-verdade-e-vai-apresenta-la-na-justica?ref=ac%20viseu_bucketdestaquesprincipais |
| AS NOTÍCIAS Sábado | 400 | 400 | https://record.pt/noticia.aspx?id=00088668-3333-3333-3333-000000088668&idcanal=00000004-0000-0000-0000-000000000004 |
| FC Porto U | 398 | 398 | https://record.pt/futebol/futebol-nacional/liga-nos/detalhe/liga-nos-resultados-e-marcadores.html |
| Liga Portugal | 395 | 569 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/antonio-albino-garante-o-ac-viseu-tem-a-sua-verdade-e-vai-apresenta-la-na-justica?ref=ac%20viseu_bucketdestaquesprincipais |
| Boavista P | 392 | 394 | https://record.pt/modalidades/voleibol/detalhe/20180429_1354_benfica-sporting-em-direto.html |
| Boavista Setúbal | 390 | 770 | https://record.pt/noticia.asp?id=157357&idcanal=23 |
| Braga Alverca | 390 | 770 | https://record.pt/noticia.asp?id=157357&idcanal=23 |
| Guimarães Leiria | 390 | 770 | https://record.pt/noticia.asp?id=157357&idcanal=23 |
| Estádio José Alvalade | 388 | 456 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/detalhe/estadio-do-pacos-de-ferreira-junta-se-a-lista-de-recintos-aprovados-para-ter-jogos-da-liga-nos?ref=p.%20ferreira_destaquesprincipais |
| Pedro Proença | 387 | 630 | https://liga.record.pt/futebol/futebol-nacional/2--liga/chaves/detalhe/cesar-peixoto-e-o-fim-da-2-liga-e-uma-decisao-ridicula?ref=chaves_bucketdestaquesprincipais |
| Ao Minuto | 385 | 385 | https://record.pt/especial/detalhe/eleicoes-europeias-em-direto-extrema-direita-vence-em-franca-e-macron-anuncia-legislativas-antecipadas?ref=detalhe_destaquestopo |
| RTP1 Campeonato | 385 | 385 | https://record.pt/noticia.asp?id=100516&idcanal=306 |
| Allianz Cup | 383 | 563 | https://liga.record.pt/futebol/futebol-nacional/2--liga/academica/detalhe/mika-renova-com-a-academica?ref=ac%20viseu_destaquesprincipais |
| FINAL DA PARTIDA | 377 | 377 | https://record.pt/futebol/detalhe/20170723_1908_v-guimaraes-fc-porto-em-direto.html |
| Estádio D | 376 | 440 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/detalhe/estadio-do-pacos-de-ferreira-junta-se-a-lista-de-recintos-aprovados-para-ter-jogos-da-liga-nos?ref=p.%20ferreira_destaquesprincipais |
| Frederico Varandas | 375 | 613 | https://liga.record.pt/futebol/futebol-feminino/detalhe/nove-jogadoras-deixam-o-sporting?ref=hp_2bucketdestaquesprincipais |
| Ponta Delgada | 374 | 485 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/detalhe/regulamentos-foram-cumpridos-no-adiamento-do-santa-clara-pacos-de-ferreira?ref=p.%20ferreira_destaquesprincipais |
| Estádio do Bessa | 374 | 418 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/boavista/detalhe/xadrez-foi-rei-ha-19-anos?ref=boavista_bucketdestaquesprincipais |
| Taça do Mundo | 370 | 611 | https://liga.record.pt/fazemos-campeoes/detalhe/teresa-portela-orgulho-em-dizer-faco-parte-da-evolucao?ref=hp_3blocoareasemdestaques |
| Boavista U | 370 | 370 | https://record.pt/futebol/futebol-nacional/liga-nos/detalhe/liga-nos-resultados-e-marcadores.html |
| Vítor Chi | 368 | 369 | https://liga.record.pt/futebol/futebol-nacional/2--liga/detalhe/final-quente-no-benfica-b-fc-porto-b-com-rodrigo-conceicao-e-samuel-pedro-no-olho-do-furacao?ref=benfica%20b_destaquesprincipais |
| Ministério Público | 367 | 508 | https://record.pt//futebol/futebol-nacional/2--liga/detalhe/mafra-defende-impugnacao-do-campeonato.html |
| AF Lisboa | 366 | 406 | https://liga.record.pt/futebol-ao-vivo/detalhe/transmissao-em-direto-do-belenenses-ac-malveira-af-lisboa?ref=coluna%20distrital_destaquesprincipais |
| Sá Pinto | 364 | 659 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/moreirense/detalhe/sp-braga-empresta-luther-singh-ao-moreirense?ref=moreirense_bucketdestaquesprincipais |
| Salgueiros Sp | 361 | 361 | https://record.pt/noticia.asp?id=100437&idcanal=123 |
| Paris Saint Germain | 359 | 422 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/artur-soares-dias-a-caminho-da-sexta-fase-final?ref=europeu_destaquesprincipais |
| Agência Lusa | 359 | 370 | https://liga.record.pt/modalidades/motores/motociclismo/detalhe/miguel-oliveira-recorda-sonho-de-crianca-cumprido-ao-ouvir-o-hino?ref=motores_destaquesprincipais |
| Paços Ferreira Sp | 359 | 359 | https://record.pt/noticia.asp?id=100437&idcanal=123 |
| Santa Clara RTP1 SIC TVI | 359 | 359 | https://record.pt/noticia.asp?id=100437&idcanal=123 |
| Sta Clara V | 359 | 359 | https://record.pt/noticia.asp?id=100437&idcanal=123 |
| Borussia Dortmund | 353 | 481 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/vlachodimos-diz-que-paragem-por-causa-do-coronavirus-pode-beneficiar-weigl?ref=judo_2blocoareasemdestaques |
| Taça CTT | 351 | 457 | https://record.pt//aposta-na-desportiva/detalhe/benfica-sporting-quem-saira-a-rir-do-derbi.html |
| Armando Alves Temas | 351 | 351 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/portimonense/detalhe/portimonense-solidario-com-cova-da-piedade-e-casa-pia?ref=cova%20da%20piedade_destaquesprincipais |
| Fernando Gomes | 350 | 553 | https://liga.record.pt/futebol/futebol-nacional/2--liga/chaves/detalhe/francisco-jose-carvalho-o-melhor-e-fazer-um-campeonato-so-com-os-tres-grandes?ref=chaves_bucketdestaquesprincipais |
| Liga Europeia | 349 | 637 | https://liga.record.pt/modalidades/andebol/detalhe/belenenses-esta-de-regresso-a-europa?ref=belenenses%20sad_bucketdestaquesprincipais |
| Liga Sabseg | 348 | 472 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/camara-de-viseu-autoriza-ac-viseu-a-receber-varzim-ainda-no-fontelo?ref=ac%20viseu_destaquesprincipais |
| Vila das Aves | 347 | 408 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/aves/detalhe/aves-ameaca-com-impugnacao-do-campeonato-se-nao-jogar-em-casa?ref=aves_bucketdestaquesprincipais |
| Figueira da Foz | 344 | 441 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/famalicao/detalhe/joao-pedro-sousa-e-o-novo-treinador-do-famalicao?ref=detalhe_vistas |
| Viana do Castelo | 337 | 416 | https://record.pt/especial/detalhe/eleicoes-legislativas-em-direto-siga-aqui-todas-as-reacoes-e-desenvolvimentos?ref=detalhe_blocoultimasarea |
| LIGA SAGRES FC Porto | 337 | 337 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| MAIOR VANTAGEM PONTUAL SOBRE RIVAIS | 337 | 337 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| Instagram Uma | 336 | 404 | https://liga.record.pt/internacional/paises/espanha/granada/detalhe/rui-silva-diz-adeus-ao-granada-um-dos-dias-mais-tristes-da-minha-vida?ref=espanha_bucketdestaquesprincipais |
| Boavista S | 335 | 335 | https://record.pt/noticia.asp?id=127955&idcanal=19 |
| Vila Real | 333 | 449 | https://liga.record.pt/noticia.asp?id=686445&amp;idcanal=128 |
| FC Porto Alverca | 333 | 333 | https://record.pt/noticia.asp?id=127955&idcanal=19 |
| Comité Olímpico de Portugal | 332 | 379 | https://liga.record.pt/iniciativas/detalhe/talks-santaderrecord-proenca-scolari-e-muitos-mais-debatem-futuro-do-futebol?ref=iniciativas_destaquesprincipais |
| Rio Maior | 329 | 458 | https://liga.record.pt/futebol/futebol-nacional/2--liga/detalhe/vilafranquense-varzim-1-3-poveiros-com-triunfo-importante-rumo-a-salvacao?ref=vilafranquense_destaquesprincipais |
| Momentos Chave | 329 | 329 | https://liga.record.pt/mercado/detalhe/20210601-0905-mercado-ja-mexe-todos-os-rumores-e-confirmacoes?ref=euro%202020_vistas |
| Inter Milão | 327 | 421 | https://liga.record.pt/internacional/paises/italia/ac-milan/detalhe/maldini-e-a-saida-de-donnarumma-do-milan-ele-nunca-nos-desrespeitou?ref=it%c3%a1lia_destaquesprincipais |
| Grupo D | 323 | 410 | https://record.pt//futebol/selecao-feminina/detalhe/portugal-estreia-se-com-a-espanha-no-europeu.html |
| Manuel Vilarinho | 316 | 488 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/benfica/detalhe/rui-gomes-da-silva-responde-a-vieira-nunca-fui-visita-de-casa-do-presidente-do-fc-porto?ref=canoagem_2blocoareasemdestaques |
| PUB O | 314 | 316 | https://record.pt/fazemos-campeoes/amp/decisoes-voltam-em-grande-a-portugal |
| Conselho de Disciplina | 313 | 413 | https://liga.record.pt/futebol/futebol-nacional/2--liga/ac-viseu/detalhe/ac-viseu-diz-que-tad-aceitou-suspensao-da-exclusao-das-competicoes-profissionais?ref=ac%20viseu_destaquesprincipais |
| Estádio do Bonfim | 313 | 398 | https://liga.record.pt/futebol/futebol-nacional/campeonato-de-portugal/v--setubal/detalhe/camara-de-setubal-adquiriu-direito-de-superficie-sobre-terrenos-do-estadio-do-bonfim?ref=hp_blococoloridosec%c3%a7%c3%a3odestaque |
| José Couceiro | 311 | 429 | https://record.pt//futebol/futebol-nacional/liga-nos/v--setubal/detalhe/arnold-bisa-no-triunfo-sobre-o-sporting-b.html |
| I Divisão | 311 | 395 | https://liga.record.pt/entrevistas/conversas-de-sofa/detalhe/ze-nuno-azevedo-e-o-inedito-no-famalicao-quando-iamos-jogar-contra-o-maritimo-fomos-para-a-3-divisao?ref=conversas%20de%20sof%c3%a1_destaquesprincipais |
| Liga Record | 307 | 485 | https://liga.record.pt/noticia.asp?id=574942&amp |
| West Ham | 307 | 444 | https://record.pt//aposta-na-desportiva/detalhe/tottenham-west-ham-acerto-de-calendario-na-premier-league.html |
| Open da Austrália | 306 | 442 | https://liga.record.pt/modalidades/tenis/detalhe/roland-garros-adiado-devido-ao-coronavirus?ref=roland%20garros_destaquesprincipais |
| Grupo C | 306 | 375 | https://record.pt//aposta-na-desportiva/detalhe/v-setubal-oliveirense-reencontro-72-anos-depois.html |
| Old Trafford | 305 | 370 | https://record.pt//futebol/futebol-nacional/liga-nos/detalhe/20170107_1633_v-guimaraes-benfica-em-direto.html |
| Vale e Azevedo | 304 | 594 | https://record.pt//futebol/futebol-nacional/liga-nos/detalhe/20170423_1703_v-guimaraes-boavista-em-direto.html |
| Nova Zelândia | 304 | 406 | https://liga.record.pt/modalidades/basquetebol/detalhe/coronavirus-pre-olimpico-de-basquetebol-com-novas-datas-e-sedes-definidas?ref=jogos%20ol%c3%admpicos_bucketdestaquesprincipais |
| Pedro Morais Temas | 304 | 304 | https://liga.record.pt/futebol/futebol-nacional/2--liga/feirense/detalhe/elves-balde-e-bruno-ramires-ja-treinam-no-feirense?ref=feirense_destaquesprincipais |
| Alexandre Reis Temas | 302 | 302 | https://liga.record.pt/modalidades/andebol/detalhe/benfica-vence-vitoria-de-setubal-e-mantem-esperanca?ref=andebol_bucketdestaquesprincipais |
| Estádio do Mar | 301 | 375 | https://liga.record.pt/futebol/futebol-nacional/2--liga/leixoes/detalhe/estadio-do-mar-alvo-de-atos-de-vandalismo?ref=leix%c3%b5es_destaquesprincipais |
| Luís Figo | 300 | 369 | https://record.pt//futebol/futebol-nacional/portugal-prio/detalhe/paulo-china-e-ricardo-entre-os-investidores-para-formar-sad-no-almancilense.html |
| Roger Schmidt | 298 | 463 | https://record.pt/fora-de-campo/detalhe/record-na-hora-de-hoje-o-ouro-de-portugal-nos-jogos-olimpicos-analise-a-vitoria-do-sporting-e-a-conferencia-de-schmidt?ref=detalhe_blocoultimasarea |
| Roland Garros | 294 | 425 | https://liga.record.pt/modalidades/tenis/detalhe/campeao-de-roland-garros-troca-tenis-por-trabalho-em-supermercado-e-salario-de-450-euros?ref=roland%20garros_destaquesprincipais |
| Manuel Cajuda | 293 | 406 | https://record.pt//futebol/futebol-nacional/2--liga/ac-viseu/detalhe/manuel-cajuda-ja-foi-apresentado.html |
| Vila Franca de Xira | 292 | 351 | https://liga.record.pt/entrevistas/detalhe/rodolfo-frutuoso-assino-por-cinco-anos-pelo-sporting-logo-apos-o-primeiro-treino?ref=vilafranquense_destaquesprincipais |
| Twitter Orkut Google MySpace Windows Live EXCLUSIVOS JORNAL RECORD Tetra | 292 | 292 | https://record.pt/noticia.aspx?id=00805057-3333-3333-3333-000000805057&idcanal=00003445-0000-0000-0000-000000003445 |
| MINUTO A MINUTO | 290 | 476 | https://record.pt/futebol/futebol-nacional/2--liga/academica/detalhe/academica-naval-3-1-eder-62-sougou-64-saleiro-70-paulao-26 |
| TAÇA DA LIGA Grandes | 289 | 289 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| João Henriques | 288 | 503 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/santa-clara/detalhe/20200818-1257-santa-clara-contrata-trinco-brasileiro-julio-romao?ref=santa%20clara_destaquesprincipais |
| Salgueiros P | 288 | 288 | https://record.pt/noticia.asp?id=101807&idcanal=15 |
| Youth League | 286 | 521 | https://liga.record.pt/futebol/futebol-nacional/2--liga/varzim/detalhe/pedro-ferreira-o-maior-desafio-foi-mesmo-vir-para-o-norte?ref=varzim_destaquesprincipais |
| Taça das Nações Africanas | 284 | 308 | https://liga.record.pt/internacional/competicoes-de-selecoes/can/detalhe/angola-empata-com-a-rd-congo-na-corrida-a-can2022?ref=angola_destaquesprincipais |
| Vila Nova de Gaia | 284 | 300 | https://liga.record.pt/futebol/futebol-nacional/2--liga/detalhe/fc-porto-b-academica-1-3-briosa-chega-a-quarta-vitoria-seguida?ref=fc%20porto%20b_destaquesprincipais |
| Peter Spark Movephoto | 283 | 283 | https://liga.record.pt/futebol/futebol-nacional/2--liga/chaves/detalhe/cesar-peixoto-e-o-fim-da-2-liga-e-uma-decisao-ridicula?ref=chaves_bucketdestaquesprincipais |
| TERCEIRA FASE JOGA SE JÁ EM JANEIRO Terça Feira | 283 | 283 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| Bruno Paixão | 282 | 452 | https://liga.record.pt/multimedia/podcast-record/detalhe/bruno-paixao-aquilo-descambou-e-tiveram-de-chamar-um-padre?ref=podcast%20record_1bucketdestaqueprincipal |
| Jogos Olímpicos de Tóquio | 282 | 327 | https://liga.record.pt/modalidades/basquetebol/detalhe/coronavirus-pre-olimpico-de-basquetebol-com-novas-datas-e-sedes-definidas?ref=jogos%20ol%c3%admpicos_bucketdestaquesprincipais |
| JORNADAS Quinta Feira | 281 | 281 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| Jogos Olímpicos Tóquio | 280 | 323 | https://liga.record.pt/internacional/competicoes-de-selecoes/europeu/euro-2020/detalhe/artur-soares-dias-a-caminho-da-sexta-fase-final?ref=europeu_destaquesprincipais |
| ENCARNADOS SOMAM | 280 | 280 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| GOLOS EM | 280 | 280 | https://record.pt/noticia.aspx?id=00064304-3333-3333-3333-000000064304&idcanal=00000011-0000-0000-0000-000000000011 |
| Vítor Campelos | 277 | 430 | https://liga.record.pt/futebol/futebol-nacional/2--liga/detalhe/estoril-falha-festa-antecipada-do-titulo-com-empate-contra-o-chaves?ref=estoril_destaquesprincipais |
| Camp Nou | 277 | 345 | https://liga.record.pt/multimedia/fotogalerias/detalhe/treino-conjunto-do-fc-porto-com-a-equipa-b-ate-teve-direito-a-equipamentos-oficiais?ref=fc%20porto_1bucketdestaqueprincipal |
| Liga de Clubes | 277 | 318 | https://liga.record.pt/futebol/futebol-nacional/liga-nos/moreirense/detalhe/estadio-do-moreirense-tambem-ja-esta-aprovado-para-receber-jogos-da-liga?ref=moreirense_destaquesprincipais |

Tabela limitada aos 200 primeiros; todos em `output/corpus_candidate_entities_por_ano.csv`. Lista descritiva desta amostra, não uma avaliação de precisão nem uma proposta de pipeline.
