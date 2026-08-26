# Profiling da API TextSearch

Parâmetros comuns: `siteSearch=record.pt`, `maxItems=100`, `dedupField=url`, `dedupValue=1`. O cliente existente inclui também o host `www.record.pt`.

| Query | Período | Estimated | Recebidos | URLs distintas | /detalhe/ | Não /detalhe/ | Mais antiga | Mais recente |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Benfica | 2010–2020 | 6704201 | 30 | 30 | 20 | 10 | 20091218155003 | 20191120042156 |
| Benfica | 2015–2020 | 6697559 | 30 | 30 | 20 | 10 | 20170108035418 | 20191120042156 |
| Benfica | 2018–2020 | 4197109 | 22 | 22 | 16 | 6 | 20171216204205 | 20191120042156 |
| Benfica | 2018–2022 | 4226546 | 27 | 27 | 20 | 7 | 20171216204205 | 20201008064401 |
| Sporting | 2015–2020 | 6721102 | 33 | 33 | 26 | 7 | 20170107065550 | 20191120063616 |
| FC Porto | 2015–2020 | 6213394 | 24 | 24 | 20 | 4 | 20170228215026 | 20190711195747 |

## Destaques

- Mais URLs distintas: **Sporting (2015–2020)**, com **33**.
- Mais URLs com `/detalhe/`: **Sporting (2015–2020)**, com **26**.

`/detalhe/` é apenas um indicador exploratório, não uma classificação definitiva de Artigo.

## Anomalias observadas

- Benfica (2010–2020): a captura mais antiga (20091218155003) é anterior ao ano inicial pedido.
- Benfica (2010–2020): estimated_nr_results=6704201, mas foram devolvidos 30 itens e não existe next_page.
- Benfica (2015–2020): estimated_nr_results=6697559, mas foram devolvidos 30 itens e não existe next_page.
- Benfica (2018–2020): a captura mais antiga (20171216204205) é anterior ao ano inicial pedido.
- Benfica (2018–2020): estimated_nr_results=4197109, mas foram devolvidos 22 itens e não existe next_page.
- Benfica (2018–2022): a captura mais antiga (20171216204205) é anterior ao ano inicial pedido.
- Benfica (2018–2022): estimated_nr_results=4226546, mas foram devolvidos 27 itens e não existe next_page.
- Sporting (2015–2020): estimated_nr_results=6721102, mas foram devolvidos 33 itens e não existe next_page.
- FC Porto (2015–2020): estimated_nr_results=6213394, mas foram devolvidos 24 itens e não existe next_page.
