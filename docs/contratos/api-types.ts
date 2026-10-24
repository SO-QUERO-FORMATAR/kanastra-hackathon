// GERADO por scripts/gerar_contrato_api.py. Não editar manualmente.
// Contrato planejado v1.0.0; tipos estáticos não substituem validação em runtime.

/** Decimal em BRL, ponto e duas casas; nunca JSON number. */
export type Dinheiro = string;

/** Decimal exato não negativo; até 8 casas, sem notação científica. */
export type DecimalNaoNegativo = string;

export type CodigoRecusa = "NOTA_DUPLICADA" | "CNPJ_SACADO_VALIDO" | "SITUACAO_CADASTRAL_SACADO" | "TIPO_RECEBIVEL" | "VALOR_MINIMO" | "NAO_VENCIDA" | "PRAZO_MINIMO" | "PRAZO_MAXIMO" | "CONCENTRACAO_MAXIMA_SACADO" | "CONCENTRACAO_MAXIMA_CEDENTE";

export type StatusNota = "APROVADO" | "BARRADO";

export type StatusLote = "RECEBENDO" | "NA_FILA" | "INDEXANDO" | "BLOQUEADO" | "ANALISANDO" | "CONCLUIDO" | "CONCLUIDO_COM_ERROS" | "FALHOU";

export type StatusArquivo = "AGUARDANDO_UPLOAD" | "RECEBIDO" | "INDEXANDO" | "PRONTO" | "ANALISANDO" | "CONCLUIDO" | "CONCLUIDO_COM_ERROS" | "FALHOU";

export type FormatoArquivo = "CSV" | "XLSX";

export type CodigoErro = "VALIDACAO_REQUISICAO" | "RECURSO_NAO_ENCONTRADO" | "ESTADO_INVALIDO" | "IDEMPOTENCIA_CONFLITANTE" | "REQUISICAO_EM_ANDAMENTO" | "UPLOAD_INCOMPLETO" | "LIMITE_UPLOAD_EXCEDIDO" | "LIMITE_LOTE_EXCEDIDO" | "TIPO_ARQUIVO_NAO_SUPORTADO" | "INTEGRIDADE_ARQUIVO" | "ARQUIVO_FORA_MANIFESTO" | "ARQUIVO_JA_RECEBIDO" | "CURSOR_INVALIDO" | "VERSAO_REGRAS_CONFLITANTE" | "CONFIGURACAO_INVALIDA" | "ESTRUTURA_ARQUIVO_INVALIDA" | "ARQUIVO_CORROMPIDO" | "DADOS_IMPEDEM_PL" | "FUNDOS_SEM_REGRAS" | "BASE_CADASTRAL_INDISPONIVEL" | "INFRAESTRUTURA_INDISPONIVEL" | "ERRO_INTERNO";

export type DetalheErroDTO = {
  "campo": string | null;
  "codigo": string;
  "mensagem": string;
};

export type ErroDTO = {
  "codigo": CodigoErro;
  "mensagem": string;
  "retry_permitido": boolean;
  "detalhes": Array<DetalheErroDTO>;
  "versao_atual": string | null;
};

export type ErroResponse = {
  "request_id": string;
  "erro": ErroDTO;
};

export type SaudeResponse = {
  "status": "OK";
  "servico": "antecipe-api";
  "versao_api": "1.0.0";
  "verificado_em": string;
};

export type CapacidadesResponse = {
  "versao_contrato": "1.0.0";
  "autenticacao": "SEM_AUTENTICACAO_DEMO";
  "formatos": Array<FormatoArquivo>;
  "max_arquivos_lote": number;
  "max_arquivos_batch": number;
  "max_bytes_arquivo": number;
  "max_bytes_batch": number;
  "max_linhas_lote": number;
  "max_pagina": number;
  "polling_intervalo_ms": number;
  "permite_exportacao": boolean;
  "permite_cancelamento": boolean;
};

export type BaseCadastralStatusResponse = {
  "disponivel": boolean;
  "versao": string | null;
  "sha256": string | null;
  "quantidade_cnpjs": number;
  "importado_em": string | null;
};

export type FundoDTO = {
  "id": string;
  "nome": string;
  "cnpj": string;
  "configurado": boolean;
  "versao_regras_atual": string | null;
};

export type ParametrosVaziosDTO = Record<string, never>;

export type ParametrosSituacaoDTO = {
  "situacoes_aceitas": Array<string>;
};

export type ParametrosTipoDTO = {
  "tipos_aceitos": Array<string>;
};

export type ParametrosValorMinimoDTO = {
  "valor_minimo": DecimalNaoNegativo;
};

export type ParametrosPrazoMinimoDTO = {
  "prazo_minimo_dias": number;
};

export type ParametrosPrazoMaximoDTO = {
  "prazo_maximo_dias": number;
};

export type ParametrosConcentracaoDTO = {
  "percentual_maximo": DecimalNaoNegativo;
  "agrupamento": "RAIZ_CNPJ";
};

export type ValidadorCnpjSacadoValidoDTO = {
  "codigo": "CNPJ_SACADO_VALIDO";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorSituacaoCadastralSacadoDTO = {
  "codigo": "SITUACAO_CADASTRAL_SACADO";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorTipoRecebivelDTO = {
  "codigo": "TIPO_RECEBIVEL";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorValorMinimoDTO = {
  "codigo": "VALOR_MINIMO";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorNaoVencidaDTO = {
  "codigo": "NAO_VENCIDA";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorPrazoMinimoDTO = {
  "codigo": "PRAZO_MINIMO";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorPrazoMaximoDTO = {
  "codigo": "PRAZO_MAXIMO";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorConcentracaoMaximaSacadoDTO = {
  "codigo": "CONCENTRACAO_MAXIMA_SACADO";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorConcentracaoMaximaCedenteDTO = {
  "codigo": "CONCENTRACAO_MAXIMA_CEDENTE";
  "ativo": boolean;
  "parametros": Record<string, unknown>;
};

export type ValidadorDTO = ValidadorCnpjSacadoValidoDTO | ValidadorSituacaoCadastralSacadoDTO | ValidadorTipoRecebivelDTO | ValidadorValorMinimoDTO | ValidadorNaoVencidaDTO | ValidadorPrazoMinimoDTO | ValidadorPrazoMaximoDTO | ValidadorConcentracaoMaximaSacadoDTO | ValidadorConcentracaoMaximaCedenteDTO;

export type PrecificacaoDTO = {
  "metodo": "DESCONTO_SIMPLES";
  "taxa_mensal_percentual": DecimalNaoNegativo;
  "base_dias": number;
};

/** Exatamente uma ocorrência de cada código configurável. NOTA_DUPLICADA não é configurável. Somente parâmetros de validadores ativos são validados. */
export type ConfiguracaoRegrasDTO = {
  "validadores": Array<ValidadorDTO>;
  "precificacao": PrecificacaoDTO;
};

/** versao_base=null somente para primeira configuração; para edição, versão obtida no GET. Atualização integral dos nove validadores. */
export type AtualizarRegrasRequest = {
  "versao_base": string | null;
  "configuracao": ConfiguracaoRegrasDTO;
};

export type RegrasFundoResponse = {
  "fundo": FundoDTO;
  "versao": string;
  "criada_em": string;
  "configuracao": ConfiguracaoRegrasDTO;
};

/** Conteúdo do JSON de inputs: objeto com fundo, validadores e precificacao, ou array de até 100 objetos. Aceita decimais numéricos do formato de inputs. Validação semântica integral antes de publicar; importação atômica. */
export type ImportarRegrasRequest = Record<string, unknown> | Array<Record<string, unknown>>;

export type ImportarRegrasResponse = {
  "fundos": Array<FundoDTO>;
};

/** client_id gerado pelo front e único no lote. ordem deve ser contígua de 0 a N-1. aba=null para CSV; XLSX null seleciona primeira aba com dados. */
export type ArquivoManifestoRequest = {
  "client_id": string;
  "nome": string;
  "formato": FormatoArquivo;
  "tamanho_bytes": number;
  "sha256": string;
  "ordem": number;
  "aba": string | null;
};

export type CriarLoteRequest = {
  "nome": string;
  "arquivos": Array<ArquivoManifestoRequest>;
};

export type ArquivoDTO = {
  "id": string;
  "lote_id": string;
  "client_id": string;
  "nome": string;
  "formato": FormatoArquivo;
  "ordem": number;
  "aba": string | null;
  "tamanho_bytes": number;
  "sha256": string;
  "bytes_recebidos": number;
  "status": StatusArquivo;
  "linhas_total": number | null;
  "linhas_processadas": number;
  "aprovadas": number;
  "barradas": number;
  "erros_dados": number;
  "recebido_em": string | null;
  "concluido_em": string | null;
  "erro": ErroDTO | null;
};

/** Contadores persistidos. Total null até terminar indexação. Não somar as duas passagens como notas diferentes. */
export type ProgressoDTO = {
  "fase": "AGUARDANDO" | "INDEXACAO" | "ANALISE" | "FINALIZADO";
  "arquivos_total": number;
  "arquivos_recebidos": number;
  "arquivos_falhos": number;
  "bytes_esperados": number;
  "bytes_recebidos": number;
  "linhas_lidas_primeira_passagem": number;
  "linhas_total": number | null;
  "linhas_processadas": number;
};

/** Durante execução, totais parciais; total_nominal é PL dos arquivos válidos após indexação. Não é patrimônio global histórico do fundo. */
export type ResumoFinanceiroDTO = {
  "definitivo": boolean;
  "total_nominal": Dinheiro;
  "total_nominal_aprovado": Dinheiro;
  "total_nominal_barrado": Dinheiro;
  "total_nominal_erro_dados": Dinheiro;
  "total_desconto": Dinheiro;
  "total_liquido": Dinheiro;
  "aprovadas": number;
  "barradas": number;
  "erros_dados": number;
};

export type AcoesLoteDTO = {
  "pode_enviar_arquivos": boolean;
  "pode_iniciar": boolean;
  "pode_retomar": boolean;
  "precisa_corrigir_configuracao": boolean;
  "precisa_recriar_lote": boolean;
};

export type LoteDTO = {
  "id": string;
  "nome": string;
  "status": StatusLote;
  "criado_em": string;
  "iniciado_em": string | null;
  "concluido_em": string | null;
  "atualizado_em": string;
  "versao_cadastral": string | null;
  "progresso": ProgressoDTO;
  "resumo": ResumoFinanceiroDTO;
  "quantidade_pendencias": number;
  "acoes": AcoesLoteDTO;
  "erro": ErroDTO | null;
};

export type CriarLoteResponse = {
  "lote": LoteDTO;
  "arquivos": Array<ArquivoDTO>;
};

export type LoteResumoDTO = {
  "id": string;
  "nome": string;
  "status": StatusLote;
  "criado_em": string;
  "atualizado_em": string;
  "arquivos_total": number;
  "linhas_processadas": number;
  "total_liquido": Dinheiro;
};

/** A posição de arquivo_ids corresponde à posição de cada parte multipart arquivos. Não mapear por nome do arquivo. */
export type BatchMetadadosDTO = {
  "arquivo_ids": Array<string>;
};

export type EnviarBatchRequest = {
  "metadados": string;
  "arquivos": Array<Blob>;
};

export type ArquivoRecebidoDTO = {
  "arquivo_id": string;
  "client_id": string;
  "sha256": string;
  "bytes_recebidos": number;
  "status": "RECEBIDO";
};

export type EnviarBatchResponse = {
  "batch_id": string;
  "lote_id": string;
  "recebido_em": string;
  "arquivos": Array<ArquivoRecebidoDTO>;
};

export type ProcessarLoteResponse = {
  "lote_id": string;
  "execucao_id": string;
  "status": "NA_FILA";
  "aceito_em": string;
  "status_url": string;
};

export type PendenciaDTO = {
  "codigo": "FUNDO_SEM_REGRAS" | "BASE_CADASTRAL_AUSENTE" | "DADOS_IMPEDEM_PL";
  "mensagem": string;
  "fundo": FundoDTO | null;
  "arquivo_id": string | null;
  "linha": number | null;
  "campo": string | null;
  "acao": "CONFIGURAR_FUNDO" | "IMPORTAR_BASE_CADASTRAL" | "RECRIAR_LOTE";
};

/** Limite null se regra inativa ou contexto ainda não congelado. versao_regras_utilizada identifica a versão histórica, não necessariamente a atual do fundo. */
export type ResumoFundoDTO = {
  "fundo": FundoDTO;
  "versao_regras_utilizada": string | null;
  "pl": Dinheiro;
  "limite_sacado": Dinheiro | null;
  "limite_cedente": Dinheiro | null;
  "resumo": ResumoFinanceiroDTO;
};

/** Explicação para exibição; frontend não recalcula a regra nem interpreta os valores textuais como contrato de cálculo. */
export type MotivoDTO = {
  "codigo": CodigoRecusa;
  "mensagem": string;
  "valor_observado": string | null;
  "limite_aplicado": string | null;
};

export type ErroDadoDTO = {
  "campo": string;
  "codigo": "OBRIGATORIO" | "FORMATO_INVALIDO" | "DATA_INVALIDA" | "DECIMAL_INVALIDO" | "FORMULA_SEM_VALOR" | "DOCUMENTO_SEM_RAIZ" | "FUNDO_SEM_REGRAS";
  "mensagem": string;
};

export type DadosOriginaisTituloDTO = {
  "NOME_FUNDO": string | null;
  "DOC_FUNDO": string | null;
  "NOME_CEDENTE": string | null;
  "DOC_CEDENTE": string | null;
  "NOME_SACADO": string | null;
  "DOC_SACADO": string | null;
  "NU_DOCUMENTO": string | null;
  "TIPO_RECEBIVEL": string | null;
  "VALOR_NOMINAL": string | null;
  "DATA_VENCIMENTO_ORIGINAL": string | null;
  "DATA_AQUISICAO": string | null;
};

/** Documento observado pode ser inválido e gerar CNPJ_SACADO_VALIDO. Não aplicar regex CNPJ válido aos campos doc_sacado/cedente do resultado. */
export type TituloNormalizadoDTO = {
  "fundo_id": string;
  "nome_fundo": string;
  "doc_fundo": string;
  "nome_cedente": string;
  "doc_cedente": string;
  "raiz_cedente": string | null;
  "nome_sacado": string;
  "doc_sacado": string;
  "raiz_sacado": string | null;
  "nu_documento": string;
  "tipo_recebivel": string;
  "valor_nominal": Dinheiro;
  "data_aquisicao": string;
  "data_vencimento_original": string;
  "prazo_dias": number;
};

export type ResultadoAprovadoDTO = {
  "id": string;
  "lote_id": string;
  "arquivo_id": string;
  "sequencia": number;
  "linha": number;
  "dados_originais": DadosOriginaisTituloDTO;
  "tipo": "ANALISE";
  "status": "APROVADO";
  "titulo": TituloNormalizadoDTO;
  "motivos": Array<MotivoDTO>;
  "erros_dados": Array<ErroDadoDTO>;
  "desconto": Dinheiro;
  "valor_liquido": Dinheiro;
};

export type ResultadoBarradoDTO = {
  "id": string;
  "lote_id": string;
  "arquivo_id": string;
  "sequencia": number;
  "linha": number;
  "dados_originais": DadosOriginaisTituloDTO;
  "tipo": "ANALISE";
  "status": "BARRADO";
  "titulo": TituloNormalizadoDTO;
  "motivos": Array<MotivoDTO>;
  "erros_dados": Array<ErroDadoDTO>;
  "desconto": "0.00";
  "valor_liquido": "0.00";
};

/** Diagnóstico de parsing; não é um novo status financeiro nem um novo código de recusa FIDC. Usar dados_originais na interface. */
export type ResultadoErroDadosDTO = {
  "id": string;
  "lote_id": string;
  "arquivo_id": string;
  "sequencia": number;
  "linha": number;
  "dados_originais": DadosOriginaisTituloDTO;
  "tipo": "ERRO_DADOS";
  "status": null;
  "titulo": null;
  "motivos": Array<MotivoDTO>;
  "erros_dados": Array<ErroDadoDTO>;
  "desconto": "0.00";
  "valor_liquido": "0.00";
};

export type ResultadoDTO = ResultadoAprovadoDTO | ResultadoBarradoDTO | ResultadoErroDadosDTO;

export type PaginacaoQuery = {
  "limit"?: number;
  "cursor"?: string;
};

export type ListarFundosQuery = {
  "limit"?: number;
  "cursor"?: string;
  "busca"?: string;
  "configurado"?: boolean;
};

export type ListarLotesQuery = {
  "limit"?: number;
  "cursor"?: string;
  "status"?: StatusLote;
};

export type ConsultarRegrasQuery = {
  "versao"?: string;
};

export type ListarResultadosQuery = {
  "limit"?: number;
  "cursor"?: string;
  "status"?: StatusNota;
  "motivo"?: CodigoRecusa;
  "tipo"?: "ANALISE" | "ERRO_DADOS";
};

export type FundosPageResponse = {
  "itens": Array<FundoDTO>;
  "proximo_cursor": string | null;
  "limit": number;
};

export type LotesPageResponse = {
  "itens": Array<LoteResumoDTO>;
  "proximo_cursor": string | null;
  "limit": number;
};

export type ArquivosPageResponse = {
  "itens": Array<ArquivoDTO>;
  "proximo_cursor": string | null;
  "limit": number;
};

export type PendenciasPageResponse = {
  "itens": Array<PendenciaDTO>;
  "proximo_cursor": string | null;
  "limit": number;
};

export type ResumosFundosPageResponse = {
  "itens": Array<ResumoFundoDTO>;
  "proximo_cursor": string | null;
  "limit": number;
};

/** Cursor fixa teto de sequência e filtros. Refazer primeira página para incluir resultados mais recentes. Não fornece total filtrado nem salto arbitrário de página. */
export type ResultadosPageResponse = {
  "itens": Array<ResultadoDTO>;
  "proximo_cursor": string | null;
  "limit": number;
  "snapshot_ate_sequencia": number;
  "arquivo_finalizado": boolean;
};

