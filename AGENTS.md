# Semantic Driven Harvester — guia para agentes

Instruções canónicas do projeto, independentes da ferramenta de IA utilizada.
Protótipo de uma dissertação de Mestrado para recolher metadados e textos do
Arquivo.pt e representar recursos Web e capturas temporais em RDF.

## Antes de trabalhar

1. Inspecionar `git status --short`, `git log -5 --oneline` e o diff existente.
2. Ler [README.md](README.md) e [estado do projeto](docs/PROJECT_STATUS.md).
3. Para dados/experiências, ler [observações](docs/observations.md) e
   [experiências e decisões](docs/experiments.md).
4. Para testes, ler [política das fixtures](tests/fixtures/README.md).
5. Ler o código e testes afetados; para RDF, também a ontologia abaixo.

Não afirmar comportamento, resultados ou decisões sem verificar as fontes.

## Mapa e arquitetura atual

- `src/semantic_harvester/arquivo_client.py`: HTTP, TextSearch, versionHistory
  e preservação dos bytes de JSON/texto.
- `history_pipeline.py`: paginação, textos, manifesto JSONL e métricas.
- `rdf_mapper.py`: IDs determinísticos, grafos de sample/histórico e Turtle.
- `smoke_test.py`, `api_profiling.py`, `api_diagnostics.py`,
  `api_diagnostics_offset.py`: execuções reais manuais; estes módulos também
  estão em `src/semantic_harvester/`.
- [ontology/semantic_harvester.ttl](ontology/semantic_harvester.ttl): vocabulário.
- `tests/`: suite offline, transporte simulado e fixtures sintéticas.
- `data/raw/`: artefactos locais ignorados pelo Git, salvo `.gitkeep`.
- `data/processed/`: manifesto; `output/`: RDF e relatórios, alguns versionados.
- `docs/`: estado, observações e decisões; não duplicar resultados dos relatórios.

Fluxo: API → bytes raw → registos/manifesto → RDF; profiling e diagnóstico
produzem relatórios separados. Não existe serviço Web nem base de dados.

## Ambiente e comandos

Python >=3.11; dependências em `pyproject.toml`: RDFLib >=7.6,<8 e
requests >=2.31,<3; empacotamento setuptools com layout `src/`.
Na raiz, criar `.venv` com `python -m venv .venv` (`python3` em sistemas que
assim designam o Python). Ativar com `.venv\Scripts\Activate.ps1` no PowerShell
ou `source .venv/bin/activate` em shells POSIX. Depois:

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

No Windows também é possível usar `.venv\Scripts\python.exe` sem ativar.
Comandos de execução, apenas quando a tarefa pedir essa operação:

| Comando | Pré-requisitos / efeito |
| --- | --- |
| `python -m semantic_harvester.smoke_test` | Rede; pesquisa e grava raw/textos. |
| `python -m semantic_harvester.rdf_mapper` | Raw M1 e texto da captura selecionada; grava Turtle. |
| `python -m semantic_harvester.history_pipeline` | Rede; recolhe histórico; a geração RDF final também exige o JSON M1 selecionado. |
| `python -m semantic_harvester.api_profiling` | Rede; grava raw e relatórios. |
| `python -m semantic_harvester.api_diagnostics` | Rede; grava raw e relatórios. |
| `python -m semantic_harvester.api_diagnostics_offset` | Rede; grava raw e relatórios. |

Os detalhes e parâmetros estão no README e nos módulos. Estes comandos reais
não são pré-requisitos da suite unitária nem devem ser executados para a reparar.

## Regras de trabalho e dados

- Preferir alterações pequenas, justificadas e testáveis; preservar comportamento
  já testado. Não fazer refactors nem acrescentar funcionalidades fora do pedido.
- Distinguir implementação observada, hipótese, resultado histórico e proposta.
  Não inventar resultados científicos, medições, arquitetura ou decisões.
- Não editar, fabricar ou substituir raw para fazer testes passar. Preservar
  os bytes originais e a proveniência; fixtures são sintéticas e ficam em `tests/fixtures/`.
- Raw não acompanha um clone. Relatórios e caminhos no manifesto não provam
  que os ficheiros referenciados existem localmente; verificar antes de os usar.
- Não repetir recolhas live sem isso fazer parte do pedido. Novas execuções
  podem sobrescrever artefactos: preservar a evidência anterior antes de repetir.
- Não generalizar conclusões de uma amostra para toda a API. Consultar as
  decisões de `docs/experiments.md` sobre estimativas, offsets e deduplicação.
- Registar decisões importantes com motivo e evidência na documentação existente:
  método em `docs/experiments.md`, observações em `docs/observations.md`,
  estado/limitações em `docs/PROJECT_STATUS.md`; evitar fontes paralelas.

## Ontologia e RDF

- Distinguir `Artigo`, `RecursoWeb`, `CapturaArquivada` e `TextoExtraido`.
  Uma página devolvida pela pesquisa não é automaticamente um artigo.
- Preservar IDs com SHA-256 do URL e `tstamp` nas URIs de captura/texto;
  capturas do mesmo URL partilham `article_id`. Digest não prova equivalência semântica.
- Explicar alterações de classes, propriedades, datatypes, relações ou IDs e
  o impacto em dados/consumidores antes de as implementar como mudanças triviais.
- Manter ontologia, mapper e testes coerentes; verificar relações, ficheiros
  referenciados e releitura do Turtle. Não corrigir outputs históricos à mão.

## Testes, Git e conclusão

- Testes automatizados usam fixtures determinísticas e diretórios temporários;
  sem rede, `data/raw/`, outputs históricos ou pipeline prévia. Usar o suporte offline existente.
- Manter assertions relevantes; acrescentar testes proporcionais às mudanças.
  Integrações reais devem ser opcionais e separadas da descoberta unitária.
- Correr a suite relevante após alterações e a suite completa acima antes de concluir.
  Informar comando, contagem, resultado e limitações; não declarar sucesso sem execução.
- Preservar alterações alheias; não adicionar raw, `.venv/` ou segredos ao Git.
  Não fazer commit, push ou reescrever histórico sem pedido explícito.
- Concluir quando o âmbito pedido estiver resolvido, testes passarem, documentação
  estiver coerente e `git diff --check` estiver limpo. Rever o diff e apresentar
  ficheiros alterados, motivo e `git diff --stat`; explicar bloqueios se existirem.
