# Evidências de desenvolvimento

Inspeção inicial em 24/10/2026: nenhuma implementação de backend existente.
T00 já preparado; README modificado e `.gitignore`, docs, scripts, PDF e files não
rastreados antes deste trabalho. Nenhum AGENTS.md aplicável encontrado.
Os quatro hashes dos insumos conferem com a auditoria original.

Cada `Tnn-red.txt` registra a falha anterior à implementação; `Tnn-green.txt/xml`
registra a regressão acumulada. Comando padrão: `uv run --directory backend python
check.py Tnn green`. Logs iniciais anteriores ao runner são descritos abaixo.
Em T01, as quatro falhas iniciais foram observadas no terminal antes da criação
do runner; não existe arquivo `T01-red.txt`. A partir de T02, os registros red/green
foram persistidos em arquivos. Falhas iniciais não foram recriadas artificialmente
após a implementação.

| Tarefa | Implementação | Validação | Aceitação |
|---|---|---|---|
| T01 | Concluída | 4 testes passando, PostgreSQL 16.15 Docker; lint/tipos/contrato válidos | Não depende de gabarito |
| T02 | Concluída | Documentos textuais, identidade e calendário | Sintética validada |
| T03 | Concluída | Configurações imutáveis e parâmetros dos nove validadores | Sintética validada |
| T04 | Concluída | Regras individuais, limites, ausências e toggles | Sintética validada |
| T05 | Concluída | PL completo, raízes, saldo anterior e centavos | Sintética validada |
| T06 | Concluída | Decimal 38 e HALF_UP; strings HTTP | Sintética validada |
| T07 | Concluída | Ordem, duplicidade e efeitos exclusivos de aprovação | Sintética validada |
| T08 | Concluída | Migrações, FKs, unicidade e rollback em PostgreSQL | Validada |
| T09 | Concluída | 3.041 cadastros, reimportação, corrida e versões congeladas | Validada; só ANTECIPE configurado |
| T10 | Concluída | Duas conexões com barreiras, limites, chave global e retry | Validada |
| T11 | Concluída | CSV, calamine, fallback, fórmulas, corrupção, PL e origem | Validada |
| T12 | Concluída | Manifesto, 64 MiB, multipart, replay concorrente e falha de disco | Validada |
| T13 | Concluída | Duas passagens, dois workers, commit/checkpoint e queda real do processo antes/depois de commit | Validada |
| T14 | Concluída | 16 operações reais, schemas, erros, headers e histórico | Contrato v1.0.0 preservado |
| T15 | Concluída | 17ª operação, snapshots, HMAC, filtros e invalidação de cursor após resolver pendências | Funcional validada; latência em T17 |
| T16 | Implementação concluída | Fluxo sintético integral verde; oficial indexado e bloqueado corretamente | **Oficial pendente** |
| T17 | Concluída | CSV 100k e XLSX 500k completos, somas corretas, p95 ≤ 300 ms em cada filtro | Meta atendida nos dois volumes |
| T18 | Implementação concluída | CLI, saúde, falha de banco, CI, documentação, Compose completo e 94 testes passando | **Integral pendente de T16** |

Aceitação oficial permanece pendente: regras de 17 fundos, cadastro/gabarito
incompatíveis, aprovações repetidas e estado inicial de exposições não fornecido.

T02 concluída: 11 novos cenários; regressão 15/15. Evidências T02-red/green. Documentos, identidade e calendário verificados.

T03 concluída: configuração imutável, nove códigos/parametrizações, importador Decimal. Regressão 26/26; T03-red/green.

T04 concluída: limites, ausências cadastrais e toggles das sete regras individuais; regressão 36/36; T04-red/green.

T05 concluída: PL multi-fundo/arquivo, raízes, saldo anterior, igualdade/excesso de centavo sem mutação; 38/38; T05-red/green.

T06 concluída: Decimal 38, HALF_UP apenas no fechamento, negativos e casos financeiros; 46/46; T06-red/green. Round-trip HTTP será exercitado em T14.

T07 concluída: motor determinístico, duplicidade antecipada, barrados sem efeitos, duas exposições apenas na aprovação; 49/49; T07-red/green. Corrigida expectativa sintética de líquido: fixture de dois dias resulta 9986.67, não a de 30 dias.

T08 concluída: migração Alembic SQL congelada, NUMERIC(38,2), FKs, unicidade operacional global/origem, barrados repetidos e rollback PostgreSQL real; 51/51; T08-red/green.

T09: cargas/regras implementadas; 54/54 na etapa. Reimportação, conflito/rollback, cadastro 3041, consulta agrupada, histórico e proteção de lote recuperável verificados. Corrida importação/congelamento e preservação de versões foram depois verificadas em `test_hardening.py` com PostgreSQL real e barreira.

T10 concluída: disputas sincronizadas por Barrier em conexões reais, mesma nota entre fundos, limite concorrente, fault após aprovação e retry; 58/58; T10-red/green. Locks de fundo e chave operacional em ordem global; vencedores entre lotes não são determinísticos.

T11 leitores CSV/XLSX e parsing implementados: 61/61 na etapa; T11-red/green. XLSX usa calamine e fallback openpyxl read-only para memória limitada e diagnóstico de fórmulas. Ambos os caminhos foram exercitados. Erro de data preserva PL; nominal/fundo ilegível bloqueia. Correções adicionais reproduzidas antes do ajuste: `T11-calamine`, `originals`, `xlsx-storage` e `xlsx-container`, cada uma com logs red/green.

T12 implementada e validada: criação/replay/conflito, chegada invertida, selagem, atomicidade/hash/quantidade/erro de disco; 63/63; T12-red/green. Limites HTTP/multipart e concorrência de upload complementados em T14.

T13 worker implementado: staging/chunks, PL completo, bloqueio/retomada, congelamento, lock de sessão, checkpoints e recuperação antes/depois de commit. 67/67 na etapa; T13-red/green. Corrida cadastral, falha estrutural sem PL parcial e versões congeladas incluídas na regressão ampliada de 86 testes.

T14: 16 operações implementadas com respostas reais validadas pelo OpenAPI, CORS/correlação, erros/IDs/query, regras otimistas e replay. 72/72; T14-red/green. Contrato canônico usado também na validação de entrada; nenhum artefato de contrato alterado.

T15 concluída funcionalmente: cursor HMAC com arquivo/filtros/limit/teto, sem lacunas/repetições, filtros/status/erro e navegação durante commits. 74/74; T15-red/green. Latência será medida em T17.

T16: `T16-red/green` e `test_t16_acceptance.py` verificam o fluxo HTTP/worker com todos os códigos de recusa, aprovação, replay e totais. Retomada consta em T13. [Aceitação oficial](aceitacao-oficial.md) registra o bloqueio dos 18 fundos (17 pendências), sem decisões fabricadas. [Auditoria por linha](divergencias-referencia.jsonl) identifica 4.941 aprovações repetidas e 712 aprovações do ANTECIPE sem cadastro.

T17: `T17-red/green` valida gerador determinístico CSV/XLSX e somas. O primeiro benchmark levou à substituição de consultas com grandes listas `IN` por joins com `VALUES`. O filtro de motivo exigiu índice direto por arquivo/código/sequência (migração 0002), seguido de regressão de 86 testes (`T17-indexed-green`). Medições definitivas são registradas separadamente; os baselines não comprovam a meta final.

T18: `T18-red/green` verifica CLI, limites de chunk, live e readiness com banco indisponível. Regeneração de todos os contratos e do handoff foi idêntica byte a byte; TypeScript compilou sem erros. CI foi configurada, mas não executada remotamente nesta entrega. [Operação](../../backend/README.md) e [arquitetura](arquitetura.md) descrevem os comandos e escolhas efetivamente implementadas.

Correção do cursor auxiliar: `pending-cursor-red.txt` reproduziu resposta 200 indevida após resolução das pendências. A revisão agora muda em toda revalidação, inclusive quando todas são resolvidas. `pending-cursor-green.txt` registra 90 testes passando, incluindo morte real do processo por `os._exit(42)` antes/depois do commit e retomada em outra conexão.

Ambiente completo: `docker-build.txt`, `docker-status.txt`, `docker-runtime.txt` e `docker-smoke.json` registram build Linux, migrações sobre banco vazio, API saudável, cargas administrativas e lote HTTP processado pelo worker Docker. O lote sintético tem 12 resultados: uma aprovação, 11 barramentos, nominal `120000.00`, desconto `200.00` e líquido `9800.00`. Seu histórico foi preservado no banco da instalação. Os testes/benchmarks usam outro banco.

## Consolidação da entrega

- Regressão ampliada: **94 testes passaram**, sem skips. `precision-summary-red.txt`
  reproduz a perda de centavos no resumo para valores além da precisão Decimal
  padrão; `precision-summary-green.txt` registra a correção e a regressão completa.
  `entrega-green.txt/xml` registra a execução final com cobertura. A cobertura
  dessa suíte não agrega os processos externos de CLI, Docker e benchmarks.
- `csv-lines-red/green` comprova a correção da origem física de registros CSV
  com quebra de linha entre aspas. Células originais continuam preservadas.
- Migração 0002 validada também sobre motivos/resultados já existentes, verificando
  backfill e igualdade da consulta antes/depois. Erro técnico após commit validado
  com estado `FALHOU`, ação de retomada e aprovação/exposições sem duplicação.
- [Desempenho](desempenho.md): CSV 100k em 81,961 s e XLSX 500k em 740,434 s;
  maior p95 entre filtros de 96,812 ms e 54,753 ms, respectivamente. Ambos passaram.
  A repetição do XLSX confirmou 450.000 aprovações e 50.000 barramentos.
- `lint-final.txt`, `tipos-final.txt`, `contratos-final.txt` e
  `typescript-final.txt` registram as verificações estáticas. `hashes-finais.txt`
  confirma os quatro insumos originais sem alteração. O contrato v1.0.0 e o
  handoff continuam idênticos byte a byte após regeneração.
- T01–T15 e T17 têm implementação e validações concluídas. T16 tem fluxo sintético,
  comparador e auditoria concluídos, mas **aceitação oficial pendente**. T18 tem
  operação/documentação/regressão verificadas; sua conclusão integral depende
  da aceitação oficial, conforme o planejamento. Nenhuma configuração, situação
  cadastral ou exposição anterior foi inventada para encerrar essa pendência.
- A repetição final da aceitação oficial (`aceitacao-oficial-execucao.txt`) indexou
  100.554 linhas em 19,630 s e confirmou novamente `BLOQUEADO` com 17 pendências,
  sem resultados/aprovações. A auditoria final confirmou as mesmas 4.941 duplicatas
  aprovadas e 712 aprovações sem cadastro. O container reconstruído permanece
  saudável (`docker-status-final.txt`, `docker-ready-final.json`).
