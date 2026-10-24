# Integração com o backend

A stack é Vue 3 + Quasar (SPA com Vite), conforme o PDF v2.1. O contrato HTTP v1.0.0 canônico está em `docs/contratos/openapi.json` na raiz do repositório. A cópia em `frontend/contracts/openapi.json` é usada pela interface e verificada por `npm run check:api`; qualquer alteração deve ser coordenada com o backend. Os testes validam todos os exemplos fornecidos contra os schemas.

## Operações

| Tela           | Operações                                                                |
| -------------- | ------------------------------------------------------------------------ |
| Preparação     | GET health/live, health/ready, capacidades, cadastro/status              |
| Histórico      | GET lotes, lotes/{id}                                                    |
| Upload         | POST lotes, GET lotes/{id}/arquivos, POST lotes/{id}/batches             |
| Acompanhamento | GET lotes/{id}, arquivos, pendencias, resumos-fundos; POST processamento |
| Fundos         | GET fundos, GET/PUT fundos/{id}/regras                                   |
| Resultados     | GET arquivos/{id}, arquivos/{id}/resultados                              |

Todas as rotas usam `/api/v1`. O cliente implementa as 18 operações, incluindo a importação atômica de regras por JSON em `/fundos/regras/importacao`. Health e consulta individual de arquivo estão disponíveis para diagnóstico; o fluxo da interface usa as operações apropriadas a cada tela.

## Recuperação

Manifesto, IDs, chaves de criação/batches e sessão pendente são armazenados em localStorage, com namespace separado por API/modo. Bytes dos arquivos não são persistidos: após recarregar, selecione os mesmos arquivos na mesma ordem; o hash deve coincidir. Antes de reenviar, consulte a lista completa de arquivos confirmados. Um batch incerto é repetido com os mesmos IDs, bytes e chave. A sessão concluída é arquivada pelo ID do lote para preservar as chaves.

A chave de processamento permanece até confirmar a aceitação. Retomada após correção é uma nova operação. O botão depende de `acoes`, nunca somente do status. Em bloqueio, o polling para e as pendências são consultadas. Mudanças de regras exigem revisão explícita; 409 de versão impede sobrescrita e oferece recarga. Chaves de regras são guardadas por fingerprint e versão por 24 horas.

A paginação preserva os cursores anteriores, os filtros e o limite. Mudanças de filtro/limite e atualização explícita reiniciam o snapshot. Não existem contagens filtradas inventadas ou navegação por offset.

## Validação contra o serviço real (pendente)

O Compose recebido publica a API na porta 8000 e a expõe como `api:8000` dentro da rede Docker. A configuração de proxy está pronta em `compose.frontend.yaml`; o código FastAPI, as migrações e o worker estão em `backend/`. Para certificar a integração, siga [o guia local](local-development.md) e execute com `VITE_DEMO_MODE=false`:

1. Confirmar health/live, health/ready, capacidades e cadastro/status.
2. Em banco de teste limpo, criar um lote de CSV/XLSX conhecido, incluindo nomes repetidos; verificar o manifesto e SHA-256 no servidor.
3. Enviar batches e simular perda de resposta; conferir replay da mesma chave e confirmação atômica.
4. Iniciar processamento, aguardar bloqueio por fundos sem configuração e configurar cada fundo explicitamente (inclusive os 17 pendentes do dataset completo).
5. Retomar, verificar contexto congelado e versões históricas, aguardar conclusão e conferir resumos e resultados com o backend.
6. Conferir filtros, cursores/snapshot, conflito de versões, 422 com detalhes, erros técnicos e recuperação permitida.

O gabarito não é utilizado como motor nem como evidência de aprovação certificada. A UI de demonstração usa apenas as fixtures fornecidas, com um resumo sintético fixo dos três resultados ilustrativos. A igualdade dos contratos versionados é validada automaticamente. A validação do serviço em execução e do processamento completo continua sendo uma etapa separada, conforme o roteiro acima.
