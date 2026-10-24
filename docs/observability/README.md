# Logs de diagnóstico — contrato v1

A API, o worker e a CLI escrevem **um objeto JSON por linha em stderr**, validado
nos testes contra [log-event.schema.json](log-event.schema.json). O stdout da CLI
continua reservado ao resultado do comando. Os logs não alteram decisões,
contratos HTTP, regras financeiras, persistência ou retentativas.

## Envelope e correlação

| Campo | Uso |
|---|---|
| `schema_version` | Versão do contrato de logs (`1.0`). |
| `timestamp` | Instante UTC com offset explícito. |
| `severity_text` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`. |
| `service` | Nome do processo, versão da aplicação, ambiente e revisão Git opcional. |
| `event` | Nome estável, categoria e resultado: `started`, `observed`, `success`, `partial`, `rejected`, `blocked` ou `failure`. |
| `correlation` | UUIDs internos de requisição, lote, execução, arquivo e fundo, quando disponíveis. |
| `operation` | ID de operação do contrato HTTP ou comando CLI; nunca a URL recebida. |
| `duration_ms` | Tempo monotônico decorrido, em milissegundos. |
| `counts` | Contagens de arquivos, bytes, linhas, erros, aprovações, recusas e checkpoint. |
| `versions` | UUIDs das versões de regras e cadastro utilizadas. |
| `decision` | Replay, recuperação e contagem de motivos permitidos. |
| `error` | Categoria, código estável, possibilidade de retry e até oito localizações no código da aplicação. |
| `http` | Status HTTP; sem IP, rota literal, query, headers ou corpo. |

Exemplo ilustrativo de um chunk já confirmado no banco:

```json
{"schema_version":"1.0","timestamp":"2026-10-24T22:00:00+00:00","severity_text":"INFO","service":{"name":"antecipe-worker","version":"1.0.0","environment":"production"},"event":{"name":"worker.chunk_committed","category":"worker","outcome":"success"},"correlation":{"lot_id":"11111111-1111-4111-8111-111111111111","execution_id":"22222222-2222-4222-8222-222222222222"},"counts":{"row_count":2000,"approved_count":1800,"rejected_count":200,"error_count":0,"checkpoint":2000},"decision":{"reason_counts":{"NOTA_DUPLICADA":200}},"duration_ms":125.5}
```

O `request_id` é gerado no servidor e devolvido em `X-Request-Id`. A criação liga
esse ID ao `lot_id`; o enfileiramento liga o lote ao `execution_id`; o worker
carrega esses IDs e o `file_id` em suas etapas. Contextos são isolados por
requisição/tarefa, inclusive na passagem da API para o threadpool. Não há
introdução de um protocolo de tracing distribuído ou mudança no banco.

## Eventos e semântica

| Fluxo | Eventos principais |
|---|---|
| HTTP | `http.finished`, `http.failed`: operação, status, duração e código de falha. |
| Recebimento | `lot.create.*`, `lot.upload.*`, `lot.enqueue.*`: início, retorno confirmado ou falha. |
| Idempotência | `idempotency.replayed`, `.conflict`, `.busy`: decisão sem registrar chave ou fingerprint. |
| Configuração | `rules.publish.*`, `rules.import.*`, `rules.conflict`, `rules.reused`. |
| Cadastro | `registry.import.*`, `registry.reused`, `registry.busy`, `registry.reactivation_selected`. |
| Worker | `worker.claimed`, `worker.index.*`, `worker.freeze.*`, `worker.file_*`, `worker.blocking`, `worker.rules_frozen`, `worker.snapshot_reused`, `worker.chunk_committed`, `worker.completed`, `worker.failed`. |
| Processo | `service.started`, `service.stopped`, `cli.command.*`, `process.failed`. |

`*.finished` nos serviços administrativos e de upload só é emitido após a saída
da transação, incluindo seu commit. `worker.chunk_committed` confirma o chunk;
uma falha antes do commit não produz esse evento. Decisões como `worker.blocking`
e `registry.reactivation_selected` descrevem a escolha dentro da transação; o
retorno posterior confirma que ela terminou. Um processo pode morrer entre o
commit e a escrita do log: estes são diagnósticos, não um ledger de auditoria.

`worker.lot.finished` significa apenas que a função retornou (`observed`), pois
o lote pode ter parado por uma pendência. O estado final da análise é indicado
por `worker.completed` (`success`/`partial`), `worker.freeze.finished` (`blocked`)
ou pelos eventos de falha. Aprovações e recusas são agregadas por chunk; não há
um log por nota. Checkpoints de indexação e disputa de lock ficam em `DEBUG`.
Health checks bem-sucedidos também ficam em `DEBUG`; falhas não são ocultadas.

## Privacidade e operação

A implementação segue a minimização de dados para diagnóstico e os princípios
de necessidade, segurança e prevenção descritos nos arts. 6º e 46 da
[LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm).
Isso é uma medida técnica, não uma certificação de conformidade da operação.

- Somente campos e códigos explicitamente permitidos entram no evento. A mesma
  restrição vale em `DEBUG`. Campos novos exigem atualização do contrato e testes.
- Não entram nomes, CPF/CNPJ, número de nota, valores financeiros, dados originais,
  configurações completas, nomes/caminhos de arquivos, hash do conteúdo, chaves
  de idempotência, IP, URL literal, parâmetros de busca, cookies, tokens ou senhas.
- Exceções preservam categoria e `arquivo_do_codigo.py:linha`. Não incluem
  mensagens, cadeias de exceção, código-fonte, locais, caminhos absolutos ou SQL.
  O formatter também descarta mensagens livres de bibliotecas; essas ocorrências
  aparecem como `runtime.log`, com severidade e categoria de erro quando disponível.
- O access log padrão do Uvicorn é desabilitado em favor dos eventos HTTP seguros.
  A configuração é reaplicada no startup, inclusive quando o servidor recebe uma
  instância da aplicação. Exceções não tratadas da CLI/threads usam o mesmo formato.
- IDs internos podem ser relacionados a registros de negócio; são referências
  pseudônimas, não dados garantidamente anônimos. Restrinja o acesso ao coletor
  por função e finalidade, audite consultas e proteja transporte/armazenamento.
- API, worker e migração usam rotação local do Docker: três arquivos de até 10 MiB
  por container. Esse limite de volume **não define retenção temporal**. O operador
  deve configurar prazo de retenção, expurgo e controle de acesso no coletor conforme
  a finalidade e as obrigações aplicáveis. Logs do proxy, PostgreSQL e outros
  componentes externos precisam de política própria; não são sanitizados por Python.
- O sink é best effort: falhas de logging não devem mudar a decisão nem provocar
  retry financeiro. Monitore a disponibilidade/ingestão no coletor; não confunda
  ausência de um evento com ausência de commit.

## Configuração e investigação

| Variável | Valores |
|---|---|
| `LOG_LEVEL` | `INFO` por padrão; `DEBUG`, `WARNING`, `ERROR`, `CRITICAL`. Valor inválido usa `INFO`. |
| `APP_ENV` | `local` por padrão; `test`, `staging`, `production`. Valor inválido usa `local`. |
| `APP_REVISION` | SHA Git completo com 40 caracteres hexadecimais minúsculos; inválido/ausente é omitido. |

Essas variáveis são propagadas pelo Compose sem mudar suas portas ou serviços.
`service.name` é definido pelo processo (`antecipe-api`, `antecipe-worker` ou
`antecipe-cli`); não aceita texto livre recebido de clientes.

Para encontrar um problema, parta do `X-Request-Id`, filtre
`correlation.request_id`, obtenha `correlation.lot_id` e acompanhe o lote no
worker pela execução. Use `versions` para conferir o snapshot utilizado e
`counts.checkpoint` para localizar o último chunk confirmado. Investigue dados
de uma nota somente no sistema de origem com acesso autorizado.

Exemplos de filtros no coletor: `event.name = http.failed` e status >= 500 para
erros da API; `event.name = worker.failed` para falhas de processamento;
`event.name = worker.blocking` para pendências; `event.name = idempotency.conflict`
para conflitos de chave. Alertas devem selecionar o evento responsável para
não contar a mesma falha novamente em seu resumo HTTP ou CLI.

O formato é JSON transportável por coletores com suporte a parsing JSON. A
configuração de exportadores ou a certificação em um produto específico não faz
parte deste contrato. Testes validam schema, isolamento concorrente, rollback,
retomada e ausência de dados pessoais/credenciais em cenários de sucesso e erro.
