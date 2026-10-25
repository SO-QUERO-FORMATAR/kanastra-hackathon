# Antecipe

Frontend de gestão de recebíveis em **Vue 3 (Composition API), Quasar, Vite e TypeScript**, baseado na arquitetura Antecipe v2.1 e integrado ao contrato HTTP v1.0.0 mantido no repositório. Paleta institucional verde/creme, fontes Inter e Syne hospedadas no próprio bundle, layout responsivo e interface em português.

O [relatório curto na raiz](../README.md#relatório-curto) reúne a entrega, tecnologias, decisões e itens fora do escopo. Este guia detalha o desenvolvimento da interface; o [guia do backend](../backend/README.md) cobre API, persistência e processamento.

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
- **Acompanhamento:** polling visível com backoff e Retry-After, estados de processamento, pendências acionáveis, retomada explícita, contadores separados e resumos por fundo. Fundos sem regras não impedem a consulta dos resultados dos fundos configurados.
- **Fundos e regras:** edição em modal, nove validadores tipados, precificação, configuração individual explícita, controle de versão e leitura das regras históricas. Apenas parâmetros de regras ativas são validados; a precificação é obrigatória. Importação de arquivo JSON com um objeto ou lista de até 100 fundos e limite de 1 MiB, publicada de forma atômica pela API.
- **Resultados:** filtros compatíveis, navegação anterior/próxima por cursor, snapshot, originais e explicações de recusa ou erros de ingestão. Notas sem configuração mostram **“Regras de fundo não configuradas”** em vermelho; após salvar as regras, **Retomar análise** processa as pendências e preserva decisões anteriores.

As opções de situação cadastral são **Ativa, Suspensa, Inapta e Baixada**; as de tipo de recebível são **Duplicata, Duplicata de Serviço, Cheque, CCB e Nota Comercial**. Os seletores permitem múltiplas opções do catálogo definido no contrato, sem cadastrar valores por texto livre. A API também valida as opções ativas recebidas por JSON.

Dinheiro é mantido em strings; nenhuma decisão financeira é calculada no frontend. Não há exportação, cancelamento ou edição de decisão porque essas operações não existem no contrato.

**Base cadastral:** o JSON de regras e o CSV cadastral são arquivos distintos. Use **Importar base cadastral** em Fundos e regras, no aviso do upload ou na pendência do lote. O CSV usa UTF-8 e cabeçalho `DOC;SITUACAO_CADASTRAL`, com limite de 1 MiB. Após a carga, clique em **Retomar análise** no lote. No modo de demonstração, a carga é simulada; no modo real, é publicada no PostgreSQL pela API.

Notas recusadas exibem a lista completa de requisitos não atendidos na tabela e no detalhe, com as mensagens fornecidas pelo backend e os valores da nota e da configuração aplicada.

## Validação

```sh
npm test
npm run check:api
npm run build
npx playwright install chromium
npm run test:e2e
```

Instale o Chromium com `npx playwright install chromium` antes da primeira execução. O download padrão do Playwright exige acesso ao CDN oficial. Para usar um navegador já instalado, defina a variável de ambiente `PLAYWRIGHT_EXECUTABLE_PATH` com o caminho do executável. Os testes funcionam no Windows e no Linux/macOS e iniciam seus próprios servidores nas portas 5183 e 5184, que devem estar livres; o Compose pode continuar ativo na porta 5173. Para usar portas diferentes, configure `E2E_DEMO_PORT` e `E2E_API_PORT`.

Os testes unitários validam schemas/exemplos, operações HTTP, strings monetárias, SHA-256, multipart, batches, headers, erros, cursores e parâmetros de regras. Os testes de navegador cobrem também modal, importação JSON, parâmetros desativados, resultados parciais e restauração das opções após salvar e recarregar. Usam demonstração e respostas HTTP controladas; a persistência e o processamento reais são verificados pelos [testes do backend](../backend/README.md#testes-e-evidências). Veja [integração e limitações](docs/integration.md).

Tipos gerados em `src/api/schema.d.ts`; fonte normativa em `contracts/openapi.json`. Regere com `npm run generate:api`. O CI verifica geração determinística, testes, tipos, build e navegador.

## Estrutura

- `src/api`: cliente HTTP tipado, transporte XHR e demonstração isolada.
- `src/pages`: histórico, upload, acompanhamento e fundos.
- `src/components`: resultados, erros, estados e navegação por cursor.
- `src/composables`: estado de paginação remota com proteção contra respostas atrasadas.
- `contracts`: cópia do OpenAPI e fixtures de integração, sincronizados com os artefatos em `../docs/contratos/`.
- `docs/style-guide.md`: guia visual fornecido.
