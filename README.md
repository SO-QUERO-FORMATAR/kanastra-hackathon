# Antecipe — execução local

O repositório usa pastas irmãs para frontend e backend:

```text
kanastra-hackathon/
├── compose.yaml             # serviços fornecidos pelo backend
├── compose.frontend.yaml    # frontend + proxy + mounts locais
├── backend/
│   ├── Dockerfile
│   ├── init-test.sql
│   └── ...                  # código do backend
├── files/                   # insumos administrativos usados pelo backend
└── frontend/                # Vue 3 + Quasar + Vite + TypeScript
```

O backend FastAPI está em `backend/`, o frontend Vue 3 + Quasar está em `frontend/`, e os contratos, insumos e scripts compartilhados permanecem em `docs/`, `files/` e `scripts/`. Cada aplicação mantém suas próprias dependências, testes e configuração de CI.

## Rodar todos os serviços

Requisitos: Docker Engine/Desktop com Compose v2. Execute na raiz do repositório:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app up --build -d
docker compose -f compose.yaml -f compose.frontend.yaml --profile app ps

# Cargas administrativas iniciais, após a API estar saudável
docker compose exec api python -m antecipe.cli import-registry /inputs/cnpj_situacao_mock.csv
docker compose exec api python -m antecipe.cli import-rules /inputs/validadores_antecipe.json
```

O frontend usa a porta **5173**, a API **8000** e o banco **55432**, publicados apenas na interface local. A ordem de inicialização é banco → migrações → API/worker → frontend. O frontend aguarda a API saudável e encaminha `/api` para `http://api:8000` na rede Docker. A URL de API usada pelo navegador é relativa (`/api/v1`), sem depender do DNS interno dos containers ou de CORS entre portas. A demonstração fica desativada nessa composição.

Com Node.js instalado, há um comando equivalente que verifica os arquivos ausentes antes de executar o Compose:

```sh
npm --prefix frontend run local:up
npm --prefix frontend run local:status
npm --prefix frontend run local:logs
```

Para parar os serviços, preservando dados do PostgreSQL e dos arquivos:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app down
```

Veja [o guia local completo](frontend/docs/local-development.md) para executar Vite fora do Docker, validar a API, usar um checkout separado do backend e diagnosticar a carga cadastral. A [documentação do frontend](frontend/README.md) detalha as telas e os testes.

## Documentação e contratos compartilhados

- [Backend e comandos administrativos](backend/README.md).
- [Planejamento do backend](docs/planejamento-backend.md) e [evidências de aceitação](docs/execucao/checklist.md).
- [Contrato HTTP](docs/contrato-api.md), [OpenAPI canônico](docs/contratos/openapi.json), [DTOs](docs/contratos/dtos.md), [tipos TypeScript](docs/contratos/api-types.ts) e [exemplos](docs/contratos/exemplos.json).
- [Auditoria dos insumos](docs/auditoria-insumos.md) e [documento de referência do frontend](docs/handoff-frontend.md).

Os geradores compartilhados continuam em `scripts/`: `python scripts/gerar_contrato_api.py`, `python scripts/auditar_insumos.py` e `python scripts/validar_contrato_api.py` (este último usa `scripts/requirements-contratos.txt`). `npm --prefix frontend run check:api` verifica que o contrato usado pelo frontend coincide com o contrato canônico e que os tipos gerados estão atualizados.

A carga de regras inicial configura somente ANTECIPE. Os demais fundos precisam de configuração explícita; consulte as limitações e evidências no README do backend.
