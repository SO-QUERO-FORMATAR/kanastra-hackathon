# Prompt autocontido para planejar o frontend Antecipe

Copie TODO este documento para o outro contexto, ou anexe somente este arquivo. Ele contém o contrato completo: não é necessário ter acesso ao repositório, aos outros documentos ou à conversa anterior. O conteúdo entre os marcadores abaixo é o prompt.

<!-- INICIO DO PROMPT -->

Você vai planejar o frontend do Antecipe em Vue 3 + Quasar com TypeScript. O Antecipe recebe notas/recebíveis CSV ou XLSX, processa regras de FIDC no backend e apresenta aprovações, recusas, motivos e valores líquidos.

Quero um planejamento sequencial de implementação do frontend. Para cada tarefa, descreva objetivo, dependências, tela/componentes, operação HTTP, DTOs de request/response, testes novos, regressão acumulada e critério de conclusão. Comece pelos tipos e cliente da API, depois mocks, seleção/upload, acompanhamento e pendências, configuração de regras, resumos, histórico e tabela de resultados. Finalize com testes de contrato e integração real. Não considere nenhuma funcionalidade já implementada.

Este prompt é a fonte completa do contrato v1.0.0. Não peça para ler arquivos locais nem dependa do chat anterior. Gere os tipos TypeScript a partir do OpenAPI incluído aqui; não invente endpoints, campos, enums, autenticação ou paginação por offset. Os schemas são normativos; os exemplos são ilustrativos e não substituem obrigatoriedade, tipos ou validações. Se identificar uma incompatibilidade, registre-a antes de propor qualquer mudança coordenada no contrato.

## Entrega esperada do planejamento

1. Mapa de telas e navegação, estados de carregamento, erro, vazio, bloqueio e sucesso.
2. Estrutura do projeto, componentes, cliente HTTP, stores/composables e tipos derivados do contrato.
3. Tarefas em ordem de execução com testes a cada etapa e regressão antes de avançar.
4. Matriz tela/ação → operationId → request → response → erros → testes.
5. Estratégia de mocks usando os JSONs abaixo, seguida de validação contra a API real quando disponível.
6. Checklist final de compatibilidade: multipart, idempotência, dinheiro em string, versionamento, polling, retomada e cursores.

## Contexto confirmado

- Backend planejado: Python/FastAPI/PostgreSQL, processamento assíncrono em duas passagens. Ainda não implementado.
- Há 100.554 notas de 18 fundos no dataset; só o ANTECIPE FIDC possui regras fornecidas.
- Decisão do usuário: cada fundo exige configuração própria. Não copiar regras automaticamente para os outros 17. A interface deve informar e resolver as pendências.
- A base cadastral é importada em tabela PostgreSQL por operação administrativa, não por upload de notas no navegador.
- O gabarito contém inconsistências: 712 aprovações do ANTECIPE sem cadastro do sacado e 4.941 aprovações repetidas de chaves no conjunto. Não tratar esse gabarito como execução certificada nem usá-lo como fonte de decisões da interface.
- O frontend pode ser planejado e testado sem esses arquivos. Todas as DTOs necessárias estão neste documento.
- Não implementar login, exportação, cancelamento, edição de decisão, upload do gabarito ou importação cadastral no navegador: não há contrato para essas funções no MVP.

## Convenções gerais

| Assunto | Contrato |
|---|---|
| Base | `/api/v1`; frontend usa `VITE_API_BASE_URL` ou proxy, sem hostname fixo no código |
| JSON | UTF-8, campos em `snake_case`; `Content-Type: application/json` |
| IDs | UUID textual; `NU_DOCUMENTO` é string e não é ID de recurso da API |
| Valores | BRL em strings com ponto e duas casas, por exemplo `"9800.00"`; taxas/percentuais também são strings decimais |
| Datas | Dados de domínio em `YYYY-MM-DD`; instantes em RFC 3339 UTC com `Z`; interface pode formatar em America/Sao_Paulo |
| CNPJ | Fundo/cadastro normalizados com 14 dígitos, preservando zeros; documentos observados nas notas podem estar inválidos e não obedecer ao formato |
| Nulos | Campos de resposta são presentes, inclusive quando `null`. Parâmetros opcionais de query são omitidos, nunca enviados como `"null"` |
| Corpo | Campos desconhecidos são rejeitados. Não enviar corpo em GET nem no POST de processamento |
| Erros | Todas as respostas de erro JSON seguem `ErroResponse`; inclusive erros de validação FastAPI, sem expor formato interno de exceção |
| Correlação | `X-Request-Id` em respostas; `request_id` no corpo de erro |
| Status | HTTP informa transporte/aceitação da operação; status do lote informa processamento assíncrono |
| Autenticação | MVP local de demonstração sem login, token ou multitenancy. Não presumir endpoints de autenticação |
| CORS | Origens do frontend configuradas no backend; permitir Content-Type e Idempotency-Key; expor X-Request-Id, Idempotency-Replayed e Retry-After |

O front não calcula PL, concentração, prazo decisório ou deságio. Formata valores para exibição e apresenta os números retornados. Não usar `Number`/`parseFloat` para cálculos monetários ou para serializar valores de volta à API; preservar strings decimais.

## Mapa completo de operações

Todas as rotas da tabela são relativas a `/api/v1`. IDs nos paths são UUID. `PaginacaoQuery` contém `limit` (1–100, default 50) e `cursor` opcional.

| Método e rota | Query | Request/body | Sucesso | Response |
|---|---|---|---|---|
| GET `/health/live` | — | — | 200 | `SaudeResponse` |
| GET `/health/ready` | — | — | 200 | `SaudeResponse` |
| GET `/capacidades` | — | — | 200 | `CapacidadesResponse` |
| GET `/cadastro/status` | — | — | 200 | `BaseCadastralStatusResponse` |
| GET `/fundos` | `ListarFundosQuery` | — | 200 | `FundosPageResponse` |
| GET `/fundos/{fundo_id}/regras` | `ConsultarRegrasQuery` (`versao` opcional) | — | 200 | `RegrasFundoResponse` |
| PUT `/fundos/{fundo_id}/regras` | — | `AtualizarRegrasRequest` | 200 | `RegrasFundoResponse` |
| GET `/lotes` | `ListarLotesQuery` | — | 200 | `LotesPageResponse` |
| POST `/lotes` | — | `CriarLoteRequest` | 201 | `CriarLoteResponse` |
| GET `/lotes/{lote_id}` | — | — | 200 | `LoteDTO` |
| POST `/lotes/{lote_id}/batches` | — | `EnviarBatchRequest` multipart | 201 | `EnviarBatchResponse` |
| POST `/lotes/{lote_id}/processamento` | — | **Sem corpo** | 202 | `ProcessarLoteResponse` |
| GET `/lotes/{lote_id}/arquivos` | `PaginacaoQuery` | — | 200 | `ArquivosPageResponse` |
| GET `/lotes/{lote_id}/pendencias` | `PaginacaoQuery` | — | 200 | `PendenciasPageResponse` |
| GET `/lotes/{lote_id}/resumos-fundos` | `PaginacaoQuery` | — | 200 | `ResumosFundosPageResponse` |
| GET `/arquivos/{arquivo_id}` | — | — | 200 | `ArquivoDTO` |
| GET `/arquivos/{arquivo_id}/resultados` | `ListarResultadosQuery` | — | 200 | `ResultadosPageResponse` |

`Idempotency-Key: <UUID>` é obrigatório em POST de criação, batches, processamento e PUT de regras. As respostas exatas de erro por operação estão no OpenAPI.

Em `ListarFundosQuery`, `busca` compara substring do nome sem distinguir caixa; quando a busca contém apenas dígitos/máscara de CNPJ, também compara prefixo do CNPJ normalizado. `configurado` filtra presença de versão ativa. `ListarLotesQuery.status` aceita um estado por requisição. Não existem filtros adicionais implícitos.

Os códigos 201 de criação/upload e 202 de processamento são intencionais: upload confirmado não significa título aprovado. `GET /fundos/{id}/regras` retorna 404 quando o fundo existe, mas ainda não tem configuração. O front identifica esse caso pelo `FundoDTO.configurado=false`.

Não há endpoint para enviar o gabarito ao motor, editar decisão de nota, cancelar lote, exportar resultados, importar cadastro pelo navegador ou excluir histórico no MVP. A carga cadastral e a carga inicial de regras são operações administrativas CLI. Não planejar botões para funcionalidades ausentes.

## Fluxo 1 — Criar e enviar um lote

1. Consultar `/capacidades` e `/cadastro/status`. A capacidade do MVP é 100 arquivos por lote, até 3 por batch, 64 MiB por arquivo e por soma de binários do batch, 500.000 linhas de dados por lote e 100 itens por página. Polling sugerido: 2.000 ms. Configuração de infraestrutura pode ser mais restritiva somente com nova capacidade publicada antes do upload.
2. Usuário escolhe `.csv` ou `.xlsx`. O ZIP fornecido é embalagem do dataset; deve ser extraído antes da seleção. O sistema não recebe ZIP no endpoint de notas.
3. O front gera `client_id` UUID por arquivo, calcula SHA-256 sobre os bytes originais e envia manifesto em `CriarLoteRequest`. `ordem` é contígua de 0 a N−1, independente da ordem de chegada dos batches. Nomes repetidos são permitidos porque a identidade é o ID, não o nome.
4. `CriarLoteResponse` retorna o lote em `RECEBENDO` e todos os IDs de arquivo. Guardar o mapa `client_id → id` e as chaves idempotentes para retry. O manifesto é imutável; para alterar bytes, hash, tamanho ou seleção, criar novo lote.
5. Dividir arquivos em batches respeitando quantidade e bytes. Um arquivo não é dividido entre requisições. Até duas requisições simultâneas de upload no cliente é a configuração inicial; a ordem final continua sendo a do manifesto.
6. Atualizar progresso de transferência por eventos do cliente HTTP/XHR. O backend não informa cada byte em trânsito; `bytes_recebidos` informa somente arquivo confirmado integralmente.
7. Com todos os arquivos recebidos, chamar `POST /lotes/{id}/processamento`, sem corpo, usando uma chave de operação própria.

### Multipart sem ambiguidade

`metadados` é um campo textual contendo JSON serializado de `BatchMetadadosDTO`. `arquivos` é uma sequência de partes binárias com o mesmo nome. A posição da parte deve coincidir com a posição em `arquivo_ids`. A implementação FastAPI recebe `metadados` como string de formulário e `arquivos` como lista de uploads, então valida o JSON de metadados.

```typescript
const form = new FormData();
form.append("metadados", JSON.stringify({ arquivo_ids: batch.map(x => x.arquivo_id) }));
for (const item of batch) form.append("arquivos", item.file, item.file.name);
await fetch(`${apiBase}/lotes/${loteId}/batches`, {
  method: "POST",
  headers: { "Idempotency-Key": chavePersistidaDoBatch },
  body: form,
}); // Não definir Content-Type manualmente: o navegador inclui o boundary.
```

O batch é atômico na confirmação: todos os arquivos são recebidos ou nenhum fica confirmado. Validar hash, tamanho, identidade e extensão/estrutura do container. Se cair a conexão, consultar arquivos e repetir a mesma requisição/chave; staging temporário não é confirmação. Falha de parsing de CSV/XLSX após upload é erro de processamento, não de transporte.

O limite de 67.108.864 bytes considera a soma dos conteúdos binários. Configurar proxy/servidor para aceitar também até 1 MiB de overhead multipart, mantendo a validação exata no adaptador. Um arquivo que exceda o limite não deve ser fatiado pelo front como solução improvisada.

## Fluxo 2 — Processar, configurar pendências e retomar

```text
RECEBENDO -- POST processamento --> NA_FILA --> INDEXANDO
INDEXANDO --> BLOQUEADO     (fundo sem regras, base ausente ou dado que impede PL)
INDEXANDO --> ANALISANDO    (estrutura, PL, cadastro e regras prontos)
BLOQUEADO -- POST processamento --> NA_FILA  (após correção recuperável)
ANALISANDO --> CONCLUIDO | CONCLUIDO_COM_ERROS | FALHOU
FALHOU -- POST processamento --> NA_FILA     (somente acoes.pode_retomar=true)
```

`NA_FILA` pode voltar diretamente à `ANALISANDO` em recuperação com indexação/contexto já persistidos. Falhas técnicas podem ocorrer também na fila/indexação. Consultar `acoes` para habilitar botões, sem derivar permissões somente do status.

- **CONCLUIDO:** todos os arquivos elegíveis finalizados, sem erros técnicos/de parsing. Notas `BARRADO` são resultados normais e não tornam o lote defeituoso.
- **CONCLUIDO_COM_ERROS:** outros arquivos/linhas foram processados, mas houve arquivo estruturalmente falho ou diagnóstico `ERRO_DADOS`.
- **FALHOU:** falha técnica ou nenhum arquivo utilizável. `erro.retry_permitido` e `acoes.pode_retomar` orientam recuperação.
- **BLOQUEADO:** worker terminou a preparação e precisa de ação. Parar polling contínuo, buscar pendências e exibir ações. O usuário retoma explicitamente.

O worker descobre os fundos pelos documentos dos arquivos, cadastra identidades sem copiar regras e verifica todos antes da primeira aprovação. **Decisão confirmada pelo usuário: cada um dos 18 fundos exige configuração própria.** `PendenciaDTO` contém fundo/id/CNPJ e `acao=CONFIGURAR_FUNDO`. Nenhuma nota é aprovada antes de resolver as configurações de todos os fundos dos arquivos utilizáveis do lote.

Para resolver: `GET /fundos` ou usar o fundo da pendência → `PUT /fundos/{id}/regras` → repetir para os pendentes → `POST /lotes/{id}/processamento` com **nova chave**. O backend revalida os pré-requisitos; não confiar apenas no estado da tela.

**Congelamento:** versões das regras e cadastro são fixadas atomicamente na primeira transição para `ANALISANDO`. Até esse ponto, o lote pode resolver configurações ausentes. Depois, mudanças são aplicadas apenas a lotes ainda não iniciados em análise. Retry do mesmo job usa o contexto original e checkpoints. `ResumoFundoDTO.versao_regras_utilizada` permite consultar a versão histórica via `GET .../regras?versao=...`.

**Base cadastral:** carregar em tabela PostgreSQL indexada por CNPJ textual, via CLI, antes da análise. Reimportação idêntica não duplica registros; conflito de situações no mesmo arquivo é erro de carga. No MVP, impedir publicação de nova base enquanto um lote usar a atual, inclusive lote com falha recuperável. Recuperar ou encerrar administrativamente esses jobs antes de substituir a carga. Base disponível com CNPJ ausente é recusa cadastral normal, não bloqueio de configuração.

### Progresso e recuperação

Em `NA_FILA`, `INDEXANDO` e `ANALISANDO`, consultar `GET /lotes/{id}` a cada 2 segundos enquanto a tela estiver visível. Suspender ao desmontar a tela, ocultar a aba ou entrar em estado terminal/bloqueado. Backoff de falhas de rede: 2, 4, 8 e até 30 segundos; respeitar `Retry-After`. Retomar consulta imediata ao voltar à tela.

`linhas_total=null` enquanto a indexação não termina: mostrar progresso indeterminado. Usar contadores distintos das duas passagens; não exibir 200% nem inventar uma estimativa de tempo. `linhas_processadas` conta decisões ou diagnósticos persistidos; o worker não incrementa progresso antes do commit.

Após indexação, `linhas_total` contabiliza linhas não vazias dos arquivos estruturalmente utilizáveis, incluindo erros de dados. Arquivos com estrutura falha ficam fora desse denominador. O limite de 500.000 linhas é verificado na preparação, contando linhas não vazias lidas; excesso gera FALHOU com LIMITE_LOTE_EXCEDIDO e necessidade de novo lote menor, antes de qualquer aprovação.

Nenhum retry de worker transforma uma aprovação já persistida pelo próprio job em `NOTA_DUPLICADA`. O resultado existente é recuperado. Em um **novo lote**, a mesma chave já aprovada deve ser barrada.

## Fluxo 3 — Regras dinâmicas e edição concorrente

`AtualizarRegrasRequest` contém `versao_base` e a configuração completa. Usar `versao_base=null` apenas na primeira configuração; depois, enviar a versão lida no GET. Se outra edição venceu, servidor retorna 409 `VERSAO_REGRAS_CONFLITANTE` com `versao_atual`; recarregar e pedir ao usuário que revise o formulário, sem sobrescrever automaticamente.

Os nove validadores são uma union discriminada por `codigo`; `parametros` não é um dicionário livre. Todos os nove devem aparecer exatamente uma vez, inclusive inativos. `NOTA_DUPLICADA` não tem toggle. Campos e estados do formulário vêm dos tipos do contrato, não dos nomes internos do Python.

| Código | Parâmetros HTTP | Valores iniciais do arquivo entregue |
|---|---|---|
| CNPJ_SACADO_VALIDO | `{}` | ativo |
| SITUACAO_CADASTRAL_SACADO | `situacoes_aceitas: string[]` | ativo, `["ATIVA"]` |
| TIPO_RECEBIVEL | `tipos_aceitos: string[]` | ativo, `["Duplicata", "Duplicata de Serviço"]` |
| VALOR_MINIMO | `valor_minimo: string decimal` | ativo, `"100.0"` |
| NAO_VENCIDA | `{}` | ativo |
| PRAZO_MINIMO | `prazo_minimo_dias: integer >= 0` | inativo, 30 |
| PRAZO_MAXIMO | `prazo_maximo_dias: integer >= 0` | ativo, 180 |
| CONCENTRACAO_MAXIMA_SACADO | `percentual_maximo: string decimal`, `agrupamento: "RAIZ_CNPJ"` | ativo, `"10.0"` |
| CONCENTRACAO_MAXIMA_CEDENTE | mesmos campos de concentração | inativo, `"8.0"` |

`precificacao` exige `metodo="DESCONTO_SIMPLES"`, taxa mensal percentual decimal não negativa e `base_dias` inteira de 1 a 366. Percentual de concentração fica entre 0 e 100; duplicação de códigos e parâmetros incoerentes são 422. Alterar `ativo` não apaga os parâmetros.

O JSON entregue é um **contrato de importação**, não o corpo HTTP direto: o importador lê números com `Decimal`, identifica o fundo pela raiz `fundo.cnpj`, completa `agrupamento=RAIZ_CNPJ` no cedente e publica strings decimais na API. Isso preserva os valores sem exigir que o frontend adivinhe diferenças entre formatos.

## Fluxo 4 — Resultados, filtros e tabelas

`GET /arquivos/{id}/resultados` recebe `limit`, `cursor`, `status`, `motivo` e `tipo`. Filtros combinam com AND. `tipo=ERRO_DADOS` não pode ser combinado com status financeiro ou motivo; `status=APROVADO` com motivo também retorna 422.

`ResultadoDTO` é uma union explícita:

| Variante | tipo | status | titulo | motivos | erros_dados |
|---|---|---|---|---|---|
| ResultadoAprovadoDTO | ANALISE | APROVADO | normalizado | vazio | vazio |
| ResultadoBarradoDTO | ANALISE | BARRADO | normalizado | um ou mais | vazio |
| ResultadoErroDadosDTO | ERRO_DADOS | null | null | vazio | um ou mais |

`ERRO_DADOS` é diagnóstico de ingestão, não um terceiro status de decisão financeira. Exibir badge próprio e valores originais, sem atribuir um código FIDC inventado. Em barrados e erros de dados, desconto e líquido são `"0.00"`. `MotivoDTO` fornece código, mensagem pronta e valores textuais observados/limites para explicação. Não usar mensagens como identificadores de filtro.

Cada resultado contém `id` UUID, `arquivo_id`, `lote_id`, `sequencia`, `linha` e as onze colunas originais. `linha` considera o cabeçalho como linha 1; em XLSX preserva o número físico da linha na aba. `nu_documento` preserva zeros e hífens. Linhas completamente vazias são ignoradas sem renumerar as posteriores.

### Semântica de cursor

- Ordenar resultados por sequência persistida que respeite a ordem das linhas de origem. Na primeira página, capturar o maior valor disponível em `snapshot_ate_sequencia`.
- Cursor opaco, autenticado pelo servidor, contém arquivo, filtros, limit, último item e teto do snapshot. Nas próximas páginas, front repete os mesmos filtros/limit e envia o cursor.
- O teto não muda durante essa navegação. Novos resultados aparecem quando o usuário atualiza a primeira página. Nenhum resultado confirmado é editado durante a navegação.
- Diagnósticos descobertos na primeira passagem ficam em staging e, quando houver análise, são publicados junto aos resultados na ordem de origem. Não publicar uma linha alta antes de inserir linhas anteriores dentro do teto já exposto. Em lote bloqueado, detalhes impeditivos são expostos por pendências, sem decisões financeiras parciais.
- `proximo_cursor=null` indica fim do snapshot; `arquivo_finalizado=false` indica que poderão surgir resultados posteriormente.
- Trocar filtro ou page size limpa a pilha de cursores. Para voltar, o front guarda cursores das páginas anteriores. Não há offset, salto arbitrário para página N ou total de páginas conhecido.
- QTable deve usar controles anterior/próxima e carregamento remoto; não inventar `rowsNumber` como total filtrado. Contagens de cards vêm do resumo, não da quantidade da página.

Listagens auxiliares usam cursor e ordenação estável: fundos por `(cnpj,id)`, lotes por `(criado_em DESC,id DESC)`, arquivos por `(ordem,id)`, resumos por `(cnpj,id)` e pendências por `(codigo,fundo_id,arquivo_id,linha)` com nulos ordenados primeiro e desempate interno. Cursores de pendências tornam-se inválidos quando muda o conjunto de bloqueios: reiniciar a listagem após retomar. Histórico fixa o teto da primeira página; campos de status/progresso podem atualizar, sem prometer snapshot transacional dessas colunas.

## Precisão e consistência do domínio

- Calcular desconto simples com Decimal e precisão interna de 38 dígitos. Não quantizar taxa diária; calcular desconto como `(nominal * taxa_mensal * prazo) / (100 * base_dias)` para evitar arredondamento intermediário desnecessário. Quantizar desconto a centavos com `ROUND_HALF_UP` no fechamento da nota e calcular líquido por diferença.
- Somar os valores monetários já fechados das notas nos resumos. Para aprovados, `nominal = desconto + líquido`; barrados não têm deságio financeiro.
- O PDF não estabelece trava adicional para líquido negativo ou prazo negativo quando suas regras estão desativadas. O motor aplica a fórmula e regras ativas literalmente: valores negativos podem aparecer, sem clamp silencioso e sem código novo. O frontend preserva sinal. Nova regra financeira exigirá revisão explícita do domínio/contrato.
- PL usa todas as notas com nominal/fundo interpretáveis dos arquivos estruturalmente utilizáveis, inclusive as posteriormente barradas ou com outros erros de dados. Erro de data não altera silenciosamente esse PL.
- Nominal ou identidade do fundo ilegíveis impedem apurar PL confiável: registrar diagnóstico e bloquear o lote **antes de qualquer aprovação**, com `DADOS_IMPEDEM_PL` e `acao=RECRIAR_LOTE`. O arquivo original é imutável; corrigir e criar novo lote. Não substituir nominal ilegível por zero ou processar com PL parcial.
- Arquivo com cabeçalho inválido/corrompido fica `FALHOU`; descartar sua contribuição parcial de PL. Os demais arquivos podem prosseguir, tornando o lote `CONCLUIDO_COM_ERROS`; se nenhum for utilizável, lote `FALHOU`.
- CNPJ com DV inválido é dado interpretável e recebe a regra oficial quando ativa. Documento sem raiz utilizável, se necessário à concentração, produz diagnóstico de dado; não fabricar uma raiz. Duplicidade operacional continua sendo verificada antes das regras nos títulos interpretáveis.
- `linhas_processadas = aprovadas + barradas + erros_dados`. Ao concluir análise de arquivos utilizáveis, `total_nominal = total_nominal_aprovado + total_nominal_barrado + total_nominal_erro_dados`. Enquanto a análise avança, os três subtotais ainda não precisam somar o PL completo. Em bloqueio por PL ilegível, os totais são apenas parciais e `definitivo=false`.

## Idempotência, erros e retry

Escopo da chave: método + caminho + `Idempotency-Key`. Corpo/conteúdo diferente com mesma chave retorna 409 `IDEMPOTENCIA_CONFLITANTE`. Em upload, fingerprint inclui metadados e hashes dos binários, nunca o boundary aleatório do multipart. Repetir sucesso devolve o status/corpo originais e `Idempotency-Replayed: true`; usar GET para obter estado atual.

Reter chaves de lote/upload/processamento pela vida do lote; chaves de edição de regras por no mínimo 24 horas. Requisição equivalente ainda em andamento: 409 `REQUISICAO_EM_ANDAMENTO` com `Retry-After`. Falhas transitórias sem confirmação não ficam cacheadas como sucesso. Nova ação após corrigir configuração usa nova chave; retry por perda de resposta usa a mesma.

| HTTP | Situação | Ação do frontend |
|---|---|---|
| 400 | Cursor/metadados malformados | Corrigir request; cursor inválido reinicia primeira página |
| 404 | Recurso/versão inexistente | Mostrar indisponibilidade; configuração inicial usa `configurado=false` |
| 409 | Estado, versão, idempotência ou operação concorrente | Reconsultar estado; tratar código específico, sem retry cego |
| 413 | Excesso de bytes/quantidade no upload | Reagrupar batches; arquivo acima do máximo exige outra entrada |
| 415 | Mídia não suportada | Selecionar CSV/XLSX ou corrigir Content-Type |
| 422 | Campo/parâmetro/regra inválidos | Associar `erro.detalhes[].campo` ao formulário |
| 500/503 | Erro inesperado/infraestrutura | Mostrar request_id; retry apenas conforme `retry_permitido` e Retry-After |

Erros do worker são persistidos em `LoteDTO.erro`/`ArquivoDTO.erro`, sem mudar um polling bem-sucedido de 200 para 500. O cliente deve diferenciar erro de GET do estado `FALHOU` retornado normalmente pelo GET.

## Testes compartilhados obrigatórios

1. Validar OpenAPI, resolver todas as referências e validar exemplos contra os schemas antes de implementar.
2. Backend: DTOs não aceitam propriedades desconhecidas; tipos, nulos, limites, unions, decimais e códigos HTTP respeitam o contrato. Parametrizar os 17 operationIds.
3. Frontend: mocks usam os tipos e fixtures fornecidos; testar upload multipart com arquivos de mesmo nome, retry, bloqueio por fundos sem regras, edição concorrente, estados vazios/erro e tabela por cursor.
4. Integração real: manifesto → upload → indexação → bloqueio por 17 configurações ausentes → configuração explícita → retomada → polling → filtros/resultados. Rodar em banco limpo; nunca obter resultados esperados do gabarito dentro do motor.
5. Regressão: round-trip Decimal/string; CNPJ e documento com zeros; mudança de regras após snapshot; retry após commit; navegação durante processamento; todos os erros de validação no mesmo envelope.
6. CI: verificar que regeneração do contrato não cria diff inesperado e que OpenAPI emitido por FastAPI é compatível com o contrato acordado. Divergência não pode ser corrigida só no front ou só no back.


## OpenAPI completo — todas as operações e todos os schemas de DTO

O bloco abaixo é JSON válido e autocontido. Os `$ref` são referências internas ao próprio bloco (`#/components/schemas/...`), não a arquivos externos. Os DTOs de query, corpos de request, responses, erros, enums e variantes estão todos em `components.schemas`. Não omitir propriedades ao gerar os tipos. Campos opcionais e campos `null` são conceitos diferentes.

```json
{
  "openapi": "3.1.0",
  "info": {"title":"Antecipe — Contrato backend/frontend","version":"1.0.0","description":"Contrato de projeto; implementação ainda pendente. Fonte editável: scripts/gerar_contrato_api.py. Complementado por docs/contrato-api.md. Ambiente MVP de demonstração, sem autenticação. Não representa serviço publicado."},
  "servers": [{"url":"/api/v1","description":"Usar proxy de desenvolvimento ou VITE_API_BASE_URL."}],
  "security": [],
  "paths": {
  "/health/live": {"get":{"operationId":"verificarVida","summary":"Verificar processo","description":"","tags":["health"],"parameters":[],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/SaudeResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/health/ready": {"get":{"operationId":"verificarProntidao","summary":"Verificar banco e armazenamento","description":"","tags":["health"],"parameters":[],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/SaudeResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/capacidades": {"get":{"operationId":"obterCapacidades","summary":"Limites e recursos do MVP","description":"","tags":["capacidades"],"parameters":[],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/CapacidadesResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/cadastro/status": {"get":{"operationId":"obterStatusCadastro","summary":"Disponibilidade da base cadastral","description":"","tags":["cadastro"],"parameters":[],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/BaseCadastralStatusResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/fundos": {"get":{"operationId":"listarFundos","summary":"Listar fundos cadastrados ou descobertos no estoque","description":"","tags":["fundos"],"parameters":[{"name":"limit","in":"query","required":false,"schema":{"type":"integer","minimum":1,"maximum":100,"default":50}},{"name":"cursor","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":4096}},{"name":"busca","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":120}},{"name":"configurado","in":"query","required":false,"schema":{"type":"boolean"}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/FundosPageResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/fundos/{fundo_id}/regras": {"get":{"operationId":"consultarRegrasFundo","summary":"Consultar versão atual ou histórica das regras","description":"","tags":["fundos"],"parameters":[{"name":"fundo_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"versao","in":"query","required":false,"schema":{"type":"string","format":"uuid"}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/RegrasFundoResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}},"put":{"operationId":"atualizarRegrasFundo","summary":"Configurar um fundo ou publicar nova versão","description":"Primeira configuração e atualização retornam 200. Não copia regras para outros fundos. Verifica versao_base; conflito retorna 409. Lote que já começou análise mantém seu snapshot.","tags":["fundos"],"parameters":[{"name":"fundo_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"Idempotency-Key","in":"header","required":true,"schema":{"type":"string","format":"uuid"},"description":"UUID por operação lógica; repetir em retry do mesmo conteúdo. Escopo método + caminho + chave; retenção durante toda a vida do lote (regras: mínima de 24h)."}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."},"Idempotency-Replayed":{"schema":{"type":"boolean"},"description":"true quando devolve o corpo/status originalmente persistidos."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/RegrasFundoResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"409":{"description":"Conflito de estado, idempotência ou versão.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"415":{"description":"Tipo de mídia não suportado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}},"requestBody":{"required":true,"content":{"application/json":{"schema":{"$ref":"#/components/schemas/AtualizarRegrasRequest"}}}}}},
  "/lotes": {"get":{"operationId":"listarLotes","summary":"Histórico de lotes","description":"","tags":["lotes"],"parameters":[{"name":"limit","in":"query","required":false,"schema":{"type":"integer","minimum":1,"maximum":100,"default":50}},{"name":"cursor","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":4096}},{"name":"status","in":"query","required":false,"schema":{"$ref":"#/components/schemas/StatusLote"}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/LotesPageResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}},"post":{"operationId":"criarLote","summary":"Criar manifesto imutável","description":"","tags":["lotes"],"parameters":[{"name":"Idempotency-Key","in":"header","required":true,"schema":{"type":"string","format":"uuid"},"description":"UUID por operação lógica; repetir em retry do mesmo conteúdo. Escopo método + caminho + chave; retenção durante toda a vida do lote (regras: mínima de 24h)."}],"responses":{"201":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."},"Idempotency-Replayed":{"schema":{"type":"boolean"},"description":"true quando devolve o corpo/status originalmente persistidos."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/CriarLoteResponse"}}}},"409":{"description":"Conflito de estado, idempotência ou versão.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"415":{"description":"Tipo de mídia não suportado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}},"requestBody":{"required":true,"content":{"application/json":{"schema":{"$ref":"#/components/schemas/CriarLoteRequest"}}}}}},
  "/lotes/{lote_id}": {"get":{"operationId":"consultarLote","summary":"Estado, progresso, resumo e ações disponíveis","description":"","tags":["lotes"],"parameters":[{"name":"lote_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/LoteDTO"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/lotes/{lote_id}/batches": {"post":{"operationId":"enviarBatch","summary":"Receber até três arquivos, atomicamente","description":"Até 67108864 bytes somados de conteúdo binário, sem overhead multipart. Formatos CSV/XLSX; ZIP não é upload válido. Metadados JSON string com arquivo_ids na ordem das partes arquivos. Aceita somente lote RECEBENDO. Todos os arquivos deste batch são confirmados ou nenhum é confirmado.","tags":["lotes"],"parameters":[{"name":"lote_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"Idempotency-Key","in":"header","required":true,"schema":{"type":"string","format":"uuid"},"description":"UUID por operação lógica; repetir em retry do mesmo conteúdo. Escopo método + caminho + chave; retenção durante toda a vida do lote (regras: mínima de 24h)."}],"responses":{"201":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."},"Idempotency-Replayed":{"schema":{"type":"boolean"},"description":"true quando devolve o corpo/status originalmente persistidos."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/EnviarBatchResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"409":{"description":"Conflito de estado, idempotência ou versão.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"413":{"description":"Limite de upload excedido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"415":{"description":"Tipo de mídia não suportado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}},"requestBody":{"required":true,"content":{"multipart/form-data":{"schema":{"$ref":"#/components/schemas/EnviarBatchRequest"},"encoding":{"metadados":{"contentType":"text/plain"},"arquivos":{"style":"form","explode":true}}}}}}},
  "/lotes/{lote_id}/processamento": {"post":{"operationId":"solicitarProcessamento","summary":"Selar uploads e iniciar ou retomar o worker","description":"Sem corpo. Inicialmente exige todos os arquivos recebidos. Em BLOQUEADO permite nova tentativa após correção de cadastro/regras; em FALHOU somente se acoes.pode_retomar. Nunca descarta aprovações já persistidas. Não espera análise no HTTP.","tags":["lotes"],"parameters":[{"name":"lote_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"Idempotency-Key","in":"header","required":true,"schema":{"type":"string","format":"uuid"},"description":"UUID por operação lógica; repetir em retry do mesmo conteúdo. Escopo método + caminho + chave; retenção durante toda a vida do lote (regras: mínima de 24h)."}],"responses":{"202":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."},"Idempotency-Replayed":{"schema":{"type":"boolean"},"description":"true quando devolve o corpo/status originalmente persistidos."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ProcessarLoteResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"409":{"description":"Conflito de estado, idempotência ou versão.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/lotes/{lote_id}/arquivos": {"get":{"operationId":"listarArquivosLote","summary":"Listar arquivos em ordem de manifesto","description":"","tags":["lotes"],"parameters":[{"name":"lote_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"limit","in":"query","required":false,"schema":{"type":"integer","minimum":1,"maximum":100,"default":50}},{"name":"cursor","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":4096}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ArquivosPageResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/lotes/{lote_id}/pendencias": {"get":{"operationId":"listarPendenciasLote","summary":"Listar bloqueios com ação requerida","description":"","tags":["lotes"],"parameters":[{"name":"lote_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"limit","in":"query","required":false,"schema":{"type":"integer","minimum":1,"maximum":100,"default":50}},{"name":"cursor","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":4096}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/PendenciasPageResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/lotes/{lote_id}/resumos-fundos": {"get":{"operationId":"listarResumosFundos","summary":"Consultar PL e resumo por fundo","description":"","tags":["lotes"],"parameters":[{"name":"lote_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"limit","in":"query","required":false,"schema":{"type":"integer","minimum":1,"maximum":100,"default":50}},{"name":"cursor","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":4096}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ResumosFundosPageResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/arquivos/{arquivo_id}": {"get":{"operationId":"consultarArquivo","summary":"Consultar estado de um arquivo","description":"","tags":["arquivos"],"parameters":[{"name":"arquivo_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ArquivoDTO"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}},
  "/arquivos/{arquivo_id}/resultados": {"get":{"operationId":"listarResultados","summary":"Consultar resultados e diagnósticos por cursor","description":"Filtros combinados com AND. motivo seleciona barramentos. tipo=ERRO_DADOS com status/motivo é inválido (422); APROVADO com motivo também. Cursor não pode ser reutilizado com outro arquivo, filtros ou limit.","tags":["arquivos"],"parameters":[{"name":"arquivo_id","in":"path","required":true,"schema":{"type":"string","format":"uuid"}},{"name":"limit","in":"query","required":false,"schema":{"type":"integer","minimum":1,"maximum":100,"default":50}},{"name":"cursor","in":"query","required":false,"schema":{"type":"string","minLength":1,"maxLength":4096}},{"name":"status","in":"query","required":false,"schema":{"$ref":"#/components/schemas/StatusNota"}},{"name":"motivo","in":"query","required":false,"schema":{"$ref":"#/components/schemas/CodigoRecusa"}},{"name":"tipo","in":"query","required":false,"schema":{"type":"string","enum":["ANALISE","ERRO_DADOS"]}}],"responses":{"200":{"description":"Sucesso.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"},"description":"Identificador de correlação da requisição atual."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ResultadosPageResponse"}}}},"400":{"description":"Requisição ou cursor inválido.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"404":{"description":"Recurso ou versão não encontrado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"422":{"description":"Falha de validação do contrato.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"500":{"description":"Erro inesperado.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}},"503":{"description":"Infraestrutura indisponível; observar Retry-After quando presente.","headers":{"X-Request-Id":{"schema":{"type":"string","format":"uuid"}},"Retry-After":{"schema":{"type":"integer","minimum":0},"description":"Segundos; somente quando retry automático for apropriado."}},"content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErroResponse"}}}}}}}
},
  "components": {"schemas":{
  "Dinheiro": {"type":"string","description":"Decimal em BRL, ponto e duas casas; nunca JSON number.","pattern":"^-?(0|[1-9][0-9]*)\\.[0-9]{2}$","examples":["2278.08"]},
  "DecimalNaoNegativo": {"type":"string","description":"Decimal exato não negativo; até 8 casas, sem notação científica.","pattern":"^(0|[1-9][0-9]*)(\\.[0-9]{1,8})?$","examples":["2.0"]},
  "CodigoRecusa": {"type":"string","enum":["NOTA_DUPLICADA","CNPJ_SACADO_VALIDO","SITUACAO_CADASTRAL_SACADO","TIPO_RECEBIVEL","VALOR_MINIMO","NAO_VENCIDA","PRAZO_MINIMO","PRAZO_MAXIMO","CONCENTRACAO_MAXIMA_SACADO","CONCENTRACAO_MAXIMA_CEDENTE"]},
  "StatusNota": {"type":"string","enum":["APROVADO","BARRADO"]},
  "StatusLote": {"type":"string","enum":["RECEBENDO","NA_FILA","INDEXANDO","BLOQUEADO","ANALISANDO","CONCLUIDO","CONCLUIDO_COM_ERROS","FALHOU"]},
  "StatusArquivo": {"type":"string","enum":["AGUARDANDO_UPLOAD","RECEBIDO","INDEXANDO","PRONTO","ANALISANDO","CONCLUIDO","CONCLUIDO_COM_ERROS","FALHOU"]},
  "FormatoArquivo": {"type":"string","enum":["CSV","XLSX"]},
  "CodigoErro": {"type":"string","enum":["VALIDACAO_REQUISICAO","RECURSO_NAO_ENCONTRADO","ESTADO_INVALIDO","IDEMPOTENCIA_CONFLITANTE","REQUISICAO_EM_ANDAMENTO","UPLOAD_INCOMPLETO","LIMITE_UPLOAD_EXCEDIDO","LIMITE_LOTE_EXCEDIDO","TIPO_ARQUIVO_NAO_SUPORTADO","INTEGRIDADE_ARQUIVO","ARQUIVO_FORA_MANIFESTO","ARQUIVO_JA_RECEBIDO","CURSOR_INVALIDO","VERSAO_REGRAS_CONFLITANTE","CONFIGURACAO_INVALIDA","ESTRUTURA_ARQUIVO_INVALIDA","ARQUIVO_CORROMPIDO","DADOS_IMPEDEM_PL","FUNDOS_SEM_REGRAS","BASE_CADASTRAL_INDISPONIVEL","INFRAESTRUTURA_INDISPONIVEL","ERRO_INTERNO"]},
  "DetalheErroDTO": {"type":"object","additionalProperties":false,"properties":{"campo":{"anyOf":[{"type":"string","description":"JSON Pointer no corpo, ou query.nome/header.nome; null para erro geral."},{"type":"null"}]},"codigo":{"type":"string"},"mensagem":{"type":"string"}},"required":["campo","codigo","mensagem"]},
  "ErroDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"$ref":"#/components/schemas/CodigoErro"},"mensagem":{"type":"string"},"retry_permitido":{"type":"boolean"},"detalhes":{"type":"array","items":{"$ref":"#/components/schemas/DetalheErroDTO"}},"versao_atual":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]}},"required":["codigo","mensagem","retry_permitido","detalhes","versao_atual"]},
  "ErroResponse": {"type":"object","additionalProperties":false,"properties":{"request_id":{"type":"string","format":"uuid"},"erro":{"$ref":"#/components/schemas/ErroDTO"}},"required":["request_id","erro"]},
  "SaudeResponse": {"type":"object","additionalProperties":false,"properties":{"status":{"type":"string","enum":["OK"]},"servico":{"type":"string","enum":["antecipe-api"]},"versao_api":{"type":"string","enum":["1.0.0"]},"verificado_em":{"type":"string","format":"date-time"}},"required":["status","servico","versao_api","verificado_em"]},
  "CapacidadesResponse": {"type":"object","additionalProperties":false,"properties":{"versao_contrato":{"type":"string","enum":["1.0.0"]},"autenticacao":{"type":"string","enum":["SEM_AUTENTICACAO_DEMO"]},"formatos":{"type":"array","items":{"$ref":"#/components/schemas/FormatoArquivo"}},"max_arquivos_lote":{"type":"integer","minimum":1},"max_arquivos_batch":{"type":"integer","minimum":1},"max_bytes_arquivo":{"type":"integer","minimum":1},"max_bytes_batch":{"type":"integer","minimum":1},"max_linhas_lote":{"type":"integer","minimum":1},"max_pagina":{"type":"integer","minimum":1},"polling_intervalo_ms":{"type":"integer","minimum":1000},"permite_exportacao":{"type":"boolean"},"permite_cancelamento":{"type":"boolean"}},"required":["versao_contrato","autenticacao","formatos","max_arquivos_lote","max_arquivos_batch","max_bytes_arquivo","max_bytes_batch","max_linhas_lote","max_pagina","polling_intervalo_ms","permite_exportacao","permite_cancelamento"]},
  "BaseCadastralStatusResponse": {"type":"object","additionalProperties":false,"properties":{"disponivel":{"type":"boolean"},"versao":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]},"sha256":{"anyOf":[{"type":"string","pattern":"^[a-f0-9]{64}$"},{"type":"null"}]},"quantidade_cnpjs":{"type":"integer","minimum":0},"importado_em":{"anyOf":[{"type":"string","format":"date-time"},{"type":"null"}]}},"required":["disponivel","versao","sha256","quantidade_cnpjs","importado_em"]},
  "FundoDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"nome":{"type":"string"},"cnpj":{"type":"string","pattern":"^[0-9]{14}$"},"configurado":{"type":"boolean"},"versao_regras_atual":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]}},"required":["id","nome","cnpj","configurado","versao_regras_atual"]},
  "ParametrosVaziosDTO": {"type":"object","additionalProperties":false,"properties":{},"required":[]},
  "ParametrosSituacaoDTO": {"type":"object","additionalProperties":false,"properties":{"situacoes_aceitas":{"type":"array","items":{"type":"string","minLength":1},"minItems":1,"uniqueItems":true}},"required":["situacoes_aceitas"]},
  "ParametrosTipoDTO": {"type":"object","additionalProperties":false,"properties":{"tipos_aceitos":{"type":"array","items":{"type":"string","minLength":1},"minItems":1,"uniqueItems":true}},"required":["tipos_aceitos"]},
  "ParametrosValorMinimoDTO": {"type":"object","additionalProperties":false,"properties":{"valor_minimo":{"$ref":"#/components/schemas/DecimalNaoNegativo"}},"required":["valor_minimo"]},
  "ParametrosPrazoMinimoDTO": {"type":"object","additionalProperties":false,"properties":{"prazo_minimo_dias":{"type":"integer","minimum":0}},"required":["prazo_minimo_dias"]},
  "ParametrosPrazoMaximoDTO": {"type":"object","additionalProperties":false,"properties":{"prazo_maximo_dias":{"type":"integer","minimum":0}},"required":["prazo_maximo_dias"]},
  "ParametrosConcentracaoDTO": {"type":"object","additionalProperties":false,"properties":{"percentual_maximo":{"$ref":"#/components/schemas/DecimalNaoNegativo","description":"Entre 0 e 100, inclusive; limite semântico validado pelo servidor."},"agrupamento":{"type":"string","enum":["RAIZ_CNPJ"]}},"required":["percentual_maximo","agrupamento"]},
  "ValidadorCnpjSacadoValidoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["CNPJ_SACADO_VALIDO"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosVaziosDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorSituacaoCadastralSacadoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["SITUACAO_CADASTRAL_SACADO"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosSituacaoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorTipoRecebivelDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["TIPO_RECEBIVEL"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosTipoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorValorMinimoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["VALOR_MINIMO"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosValorMinimoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorNaoVencidaDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["NAO_VENCIDA"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosVaziosDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorPrazoMinimoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["PRAZO_MINIMO"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosPrazoMinimoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorPrazoMaximoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["PRAZO_MAXIMO"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosPrazoMaximoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorConcentracaoMaximaSacadoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["CONCENTRACAO_MAXIMA_SACADO"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosConcentracaoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorConcentracaoMaximaCedenteDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["CONCENTRACAO_MAXIMA_CEDENTE"]},"ativo":{"type":"boolean"},"parametros":{"$ref":"#/components/schemas/ParametrosConcentracaoDTO"}},"required":["codigo","ativo","parametros"]},
  "ValidadorDTO": {"oneOf":[{"$ref":"#/components/schemas/ValidadorCnpjSacadoValidoDTO"},{"$ref":"#/components/schemas/ValidadorSituacaoCadastralSacadoDTO"},{"$ref":"#/components/schemas/ValidadorTipoRecebivelDTO"},{"$ref":"#/components/schemas/ValidadorValorMinimoDTO"},{"$ref":"#/components/schemas/ValidadorNaoVencidaDTO"},{"$ref":"#/components/schemas/ValidadorPrazoMinimoDTO"},{"$ref":"#/components/schemas/ValidadorPrazoMaximoDTO"},{"$ref":"#/components/schemas/ValidadorConcentracaoMaximaSacadoDTO"},{"$ref":"#/components/schemas/ValidadorConcentracaoMaximaCedenteDTO"}],"discriminator":{"propertyName":"codigo","mapping":{"CNPJ_SACADO_VALIDO":"#/components/schemas/ValidadorCnpjSacadoValidoDTO","SITUACAO_CADASTRAL_SACADO":"#/components/schemas/ValidadorSituacaoCadastralSacadoDTO","TIPO_RECEBIVEL":"#/components/schemas/ValidadorTipoRecebivelDTO","VALOR_MINIMO":"#/components/schemas/ValidadorValorMinimoDTO","NAO_VENCIDA":"#/components/schemas/ValidadorNaoVencidaDTO","PRAZO_MINIMO":"#/components/schemas/ValidadorPrazoMinimoDTO","PRAZO_MAXIMO":"#/components/schemas/ValidadorPrazoMaximoDTO","CONCENTRACAO_MAXIMA_SACADO":"#/components/schemas/ValidadorConcentracaoMaximaSacadoDTO","CONCENTRACAO_MAXIMA_CEDENTE":"#/components/schemas/ValidadorConcentracaoMaximaCedenteDTO"}}},
  "PrecificacaoDTO": {"type":"object","additionalProperties":false,"properties":{"metodo":{"type":"string","enum":["DESCONTO_SIMPLES"]},"taxa_mensal_percentual":{"$ref":"#/components/schemas/DecimalNaoNegativo"},"base_dias":{"type":"integer","minimum":1,"maximum":366}},"required":["metodo","taxa_mensal_percentual","base_dias"]},
  "ConfiguracaoRegrasDTO": {"type":"object","additionalProperties":false,"properties":{"validadores":{"type":"array","items":{"$ref":"#/components/schemas/ValidadorDTO"},"minItems":9,"maxItems":9,"allOf":[{"contains":{"type":"object","properties":{"codigo":{"const":"CNPJ_SACADO_VALIDO"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"SITUACAO_CADASTRAL_SACADO"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"TIPO_RECEBIVEL"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"VALOR_MINIMO"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"NAO_VENCIDA"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"PRAZO_MINIMO"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"PRAZO_MAXIMO"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"CONCENTRACAO_MAXIMA_SACADO"}},"required":["codigo"]},"minContains":1,"maxContains":1},{"contains":{"type":"object","properties":{"codigo":{"const":"CONCENTRACAO_MAXIMA_CEDENTE"}},"required":["codigo"]},"minContains":1,"maxContains":1}]},"precificacao":{"$ref":"#/components/schemas/PrecificacaoDTO"}},"required":["validadores","precificacao"],"description":"Exatamente uma ocorrência de cada código configurável. NOTA_DUPLICADA não é configurável. Parâmetros inativos também devem ser válidos."},
  "AtualizarRegrasRequest": {"type":"object","additionalProperties":false,"properties":{"versao_base":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]},"configuracao":{"$ref":"#/components/schemas/ConfiguracaoRegrasDTO"}},"required":["versao_base","configuracao"],"description":"versao_base=null somente para primeira configuração; para edição, versão obtida no GET. Atualização integral dos nove validadores."},
  "RegrasFundoResponse": {"type":"object","additionalProperties":false,"properties":{"fundo":{"$ref":"#/components/schemas/FundoDTO"},"versao":{"type":"string","format":"uuid"},"criada_em":{"type":"string","format":"date-time"},"configuracao":{"$ref":"#/components/schemas/ConfiguracaoRegrasDTO"}},"required":["fundo","versao","criada_em","configuracao"]},
  "ArquivoManifestoRequest": {"type":"object","additionalProperties":false,"properties":{"client_id":{"type":"string","format":"uuid"},"nome":{"type":"string","minLength":1,"maxLength":255},"formato":{"$ref":"#/components/schemas/FormatoArquivo"},"tamanho_bytes":{"type":"integer","minimum":1,"maximum":67108864},"sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"},"ordem":{"type":"integer","minimum":0,"maximum":99},"aba":{"anyOf":[{"type":"string","minLength":1,"maxLength":31},{"type":"null"}]}},"required":["client_id","nome","formato","tamanho_bytes","sha256","ordem","aba"],"description":"client_id gerado pelo front e único no lote. ordem deve ser contígua de 0 a N-1. aba=null para CSV; XLSX null seleciona primeira aba com dados."},
  "CriarLoteRequest": {"type":"object","additionalProperties":false,"properties":{"nome":{"type":"string","minLength":1,"maxLength":120},"arquivos":{"type":"array","items":{"$ref":"#/components/schemas/ArquivoManifestoRequest"},"minItems":1,"maxItems":100}},"required":["nome","arquivos"]},
  "ArquivoDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"lote_id":{"type":"string","format":"uuid"},"client_id":{"type":"string","format":"uuid"},"nome":{"type":"string"},"formato":{"$ref":"#/components/schemas/FormatoArquivo"},"ordem":{"type":"integer","minimum":0},"aba":{"anyOf":[{"type":"string"},{"type":"null"}]},"tamanho_bytes":{"type":"integer","minimum":1},"sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"},"bytes_recebidos":{"type":"integer","minimum":0},"status":{"$ref":"#/components/schemas/StatusArquivo"},"linhas_total":{"anyOf":[{"type":"integer","minimum":0},{"type":"null"}]},"linhas_processadas":{"type":"integer","minimum":0},"aprovadas":{"type":"integer","minimum":0},"barradas":{"type":"integer","minimum":0},"erros_dados":{"type":"integer","minimum":0},"recebido_em":{"anyOf":[{"type":"string","format":"date-time"},{"type":"null"}]},"concluido_em":{"anyOf":[{"type":"string","format":"date-time"},{"type":"null"}]},"erro":{"anyOf":[{"$ref":"#/components/schemas/ErroDTO"},{"type":"null"}]}},"required":["id","lote_id","client_id","nome","formato","ordem","aba","tamanho_bytes","sha256","bytes_recebidos","status","linhas_total","linhas_processadas","aprovadas","barradas","erros_dados","recebido_em","concluido_em","erro"]},
  "ProgressoDTO": {"type":"object","additionalProperties":false,"properties":{"fase":{"type":"string","enum":["AGUARDANDO","INDEXACAO","ANALISE","FINALIZADO"]},"arquivos_total":{"type":"integer","minimum":0},"arquivos_recebidos":{"type":"integer","minimum":0},"arquivos_falhos":{"type":"integer","minimum":0},"bytes_esperados":{"type":"integer","minimum":0},"bytes_recebidos":{"type":"integer","minimum":0},"linhas_lidas_primeira_passagem":{"type":"integer","minimum":0},"linhas_total":{"anyOf":[{"type":"integer","minimum":0},{"type":"null"}]},"linhas_processadas":{"type":"integer","minimum":0}},"required":["fase","arquivos_total","arquivos_recebidos","arquivos_falhos","bytes_esperados","bytes_recebidos","linhas_lidas_primeira_passagem","linhas_total","linhas_processadas"],"description":"Contadores persistidos. Total null até terminar indexação. Não somar as duas passagens como notas diferentes."},
  "ResumoFinanceiroDTO": {"type":"object","additionalProperties":false,"properties":{"definitivo":{"type":"boolean"},"total_nominal":{"$ref":"#/components/schemas/Dinheiro"},"total_nominal_aprovado":{"$ref":"#/components/schemas/Dinheiro"},"total_nominal_barrado":{"$ref":"#/components/schemas/Dinheiro"},"total_nominal_erro_dados":{"$ref":"#/components/schemas/Dinheiro"},"total_desconto":{"$ref":"#/components/schemas/Dinheiro"},"total_liquido":{"$ref":"#/components/schemas/Dinheiro"},"aprovadas":{"type":"integer","minimum":0},"barradas":{"type":"integer","minimum":0},"erros_dados":{"type":"integer","minimum":0}},"required":["definitivo","total_nominal","total_nominal_aprovado","total_nominal_barrado","total_nominal_erro_dados","total_desconto","total_liquido","aprovadas","barradas","erros_dados"],"description":"Durante execução, totais parciais; total_nominal é PL dos arquivos válidos após indexação. Não é patrimônio global histórico do fundo."},
  "AcoesLoteDTO": {"type":"object","additionalProperties":false,"properties":{"pode_enviar_arquivos":{"type":"boolean"},"pode_iniciar":{"type":"boolean"},"pode_retomar":{"type":"boolean"},"precisa_corrigir_configuracao":{"type":"boolean"},"precisa_recriar_lote":{"type":"boolean"}},"required":["pode_enviar_arquivos","pode_iniciar","pode_retomar","precisa_corrigir_configuracao","precisa_recriar_lote"]},
  "LoteDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"nome":{"type":"string"},"status":{"$ref":"#/components/schemas/StatusLote"},"criado_em":{"type":"string","format":"date-time"},"iniciado_em":{"anyOf":[{"type":"string","format":"date-time"},{"type":"null"}]},"concluido_em":{"anyOf":[{"type":"string","format":"date-time"},{"type":"null"}]},"atualizado_em":{"type":"string","format":"date-time"},"versao_cadastral":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]},"progresso":{"$ref":"#/components/schemas/ProgressoDTO"},"resumo":{"$ref":"#/components/schemas/ResumoFinanceiroDTO"},"quantidade_pendencias":{"type":"integer","minimum":0},"acoes":{"$ref":"#/components/schemas/AcoesLoteDTO"},"erro":{"anyOf":[{"$ref":"#/components/schemas/ErroDTO"},{"type":"null"}]}},"required":["id","nome","status","criado_em","iniciado_em","concluido_em","atualizado_em","versao_cadastral","progresso","resumo","quantidade_pendencias","acoes","erro"]},
  "CriarLoteResponse": {"type":"object","additionalProperties":false,"properties":{"lote":{"$ref":"#/components/schemas/LoteDTO"},"arquivos":{"type":"array","items":{"$ref":"#/components/schemas/ArquivoDTO"},"minItems":1,"maxItems":100}},"required":["lote","arquivos"]},
  "LoteResumoDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"nome":{"type":"string"},"status":{"$ref":"#/components/schemas/StatusLote"},"criado_em":{"type":"string","format":"date-time"},"atualizado_em":{"type":"string","format":"date-time"},"arquivos_total":{"type":"integer","minimum":0},"linhas_processadas":{"type":"integer","minimum":0},"total_liquido":{"$ref":"#/components/schemas/Dinheiro"}},"required":["id","nome","status","criado_em","atualizado_em","arquivos_total","linhas_processadas","total_liquido"]},
  "BatchMetadadosDTO": {"type":"object","additionalProperties":false,"properties":{"arquivo_ids":{"type":"array","items":{"type":"string","format":"uuid"},"minItems":1,"maxItems":3,"uniqueItems":true}},"required":["arquivo_ids"],"description":"A posição de arquivo_ids corresponde à posição de cada parte multipart arquivos. Não mapear por nome do arquivo."},
  "EnviarBatchRequest": {"type":"object","additionalProperties":false,"properties":{"metadados":{"type":"string","description":"JSON serializado de BatchMetadadosDTO; campo textual do FormData."},"arquivos":{"type":"array","items":{"type":"string","format":"binary"},"minItems":1,"maxItems":3}},"required":["metadados","arquivos"]},
  "ArquivoRecebidoDTO": {"type":"object","additionalProperties":false,"properties":{"arquivo_id":{"type":"string","format":"uuid"},"client_id":{"type":"string","format":"uuid"},"sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"},"bytes_recebidos":{"type":"integer","minimum":1},"status":{"type":"string","enum":["RECEBIDO"]}},"required":["arquivo_id","client_id","sha256","bytes_recebidos","status"]},
  "EnviarBatchResponse": {"type":"object","additionalProperties":false,"properties":{"batch_id":{"type":"string","format":"uuid"},"lote_id":{"type":"string","format":"uuid"},"recebido_em":{"type":"string","format":"date-time"},"arquivos":{"type":"array","items":{"$ref":"#/components/schemas/ArquivoRecebidoDTO"},"minItems":1,"maxItems":3}},"required":["batch_id","lote_id","recebido_em","arquivos"]},
  "ProcessarLoteResponse": {"type":"object","additionalProperties":false,"properties":{"lote_id":{"type":"string","format":"uuid"},"execucao_id":{"type":"string","format":"uuid"},"status":{"type":"string","enum":["NA_FILA"]},"aceito_em":{"type":"string","format":"date-time"},"status_url":{"type":"string","format":"uri-reference"}},"required":["lote_id","execucao_id","status","aceito_em","status_url"]},
  "PendenciaDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"type":"string","enum":["FUNDO_SEM_REGRAS","BASE_CADASTRAL_AUSENTE","DADOS_IMPEDEM_PL"]},"mensagem":{"type":"string"},"fundo":{"anyOf":[{"$ref":"#/components/schemas/FundoDTO"},{"type":"null"}]},"arquivo_id":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]},"linha":{"anyOf":[{"type":"integer","minimum":2},{"type":"null"}]},"campo":{"anyOf":[{"type":"string"},{"type":"null"}]},"acao":{"type":"string","enum":["CONFIGURAR_FUNDO","IMPORTAR_BASE_CADASTRAL","RECRIAR_LOTE"]}},"required":["codigo","mensagem","fundo","arquivo_id","linha","campo","acao"]},
  "ResumoFundoDTO": {"type":"object","additionalProperties":false,"properties":{"fundo":{"$ref":"#/components/schemas/FundoDTO"},"versao_regras_utilizada":{"anyOf":[{"type":"string","format":"uuid"},{"type":"null"}]},"pl":{"$ref":"#/components/schemas/Dinheiro"},"limite_sacado":{"anyOf":[{"$ref":"#/components/schemas/Dinheiro"},{"type":"null"}]},"limite_cedente":{"anyOf":[{"$ref":"#/components/schemas/Dinheiro"},{"type":"null"}]},"resumo":{"$ref":"#/components/schemas/ResumoFinanceiroDTO"}},"required":["fundo","versao_regras_utilizada","pl","limite_sacado","limite_cedente","resumo"],"description":"Limite null se regra inativa ou contexto ainda não congelado. versao_regras_utilizada identifica a versão histórica, não necessariamente a atual do fundo."},
  "MotivoDTO": {"type":"object","additionalProperties":false,"properties":{"codigo":{"$ref":"#/components/schemas/CodigoRecusa"},"mensagem":{"type":"string"},"valor_observado":{"anyOf":[{"type":"string"},{"type":"null"}]},"limite_aplicado":{"anyOf":[{"type":"string"},{"type":"null"}]}},"required":["codigo","mensagem","valor_observado","limite_aplicado"],"description":"Explicação para exibição; frontend não recalcula a regra nem interpreta os valores textuais como contrato de cálculo."},
  "ErroDadoDTO": {"type":"object","additionalProperties":false,"properties":{"campo":{"type":"string"},"codigo":{"type":"string","enum":["OBRIGATORIO","FORMATO_INVALIDO","DATA_INVALIDA","DECIMAL_INVALIDO","FORMULA_SEM_VALOR","DOCUMENTO_SEM_RAIZ"]},"mensagem":{"type":"string"}},"required":["campo","codigo","mensagem"]},
  "DadosOriginaisTituloDTO": {"type":"object","additionalProperties":false,"properties":{"NOME_FUNDO":{"anyOf":[{"type":"string"},{"type":"null"}]},"DOC_FUNDO":{"anyOf":[{"type":"string"},{"type":"null"}]},"NOME_CEDENTE":{"anyOf":[{"type":"string"},{"type":"null"}]},"DOC_CEDENTE":{"anyOf":[{"type":"string"},{"type":"null"}]},"NOME_SACADO":{"anyOf":[{"type":"string"},{"type":"null"}]},"DOC_SACADO":{"anyOf":[{"type":"string"},{"type":"null"}]},"NU_DOCUMENTO":{"anyOf":[{"type":"string"},{"type":"null"}]},"TIPO_RECEBIVEL":{"anyOf":[{"type":"string"},{"type":"null"}]},"VALOR_NOMINAL":{"anyOf":[{"type":"string"},{"type":"null"}]},"DATA_VENCIMENTO_ORIGINAL":{"anyOf":[{"type":"string"},{"type":"null"}]},"DATA_AQUISICAO":{"anyOf":[{"type":"string"},{"type":"null"}]}},"required":["NOME_FUNDO","DOC_FUNDO","NOME_CEDENTE","DOC_CEDENTE","NOME_SACADO","DOC_SACADO","NU_DOCUMENTO","TIPO_RECEBIVEL","VALOR_NOMINAL","DATA_VENCIMENTO_ORIGINAL","DATA_AQUISICAO"]},
  "TituloNormalizadoDTO": {"type":"object","additionalProperties":false,"properties":{"fundo_id":{"type":"string","format":"uuid"},"nome_fundo":{"type":"string"},"doc_fundo":{"type":"string","pattern":"^[0-9]{14}$"},"nome_cedente":{"type":"string"},"doc_cedente":{"type":"string"},"raiz_cedente":{"anyOf":[{"type":"string","pattern":"^[0-9]{8}$"},{"type":"null"}]},"nome_sacado":{"type":"string"},"doc_sacado":{"type":"string"},"raiz_sacado":{"anyOf":[{"type":"string","pattern":"^[0-9]{8}$"},{"type":"null"}]},"nu_documento":{"type":"string"},"tipo_recebivel":{"type":"string"},"valor_nominal":{"$ref":"#/components/schemas/Dinheiro"},"data_aquisicao":{"type":"string","format":"date"},"data_vencimento_original":{"type":"string","format":"date"},"prazo_dias":{"type":"integer"}},"required":["fundo_id","nome_fundo","doc_fundo","nome_cedente","doc_cedente","raiz_cedente","nome_sacado","doc_sacado","raiz_sacado","nu_documento","tipo_recebivel","valor_nominal","data_aquisicao","data_vencimento_original","prazo_dias"],"description":"Documento observado pode ser inválido e gerar CNPJ_SACADO_VALIDO. Não aplicar regex CNPJ válido aos campos doc_sacado/cedente do resultado."},
  "ResultadoAprovadoDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"lote_id":{"type":"string","format":"uuid"},"arquivo_id":{"type":"string","format":"uuid"},"sequencia":{"type":"integer","minimum":1},"linha":{"type":"integer","minimum":2},"dados_originais":{"$ref":"#/components/schemas/DadosOriginaisTituloDTO"},"tipo":{"type":"string","enum":["ANALISE"]},"status":{"type":"string","enum":["APROVADO"]},"titulo":{"$ref":"#/components/schemas/TituloNormalizadoDTO"},"motivos":{"type":"array","items":{"$ref":"#/components/schemas/MotivoDTO"},"maxItems":0},"erros_dados":{"type":"array","items":{"$ref":"#/components/schemas/ErroDadoDTO"},"maxItems":0},"desconto":{"$ref":"#/components/schemas/Dinheiro"},"valor_liquido":{"$ref":"#/components/schemas/Dinheiro"}},"required":["id","lote_id","arquivo_id","sequencia","linha","dados_originais","tipo","status","titulo","motivos","erros_dados","desconto","valor_liquido"]},
  "ResultadoBarradoDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"lote_id":{"type":"string","format":"uuid"},"arquivo_id":{"type":"string","format":"uuid"},"sequencia":{"type":"integer","minimum":1},"linha":{"type":"integer","minimum":2},"dados_originais":{"$ref":"#/components/schemas/DadosOriginaisTituloDTO"},"tipo":{"type":"string","enum":["ANALISE"]},"status":{"type":"string","enum":["BARRADO"]},"titulo":{"$ref":"#/components/schemas/TituloNormalizadoDTO"},"motivos":{"type":"array","items":{"$ref":"#/components/schemas/MotivoDTO"},"minItems":1},"erros_dados":{"type":"array","items":{"$ref":"#/components/schemas/ErroDadoDTO"},"maxItems":0},"desconto":{"type":"string","enum":["0.00"]},"valor_liquido":{"type":"string","enum":["0.00"]}},"required":["id","lote_id","arquivo_id","sequencia","linha","dados_originais","tipo","status","titulo","motivos","erros_dados","desconto","valor_liquido"]},
  "ResultadoErroDadosDTO": {"type":"object","additionalProperties":false,"properties":{"id":{"type":"string","format":"uuid"},"lote_id":{"type":"string","format":"uuid"},"arquivo_id":{"type":"string","format":"uuid"},"sequencia":{"type":"integer","minimum":1},"linha":{"type":"integer","minimum":2},"dados_originais":{"$ref":"#/components/schemas/DadosOriginaisTituloDTO"},"tipo":{"type":"string","enum":["ERRO_DADOS"]},"status":{"type":"null"},"titulo":{"type":"null"},"motivos":{"type":"array","items":{"$ref":"#/components/schemas/MotivoDTO"},"maxItems":0},"erros_dados":{"type":"array","items":{"$ref":"#/components/schemas/ErroDadoDTO"},"minItems":1},"desconto":{"type":"string","enum":["0.00"]},"valor_liquido":{"type":"string","enum":["0.00"]}},"required":["id","lote_id","arquivo_id","sequencia","linha","dados_originais","tipo","status","titulo","motivos","erros_dados","desconto","valor_liquido"],"description":"Diagnóstico de parsing; não é um novo status financeiro nem um novo código de recusa FIDC. Usar dados_originais na interface."},
  "ResultadoDTO": {"oneOf":[{"$ref":"#/components/schemas/ResultadoAprovadoDTO"},{"$ref":"#/components/schemas/ResultadoBarradoDTO"},{"$ref":"#/components/schemas/ResultadoErroDadosDTO"}]},
  "PaginacaoQuery": {"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"maximum":100,"default":50},"cursor":{"type":"string","minLength":1,"maxLength":4096}},"required":[]},
  "ListarFundosQuery": {"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"maximum":100,"default":50},"cursor":{"type":"string","minLength":1,"maxLength":4096},"busca":{"type":"string","minLength":1,"maxLength":120},"configurado":{"type":"boolean"}},"required":[]},
  "ListarLotesQuery": {"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"maximum":100,"default":50},"cursor":{"type":"string","minLength":1,"maxLength":4096},"status":{"$ref":"#/components/schemas/StatusLote"}},"required":[]},
  "ConsultarRegrasQuery": {"type":"object","additionalProperties":false,"properties":{"versao":{"type":"string","format":"uuid"}},"required":[]},
  "ListarResultadosQuery": {"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"maximum":100,"default":50},"cursor":{"type":"string","minLength":1,"maxLength":4096},"status":{"$ref":"#/components/schemas/StatusNota"},"motivo":{"$ref":"#/components/schemas/CodigoRecusa"},"tipo":{"type":"string","enum":["ANALISE","ERRO_DADOS"]}},"required":[]},
  "FundosPageResponse": {"type":"object","additionalProperties":false,"properties":{"itens":{"type":"array","items":{"$ref":"#/components/schemas/FundoDTO"},"maxItems":100},"proximo_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]},"limit":{"type":"integer","minimum":1,"maximum":100}},"required":["itens","proximo_cursor","limit"]},
  "LotesPageResponse": {"type":"object","additionalProperties":false,"properties":{"itens":{"type":"array","items":{"$ref":"#/components/schemas/LoteResumoDTO"},"maxItems":100},"proximo_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]},"limit":{"type":"integer","minimum":1,"maximum":100}},"required":["itens","proximo_cursor","limit"]},
  "ArquivosPageResponse": {"type":"object","additionalProperties":false,"properties":{"itens":{"type":"array","items":{"$ref":"#/components/schemas/ArquivoDTO"},"maxItems":100},"proximo_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]},"limit":{"type":"integer","minimum":1,"maximum":100}},"required":["itens","proximo_cursor","limit"]},
  "PendenciasPageResponse": {"type":"object","additionalProperties":false,"properties":{"itens":{"type":"array","items":{"$ref":"#/components/schemas/PendenciaDTO"},"maxItems":100},"proximo_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]},"limit":{"type":"integer","minimum":1,"maximum":100}},"required":["itens","proximo_cursor","limit"]},
  "ResumosFundosPageResponse": {"type":"object","additionalProperties":false,"properties":{"itens":{"type":"array","items":{"$ref":"#/components/schemas/ResumoFundoDTO"},"maxItems":100},"proximo_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]},"limit":{"type":"integer","minimum":1,"maximum":100}},"required":["itens","proximo_cursor","limit"]},
  "ResultadosPageResponse": {"type":"object","additionalProperties":false,"properties":{"itens":{"type":"array","items":{"$ref":"#/components/schemas/ResultadoDTO"},"maxItems":100},"proximo_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]},"limit":{"type":"integer","minimum":1,"maximum":100},"snapshot_ate_sequencia":{"type":"integer","minimum":0},"arquivo_finalizado":{"type":"boolean"}},"required":["itens","proximo_cursor","limit","snapshot_ate_sequencia","arquivo_finalizado"],"description":"Cursor fixa teto de sequência e filtros. Refazer primeira página para incluir resultados mais recentes. Não fornece total filtrado nem salto arbitrário de página."}
}}
}
```

## Exemplos JSON de todos os schemas

Há uma entrada por schema do contrato, incluindo tipos escalares, enums, objetos auxiliares, DTOs de query, requests, responses e variantes discriminadas. Estes são exemplos de forma e de cenários independentes: IDs não precisam representar uma única execução coerente entre entradas. As strings de cursor são ilustrativas e não podem ser usadas como cursores reais do servidor. Os exemplos não dispensam as restrições semânticas descritas acima.

`EnviarBatchRequest` é a única representação de transporte multipart: seu campo `arquivos` contém placeholders descritivos de bytes, não strings para enviar como JSON. Use FormData e arquivos binários reais, seguindo a seção de multipart. Queries viram parâmetros de URL, nunca corpos JSON. POST de processamento não tem corpo.

```json
{
  "Dinheiro": "2278.08",
  "DecimalNaoNegativo": "2.0",
  "CodigoRecusa": "NOTA_DUPLICADA",
  "StatusNota": "APROVADO",
  "StatusLote": "RECEBENDO",
  "StatusArquivo": "AGUARDANDO_UPLOAD",
  "FormatoArquivo": "CSV",
  "CodigoErro": "VALIDACAO_REQUISICAO",
  "DetalheErroDTO": {"campo":"exemplo","codigo":"exemplo","mensagem":"exemplo"},
  "ErroDTO": {"codigo":"VERSAO_REGRAS_CONFLITANTE","mensagem":"As regras foram alteradas por outra operação. Recarregue a configuração.","retry_permitido":false,"detalhes":[],"versao_atual":"00000000-0000-4000-8000-000000000003"},
  "ErroResponse": {"request_id":"00000000-0000-4000-8000-000000000099","erro":{"codigo":"VERSAO_REGRAS_CONFLITANTE","mensagem":"As regras foram alteradas por outra operação. Recarregue a configuração.","retry_permitido":false,"detalhes":[],"versao_atual":"00000000-0000-4000-8000-000000000003"}},
  "SaudeResponse": {"status":"OK","servico":"antecipe-api","versao_api":"1.0.0","verificado_em":"2026-10-24T18:00:00Z"},
  "CapacidadesResponse": {"versao_contrato":"1.0.0","autenticacao":"SEM_AUTENTICACAO_DEMO","formatos":["CSV","XLSX"],"max_arquivos_lote":100,"max_arquivos_batch":3,"max_bytes_arquivo":67108864,"max_bytes_batch":67108864,"max_linhas_lote":500000,"max_pagina":100,"polling_intervalo_ms":2000,"permite_exportacao":false,"permite_cancelamento":false},
  "BaseCadastralStatusResponse": {"disponivel":true,"versao":"00000000-0000-4000-8000-000000000040","sha256":"522ba08c9685a48d2c2a5b20bfde0773f58bb15b095e03cf605b44c224ca6916","quantidade_cnpjs":3041,"importado_em":"2026-10-24T18:00:00Z"},
  "FundoDTO": {"id":"00000000-0000-4000-8000-000000000001","nome":"ANTECIPE FIDC","cnpj":"92234400000180","configurado":true,"versao_regras_atual":"00000000-0000-4000-8000-000000000002"},
  "ParametrosVaziosDTO": {},
  "ParametrosSituacaoDTO": {"situacoes_aceitas":["ATIVA"]},
  "ParametrosTipoDTO": {"tipos_aceitos":["Duplicata","Duplicata de Serviço"]},
  "ParametrosValorMinimoDTO": {"valor_minimo":"100.0"},
  "ParametrosPrazoMinimoDTO": {"prazo_minimo_dias":30},
  "ParametrosPrazoMaximoDTO": {"prazo_maximo_dias":180},
  "ParametrosConcentracaoDTO": {"percentual_maximo":"10.0","agrupamento":"RAIZ_CNPJ"},
  "ValidadorCnpjSacadoValidoDTO": {"codigo":"CNPJ_SACADO_VALIDO","ativo":true,"parametros":{}},
  "ValidadorSituacaoCadastralSacadoDTO": {"codigo":"SITUACAO_CADASTRAL_SACADO","ativo":true,"parametros":{"situacoes_aceitas":["ATIVA"]}},
  "ValidadorTipoRecebivelDTO": {"codigo":"TIPO_RECEBIVEL","ativo":true,"parametros":{"tipos_aceitos":["Duplicata","Duplicata de Serviço"]}},
  "ValidadorValorMinimoDTO": {"codigo":"VALOR_MINIMO","ativo":true,"parametros":{"valor_minimo":"100.0"}},
  "ValidadorNaoVencidaDTO": {"codigo":"NAO_VENCIDA","ativo":true,"parametros":{}},
  "ValidadorPrazoMinimoDTO": {"codigo":"PRAZO_MINIMO","ativo":false,"parametros":{"prazo_minimo_dias":30}},
  "ValidadorPrazoMaximoDTO": {"codigo":"PRAZO_MAXIMO","ativo":true,"parametros":{"prazo_maximo_dias":180}},
  "ValidadorConcentracaoMaximaSacadoDTO": {"codigo":"CONCENTRACAO_MAXIMA_SACADO","ativo":true,"parametros":{"percentual_maximo":"10.0","agrupamento":"RAIZ_CNPJ"}},
  "ValidadorConcentracaoMaximaCedenteDTO": {"codigo":"CONCENTRACAO_MAXIMA_CEDENTE","ativo":false,"parametros":{"percentual_maximo":"8.0","agrupamento":"RAIZ_CNPJ"}},
  "ValidadorDTO": {"codigo":"CNPJ_SACADO_VALIDO","ativo":true,"parametros":{}},
  "PrecificacaoDTO": {"metodo":"DESCONTO_SIMPLES","taxa_mensal_percentual":"2.0","base_dias":30},
  "ConfiguracaoRegrasDTO": {"validadores":[{"codigo":"CNPJ_SACADO_VALIDO","ativo":true,"parametros":{}},{"codigo":"SITUACAO_CADASTRAL_SACADO","ativo":true,"parametros":{"situacoes_aceitas":["ATIVA"]}},{"codigo":"TIPO_RECEBIVEL","ativo":true,"parametros":{"tipos_aceitos":["Duplicata","Duplicata de Serviço"]}},{"codigo":"VALOR_MINIMO","ativo":true,"parametros":{"valor_minimo":"100.0"}},{"codigo":"NAO_VENCIDA","ativo":true,"parametros":{}},{"codigo":"PRAZO_MAXIMO","ativo":true,"parametros":{"prazo_maximo_dias":180}},{"codigo":"CONCENTRACAO_MAXIMA_SACADO","ativo":true,"parametros":{"percentual_maximo":"10.0","agrupamento":"RAIZ_CNPJ"}},{"codigo":"PRAZO_MINIMO","ativo":false,"parametros":{"prazo_minimo_dias":30}},{"codigo":"CONCENTRACAO_MAXIMA_CEDENTE","ativo":false,"parametros":{"percentual_maximo":"8.0","agrupamento":"RAIZ_CNPJ"}}],"precificacao":{"metodo":"DESCONTO_SIMPLES","taxa_mensal_percentual":"2.0","base_dias":30}},
  "AtualizarRegrasRequest": {"versao_base":null,"configuracao":{"validadores":[{"codigo":"CNPJ_SACADO_VALIDO","ativo":true,"parametros":{}},{"codigo":"SITUACAO_CADASTRAL_SACADO","ativo":true,"parametros":{"situacoes_aceitas":["ATIVA"]}},{"codigo":"TIPO_RECEBIVEL","ativo":true,"parametros":{"tipos_aceitos":["Duplicata","Duplicata de Serviço"]}},{"codigo":"VALOR_MINIMO","ativo":true,"parametros":{"valor_minimo":"100.0"}},{"codigo":"NAO_VENCIDA","ativo":true,"parametros":{}},{"codigo":"PRAZO_MAXIMO","ativo":true,"parametros":{"prazo_maximo_dias":180}},{"codigo":"CONCENTRACAO_MAXIMA_SACADO","ativo":true,"parametros":{"percentual_maximo":"10.0","agrupamento":"RAIZ_CNPJ"}},{"codigo":"PRAZO_MINIMO","ativo":false,"parametros":{"prazo_minimo_dias":30}},{"codigo":"CONCENTRACAO_MAXIMA_CEDENTE","ativo":false,"parametros":{"percentual_maximo":"8.0","agrupamento":"RAIZ_CNPJ"}}],"precificacao":{"metodo":"DESCONTO_SIMPLES","taxa_mensal_percentual":"2.0","base_dias":30}}},
  "RegrasFundoResponse": {"fundo":{"id":"00000000-0000-4000-8000-000000000001","nome":"ANTECIPE FIDC","cnpj":"92234400000180","configurado":true,"versao_regras_atual":"00000000-0000-4000-8000-000000000002"},"versao":"00000000-0000-4000-8000-000000000002","criada_em":"2026-10-24T18:00:00Z","configuracao":{"validadores":[{"codigo":"CNPJ_SACADO_VALIDO","ativo":true,"parametros":{}},{"codigo":"SITUACAO_CADASTRAL_SACADO","ativo":true,"parametros":{"situacoes_aceitas":["ATIVA"]}},{"codigo":"TIPO_RECEBIVEL","ativo":true,"parametros":{"tipos_aceitos":["Duplicata","Duplicata de Serviço"]}},{"codigo":"VALOR_MINIMO","ativo":true,"parametros":{"valor_minimo":"100.0"}},{"codigo":"NAO_VENCIDA","ativo":true,"parametros":{}},{"codigo":"PRAZO_MAXIMO","ativo":true,"parametros":{"prazo_maximo_dias":180}},{"codigo":"CONCENTRACAO_MAXIMA_SACADO","ativo":true,"parametros":{"percentual_maximo":"10.0","agrupamento":"RAIZ_CNPJ"}},{"codigo":"PRAZO_MINIMO","ativo":false,"parametros":{"prazo_minimo_dias":30}},{"codigo":"CONCENTRACAO_MAXIMA_CEDENTE","ativo":false,"parametros":{"percentual_maximo":"8.0","agrupamento":"RAIZ_CNPJ"}}],"precificacao":{"metodo":"DESCONTO_SIMPLES","taxa_mensal_percentual":"2.0","base_dias":30}}},
  "ArquivoManifestoRequest": {"client_id":"00000000-0000-4000-8000-000000000101","nome":"exemplo","formato":"CSV","tamanho_bytes":1,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","ordem":0,"aba":"exemplo"},
  "CriarLoteRequest": {"nome":"Demonstração de contrato","arquivos":[{"client_id":"00000000-0000-4000-8000-000000000010","nome":"exemplo.csv","formato":"CSV","tamanho_bytes":1024,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","ordem":0,"aba":null}]},
  "ArquivoDTO": {"id":"00000000-0000-4000-8000-000000000011","lote_id":"00000000-0000-4000-8000-000000000012","client_id":"00000000-0000-4000-8000-000000000010","nome":"exemplo.csv","formato":"CSV","tamanho_bytes":1024,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","ordem":0,"aba":null,"bytes_recebidos":0,"status":"AGUARDANDO_UPLOAD","linhas_total":null,"linhas_processadas":0,"aprovadas":0,"barradas":0,"erros_dados":0,"recebido_em":null,"concluido_em":null,"erro":null},
  "ProgressoDTO": {"fase":"AGUARDANDO","arquivos_total":1,"arquivos_recebidos":0,"arquivos_falhos":0,"bytes_esperados":1024,"bytes_recebidos":0,"linhas_lidas_primeira_passagem":0,"linhas_total":null,"linhas_processadas":0},
  "ResumoFinanceiroDTO": {"definitivo":false,"total_nominal":"0.00","total_nominal_aprovado":"0.00","total_nominal_barrado":"0.00","total_nominal_erro_dados":"0.00","total_desconto":"0.00","total_liquido":"0.00","aprovadas":0,"barradas":0,"erros_dados":0},
  "AcoesLoteDTO": {"pode_enviar_arquivos":true,"pode_iniciar":false,"pode_retomar":false,"precisa_corrigir_configuracao":false,"precisa_recriar_lote":false},
  "LoteDTO": {"id":"00000000-0000-4000-8000-000000000012","nome":"Demonstração de contrato","status":"BLOQUEADO","criado_em":"2026-10-24T18:00:00Z","iniciado_em":"2026-10-24T18:00:00Z","concluido_em":null,"atualizado_em":"2026-10-24T18:00:00Z","versao_cadastral":null,"progresso":{"fase":"INDEXACAO","arquivos_total":1,"arquivos_recebidos":1,"arquivos_falhos":0,"bytes_esperados":1024,"bytes_recebidos":1024,"linhas_lidas_primeira_passagem":3,"linhas_total":3,"linhas_processadas":0},"resumo":{"definitivo":false,"total_nominal":"0.00","total_nominal_aprovado":"0.00","total_nominal_barrado":"0.00","total_nominal_erro_dados":"0.00","total_desconto":"0.00","total_liquido":"0.00","aprovadas":0,"barradas":0,"erros_dados":0},"quantidade_pendencias":1,"acoes":{"pode_enviar_arquivos":false,"pode_iniciar":false,"pode_retomar":true,"precisa_corrigir_configuracao":true,"precisa_recriar_lote":false},"erro":null},
  "CriarLoteResponse": {"lote":{"id":"00000000-0000-4000-8000-000000000012","nome":"Demonstração de contrato","status":"RECEBENDO","criado_em":"2026-10-24T18:00:00Z","iniciado_em":null,"concluido_em":null,"atualizado_em":"2026-10-24T18:00:00Z","versao_cadastral":null,"progresso":{"fase":"AGUARDANDO","arquivos_total":1,"arquivos_recebidos":0,"arquivos_falhos":0,"bytes_esperados":1024,"bytes_recebidos":0,"linhas_lidas_primeira_passagem":0,"linhas_total":null,"linhas_processadas":0},"resumo":{"definitivo":false,"total_nominal":"0.00","total_nominal_aprovado":"0.00","total_nominal_barrado":"0.00","total_nominal_erro_dados":"0.00","total_desconto":"0.00","total_liquido":"0.00","aprovadas":0,"barradas":0,"erros_dados":0},"quantidade_pendencias":0,"acoes":{"pode_enviar_arquivos":true,"pode_iniciar":false,"pode_retomar":false,"precisa_corrigir_configuracao":false,"precisa_recriar_lote":false},"erro":null},"arquivos":[{"id":"00000000-0000-4000-8000-000000000011","lote_id":"00000000-0000-4000-8000-000000000012","client_id":"00000000-0000-4000-8000-000000000010","nome":"exemplo.csv","formato":"CSV","tamanho_bytes":1024,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","ordem":0,"aba":null,"bytes_recebidos":0,"status":"AGUARDANDO_UPLOAD","linhas_total":null,"linhas_processadas":0,"aprovadas":0,"barradas":0,"erros_dados":0,"recebido_em":null,"concluido_em":null,"erro":null}]},
  "LoteResumoDTO": {"id":"00000000-0000-4000-8000-000000000012","nome":"Demonstração de contrato","status":"RECEBENDO","criado_em":"2026-10-24T18:00:00Z","atualizado_em":"2026-10-24T18:00:00Z","arquivos_total":1,"linhas_processadas":0,"total_liquido":"0.00"},
  "BatchMetadadosDTO": {"arquivo_ids":["00000000-0000-4000-8000-000000000011"]},
  "EnviarBatchRequest": {"metadados":"{\"arquivo_ids\":[\"00000000-0000-4000-8000-000000000011\"]}","arquivos":["<bytes do arquivo; parte binaria multipart>"]},
  "ArquivoRecebidoDTO": {"arquivo_id":"00000000-0000-4000-8000-000000000103","client_id":"00000000-0000-4000-8000-000000000104","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","bytes_recebidos":1,"status":"RECEBIDO"},
  "EnviarBatchResponse": {"batch_id":"00000000-0000-4000-8000-000000000013","lote_id":"00000000-0000-4000-8000-000000000012","recebido_em":"2026-10-24T18:00:00Z","arquivos":[{"arquivo_id":"00000000-0000-4000-8000-000000000011","client_id":"00000000-0000-4000-8000-000000000010","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","bytes_recebidos":1024,"status":"RECEBIDO"}]},
  "ProcessarLoteResponse": {"lote_id":"00000000-0000-4000-8000-000000000012","execucao_id":"00000000-0000-4000-8000-000000000014","status":"NA_FILA","aceito_em":"2026-10-24T18:00:00Z","status_url":"/api/v1/lotes/00000000-0000-4000-8000-000000000012"},
  "PendenciaDTO": {"codigo":"FUNDO_SEM_REGRAS","mensagem":"Configure as regras deste fundo antes de analisar o lote.","fundo":{"id":"00000000-0000-4000-8000-000000000030","nome":"FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS SAFIRA VAREJO RESPONSABILIDADE LIMITADA","cnpj":"32482084000133","configurado":false,"versao_regras_atual":null},"arquivo_id":null,"linha":null,"campo":null,"acao":"CONFIGURAR_FUNDO"},
  "ResumoFundoDTO": {"fundo":{"id":"00000000-0000-4000-8000-000000000001","nome":"ANTECIPE FIDC","cnpj":"92234400000180","configurado":true,"versao_regras_atual":"00000000-0000-4000-8000-000000000002"},"versao_regras_utilizada":null,"pl":"0.00","limite_sacado":null,"limite_cedente":null,"resumo":{"definitivo":false,"total_nominal":"0.00","total_nominal_aprovado":"0.00","total_nominal_barrado":"0.00","total_nominal_erro_dados":"0.00","total_desconto":"0.00","total_liquido":"0.00","aprovadas":0,"barradas":0,"erros_dados":0}},
  "MotivoDTO": {"codigo":"NOTA_DUPLICADA","mensagem":"Título já aprovado para este cedente, sacado e documento.","valor_observado":"000351153","limite_aplicado":null},
  "ErroDadoDTO": {"campo":"DATA_AQUISICAO","codigo":"DATA_INVALIDA","mensagem":"Data inexistente no calendário."},
  "DadosOriginaisTituloDTO": {"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"01/10/2026"},
  "TituloNormalizadoDTO": {"fundo_id":"00000000-0000-4000-8000-000000000001","nome_fundo":"ANTECIPE FIDC","doc_fundo":"92234400000180","nome_cedente":"Cedente de exemplo","doc_cedente":"10062050000157","raiz_cedente":"10062050","nome_sacado":"Sacado de exemplo","doc_sacado":"22144961000102","raiz_sacado":"22144961","nu_documento":"000351153","tipo_recebivel":"Duplicata","valor_nominal":"10000.00","data_aquisicao":"2026-10-01","data_vencimento_original":"2026-10-31","prazo_dias":30},
  "ResultadoAprovadoDTO": {"id":"00000000-0000-4000-8000-000000000020","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":1,"linha":2,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"01/10/2026"},"tipo":"ANALISE","status":"APROVADO","titulo":{"fundo_id":"00000000-0000-4000-8000-000000000001","nome_fundo":"ANTECIPE FIDC","doc_fundo":"92234400000180","nome_cedente":"Cedente de exemplo","doc_cedente":"10062050000157","raiz_cedente":"10062050","nome_sacado":"Sacado de exemplo","doc_sacado":"22144961000102","raiz_sacado":"22144961","nu_documento":"000351153","tipo_recebivel":"Duplicata","valor_nominal":"10000.00","data_aquisicao":"2026-10-01","data_vencimento_original":"2026-10-31","prazo_dias":30},"motivos":[],"erros_dados":[],"desconto":"200.00","valor_liquido":"9800.00"},
  "ResultadoBarradoDTO": {"id":"00000000-0000-4000-8000-000000000021","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":2,"linha":3,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"01/10/2026"},"tipo":"ANALISE","status":"BARRADO","titulo":{"fundo_id":"00000000-0000-4000-8000-000000000001","nome_fundo":"ANTECIPE FIDC","doc_fundo":"92234400000180","nome_cedente":"Cedente de exemplo","doc_cedente":"10062050000157","raiz_cedente":"10062050","nome_sacado":"Sacado de exemplo","doc_sacado":"22144961000102","raiz_sacado":"22144961","nu_documento":"000351153","tipo_recebivel":"Duplicata","valor_nominal":"10000.00","data_aquisicao":"2026-10-01","data_vencimento_original":"2026-10-31","prazo_dias":30},"motivos":[{"codigo":"NOTA_DUPLICADA","mensagem":"Título já aprovado para este cedente, sacado e documento.","valor_observado":"000351153","limite_aplicado":null}],"erros_dados":[],"desconto":"0.00","valor_liquido":"0.00"},
  "ResultadoErroDadosDTO": {"id":"00000000-0000-4000-8000-000000000022","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":3,"linha":4,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"31/02/2026"},"tipo":"ERRO_DADOS","status":null,"titulo":null,"motivos":[],"erros_dados":[{"campo":"DATA_AQUISICAO","codigo":"DATA_INVALIDA","mensagem":"Data inexistente no calendário."}],"desconto":"0.00","valor_liquido":"0.00"},
  "ResultadoDTO": {"id":"00000000-0000-4000-8000-000000000020","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":1,"linha":2,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"01/10/2026"},"tipo":"ANALISE","status":"APROVADO","titulo":{"fundo_id":"00000000-0000-4000-8000-000000000001","nome_fundo":"ANTECIPE FIDC","doc_fundo":"92234400000180","nome_cedente":"Cedente de exemplo","doc_cedente":"10062050000157","raiz_cedente":"10062050","nome_sacado":"Sacado de exemplo","doc_sacado":"22144961000102","raiz_sacado":"22144961","nu_documento":"000351153","tipo_recebivel":"Duplicata","valor_nominal":"10000.00","data_aquisicao":"2026-10-01","data_vencimento_original":"2026-10-31","prazo_dias":30},"motivos":[],"erros_dados":[],"desconto":"200.00","valor_liquido":"9800.00"},
  "PaginacaoQuery": {"limit":50},
  "ListarFundosQuery": {"limit":50},
  "ListarLotesQuery": {"limit":50},
  "ConsultarRegrasQuery": {},
  "ListarResultadosQuery": {"limit":50},
  "FundosPageResponse": {"itens":[{"id":"00000000-0000-4000-8000-000000000001","nome":"ANTECIPE FIDC","cnpj":"92234400000180","configurado":true,"versao_regras_atual":"00000000-0000-4000-8000-000000000002"}],"proximo_cursor":null,"limit":50},
  "LotesPageResponse": {"itens":[{"id":"00000000-0000-4000-8000-000000000012","nome":"Demonstração de contrato","status":"RECEBENDO","criado_em":"2026-10-24T18:00:00Z","atualizado_em":"2026-10-24T18:00:00Z","arquivos_total":1,"linhas_processadas":0,"total_liquido":"0.00"}],"proximo_cursor":null,"limit":50},
  "ArquivosPageResponse": {"itens":[{"id":"00000000-0000-4000-8000-000000000011","lote_id":"00000000-0000-4000-8000-000000000012","client_id":"00000000-0000-4000-8000-000000000010","nome":"exemplo.csv","formato":"CSV","tamanho_bytes":1024,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","ordem":0,"aba":null,"bytes_recebidos":0,"status":"AGUARDANDO_UPLOAD","linhas_total":null,"linhas_processadas":0,"aprovadas":0,"barradas":0,"erros_dados":0,"recebido_em":null,"concluido_em":null,"erro":null}],"proximo_cursor":null,"limit":50},
  "PendenciasPageResponse": {"itens":[{"codigo":"FUNDO_SEM_REGRAS","mensagem":"Configure as regras deste fundo antes de analisar o lote.","fundo":{"id":"00000000-0000-4000-8000-000000000030","nome":"FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS SAFIRA VAREJO RESPONSABILIDADE LIMITADA","cnpj":"32482084000133","configurado":false,"versao_regras_atual":null},"arquivo_id":null,"linha":null,"campo":null,"acao":"CONFIGURAR_FUNDO"}],"proximo_cursor":null,"limit":50},
  "ResumosFundosPageResponse": {"itens":[{"fundo":{"id":"00000000-0000-4000-8000-000000000001","nome":"ANTECIPE FIDC","cnpj":"92234400000180","configurado":true,"versao_regras_atual":"00000000-0000-4000-8000-000000000002"},"versao_regras_utilizada":null,"pl":"0.00","limite_sacado":null,"limite_cedente":null,"resumo":{"definitivo":false,"total_nominal":"0.00","total_nominal_aprovado":"0.00","total_nominal_barrado":"0.00","total_nominal_erro_dados":"0.00","total_desconto":"0.00","total_liquido":"0.00","aprovadas":0,"barradas":0,"erros_dados":0}}],"proximo_cursor":null,"limit":50},
  "ResultadosPageResponse": {"itens":[{"id":"00000000-0000-4000-8000-000000000020","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":1,"linha":2,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"01/10/2026"},"tipo":"ANALISE","status":"APROVADO","titulo":{"fundo_id":"00000000-0000-4000-8000-000000000001","nome_fundo":"ANTECIPE FIDC","doc_fundo":"92234400000180","nome_cedente":"Cedente de exemplo","doc_cedente":"10062050000157","raiz_cedente":"10062050","nome_sacado":"Sacado de exemplo","doc_sacado":"22144961000102","raiz_sacado":"22144961","nu_documento":"000351153","tipo_recebivel":"Duplicata","valor_nominal":"10000.00","data_aquisicao":"2026-10-01","data_vencimento_original":"2026-10-31","prazo_dias":30},"motivos":[],"erros_dados":[],"desconto":"200.00","valor_liquido":"9800.00"},{"id":"00000000-0000-4000-8000-000000000021","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":2,"linha":3,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"01/10/2026"},"tipo":"ANALISE","status":"BARRADO","titulo":{"fundo_id":"00000000-0000-4000-8000-000000000001","nome_fundo":"ANTECIPE FIDC","doc_fundo":"92234400000180","nome_cedente":"Cedente de exemplo","doc_cedente":"10062050000157","raiz_cedente":"10062050","nome_sacado":"Sacado de exemplo","doc_sacado":"22144961000102","raiz_sacado":"22144961","nu_documento":"000351153","tipo_recebivel":"Duplicata","valor_nominal":"10000.00","data_aquisicao":"2026-10-01","data_vencimento_original":"2026-10-31","prazo_dias":30},"motivos":[{"codigo":"NOTA_DUPLICADA","mensagem":"Título já aprovado para este cedente, sacado e documento.","valor_observado":"000351153","limite_aplicado":null}],"erros_dados":[],"desconto":"0.00","valor_liquido":"0.00"},{"id":"00000000-0000-4000-8000-000000000022","lote_id":"00000000-0000-4000-8000-000000000012","arquivo_id":"00000000-0000-4000-8000-000000000011","sequencia":3,"linha":4,"dados_originais":{"NOME_FUNDO":"ANTECIPE FIDC","DOC_FUNDO":"92234400000180","NOME_CEDENTE":"Cedente de exemplo","DOC_CEDENTE":"10062050000157","NOME_SACADO":"Sacado de exemplo","DOC_SACADO":"22144961000102","NU_DOCUMENTO":"000351153","TIPO_RECEBIVEL":"Duplicata","VALOR_NOMINAL":"10000,00","DATA_VENCIMENTO_ORIGINAL":"31/10/2026","DATA_AQUISICAO":"31/02/2026"},"tipo":"ERRO_DADOS","status":null,"titulo":null,"motivos":[],"erros_dados":[{"campo":"DATA_AQUISICAO","codigo":"DATA_INVALIDA","mensagem":"Data inexistente no calendário."}],"desconto":"0.00","valor_liquido":"0.00"}],"proximo_cursor":null,"limit":50,"snapshot_ate_sequencia":3,"arquivo_finalizado":true}
}
```

## Fixtures detalhadas dos fluxos principais

Estes cenários complementam os exemplos por DTO. O arquivo/hash fictício não corresponde a bytes disponíveis: para testar upload real, gerar um arquivo e calcular seu hash/tamanho. O bloco contém criação, upload, fila, bloqueio, configuração, resultados e erro de versão.

```json
{
  "aviso": "Fixtures ilustrativas de cenários independentes, não execução do estoque; hash aaaa/arquivo de 1024 bytes são placeholders de contrato, não arquivo real.",
  "exemplos": [
    {
      "nome": "criar_lote",
      "schema": "CriarLoteRequest",
      "valor": {
        "nome": "Demonstração de contrato",
        "arquivos": [
          {
            "client_id": "00000000-0000-4000-8000-000000000010",
            "nome": "exemplo.csv",
            "formato": "CSV",
            "tamanho_bytes": 1024,
            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "ordem": 0,
            "aba": null
          }
        ]
      }
    },
    {
      "nome": "lote_criado",
      "schema": "CriarLoteResponse",
      "valor": {
        "lote": {
          "id": "00000000-0000-4000-8000-000000000012",
          "nome": "Demonstração de contrato",
          "status": "RECEBENDO",
          "criado_em": "2026-10-24T18:00:00Z",
          "iniciado_em": null,
          "concluido_em": null,
          "atualizado_em": "2026-10-24T18:00:00Z",
          "versao_cadastral": null,
          "progresso": {
            "fase": "AGUARDANDO",
            "arquivos_total": 1,
            "arquivos_recebidos": 0,
            "arquivos_falhos": 0,
            "bytes_esperados": 1024,
            "bytes_recebidos": 0,
            "linhas_lidas_primeira_passagem": 0,
            "linhas_total": null,
            "linhas_processadas": 0
          },
          "resumo": {
            "definitivo": false,
            "total_nominal": "0.00",
            "total_nominal_aprovado": "0.00",
            "total_nominal_barrado": "0.00",
            "total_nominal_erro_dados": "0.00",
            "total_desconto": "0.00",
            "total_liquido": "0.00",
            "aprovadas": 0,
            "barradas": 0,
            "erros_dados": 0
          },
          "quantidade_pendencias": 0,
          "acoes": {
            "pode_enviar_arquivos": true,
            "pode_iniciar": false,
            "pode_retomar": false,
            "precisa_corrigir_configuracao": false,
            "precisa_recriar_lote": false
          },
          "erro": null
        },
        "arquivos": [
          {
            "id": "00000000-0000-4000-8000-000000000011",
            "lote_id": "00000000-0000-4000-8000-000000000012",
            "client_id": "00000000-0000-4000-8000-000000000010",
            "nome": "exemplo.csv",
            "formato": "CSV",
            "tamanho_bytes": 1024,
            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "ordem": 0,
            "aba": null,
            "bytes_recebidos": 0,
            "status": "AGUARDANDO_UPLOAD",
            "linhas_total": null,
            "linhas_processadas": 0,
            "aprovadas": 0,
            "barradas": 0,
            "erros_dados": 0,
            "recebido_em": null,
            "concluido_em": null,
            "erro": null
          }
        ]
      }
    },
    {
      "nome": "metadados_batch",
      "schema": "BatchMetadadosDTO",
      "valor": {
        "arquivo_ids": [
          "00000000-0000-4000-8000-000000000011"
        ]
      }
    },
    {
      "nome": "batch_recebido",
      "schema": "EnviarBatchResponse",
      "valor": {
        "batch_id": "00000000-0000-4000-8000-000000000013",
        "lote_id": "00000000-0000-4000-8000-000000000012",
        "recebido_em": "2026-10-24T18:00:00Z",
        "arquivos": [
          {
            "arquivo_id": "00000000-0000-4000-8000-000000000011",
            "client_id": "00000000-0000-4000-8000-000000000010",
            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "bytes_recebidos": 1024,
            "status": "RECEBIDO"
          }
        ]
      }
    },
    {
      "nome": "processamento_aceito",
      "schema": "ProcessarLoteResponse",
      "valor": {
        "lote_id": "00000000-0000-4000-8000-000000000012",
        "execucao_id": "00000000-0000-4000-8000-000000000014",
        "status": "NA_FILA",
        "aceito_em": "2026-10-24T18:00:00Z",
        "status_url": "/api/v1/lotes/00000000-0000-4000-8000-000000000012"
      }
    },
    {
      "nome": "lote_bloqueado",
      "schema": "LoteDTO",
      "valor": {
        "id": "00000000-0000-4000-8000-000000000012",
        "nome": "Demonstração de contrato",
        "status": "BLOQUEADO",
        "criado_em": "2026-10-24T18:00:00Z",
        "iniciado_em": "2026-10-24T18:00:00Z",
        "concluido_em": null,
        "atualizado_em": "2026-10-24T18:00:00Z",
        "versao_cadastral": null,
        "progresso": {
          "fase": "INDEXACAO",
          "arquivos_total": 1,
          "arquivos_recebidos": 1,
          "arquivos_falhos": 0,
          "bytes_esperados": 1024,
          "bytes_recebidos": 1024,
          "linhas_lidas_primeira_passagem": 3,
          "linhas_total": 3,
          "linhas_processadas": 0
        },
        "resumo": {
          "definitivo": false,
          "total_nominal": "0.00",
          "total_nominal_aprovado": "0.00",
          "total_nominal_barrado": "0.00",
          "total_nominal_erro_dados": "0.00",
          "total_desconto": "0.00",
          "total_liquido": "0.00",
          "aprovadas": 0,
          "barradas": 0,
          "erros_dados": 0
        },
        "quantidade_pendencias": 1,
        "acoes": {
          "pode_enviar_arquivos": false,
          "pode_iniciar": false,
          "pode_retomar": true,
          "precisa_corrigir_configuracao": true,
          "precisa_recriar_lote": false
        },
        "erro": null
      }
    },
    {
      "nome": "pendencias",
      "schema": "PendenciasPageResponse",
      "valor": {
        "itens": [
          {
            "codigo": "FUNDO_SEM_REGRAS",
            "mensagem": "Configure as regras deste fundo antes de analisar o lote.",
            "fundo": {
              "id": "00000000-0000-4000-8000-000000000030",
              "nome": "FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS SAFIRA VAREJO RESPONSABILIDADE LIMITADA",
              "cnpj": "32482084000133",
              "configurado": false,
              "versao_regras_atual": null
            },
            "arquivo_id": null,
            "linha": null,
            "campo": null,
            "acao": "CONFIGURAR_FUNDO"
          }
        ],
        "proximo_cursor": null,
        "limit": 50
      }
    },
    {
      "nome": "configurar_fundo",
      "schema": "AtualizarRegrasRequest",
      "valor": {
        "versao_base": null,
        "configuracao": {
          "validadores": [
            {
              "codigo": "CNPJ_SACADO_VALIDO",
              "ativo": true,
              "parametros": {}
            },
            {
              "codigo": "SITUACAO_CADASTRAL_SACADO",
              "ativo": true,
              "parametros": {
                "situacoes_aceitas": [
                  "ATIVA"
                ]
              }
            },
            {
              "codigo": "TIPO_RECEBIVEL",
              "ativo": true,
              "parametros": {
                "tipos_aceitos": [
                  "Duplicata",
                  "Duplicata de Serviço"
                ]
              }
            },
            {
              "codigo": "VALOR_MINIMO",
              "ativo": true,
              "parametros": {
                "valor_minimo": "100.0"
              }
            },
            {
              "codigo": "NAO_VENCIDA",
              "ativo": true,
              "parametros": {}
            },
            {
              "codigo": "PRAZO_MAXIMO",
              "ativo": true,
              "parametros": {
                "prazo_maximo_dias": 180
              }
            },
            {
              "codigo": "CONCENTRACAO_MAXIMA_SACADO",
              "ativo": true,
              "parametros": {
                "percentual_maximo": "10.0",
                "agrupamento": "RAIZ_CNPJ"
              }
            },
            {
              "codigo": "PRAZO_MINIMO",
              "ativo": false,
              "parametros": {
                "prazo_minimo_dias": 30
              }
            },
            {
              "codigo": "CONCENTRACAO_MAXIMA_CEDENTE",
              "ativo": false,
              "parametros": {
                "percentual_maximo": "8.0",
                "agrupamento": "RAIZ_CNPJ"
              }
            }
          ],
          "precificacao": {
            "metodo": "DESCONTO_SIMPLES",
            "taxa_mensal_percentual": "2.0",
            "base_dias": 30
          }
        }
      }
    },
    {
      "nome": "regras_publicadas",
      "schema": "RegrasFundoResponse",
      "valor": {
        "fundo": {
          "id": "00000000-0000-4000-8000-000000000001",
          "nome": "ANTECIPE FIDC",
          "cnpj": "92234400000180",
          "configurado": true,
          "versao_regras_atual": "00000000-0000-4000-8000-000000000002"
        },
        "versao": "00000000-0000-4000-8000-000000000002",
        "criada_em": "2026-10-24T18:00:00Z",
        "configuracao": {
          "validadores": [
            {
              "codigo": "CNPJ_SACADO_VALIDO",
              "ativo": true,
              "parametros": {}
            },
            {
              "codigo": "SITUACAO_CADASTRAL_SACADO",
              "ativo": true,
              "parametros": {
                "situacoes_aceitas": [
                  "ATIVA"
                ]
              }
            },
            {
              "codigo": "TIPO_RECEBIVEL",
              "ativo": true,
              "parametros": {
                "tipos_aceitos": [
                  "Duplicata",
                  "Duplicata de Serviço"
                ]
              }
            },
            {
              "codigo": "VALOR_MINIMO",
              "ativo": true,
              "parametros": {
                "valor_minimo": "100.0"
              }
            },
            {
              "codigo": "NAO_VENCIDA",
              "ativo": true,
              "parametros": {}
            },
            {
              "codigo": "PRAZO_MAXIMO",
              "ativo": true,
              "parametros": {
                "prazo_maximo_dias": 180
              }
            },
            {
              "codigo": "CONCENTRACAO_MAXIMA_SACADO",
              "ativo": true,
              "parametros": {
                "percentual_maximo": "10.0",
                "agrupamento": "RAIZ_CNPJ"
              }
            },
            {
              "codigo": "PRAZO_MINIMO",
              "ativo": false,
              "parametros": {
                "prazo_minimo_dias": 30
              }
            },
            {
              "codigo": "CONCENTRACAO_MAXIMA_CEDENTE",
              "ativo": false,
              "parametros": {
                "percentual_maximo": "8.0",
                "agrupamento": "RAIZ_CNPJ"
              }
            }
          ],
          "precificacao": {
            "metodo": "DESCONTO_SIMPLES",
            "taxa_mensal_percentual": "2.0",
            "base_dias": 30
          }
        }
      }
    },
    {
      "nome": "resultados",
      "schema": "ResultadosPageResponse",
      "valor": {
        "itens": [
          {
            "id": "00000000-0000-4000-8000-000000000020",
            "lote_id": "00000000-0000-4000-8000-000000000012",
            "arquivo_id": "00000000-0000-4000-8000-000000000011",
            "sequencia": 1,
            "linha": 2,
            "dados_originais": {
              "NOME_FUNDO": "ANTECIPE FIDC",
              "DOC_FUNDO": "92234400000180",
              "NOME_CEDENTE": "Cedente de exemplo",
              "DOC_CEDENTE": "10062050000157",
              "NOME_SACADO": "Sacado de exemplo",
              "DOC_SACADO": "22144961000102",
              "NU_DOCUMENTO": "000351153",
              "TIPO_RECEBIVEL": "Duplicata",
              "VALOR_NOMINAL": "10000,00",
              "DATA_VENCIMENTO_ORIGINAL": "31/10/2026",
              "DATA_AQUISICAO": "01/10/2026"
            },
            "tipo": "ANALISE",
            "status": "APROVADO",
            "titulo": {
              "fundo_id": "00000000-0000-4000-8000-000000000001",
              "nome_fundo": "ANTECIPE FIDC",
              "doc_fundo": "92234400000180",
              "nome_cedente": "Cedente de exemplo",
              "doc_cedente": "10062050000157",
              "raiz_cedente": "10062050",
              "nome_sacado": "Sacado de exemplo",
              "doc_sacado": "22144961000102",
              "raiz_sacado": "22144961",
              "nu_documento": "000351153",
              "tipo_recebivel": "Duplicata",
              "valor_nominal": "10000.00",
              "data_aquisicao": "2026-10-01",
              "data_vencimento_original": "2026-10-31",
              "prazo_dias": 30
            },
            "motivos": [],
            "erros_dados": [],
            "desconto": "200.00",
            "valor_liquido": "9800.00"
          },
          {
            "id": "00000000-0000-4000-8000-000000000021",
            "lote_id": "00000000-0000-4000-8000-000000000012",
            "arquivo_id": "00000000-0000-4000-8000-000000000011",
            "sequencia": 2,
            "linha": 3,
            "dados_originais": {
              "NOME_FUNDO": "ANTECIPE FIDC",
              "DOC_FUNDO": "92234400000180",
              "NOME_CEDENTE": "Cedente de exemplo",
              "DOC_CEDENTE": "10062050000157",
              "NOME_SACADO": "Sacado de exemplo",
              "DOC_SACADO": "22144961000102",
              "NU_DOCUMENTO": "000351153",
              "TIPO_RECEBIVEL": "Duplicata",
              "VALOR_NOMINAL": "10000,00",
              "DATA_VENCIMENTO_ORIGINAL": "31/10/2026",
              "DATA_AQUISICAO": "01/10/2026"
            },
            "tipo": "ANALISE",
            "status": "BARRADO",
            "titulo": {
              "fundo_id": "00000000-0000-4000-8000-000000000001",
              "nome_fundo": "ANTECIPE FIDC",
              "doc_fundo": "92234400000180",
              "nome_cedente": "Cedente de exemplo",
              "doc_cedente": "10062050000157",
              "raiz_cedente": "10062050",
              "nome_sacado": "Sacado de exemplo",
              "doc_sacado": "22144961000102",
              "raiz_sacado": "22144961",
              "nu_documento": "000351153",
              "tipo_recebivel": "Duplicata",
              "valor_nominal": "10000.00",
              "data_aquisicao": "2026-10-01",
              "data_vencimento_original": "2026-10-31",
              "prazo_dias": 30
            },
            "motivos": [
              {
                "codigo": "NOTA_DUPLICADA",
                "mensagem": "Título já aprovado para este cedente, sacado e documento.",
                "valor_observado": "000351153",
                "limite_aplicado": null
              }
            ],
            "erros_dados": [],
            "desconto": "0.00",
            "valor_liquido": "0.00"
          },
          {
            "id": "00000000-0000-4000-8000-000000000022",
            "lote_id": "00000000-0000-4000-8000-000000000012",
            "arquivo_id": "00000000-0000-4000-8000-000000000011",
            "sequencia": 3,
            "linha": 4,
            "dados_originais": {
              "NOME_FUNDO": "ANTECIPE FIDC",
              "DOC_FUNDO": "92234400000180",
              "NOME_CEDENTE": "Cedente de exemplo",
              "DOC_CEDENTE": "10062050000157",
              "NOME_SACADO": "Sacado de exemplo",
              "DOC_SACADO": "22144961000102",
              "NU_DOCUMENTO": "000351153",
              "TIPO_RECEBIVEL": "Duplicata",
              "VALOR_NOMINAL": "10000,00",
              "DATA_VENCIMENTO_ORIGINAL": "31/10/2026",
              "DATA_AQUISICAO": "31/02/2026"
            },
            "tipo": "ERRO_DADOS",
            "status": null,
            "titulo": null,
            "motivos": [],
            "erros_dados": [
              {
                "campo": "DATA_AQUISICAO",
                "codigo": "DATA_INVALIDA",
                "mensagem": "Data inexistente no calendário."
              }
            ],
            "desconto": "0.00",
            "valor_liquido": "0.00"
          }
        ],
        "proximo_cursor": null,
        "limit": 50,
        "snapshot_ate_sequencia": 3,
        "arquivo_finalizado": true
      }
    },
    {
      "nome": "erro_versao",
      "schema": "ErroResponse",
      "valor": {
        "request_id": "00000000-0000-4000-8000-000000000099",
        "erro": {
          "codigo": "VERSAO_REGRAS_CONFLITANTE",
          "mensagem": "As regras foram alteradas por outra operação. Recarregue a configuração.",
          "retry_permitido": false,
          "detalhes": [],
          "versao_atual": "00000000-0000-4000-8000-000000000003"
        }
      }
    },
    {
      "nome": "capacidades",
      "schema": "CapacidadesResponse",
      "valor": {
        "versao_contrato": "1.0.0",
        "autenticacao": "SEM_AUTENTICACAO_DEMO",
        "formatos": [
          "CSV",
          "XLSX"
        ],
        "max_arquivos_lote": 100,
        "max_arquivos_batch": 3,
        "max_bytes_arquivo": 67108864,
        "max_bytes_batch": 67108864,
        "max_linhas_lote": 500000,
        "max_pagina": 100,
        "polling_intervalo_ms": 2000,
        "permite_exportacao": false,
        "permite_cancelamento": false
      }
    },
    {
      "nome": "cadastro_disponivel",
      "schema": "BaseCadastralStatusResponse",
      "valor": {
        "disponivel": true,
        "versao": "00000000-0000-4000-8000-000000000040",
        "sha256": "522ba08c9685a48d2c2a5b20bfde0773f58bb15b095e03cf605b44c224ca6916",
        "quantidade_cnpjs": 3041,
        "importado_em": "2026-10-24T18:00:00Z"
      }
    }
  ]
}
```

## Antes de concluir o planejamento

Verifique que toda ação planejada usa uma das operações acima; nenhum cálculo decisório foi transferido ao frontend; cada tarefa possui testes; e o fluxo cobre fundos não configurados, retry sem duplicação, conflito de versão, leitura por cursor e erro de dados separado de recusa financeira. Não é necessário solicitar nenhum outro arquivo para elaborar esse plano.

<!-- FIM DO PROMPT -->
