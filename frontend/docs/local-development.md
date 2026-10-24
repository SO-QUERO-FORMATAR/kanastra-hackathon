# Integração local com Docker Compose

## Estrutura e requisitos

O `compose.yaml` na raiz é o arquivo recebido do responsável pelo backend. A composição contém `db`, `migrate`, `api` e `worker`; o perfil `app` é obrigatório para os três últimos. O arquivo `compose.frontend.yaml` adiciona o frontend em `frontend/`, sem substituir a implementação do backend.

São necessários na raiz: `backend/Dockerfile`, `backend/init-test.sql`, o restante do código usado por esse Dockerfile e `files/` com os insumos administrativos reais. Esses arquivos estão versionados neste repositório. As dependências Python e os comandos administrativos são documentados em [backend/README.md](../../backend/README.md).

## Opção A — tudo em containers

Execute na raiz do repositório:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app up --build -d
```

Com Node.js local, `npm --prefix frontend run local:up` faz uma verificação prévia dos caminhos, usando a configuração efetivamente resolvida pelo Compose. O processo aborta sem criar os serviços quando os arquivos obrigatórios estiverem ausentes.

A imagem do frontend usa Node 24 e `npm ci`; seus fontes e contratos são montados para hot reload. Alterações em `package.json`/lockfile exigem reconstruir o serviço (`up --build -d frontend`). O Vite usa `--strictPort` para não escolher silenciosamente outra porta. O serviço usa `VITE_DEMO_MODE=false`, `VITE_API_BASE_URL=/api/v1` e `API_PROXY_TARGET=http://api:8000`.

Portas locais: frontend 5173, API 8000, PostgreSQL 55432. O Compose aguarda as migrações e o healthcheck da API; o healthcheck do frontend verifica a API através do proxy, não só o HTML da SPA. Não é preciso abrir o PostgreSQL para a rede nem configurar autenticação nova para este MVP.

Os volumes `pgdata` e `storage` persistem dados entre reinícios. `npm --prefix frontend run local:down` para a composição sem remover volumes. Os comandos `local:status` e `local:logs` mostram o estado e os logs. Não use remoção de volumes para solucionar falhas sem avaliar os dados existentes.

## Opção B — backend em Docker, frontend com Vite no host

Na raiz:

```sh
docker compose --profile app up --build -d
cd frontend
npm ci
cp .env.example .env.local
npm run dev -- --port 5173 --strictPort
```

O `.env.example` já aponta o proxy para `http://127.0.0.1:8000`, a porta publicada da API. Mantenha `/api/v1` como base do cliente e a demonstração desativada. Nesse modo, use o Compose original, para não subir também o frontend containerizado na mesma porta.

## Backend em outro checkout (opcional)

A estrutura acordada usa `backend/` e `frontend/` na mesma raiz, sem exigir variáveis extras. Se for necessário usar um backend em outro checkout, crie `.env` **na raiz do repositório** com:

```dotenv
BACKEND_ROOT=../checkout-do-backend
```

Esse diretório precisa conter `backend/Dockerfile`, `backend/init-test.sql` e `files/`. O override ajusta os contextos de build e mounts do backend; o frontend continua sendo construído a partir de `./frontend`. Mounts de insumos usam `create_host_path: false`, para evitar criar diretórios onde deveria existir um arquivo ausente.

## Validar conectividade e contrato

Com a composição ativa e as dependências npm instaladas:

```sh
npm --prefix frontend run api:check
```

O comando consulta, **através do proxy do frontend**, `health/live`, `health/ready`, `capacidades` e `cadastro/status`, com timeout e validação dos schemas do OpenAPI fornecido. Base cadastral ausente é relatada como pré-requisito pendente. Para isolar a API do proxy:

```sh
cd frontend
API_CHECK_BASE_URL=http://127.0.0.1:8000/api/v1 npm run api:check
```

Depois, faça uma importação com dados de teste conhecidos, confirme bloqueios, configure os fundos necessários, retome e confira resultados. Após iniciar os serviços, faça as cargas administrativas documentadas pelo backend a partir da raiz:

```sh
docker compose exec api python -m antecipe.cli import-registry /inputs/cnpj_situacao_mock.csv
docker compose exec api python -m antecipe.cli import-rules /inputs/validadores_antecipe.json
```

Essas cargas são idempotentes e configuram apenas o ANTECIPE; os outros fundos exigem configuração explícita. Consulte [o README do backend](../../backend/README.md) para restrições sobre substituição de bases em uso.

Os testes de frontend validam o cliente, contratos, transporte e UI com respostas controladas. Eles não substituem a validação conjunta contra o backend real. Veja [o roteiro de integração](integration.md).
