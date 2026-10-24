# Catálogo gerado de DTOs

Fonte editável: `scripts/gerar_contrato_api.py`. Regras de fluxo: [contrato-api.md](../contrato-api.md).

## Dinheiro

Decimal em BRL, ponto e duas casas; nunca JSON number.

```typescript
string
```

## DecimalNaoNegativo

Decimal exato não negativo; até 8 casas, sem notação científica.

```typescript
string
```

## CodigoRecusa

```typescript
"NOTA_DUPLICADA" | "CNPJ_SACADO_VALIDO" | "SITUACAO_CADASTRAL_SACADO" | "TIPO_RECEBIVEL" | "VALOR_MINIMO" | "NAO_VENCIDA" | "PRAZO_MINIMO" | "PRAZO_MAXIMO" | "CONCENTRACAO_MAXIMA_SACADO" | "CONCENTRACAO_MAXIMA_CEDENTE"
```

## StatusNota

```typescript
"APROVADO" | "BARRADO"
```

## StatusLote

```typescript
"RECEBENDO" | "NA_FILA" | "INDEXANDO" | "BLOQUEADO" | "ANALISANDO" | "CONCLUIDO" | "CONCLUIDO_COM_ERROS" | "FALHOU"
```

## StatusArquivo

```typescript
"AGUARDANDO_UPLOAD" | "RECEBIDO" | "INDEXANDO" | "PRONTO" | "ANALISANDO" | "CONCLUIDO" | "CONCLUIDO_COM_ERROS" | "FALHOU"
```

## FormatoArquivo

```typescript
"CSV" | "XLSX"
```

## CodigoErro

```typescript
"VALIDACAO_REQUISICAO" | "RECURSO_NAO_ENCONTRADO" | "ESTADO_INVALIDO" | "IDEMPOTENCIA_CONFLITANTE" | "REQUISICAO_EM_ANDAMENTO" | "UPLOAD_INCOMPLETO" | "LIMITE_UPLOAD_EXCEDIDO" | "LIMITE_LOTE_EXCEDIDO" | "TIPO_ARQUIVO_NAO_SUPORTADO" | "INTEGRIDADE_ARQUIVO" | "ARQUIVO_FORA_MANIFESTO" | "ARQUIVO_JA_RECEBIDO" | "CURSOR_INVALIDO" | "VERSAO_REGRAS_CONFLITANTE" | "CONFIGURACAO_INVALIDA" | "ESTRUTURA_ARQUIVO_INVALIDA" | "ARQUIVO_CORROMPIDO" | "DADOS_IMPEDEM_PL" | "FUNDOS_SEM_REGRAS" | "BASE_CADASTRAL_INDISPONIVEL" | "INFRAESTRUTURA_INDISPONIVEL" | "ERRO_INTERNO"
```

## DetalheErroDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `campo` | `string \| null` | sim | — |
| `codigo` | `string` | sim | — |
| `mensagem` | `string` | sim | — |

## ErroDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `CodigoErro` | sim | — |
| `mensagem` | `string` | sim | — |
| `retry_permitido` | `boolean` | sim | — |
| `detalhes` | `Array<DetalheErroDTO>` | sim | — |
| `versao_atual` | `string \| null` | sim | — |

## ErroResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `request_id` | `string` | sim | — |
| `erro` | `ErroDTO` | sim | — |

## SaudeResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `"OK"` | sim | — |
| `servico` | `"antecipe-api"` | sim | — |
| `versao_api` | `"1.0.0"` | sim | — |
| `verificado_em` | `string` | sim | — |

## CapacidadesResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `versao_contrato` | `"1.0.0"` | sim | — |
| `autenticacao` | `"SEM_AUTENTICACAO_DEMO"` | sim | — |
| `formatos` | `Array<FormatoArquivo>` | sim | — |
| `max_arquivos_lote` | `number` | sim | — |
| `max_arquivos_batch` | `number` | sim | — |
| `max_bytes_arquivo` | `number` | sim | — |
| `max_bytes_batch` | `number` | sim | — |
| `max_linhas_lote` | `number` | sim | — |
| `max_pagina` | `number` | sim | — |
| `polling_intervalo_ms` | `number` | sim | — |
| `permite_exportacao` | `boolean` | sim | — |
| `permite_cancelamento` | `boolean` | sim | — |

## BaseCadastralStatusResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `disponivel` | `boolean` | sim | — |
| `versao` | `string \| null` | sim | — |
| `sha256` | `string \| null` | sim | — |
| `quantidade_cnpjs` | `number` | sim | — |
| `importado_em` | `string \| null` | sim | — |

## FundoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `nome` | `string` | sim | — |
| `cnpj` | `string` | sim | — |
| `configurado` | `boolean` | sim | — |
| `versao_regras_atual` | `string \| null` | sim | — |

## ParametrosVaziosDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| — | objeto vazio | — | Não aceita propriedades. |

## ParametrosSituacaoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `situacoes_aceitas` | `Array<"ATIVA" \| "SUSPENSA" \| "INAPTA" \| "BAIXADA">` | sim | — |

## ParametrosTipoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `tipos_aceitos` | `Array<"Duplicata" \| "Duplicata de Serviço" \| "Cheque" \| "CCB" \| "Nota Comercial">` | sim | — |

## ParametrosValorMinimoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `valor_minimo` | `DecimalNaoNegativo` | sim | — |

## ParametrosPrazoMinimoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `prazo_minimo_dias` | `number` | sim | — |

## ParametrosPrazoMaximoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `prazo_maximo_dias` | `number` | sim | — |

## ParametrosConcentracaoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `percentual_maximo` | `DecimalNaoNegativo` | sim | Entre 0 e 100, inclusive; limite semântico validado pelo servidor. |
| `agrupamento` | `"RAIZ_CNPJ"` | sim | — |

## ValidadorCnpjSacadoValidoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"CNPJ_SACADO_VALIDO"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorSituacaoCadastralSacadoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"SITUACAO_CADASTRAL_SACADO"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorTipoRecebivelDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"TIPO_RECEBIVEL"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorValorMinimoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"VALOR_MINIMO"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorNaoVencidaDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"NAO_VENCIDA"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorPrazoMinimoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"PRAZO_MINIMO"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorPrazoMaximoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"PRAZO_MAXIMO"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorConcentracaoMaximaSacadoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"CONCENTRACAO_MAXIMA_SACADO"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorConcentracaoMaximaCedenteDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"CONCENTRACAO_MAXIMA_CEDENTE"` | sim | — |
| `ativo` | `boolean` | sim | — |
| `parametros` | `Record<string, unknown>` | sim | — |

## ValidadorDTO

```typescript
ValidadorCnpjSacadoValidoDTO | ValidadorSituacaoCadastralSacadoDTO | ValidadorTipoRecebivelDTO | ValidadorValorMinimoDTO | ValidadorNaoVencidaDTO | ValidadorPrazoMinimoDTO | ValidadorPrazoMaximoDTO | ValidadorConcentracaoMaximaSacadoDTO | ValidadorConcentracaoMaximaCedenteDTO
```

## PrecificacaoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `metodo` | `"DESCONTO_SIMPLES"` | sim | — |
| `taxa_mensal_percentual` | `DecimalNaoNegativo` | sim | — |
| `base_dias` | `number` | sim | — |

## ConfiguracaoRegrasDTO

Exatamente uma ocorrência de cada código configurável. NOTA_DUPLICADA não é configurável. Somente parâmetros de validadores ativos são validados.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `validadores` | `Array<ValidadorDTO>` | sim | — |
| `precificacao` | `PrecificacaoDTO` | sim | — |

## AtualizarRegrasRequest

versao_base=null somente para primeira configuração; para edição, versão obtida no GET. Atualização integral dos nove validadores.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `versao_base` | `string \| null` | sim | — |
| `configuracao` | `ConfiguracaoRegrasDTO` | sim | — |

## RegrasFundoResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fundo` | `FundoDTO` | sim | — |
| `versao` | `string` | sim | — |
| `criada_em` | `string` | sim | — |
| `configuracao` | `ConfiguracaoRegrasDTO` | sim | — |

## ImportarRegrasRequest

Conteúdo do JSON de inputs: objeto com fundo, validadores e precificacao, ou array de até 100 objetos. Aceita decimais numéricos do formato de inputs. Validação semântica integral antes de publicar; importação atômica.

```typescript
Record<string, unknown> | Array<Record<string, unknown>>
```

## ImportarRegrasResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fundos` | `Array<FundoDTO>` | sim | — |

## ArquivoManifestoRequest

client_id gerado pelo front e único no lote. ordem deve ser contígua de 0 a N-1. aba=null para CSV; XLSX null seleciona primeira aba com dados.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `client_id` | `string` | sim | — |
| `nome` | `string` | sim | — |
| `formato` | `FormatoArquivo` | sim | — |
| `tamanho_bytes` | `number` | sim | — |
| `sha256` | `string` | sim | — |
| `ordem` | `number` | sim | — |
| `aba` | `string \| null` | sim | — |

## CriarLoteRequest

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `nome` | `string` | sim | — |
| `arquivos` | `Array<ArquivoManifestoRequest>` | sim | — |

## ArquivoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `lote_id` | `string` | sim | — |
| `client_id` | `string` | sim | — |
| `nome` | `string` | sim | — |
| `formato` | `FormatoArquivo` | sim | — |
| `ordem` | `number` | sim | — |
| `aba` | `string \| null` | sim | — |
| `tamanho_bytes` | `number` | sim | — |
| `sha256` | `string` | sim | — |
| `bytes_recebidos` | `number` | sim | — |
| `status` | `StatusArquivo` | sim | — |
| `linhas_total` | `number \| null` | sim | — |
| `linhas_processadas` | `number` | sim | — |
| `aprovadas` | `number` | sim | — |
| `barradas` | `number` | sim | — |
| `erros_dados` | `number` | sim | — |
| `recebido_em` | `string \| null` | sim | — |
| `concluido_em` | `string \| null` | sim | — |
| `erro` | `ErroDTO \| null` | sim | — |

## ProgressoDTO

Contadores persistidos. Total null até terminar indexação. Não somar as duas passagens como notas diferentes.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fase` | `"AGUARDANDO" \| "INDEXACAO" \| "ANALISE" \| "FINALIZADO"` | sim | — |
| `arquivos_total` | `number` | sim | — |
| `arquivos_recebidos` | `number` | sim | — |
| `arquivos_falhos` | `number` | sim | — |
| `bytes_esperados` | `number` | sim | — |
| `bytes_recebidos` | `number` | sim | — |
| `linhas_lidas_primeira_passagem` | `number` | sim | — |
| `linhas_total` | `number \| null` | sim | — |
| `linhas_processadas` | `number` | sim | — |

## ResumoFinanceiroDTO

Durante execução, totais parciais; total_nominal é PL dos arquivos válidos após indexação. Não é patrimônio global histórico do fundo.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `definitivo` | `boolean` | sim | — |
| `total_nominal` | `Dinheiro` | sim | — |
| `total_nominal_aprovado` | `Dinheiro` | sim | — |
| `total_nominal_barrado` | `Dinheiro` | sim | — |
| `total_nominal_erro_dados` | `Dinheiro` | sim | — |
| `total_desconto` | `Dinheiro` | sim | — |
| `total_liquido` | `Dinheiro` | sim | — |
| `aprovadas` | `number` | sim | — |
| `barradas` | `number` | sim | — |
| `erros_dados` | `number` | sim | — |

## AcoesLoteDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `pode_enviar_arquivos` | `boolean` | sim | — |
| `pode_iniciar` | `boolean` | sim | — |
| `pode_retomar` | `boolean` | sim | — |
| `precisa_corrigir_configuracao` | `boolean` | sim | — |
| `precisa_recriar_lote` | `boolean` | sim | — |

## LoteDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `nome` | `string` | sim | — |
| `status` | `StatusLote` | sim | — |
| `criado_em` | `string` | sim | — |
| `iniciado_em` | `string \| null` | sim | — |
| `concluido_em` | `string \| null` | sim | — |
| `atualizado_em` | `string` | sim | — |
| `versao_cadastral` | `string \| null` | sim | — |
| `progresso` | `ProgressoDTO` | sim | — |
| `resumo` | `ResumoFinanceiroDTO` | sim | — |
| `quantidade_pendencias` | `number` | sim | — |
| `acoes` | `AcoesLoteDTO` | sim | — |
| `erro` | `ErroDTO \| null` | sim | — |

## CriarLoteResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `lote` | `LoteDTO` | sim | — |
| `arquivos` | `Array<ArquivoDTO>` | sim | — |

## LoteResumoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `nome` | `string` | sim | — |
| `status` | `StatusLote` | sim | — |
| `criado_em` | `string` | sim | — |
| `atualizado_em` | `string` | sim | — |
| `arquivos_total` | `number` | sim | — |
| `linhas_processadas` | `number` | sim | — |
| `total_liquido` | `Dinheiro` | sim | — |

## BatchMetadadosDTO

A posição de arquivo_ids corresponde à posição de cada parte multipart arquivos. Não mapear por nome do arquivo.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `arquivo_ids` | `Array<string>` | sim | — |

## EnviarBatchRequest

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `metadados` | `string` | sim | JSON serializado de BatchMetadadosDTO; campo textual do FormData. |
| `arquivos` | `Array<Blob>` | sim | — |

## ArquivoRecebidoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `arquivo_id` | `string` | sim | — |
| `client_id` | `string` | sim | — |
| `sha256` | `string` | sim | — |
| `bytes_recebidos` | `number` | sim | — |
| `status` | `"RECEBIDO"` | sim | — |

## EnviarBatchResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `batch_id` | `string` | sim | — |
| `lote_id` | `string` | sim | — |
| `recebido_em` | `string` | sim | — |
| `arquivos` | `Array<ArquivoRecebidoDTO>` | sim | — |

## ProcessarLoteResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `lote_id` | `string` | sim | — |
| `execucao_id` | `string` | sim | — |
| `status` | `"NA_FILA"` | sim | — |
| `aceito_em` | `string` | sim | — |
| `status_url` | `string` | sim | — |

## PendenciaDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `"FUNDO_SEM_REGRAS" \| "BASE_CADASTRAL_AUSENTE" \| "DADOS_IMPEDEM_PL"` | sim | — |
| `mensagem` | `string` | sim | — |
| `fundo` | `FundoDTO \| null` | sim | — |
| `arquivo_id` | `string \| null` | sim | — |
| `linha` | `number \| null` | sim | — |
| `campo` | `string \| null` | sim | — |
| `acao` | `"CONFIGURAR_FUNDO" \| "IMPORTAR_BASE_CADASTRAL" \| "RECRIAR_LOTE"` | sim | — |

## ResumoFundoDTO

Limite null se regra inativa ou contexto ainda não congelado. versao_regras_utilizada identifica a versão histórica, não necessariamente a atual do fundo.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fundo` | `FundoDTO` | sim | — |
| `versao_regras_utilizada` | `string \| null` | sim | — |
| `pl` | `Dinheiro` | sim | — |
| `limite_sacado` | `Dinheiro \| null` | sim | — |
| `limite_cedente` | `Dinheiro \| null` | sim | — |
| `resumo` | `ResumoFinanceiroDTO` | sim | — |

## MotivoDTO

Explicação para exibição; frontend não recalcula a regra nem interpreta os valores textuais como contrato de cálculo.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `codigo` | `CodigoRecusa` | sim | — |
| `mensagem` | `string` | sim | — |
| `valor_observado` | `string \| null` | sim | — |
| `limite_aplicado` | `string \| null` | sim | — |

## ErroDadoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `campo` | `string` | sim | — |
| `codigo` | `"OBRIGATORIO" \| "FORMATO_INVALIDO" \| "DATA_INVALIDA" \| "DECIMAL_INVALIDO" \| "FORMULA_SEM_VALOR" \| "DOCUMENTO_SEM_RAIZ" \| "FUNDO_SEM_REGRAS"` | sim | — |
| `mensagem` | `string` | sim | — |

## DadosOriginaisTituloDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `NOME_FUNDO` | `string \| null` | sim | — |
| `DOC_FUNDO` | `string \| null` | sim | — |
| `NOME_CEDENTE` | `string \| null` | sim | — |
| `DOC_CEDENTE` | `string \| null` | sim | — |
| `NOME_SACADO` | `string \| null` | sim | — |
| `DOC_SACADO` | `string \| null` | sim | — |
| `NU_DOCUMENTO` | `string \| null` | sim | — |
| `TIPO_RECEBIVEL` | `string \| null` | sim | — |
| `VALOR_NOMINAL` | `string \| null` | sim | — |
| `DATA_VENCIMENTO_ORIGINAL` | `string \| null` | sim | — |
| `DATA_AQUISICAO` | `string \| null` | sim | — |

## TituloNormalizadoDTO

Documento observado pode ser inválido e gerar CNPJ_SACADO_VALIDO. Não aplicar regex CNPJ válido aos campos doc_sacado/cedente do resultado.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fundo_id` | `string` | sim | — |
| `nome_fundo` | `string` | sim | — |
| `doc_fundo` | `string` | sim | — |
| `nome_cedente` | `string` | sim | — |
| `doc_cedente` | `string` | sim | — |
| `raiz_cedente` | `string \| null` | sim | — |
| `nome_sacado` | `string` | sim | — |
| `doc_sacado` | `string` | sim | — |
| `raiz_sacado` | `string \| null` | sim | — |
| `nu_documento` | `string` | sim | — |
| `tipo_recebivel` | `string` | sim | — |
| `valor_nominal` | `Dinheiro` | sim | — |
| `data_aquisicao` | `string` | sim | — |
| `data_vencimento_original` | `string` | sim | — |
| `prazo_dias` | `number` | sim | — |

## ResultadoAprovadoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `lote_id` | `string` | sim | — |
| `arquivo_id` | `string` | sim | — |
| `sequencia` | `number` | sim | — |
| `linha` | `number` | sim | — |
| `dados_originais` | `DadosOriginaisTituloDTO` | sim | — |
| `tipo` | `"ANALISE"` | sim | — |
| `status` | `"APROVADO"` | sim | — |
| `titulo` | `TituloNormalizadoDTO` | sim | — |
| `motivos` | `Array<MotivoDTO>` | sim | — |
| `erros_dados` | `Array<ErroDadoDTO>` | sim | — |
| `desconto` | `Dinheiro` | sim | — |
| `valor_liquido` | `Dinheiro` | sim | — |

## ResultadoBarradoDTO

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `lote_id` | `string` | sim | — |
| `arquivo_id` | `string` | sim | — |
| `sequencia` | `number` | sim | — |
| `linha` | `number` | sim | — |
| `dados_originais` | `DadosOriginaisTituloDTO` | sim | — |
| `tipo` | `"ANALISE"` | sim | — |
| `status` | `"BARRADO"` | sim | — |
| `titulo` | `TituloNormalizadoDTO` | sim | — |
| `motivos` | `Array<MotivoDTO>` | sim | — |
| `erros_dados` | `Array<ErroDadoDTO>` | sim | — |
| `desconto` | `"0.00"` | sim | — |
| `valor_liquido` | `"0.00"` | sim | — |

## ResultadoErroDadosDTO

Diagnóstico de parsing; não é um novo status financeiro nem um novo código de recusa FIDC. Usar dados_originais na interface.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `string` | sim | — |
| `lote_id` | `string` | sim | — |
| `arquivo_id` | `string` | sim | — |
| `sequencia` | `number` | sim | — |
| `linha` | `number` | sim | — |
| `dados_originais` | `DadosOriginaisTituloDTO` | sim | — |
| `tipo` | `"ERRO_DADOS"` | sim | — |
| `status` | `null` | sim | — |
| `titulo` | `null` | sim | — |
| `motivos` | `Array<MotivoDTO>` | sim | — |
| `erros_dados` | `Array<ErroDadoDTO>` | sim | — |
| `desconto` | `"0.00"` | sim | — |
| `valor_liquido` | `"0.00"` | sim | — |

## ResultadoDTO

```typescript
ResultadoAprovadoDTO | ResultadoBarradoDTO | ResultadoErroDadosDTO
```

## PaginacaoQuery

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `limit` | `number` | não | — |
| `cursor` | `string` | não | — |

## ListarFundosQuery

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `limit` | `number` | não | — |
| `cursor` | `string` | não | — |
| `busca` | `string` | não | — |
| `configurado` | `boolean` | não | — |

## ListarLotesQuery

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `limit` | `number` | não | — |
| `cursor` | `string` | não | — |
| `status` | `StatusLote` | não | — |

## ConsultarRegrasQuery

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `versao` | `string` | não | — |

## ListarResultadosQuery

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `limit` | `number` | não | — |
| `cursor` | `string` | não | — |
| `status` | `StatusNota` | não | — |
| `motivo` | `CodigoRecusa` | não | — |
| `tipo` | `"ANALISE" \| "ERRO_DADOS"` | não | — |

## FundosPageResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `itens` | `Array<FundoDTO>` | sim | — |
| `proximo_cursor` | `string \| null` | sim | — |
| `limit` | `number` | sim | — |

## LotesPageResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `itens` | `Array<LoteResumoDTO>` | sim | — |
| `proximo_cursor` | `string \| null` | sim | — |
| `limit` | `number` | sim | — |

## ArquivosPageResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `itens` | `Array<ArquivoDTO>` | sim | — |
| `proximo_cursor` | `string \| null` | sim | — |
| `limit` | `number` | sim | — |

## PendenciasPageResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `itens` | `Array<PendenciaDTO>` | sim | — |
| `proximo_cursor` | `string \| null` | sim | — |
| `limit` | `number` | sim | — |

## ResumosFundosPageResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `itens` | `Array<ResumoFundoDTO>` | sim | — |
| `proximo_cursor` | `string \| null` | sim | — |
| `limit` | `number` | sim | — |

## ResultadosPageResponse

Cursor fixa teto de sequência e filtros. Refazer primeira página para incluir resultados mais recentes. Não fornece total filtrado nem salto arbitrário de página.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `itens` | `Array<ResultadoDTO>` | sim | — |
| `proximo_cursor` | `string \| null` | sim | — |
| `limit` | `number` | sim | — |
| `snapshot_ate_sequencia` | `number` | sim | — |
| `arquivo_finalizado` | `boolean` | sim | — |

