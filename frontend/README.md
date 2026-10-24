# Antecipe

Frontend de gestão de recebíveis em **Vue 3 (Composition API), Quasar, Vite e TypeScript**, conforme a arquitetura do PDF Antecipe v2.1 e o contrato HTTP v1.0.0 fornecidos. Paleta institucional verde/creme, fontes Inter e Syne hospedadas no próprio bundle, layout responsivo e interface em português.

## Execução local integrada

O frontend agora está em `frontend/`, ao lado de `backend/`. Para subir API, worker, banco e frontend juntos, execute na raiz `docker compose -f compose.yaml -f compose.frontend.yaml --profile app up --build -d`. Veja [o guia local](docs/local-development.md).

Os comandos npm abaixo devem ser executados dentro de `frontend/`.

## Desenvolvimento

Requer Node.js 22.12+ (validado com 24.19) e npm.

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Configure `API_PROXY_TARGET` com a origem do backend. O proxy encaminha `/api` sem reescrever o caminho. Alternativamente, configure `VITE_API_BASE_URL` com a URL completa terminada em `/api/v1`; nesse caso, o backend precisa permitir a origem do frontend via CORS, os headers `Content-Type` e `Idempotency-Key`, e expor `X-Request-Id`, `Idempotency-Replayed` e `Retry-After`.

**Não há credenciais ou login no contrato deste MVP.** Variáveis `VITE_*` são públicas. Reinicie o Vite após alterá-las. Em produção, configure o servidor para retornar `index.html` nas rotas da SPA e encaminhar `/api` para o backend, ou defina a URL da API durante o build.

Para demonstração sem backend:

```sh
VITE_DEMO_MODE=true npm run dev
```

A demonstração é identificada no cabeçalho. Usa exclusivamente exemplos sintéticos do contrato, sem motor de crédito: o conteúdo dos arquivos enviados não é interpretado. O cenário inicial mostra aprovado, barrado e erro de dados; novos lotes simulam bloqueio pelo fundo Safira ainda sem configuração. O estado simulado reinicia ao recarregar a página. Para descartar uma sessão de envio simulada antiga, use **Nova seleção**. O modo real nunca substitui erros da API por dados demonstrativos.

## Telas

- **Visão geral:** resumo do último lote e histórico com filtro de status e cursores. As métricas não representam a carteira global.
- **Importação:** múltiplos CSV/XLSX, limites publicados pelo backend, SHA-256, manifesto imutável, batches atômicos, progresso de transferência e recuperação por confirmação de arquivos. Envios são sequenciais (dentro do limite máximo de duas transferências concorrentes). XLSX usa a primeira aba com dados (`aba=null`).
- **Acompanhamento:** polling visível com backoff e Retry-After, estados de processamento, pendências acionáveis, retomada explícita, contadores separados e resumos por fundo.
- **Fundos e regras:** nove validadores tipados, precificação, configuração individual explícita, validação do schema, controle de versão e leitura das regras históricas.
- **Resultados:** filtros compatíveis, navegação anterior/próxima por cursor, snapshot, originais e explicações de recusa ou erros de ingestão.

Dinheiro é mantido em strings; nenhuma decisão financeira é calculada no frontend. Não há exportação, cancelamento, edição de decisão ou importação cadastral pelo navegador porque essas operações não existem no contrato.

## Validação

```sh
npm test
npm run check:api
npm run build
npx playwright install chromium
npm run test:e2e
```

Neste ambiente, Chromium já está disponível; use `PLAYWRIGHT_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`. O download padrão do Playwright exige acesso ao CDN oficial. Os testes de navegador iniciam seus próprios servidores nas portas 5173 e 5174, que devem estar livres. Para usar portas diferentes, configure `E2E_DEMO_PORT` e `E2E_API_PORT`.

Os testes unitários validam os schemas/exemplos fornecidos, as 17 operações, strings monetárias, SHA-256, multipart, batches, headers, erros e cursores. Os testes de navegador usam demonstração e respostas HTTP controladas; não certificam o backend externo. Veja [integração e limitações](docs/integration.md).

Tipos gerados em `src/api/schema.d.ts`; fonte normativa em `contracts/openapi.json`. Regere com `npm run generate:api`. O CI verifica geração determinística, testes, tipos, build e navegador.

## Estrutura

- `src/api`: cliente HTTP tipado, transporte XHR e demonstração isolada.
- `src/pages`: histórico, upload, acompanhamento e fundos.
- `src/components`: resultados, erros, estados e navegação por cursor.
- `src/composables`: estado de paginação remota com proteção contra respostas atrasadas.
- `contracts`: OpenAPI e fixtures extraídos integralmente do texto fornecido, sem alterar o contrato.
- `docs/style-guide.md`: guia visual fornecido.

Use o checkout existente: as tarefas em nuvem já são isoladas e não precisam de outro Git worktree.
