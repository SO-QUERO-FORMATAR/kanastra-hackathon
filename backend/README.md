# Backend Antecipe

Python 3.13.5, FastAPI, SQLAlchemy Core 2.0, Alembic e PostgreSQL 16.15.
Dependências diretas e transitivas fixadas em `uv.lock`. Contrato HTTP v1.0.0
em `../docs/contratos/openapi.json`, sem alteração dos artefatos de integração.

## Iniciar com Docker

Na raiz do repositório:

```powershell
docker compose --profile app up --build -d
docker compose exec api python -m antecipe.cli import-registry /inputs/cnpj_situacao_mock.csv
docker compose exec api python -m antecipe.cli import-rules /inputs/validadores_antecipe.json
docker compose logs -f worker
```

API em `http://localhost:8000/api/v1`; documentação em `http://localhost:8000/docs`.
O serviço `migrate` termina com sucesso antes de API/worker iniciarem. PostgreSQL
e arquivos usam volumes persistentes separados. `docker compose down` preserva
esses volumes. Não usar `down -v` para uma instância cujo histórico precisa ser mantido.

As cargas acima configuram somente ANTECIPE. Os demais fundos descobertos ficam
sem regras até configuração explícita pela API; nenhuma regra é herdada.

## Desenvolvimento local

Na raiz, com Docker e [uv](https://docs.astral.sh/uv/) instalados:

```powershell
docker compose up -d --wait db
uv sync --project backend --frozen --python 3.13.5
uv run --directory backend python -m antecipe.cli migrate
uv run --directory backend python -m antecipe.cli import-registry ../files/cnpj_situacao_mock.csv
uv run --directory backend python -m antecipe.cli import-rules ../files/validadores_antecipe.json
uv run --directory backend uvicorn antecipe.adapters.http:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```powershell
uv run --directory backend python -m antecipe.cli worker --batch-size 2000
```

`worker --once` reivindica no máximo um job e encerra; `worker` permanece em
execução. O worker é um processo separado; nenhum upload ou request de início
executa análise dentro da API. Os chunks de operação são de 1.000 a 5.000 linhas.

| Variável | Padrão local |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://antecipe:antecipe@127.0.0.1:55432/antecipe` |
| `TEST_DATABASE_URL` | mesma conexão, banco `antecipe_test` |
| `STORAGE_PATH` | `backend/storage`, relativo ao diretório de execução |
| `CURSOR_SECRET` | `local-demo-change-me`; definir valor estável na instalação |
| `CORS_ORIGINS` | `http://localhost:5173`; lista separada por vírgula |

Ambiente de demonstração sem autenticação, conforme contrato. Compose publica
portas somente em loopback. Alterar o segredo invalida cursores existentes.
API e worker precisam acessar os mesmos arquivos e o mesmo banco.

## Testes e evidências

```powershell
uv run --directory backend pytest
uv run --directory backend ruff check antecipe tests
uv run --directory backend mypy antecipe
uv run --directory backend python ../scripts/verificar_regeneracao.py
uv run --directory backend python -m antecipe.acceptance.official
uv run --directory backend python -m antecipe.acceptance.audit
uv run --directory backend python -m antecipe.performance.benchmark --count 100000 --format CSV
uv run --directory backend python -m antecipe.performance.benchmark --count 500000 --format XLSX
```

**A suíte, a aceitação e os benchmarks recriam o schema `public` exclusivamente
do banco `antecipe_test`. Não executar simultaneamente contra esse banco.**
`Settings.for_tests()` recusa qualquer outro nome e nunca utiliza `DATABASE_URL`.
PostgreSQL real é obrigatório; não existem skips por ausência de banco. Pytest
falha se não coletar testes. CI roda contrato, TypeScript, lint, tipos e suíte;
`workflow_dispatch` também executa volumes completos.

Com a instalação Docker já iniciada e as duas cargas administrativas realizadas,
`uv run --directory backend python -m antecipe.acceptance.smoke` verifica o fluxo
HTTP/worker real. Esse comando cria um lote com nome "Verificação Docker sintética"
na instalação, preserva as exposições anteriores e salva `docker-smoke.json`.

Relatórios versionáveis em `../docs/execucao/`: falha inicial/regressão por tarefa,
JUnit, aceitação oficial, contradições por linha e benchmarks. Estes medem API
HTTP real em TCP, worker dedicado, RSS da árvore de processos e p95 por filtro.
`--reuse-input` reutiliza arquivos sintéticos já gerados na pasta `.local`, mas
recria o banco e repete todo o processamento e todas as verificações de totais.

## Processamento, transações e recuperação

1. Criar manifesto, enviar batches e confirmar o início por `POST /processamento`.
2. Primeira passagem grava staging por chunks, descobre fundos e calcula PL por
   fundo sobre todos os arquivos estruturalmente utilizáveis. Uma falha estrutural
   remove a contribuição inteira daquele arquivo. Erros de data preservam nominal
   no PL; nominal/fundo ilegíveis bloqueiam com `DADOS_IMPEDEM_PL`.
3. Sob lock compartilhado entre o caso de publicação cadastral e a preparação,
   conferir pendências e congelar versões de cadastro/regras na primeira análise.
4. Segunda passagem lê staging na ordem do manifesto/linha. Aprovação, resultado,
   chave global, ambas as exposições e checkpoint são confirmados na mesma transação.
   A consulta cadastral usa documentos distintos do chunk, uma consulta por batch.

Um advisory lock de sessão por lote impede dois workers de executarem o mesmo
job. A queda da conexão libera esse lock. O job `RUNNING` persistido volta a ser
reivindicável automaticamente. Em falha técnica capturada, lote fica `FALHOU`
com retry permitido e a retomada explícita ocorre pela API. Antes da indexação
completa, recuperação refaz staging; depois dela, conserva contexto e avança a
partir dos resultados/checkpoints confirmados. Uma aprovação própria é recuperada
como resultado existente, sem ser reavaliada como duplicidade.

As transações adquirem locks de fundo, origem e chave operacional em uma ordem
global. O lock de fundo é conservador: serializa chunks do mesmo fundo, inclusive
raízes distintas. A constraint de chave operacional é global entre fundos.
Resultados barrados não reservam essa chave. A ordem dentro do lote é fixa;
entre lotes concorrentes, vence quem adquirir os locks primeiro.

Uma nova base cadastral é recusada enquanto houver lote ativo ou recuperável
vinculado à base atual. Reimportar os mesmos bytes é idempotente. Resolver o job
pela retomada antes de trocar a base; não apagar histórico para contornar a proteção.
Regras publicadas após o congelamento afetam somente lotes ainda não analisados.

Para resolver um lote `BLOQUEADO`, consultar `GET /lotes/{id}/pendencias` e publicar
uma configuração explícita para cada fundo indicado em `PUT /fundos/{id}/regras`.
Usar `versao_base: null` na primeira configuração ou a versão atual na edição,
sempre com `Idempotency-Key` UUID. Depois enviar `POST /lotes/{id}/processamento`
com **uma nova chave** de idempotência e acompanhar `GET /lotes/{id}`. Repetir a
chave do início anterior recupera a resposta antiga; não solicita outra execução.
Pendência `DADOS_IMPEDEM_PL` exige arquivo corrigido em novo lote. O campo `acoes`
da resposta determina quais operações estão disponíveis. Todos esses caminhos
usam o prefixo `/api/v1`; DTOs completos estão no contrato e no Swagger.

## Arquivos, precisão e limites

- CSV UTF-8 com/sem BOM, delimitador `;`, decimal brasileiro, datas `dd/mm/aaaa`.
  Linhas vazias não renumeram as posteriores; campos entre aspas podem conter
  quebras de linha e a origem aponta para a linha física inicial do registro.
  As onze colunas são obrigatórias.
- XLSX usa calamine quando o container expandido tem até 16 MiB e não tem fórmulas;
  o fallback openpyxl `read_only` atende arquivos maiores e células com fórmulas.
  Fórmula sem valor em cache gera `FORMULA_SEM_VALOR`; nenhuma fórmula é executada.
  Macros não são aceitas. Cabeçalho deve ocupar a primeira linha da aba escolhida.
- Identificadores numéricos de Excel geram diagnóstico, pois os zeros já podem ter
  sido perdidos na origem. Exportar documentos e números de nota como células texto.
  Valores numéricos de Excel usam sua representação decimal textual, sem cálculo
  financeiro em float; precisão já perdida no arquivo não pode ser recuperada.
- Armazenamento usa UUIDs internos, preservando os bytes e hashes originais. Após
  falha entre escrita física e commit, pode existir arquivo órfão não confirmado;
  retry usa os mesmos IDs e pode substituí-lo pelo conteúdo validado do manifesto.
- Valores persistidos em `NUMERIC(38,2)`, cálculo com precisão Decimal 38 e fechamento
  em centavos com `ROUND_HALF_UP`. O leitor rejeita nominal que excede 36 dígitos
  significativos em vez de arredondá-lo silenciosamente. Sem clamp de valores negativos.
- Configurar proxy com pelo menos 65 MiB de limite de request, preservando validação
  de 64 MiB para os binários. São no máximo 3 arquivos por batch, 100 por lote e
  500.000 linhas não vazias por lote, conforme capacidades publicadas.

## Operação e aceitação

`/health/live` verifica o processo; `/health/ready` verifica PostgreSQL e escrita
no storage. Base/regras ausentes são informadas por cadastro/pendências, sem fazer
a API parecer indisponível. Erros têm `X-Request-Id`, envelope do contrato e
`Retry-After` quando cabível. Logs do worker registram lote, arquivo, fase, linha
e versão cadastral, sem imprimir os dados completos dos títulos.

Para backup consistente, pausar entrada de novos trabalhos, esperar os jobs ou
parar API/worker e copiar PostgreSQL (`pg_dump`) e o volume de arquivos como um
mesmo conjunto. Para restaurar, restaurar ambos, aplicar migrações e iniciar
worker; jobs interrompidos são recuperados. Migração inicial não oferece downgrade
destrutivo automático. Testar restauração antes de substituir uma instalação.

A aceitação oficial continua **PENDENTE**: faltam 17 configurações, há 712
aprovações do ANTECIPE sem cadastro e 4.941 aprovações repetidas no gabarito, e
não foi informado o estado inicial de exposições/aprovações. O processamento
oficial indexa 100.554 linhas e bloqueia antes da primeira decisão. O comparador
e a auditoria detalham ausências/contradições sem alimentar o motor com o gabarito.
