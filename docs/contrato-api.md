# Contrato de integração Antecipe — v1.0.0

Contrato final de planejamento para implementação independente do frontend e backend. **Os endpoints ainda não estão implementados.** As decisões abaixo complementam os pontos não especificados pelo PDF; não indicam execução ou certificação do motor.

## Fontes compartilhadas

- [OpenAPI 3.1](contratos/openapi.json): rotas, parâmetros, headers, corpos, respostas, restrições e unions dos DTOs.
- [Catálogo campo a campo dos DTOs](contratos/dtos.md): obrigatoriedade, tipos e descrições.
- [Tipos TypeScript](contratos/api-types.ts): derivados dos mesmos schemas; importar no frontend.
- [Exemplos JSON](contratos/exemplos.json): fixtures de contrato, não resultados calculados sobre o estoque oficial.
- [Plano de implementação](planejamento-backend.md) e [auditoria dos insumos](auditoria-insumos.md).

A definição editável dos schemas é `scripts/gerar_contrato_api.py`. Alterar esse arquivo e regenerar todos os artefatos em conjunto, inclusive o prompt autocontido do frontend; não editar tipos e OpenAPI separadamente. A implementação FastAPI deve reproduzir este contrato e ter testes de compatibilidade contra ele. Mudanças incompatíveis exigem atualização coordenada de ambos os planos e nova versão principal da API.

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

## Limitação da aceitação oficial

A leitura integral comprovou divergências nos insumos, detalhadas na auditoria. Isso **não impede fechar os DTOs nem implementar o sistema**. Impede prometer zero divergências com o gabarito atual sem corrigir dados, fornecer regras dos outros fundos ou revisar expressamente os requisitos. Os testes sintéticos devem preservar as regras acordadas; o comparador oficial deve evidenciar as divergências, nunca ocultá-las.

## Verificação reproduzível dos artefatos

Em um ambiente Python separado, instalar `scripts/requirements-contratos.txt`, executar `python scripts/gerar_contrato_api.py` e `python scripts/validar_contrato_api.py`. O validador verifica OpenAPI, schemas, exemplos válidos e rejeição de fixtures inválidas, incluindo dinheiro numérico, códigos duplicados e variantes incompatíveis de resultado. Compilar `docs/contratos/api-types.ts` com TypeScript em modo `--noEmit --strict --lib ES2020,DOM`. Isso testa os artefatos de planejamento, não a execução dos endpoints.

Verificação desta entrega: OpenAPI 3.1 válido, 71 schemas, 17 operações, 13 exemplos válidos e 16 casos inválidos rejeitados; tipos compilados com TypeScript 5.9.3 em modo strict. A auditoria dos insumos foi executada integralmente. Testes do backend e integração real continuam nas tarefas T01–T18.
