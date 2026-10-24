# kanastra-hackathon

## Planejamento

- [Plano sequencial do backend Antecipe](docs/planejamento-backend.md): tarefas de implementação, testes por etapa, dependências e critérios de conclusão.
- [Contrato de integração](docs/contrato-api.md): endpoints, estados, upload, erros, paginação e decisões compartilhadas.
- [OpenAPI](docs/contratos/openapi.json), [DTOs campo a campo](docs/contratos/dtos.md), [tipos TypeScript](docs/contratos/api-types.ts) e [exemplos](docs/contratos/exemplos.json).
- [Prompt autocontido do frontend para outro contexto](docs/handoff-frontend.md): inclui o OpenAPI completo, todos os schemas e exemplos JSON de todas as DTOs; basta copiar o documento inteiro ou anexar somente ele.
- [Auditoria dos arquivos fornecidos](docs/auditoria-insumos.md): inconsistências que precisam ser resolvidas para certificar a referência.

O backend está em [backend/](backend/README.md), com API FastAPI, PostgreSQL,
worker separado, migrações, cargas administrativas e testes. Consulte as
[evidências e pendências de aceitação](docs/execucao/checklist.md).

Para iniciar o ambiente: `docker compose --profile app up --build -d`.
As cargas cadastrais e de regras estão descritas no README do backend.

Para regenerar os artefatos de contrato e a auditoria, executar `python scripts/gerar_contrato_api.py` e `python scripts/auditar_insumos.py`.

Para validar o contrato, instalar `scripts/requirements-contratos.txt` em um ambiente Python separado e executar `python scripts/validar_contrato_api.py`.
