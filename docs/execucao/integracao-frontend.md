# Validação da integração frontend/backend

Verificação local em 24/10/2026, na branch `work`, com Windows/PowerShell,
Node.js 24.11.1, Python 3.13.5 e Docker Desktop com containers Linux.

`work` já incorpora `main` (`03b9f80`); o conteúdo de `backend/` é idêntico ao
da base. Os diretórios `docs/`, `files/` e `scripts/` permanecem compartilhados
na raiz, conforme os caminhos usados pelo Dockerfile e pelo Compose.

## Resultados

| Verificação | Resultado |
| --- | --- |
| Compose combinado: `config --quiet` e `up --build -d` | Sucesso |
| Estado dos serviços | Banco, API e frontend saudáveis; worker ativo; migrate encerrado com código 0 |
| Cargas `import-registry` e `import-rules` | Sucesso |
| Backend: Ruff, mypy e regeneração dos contratos | Sucesso |
| Backend: pytest com PostgreSQL real em `antecipe_test` | 94 testes passaram |
| Frontend: `npm run check:api` | Sucesso após normalizar CRLF/LF na comparação dos tipos |
| Frontend: `npm test` | 100 testes passaram |
| Frontend: `npm run build` | Sucesso |
| Frontend: `npm run test:e2e` | 9 testes Chromium passaram no Windows com Compose ativo |
| Frontend: `npm run api:check` | Saúde, capacidades e cadastro válidos pelo proxy em 5173 |
| Smoke HTTP/worker pelo proxy em 5173 | Lote concluído; 12 resultados; nominal total 120.000,00 |

O smoke foi executado com:

```sh
uv run --directory backend python -m antecipe.acceptance.smoke --base-url http://127.0.0.1:5173/api/v1
```

O lote `f9f37bb6-c6af-42b6-86f0-790fa92f55c9` foi preservado na instalação.
Foram 12 recebíveis barrados e nenhum erro de dados; o teste preserva as
exposições anteriores e não exige aprovação financeira. O relatório desta
execução está localmente em `.local/integracao-work-main-smoke.json`; a
evidência histórica `docker-smoke.json` foi preservada.

## Ajustes e limites

- Playwright define variáveis pelo campo `env`, compatível com Windows e Unix,
  e usa 5183/5184 para não disputar a porta 5173 do Compose.
- A comparação de tipos ignora somente a diferença CRLF/LF do checkout Git;
  divergências de conteúdo continuam sendo rejeitadas.
- Os testes de navegador usam respostas controladas. O smoke separado cobre
  proxy, API, banco e worker reais; não certifica todo o dataset oficial.
- O dataset oficial ainda depende das configurações de 17 fundos e da
  resolução das inconsistências de cadastro/gabarito já documentadas no
  [checklist](checklist.md). Benchmarks de volume não foram repetidos nesta revisão.
- `npm audit --omit=dev`: zero vulnerabilidades. A auditoria completa aponta
  três dependências de desenvolvimento afetadas (Vitest, `@vitest/mocker` e
  `tinypool`: duas classificadas como críticas e uma moderada). A atualização
  principal do runner sugerida pelo npm permanece pendente; não impede esta
  execução local, mas precisa de revisão antes de expor ferramentas de desenvolvimento.

O ambiente ficou disponível em `http://localhost:5173`, com API em
`http://localhost:8000/docs`. Em instalações novas, executar as duas cargas
administrativas do README após subir o Compose.
