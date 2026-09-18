# Classificação Artigo vs. redirecionamento/não-artigo (passo 6)

Regra e justificação em `docs/experiments.md`. Execução real sobre os dados já recolhidos nas Fases 1–2, sem pedidos novos à API.

## Resumo

- Recursos distintos (depois de normalizar esquema http/https): 158
- Classificados como Artigo: 127
- Excluídos — `/sabermais/`: 12
- Excluídos — `Object moved`: 13
- Excluídos — capturas > 100: 6

## Excluídos — /sabermais/

| originalURL | title | capturas |
| --- | --- | ---: |
| https://www.record.pt/sabermais/ano-zero | Saber Mais: Ano Zero | 1 |
| https://www.record.pt/sabermais/bruno-fernandes | Saber Mais: Bruno Fernandes | 143 |
| https://www.record.pt/sabermais/cristiano-ronaldo | Saber Mais: Cristiano Ronaldo | 306 |
| https://www.record.pt/sabermais/futebol | Saber Mais: Futebol | 1282 |
| https://www.record.pt/sabermais/jo%C3%A3o-f%C3%A9lix | Saber Mais: João Félix | 119 |
| https://www.record.pt/sabermais/nelson-%C3%A9vora | Saber Mais: Nelson Évora | 5 |
| https://www.record.pt/sabermais/porto | Saber Mais: Porto | 118 |
| https://www.record.pt/sabermais/sporting | Saber Mais: Sporting | 1084 |
| https://www.record.pt/sabermais/telma-monteiro | Saber Mais: Telma Monteiro | 13 |
| https://www.record.pt/sabermais/yebda | YEBDA - Saber Mais - Record | 3 |
| https://www.record.pt/sabermais/ze-pedro | ze pedro - Saber Mais - Record | 1 |
| https://www.record.pt/sabermais/zurique | Saber Mais: Zurique | 12 |

## Excluídos — Object moved

| originalURL | capturas |
| --- | ---: |
| http://www.record.pt/Futebol/Internacional/interior.aspx?content_id/x3d730429 | 4 |
| http://www.record.pt/Futebol/Internacional/interior.aspx?content_id/x3d757134 | 4 |
| http://www.record.pt/Futebol/Internacional/interior.aspx?content_id/x3d817327 | 4 |
| http://www.record.pt/Futebol/Internacional/real_madrid/interior.aspx?content_id/x3d769710 | 4 |
| http://www.record.pt/Futebol/Nacional/1a_liga/Benfica/interior.aspx?content_id/x3d750833 | 4 |
| http://www.record.pt/Futebol/Nacional/1a_liga/Benfica/interior.aspx?content_id/x3d930690 | 3 |
| http://www.record.pt/Futebol/Nacional/1a_liga/Porto/interior.aspx?content_id/x3d729433 | 4 |
| http://www.record.pt/Futebol/Nacional/1a_liga/Sporting/interior.aspx?content_id/x3d688186 | 4 |
| http://www.record.pt/Futebol/Nacional/1a_liga/Sporting/interior.aspx?content_id/x3d808398 | 1 |
| http://www.record.pt/Futebol/Nacional/1a_liga/Sporting/interior.aspx?content_id/x3d906264 | 4 |
| http://www.record.pt/Futebol/Nacional/Futsal/interior.aspx?content_id/x3d479491 | 3 |
| http://www.record.pt/Futebol/Nacional/interior.aspx?content_id/x3d901269 | 3 |
| http://www.record.pt/Modalidades/Basquetebol/NBA/interior.aspx?content_id/x3d788683 | 4 |

## Excluídos — capturas acima do limiar

| originalURL | title | capturas |
| --- | --- | ---: |
| https://www.record.pt/futebol/futebol-nacional/liga-nos/benfica | Benfica - Jornal Record | 916 |
| https://www.record.pt/modalidades/basquetebol?ref=Masterpage_Menu | Basquetebol - Jornal Record | 829 |
| https://www.record.pt/resultados-e-classificacoes/modalidades/voleibol/resultados | Voleibol - Jornal Record | 822 |
| http://www.record.pt/multimedia/fotogalerias/detalhe/esta-falta-tirou-zeegelaar-do-derbi-com-o-benfica.html | Esta falta tirou Zeegelaar do dérbi com o Benfica - Fotogalerias - Jornal Record | 472 |
| https://www.record.pt/multimedia/videos/detalhe/yuri-ribeiro-apresenta-se-aos-adeptos-do-rio-ave.html | Yuri Ribeiro apresenta-se aos adeptos do Rio Ave - Vídeos - Jornal Record | 162 |
| http://www.record.pt/multimedia/videos/detalhe/zainadine-cortou-mal-a-bola-e-otavio-abriu-o-marcador.html | Zainadine cortou mal a bola e Otávio abriu o marcador - Vídeos - Jornal Record | 135 |

Lista completa (incluindo os classificados como Artigo) em `output/corpus_classification.csv`.
