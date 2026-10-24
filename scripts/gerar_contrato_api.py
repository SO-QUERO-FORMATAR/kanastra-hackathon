"""Gera contrato de projeto OpenAPI e tipos TS; não implementa endpoints."""
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = {}


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def text(description=None, **extra):
    return {"type": "string", **({"description": description} if description else {}), **extra}


def integer(minimum=0, **extra):
    return {"type": "integer", "minimum": minimum, **extra}


def array(items, **extra):
    return {"type": "array", "items": items, **extra}


def obj(name, properties, required=None, description=None):
    S[name] = {"type": "object", "additionalProperties": False, "properties": properties,
               "required": list(properties) if required is None else required}
    if description:
        S[name]["description"] = description
    return ref(name)


def enum(name, values, description=None):
    S[name] = text(description, enum=values)
    return ref(name)


UUID = text(format="uuid")
DATE = text(format="date")
DATETIME = text(format="date-time")
BOOL = {"type": "boolean"}
CNPJ = text(pattern=r"^[0-9]{14}$")
HASH = text(pattern=r"^[a-f0-9]{64}$")
S["Dinheiro"] = text("Decimal em BRL, ponto e duas casas; nunca JSON number.", pattern=r"^-?(0|[1-9][0-9]*)\.[0-9]{2}$", examples=["2278.08"])
S["DecimalNaoNegativo"] = text("Decimal exato não negativo; até 8 casas, sem notação científica.", pattern=r"^(0|[1-9][0-9]*)(\.[0-9]{1,8})?$", examples=["2.0"])
MONEY = ref("Dinheiro")
DECIMAL = ref("DecimalNaoNegativo")
codes = ["NOTA_DUPLICADA", "CNPJ_SACADO_VALIDO", "SITUACAO_CADASTRAL_SACADO", "TIPO_RECEBIVEL", "VALOR_MINIMO", "NAO_VENCIDA", "PRAZO_MINIMO", "PRAZO_MAXIMO", "CONCENTRACAO_MAXIMA_SACADO", "CONCENTRACAO_MAXIMA_CEDENTE"]
enum("CodigoRecusa", codes)
enum("StatusNota", ["APROVADO", "BARRADO"])
enum("StatusLote", ["RECEBENDO", "NA_FILA", "INDEXANDO", "BLOQUEADO", "ANALISANDO", "CONCLUIDO", "CONCLUIDO_COM_ERROS", "FALHOU"])
enum("StatusArquivo", ["AGUARDANDO_UPLOAD", "RECEBIDO", "INDEXANDO", "PRONTO", "ANALISANDO", "CONCLUIDO", "CONCLUIDO_COM_ERROS", "FALHOU"])
enum("FormatoArquivo", ["CSV", "XLSX"])
enum("CodigoErro", ["VALIDACAO_REQUISICAO", "RECURSO_NAO_ENCONTRADO", "ESTADO_INVALIDO", "IDEMPOTENCIA_CONFLITANTE", "REQUISICAO_EM_ANDAMENTO", "UPLOAD_INCOMPLETO", "LIMITE_UPLOAD_EXCEDIDO", "LIMITE_LOTE_EXCEDIDO", "TIPO_ARQUIVO_NAO_SUPORTADO", "INTEGRIDADE_ARQUIVO", "ARQUIVO_FORA_MANIFESTO", "ARQUIVO_JA_RECEBIDO", "CURSOR_INVALIDO", "VERSAO_REGRAS_CONFLITANTE", "CONFIGURACAO_INVALIDA", "ESTRUTURA_ARQUIVO_INVALIDA", "ARQUIVO_CORROMPIDO", "DADOS_IMPEDEM_PL", "FUNDOS_SEM_REGRAS", "BASE_CADASTRAL_INDISPONIVEL", "INFRAESTRUTURA_INDISPONIVEL", "ERRO_INTERNO"])
obj("DetalheErroDTO", {"campo": nullable(text("JSON Pointer no corpo, ou query.nome/header.nome; null para erro geral.")), "codigo": text(), "mensagem": text()})
obj("ErroDTO", {"codigo": ref("CodigoErro"), "mensagem": text(), "retry_permitido": BOOL, "detalhes": array(ref("DetalheErroDTO")), "versao_atual": nullable(UUID)})
obj("ErroResponse", {"request_id": UUID, "erro": ref("ErroDTO")})
obj("SaudeResponse", {"status": text(enum=["OK"]), "servico": text(enum=["antecipe-api"]), "versao_api": text(enum=["1.0.0"]), "verificado_em": DATETIME})
obj("CapacidadesResponse", {"versao_contrato": text(enum=["1.0.0"]), "autenticacao": text(enum=["SEM_AUTENTICACAO_DEMO"]), "formatos": array(ref("FormatoArquivo")), "max_arquivos_lote": integer(1), "max_arquivos_batch": integer(1), "max_bytes_arquivo": integer(1), "max_bytes_batch": integer(1), "max_linhas_lote": integer(1), "max_pagina": integer(1), "polling_intervalo_ms": integer(1000), "permite_exportacao": BOOL, "permite_cancelamento": BOOL})
obj("BaseCadastralStatusResponse", {"disponivel": BOOL, "versao": nullable(UUID), "sha256": nullable(HASH), "quantidade_cnpjs": integer(), "importado_em": nullable(DATETIME)})
obj("FundoDTO", {"id": UUID, "nome": text(), "cnpj": CNPJ, "configurado": BOOL, "versao_regras_atual": nullable(UUID)})
obj("ParametrosVaziosDTO", {})
obj("ParametrosSituacaoDTO", {"situacoes_aceitas": array(text(minLength=1), minItems=1, uniqueItems=True)})
obj("ParametrosTipoDTO", {"tipos_aceitos": array(text(minLength=1), minItems=1, uniqueItems=True)})
obj("ParametrosValorMinimoDTO", {"valor_minimo": DECIMAL})
obj("ParametrosPrazoMinimoDTO", {"prazo_minimo_dias": integer()})
obj("ParametrosPrazoMaximoDTO", {"prazo_maximo_dias": integer()})
obj("ParametrosConcentracaoDTO", {"percentual_maximo": {**DECIMAL, "description": "Entre 0 e 100, inclusive; limite semântico validado pelo servidor."}, "agrupamento": text(enum=["RAIZ_CNPJ"])})
param_map = {
    "CNPJ_SACADO_VALIDO": "ParametrosVaziosDTO", "SITUACAO_CADASTRAL_SACADO": "ParametrosSituacaoDTO",
    "TIPO_RECEBIVEL": "ParametrosTipoDTO", "VALOR_MINIMO": "ParametrosValorMinimoDTO", "NAO_VENCIDA": "ParametrosVaziosDTO",
    "PRAZO_MINIMO": "ParametrosPrazoMinimoDTO", "PRAZO_MAXIMO": "ParametrosPrazoMaximoDTO",
    "CONCENTRACAO_MAXIMA_SACADO": "ParametrosConcentracaoDTO", "CONCENTRACAO_MAXIMA_CEDENTE": "ParametrosConcentracaoDTO",
}
validator_names = []
for code, params in param_map.items():
    name = "Validador" + "".join(word.title() for word in code.lower().split("_")) + "DTO"
    obj(name, {"codigo": text(enum=[code]), "ativo": BOOL, "parametros": ref(params)})
    validator_names.append(name)
S["ValidadorDTO"] = {"oneOf": [ref(name) for name in validator_names], "discriminator": {"propertyName": "codigo", "mapping": {code: f"#/components/schemas/{name}" for code, name in zip(param_map, validator_names)}}}
obj("PrecificacaoDTO", {"metodo": text(enum=["DESCONTO_SIMPLES"]), "taxa_mensal_percentual": DECIMAL, "base_dias": integer(1, maximum=366)})
obj("ConfiguracaoRegrasDTO", {"validadores": array(ref("ValidadorDTO"), minItems=9, maxItems=9, allOf=[{"contains": {"type": "object", "properties": {"codigo": {"const": code}}, "required": ["codigo"]}, "minContains": 1, "maxContains": 1} for code in param_map]), "precificacao": ref("PrecificacaoDTO")}, description="Exatamente uma ocorrência de cada código configurável. NOTA_DUPLICADA não é configurável. Parâmetros inativos também devem ser válidos.")
obj("AtualizarRegrasRequest", {"versao_base": nullable(UUID), "configuracao": ref("ConfiguracaoRegrasDTO")}, description="versao_base=null somente para primeira configuração; para edição, versão obtida no GET. Atualização integral dos nove validadores.")
obj("RegrasFundoResponse", {"fundo": ref("FundoDTO"), "versao": UUID, "criada_em": DATETIME, "configuracao": ref("ConfiguracaoRegrasDTO")})
obj("ArquivoManifestoRequest", {"client_id": UUID, "nome": text(minLength=1, maxLength=255), "formato": ref("FormatoArquivo"), "tamanho_bytes": integer(1, maximum=67108864), "sha256": HASH, "ordem": integer(0, maximum=99), "aba": nullable(text(minLength=1, maxLength=31))}, description="client_id gerado pelo front e único no lote. ordem deve ser contígua de 0 a N-1. aba=null para CSV; XLSX null seleciona primeira aba com dados.")
obj("CriarLoteRequest", {"nome": text(minLength=1, maxLength=120), "arquivos": array(ref("ArquivoManifestoRequest"), minItems=1, maxItems=100)})
obj("ArquivoDTO", {"id": UUID, "lote_id": UUID, "client_id": UUID, "nome": text(), "formato": ref("FormatoArquivo"), "ordem": integer(), "aba": nullable(text()), "tamanho_bytes": integer(1), "sha256": HASH, "bytes_recebidos": integer(), "status": ref("StatusArquivo"), "linhas_total": nullable(integer()), "linhas_processadas": integer(), "aprovadas": integer(), "barradas": integer(), "erros_dados": integer(), "recebido_em": nullable(DATETIME), "concluido_em": nullable(DATETIME), "erro": nullable(ref("ErroDTO"))})
obj("ProgressoDTO", {"fase": text(enum=["AGUARDANDO", "INDEXACAO", "ANALISE", "FINALIZADO"]), "arquivos_total": integer(), "arquivos_recebidos": integer(), "arquivos_falhos": integer(), "bytes_esperados": integer(), "bytes_recebidos": integer(), "linhas_lidas_primeira_passagem": integer(), "linhas_total": nullable(integer()), "linhas_processadas": integer()}, description="Contadores persistidos. Total null até terminar indexação. Não somar as duas passagens como notas diferentes.")
obj("ResumoFinanceiroDTO", {"definitivo": BOOL, "total_nominal": MONEY, "total_nominal_aprovado": MONEY, "total_nominal_barrado": MONEY, "total_nominal_erro_dados": MONEY, "total_desconto": MONEY, "total_liquido": MONEY, "aprovadas": integer(), "barradas": integer(), "erros_dados": integer()}, description="Durante execução, totais parciais; total_nominal é PL dos arquivos válidos após indexação. Não é patrimônio global histórico do fundo.")
obj("AcoesLoteDTO", {"pode_enviar_arquivos": BOOL, "pode_iniciar": BOOL, "pode_retomar": BOOL, "precisa_corrigir_configuracao": BOOL, "precisa_recriar_lote": BOOL})
obj("LoteDTO", {"id": UUID, "nome": text(), "status": ref("StatusLote"), "criado_em": DATETIME, "iniciado_em": nullable(DATETIME), "concluido_em": nullable(DATETIME), "atualizado_em": DATETIME, "versao_cadastral": nullable(UUID), "progresso": ref("ProgressoDTO"), "resumo": ref("ResumoFinanceiroDTO"), "quantidade_pendencias": integer(), "acoes": ref("AcoesLoteDTO"), "erro": nullable(ref("ErroDTO"))})
obj("CriarLoteResponse", {"lote": ref("LoteDTO"), "arquivos": array(ref("ArquivoDTO"), minItems=1, maxItems=100)})
obj("LoteResumoDTO", {"id": UUID, "nome": text(), "status": ref("StatusLote"), "criado_em": DATETIME, "atualizado_em": DATETIME, "arquivos_total": integer(), "linhas_processadas": integer(), "total_liquido": MONEY})
obj("BatchMetadadosDTO", {"arquivo_ids": array(UUID, minItems=1, maxItems=3, uniqueItems=True)}, description="A posição de arquivo_ids corresponde à posição de cada parte multipart arquivos. Não mapear por nome do arquivo.")
obj("EnviarBatchRequest", {"metadados": text("JSON serializado de BatchMetadadosDTO; campo textual do FormData."), "arquivos": array(text(format="binary"), minItems=1, maxItems=3)})
obj("ArquivoRecebidoDTO", {"arquivo_id": UUID, "client_id": UUID, "sha256": HASH, "bytes_recebidos": integer(1), "status": text(enum=["RECEBIDO"])})
obj("EnviarBatchResponse", {"batch_id": UUID, "lote_id": UUID, "recebido_em": DATETIME, "arquivos": array(ref("ArquivoRecebidoDTO"), minItems=1, maxItems=3)})
obj("ProcessarLoteResponse", {"lote_id": UUID, "execucao_id": UUID, "status": text(enum=["NA_FILA"]), "aceito_em": DATETIME, "status_url": text(format="uri-reference")})
obj("PendenciaDTO", {"codigo": text(enum=["FUNDO_SEM_REGRAS", "BASE_CADASTRAL_AUSENTE", "DADOS_IMPEDEM_PL"]), "mensagem": text(), "fundo": nullable(ref("FundoDTO")), "arquivo_id": nullable(UUID), "linha": nullable(integer(2)), "campo": nullable(text()), "acao": text(enum=["CONFIGURAR_FUNDO", "IMPORTAR_BASE_CADASTRAL", "RECRIAR_LOTE"])})
obj("ResumoFundoDTO", {"fundo": ref("FundoDTO"), "versao_regras_utilizada": nullable(UUID), "pl": MONEY, "limite_sacado": nullable(MONEY), "limite_cedente": nullable(MONEY), "resumo": ref("ResumoFinanceiroDTO")}, description="Limite null se regra inativa ou contexto ainda não congelado. versao_regras_utilizada identifica a versão histórica, não necessariamente a atual do fundo.")
obj("MotivoDTO", {"codigo": ref("CodigoRecusa"), "mensagem": text(), "valor_observado": nullable(text()), "limite_aplicado": nullable(text())}, description="Explicação para exibição; frontend não recalcula a regra nem interpreta os valores textuais como contrato de cálculo.")
obj("ErroDadoDTO", {"campo": text(), "codigo": text(enum=["OBRIGATORIO", "FORMATO_INVALIDO", "DATA_INVALIDA", "DECIMAL_INVALIDO", "FORMULA_SEM_VALOR", "DOCUMENTO_SEM_RAIZ"]), "mensagem": text()})
fields = ["NOME_FUNDO", "DOC_FUNDO", "NOME_CEDENTE", "DOC_CEDENTE", "NOME_SACADO", "DOC_SACADO", "NU_DOCUMENTO", "TIPO_RECEBIVEL", "VALOR_NOMINAL", "DATA_VENCIMENTO_ORIGINAL", "DATA_AQUISICAO"]
obj("DadosOriginaisTituloDTO", {field: nullable(text()) for field in fields})
obj("TituloNormalizadoDTO", {"fundo_id": UUID, "nome_fundo": text(), "doc_fundo": CNPJ, "nome_cedente": text(), "doc_cedente": text(), "raiz_cedente": nullable(text(pattern=r"^[0-9]{8}$")), "nome_sacado": text(), "doc_sacado": text(), "raiz_sacado": nullable(text(pattern=r"^[0-9]{8}$")), "nu_documento": text(), "tipo_recebivel": text(), "valor_nominal": MONEY, "data_aquisicao": DATE, "data_vencimento_original": DATE, "prazo_dias": {"type": "integer"}}, description="Documento observado pode ser inválido e gerar CNPJ_SACADO_VALIDO. Não aplicar regex CNPJ válido aos campos doc_sacado/cedente do resultado.")
common_result = {"id": UUID, "lote_id": UUID, "arquivo_id": UUID, "sequencia": integer(1), "linha": integer(2), "dados_originais": ref("DadosOriginaisTituloDTO")}
obj("ResultadoAprovadoDTO", {**common_result, "tipo": text(enum=["ANALISE"]), "status": text(enum=["APROVADO"]), "titulo": ref("TituloNormalizadoDTO"), "motivos": array(ref("MotivoDTO"), maxItems=0), "erros_dados": array(ref("ErroDadoDTO"), maxItems=0), "desconto": MONEY, "valor_liquido": MONEY})
obj("ResultadoBarradoDTO", {**common_result, "tipo": text(enum=["ANALISE"]), "status": text(enum=["BARRADO"]), "titulo": ref("TituloNormalizadoDTO"), "motivos": array(ref("MotivoDTO"), minItems=1), "erros_dados": array(ref("ErroDadoDTO"), maxItems=0), "desconto": text(enum=["0.00"]), "valor_liquido": text(enum=["0.00"])})
obj("ResultadoErroDadosDTO", {**common_result, "tipo": text(enum=["ERRO_DADOS"]), "status": {"type": "null"}, "titulo": {"type": "null"}, "motivos": array(ref("MotivoDTO"), maxItems=0), "erros_dados": array(ref("ErroDadoDTO"), minItems=1), "desconto": text(enum=["0.00"]), "valor_liquido": text(enum=["0.00"])}, description="Diagnóstico de parsing; não é um novo status financeiro nem um novo código de recusa FIDC. Usar dados_originais na interface.")
S["ResultadoDTO"] = {"oneOf": [ref("ResultadoAprovadoDTO"), ref("ResultadoBarradoDTO"), ref("ResultadoErroDadosDTO")]}

pagination = {"limit": integer(1, maximum=100, default=50), "cursor": text(minLength=1, maxLength=4096)}
obj("PaginacaoQuery", pagination, required=[])
obj("ListarFundosQuery", {**pagination, "busca": text(minLength=1, maxLength=120), "configurado": BOOL}, required=[])
obj("ListarLotesQuery", {**pagination, "status": ref("StatusLote")}, required=[])
obj("ConsultarRegrasQuery", {"versao": UUID}, required=[])
obj("ListarResultadosQuery", {**pagination, "status": ref("StatusNota"), "motivo": ref("CodigoRecusa"), "tipo": text(enum=["ANALISE", "ERRO_DADOS"])}, required=[])
for name, item in [("FundosPageResponse", "FundoDTO"), ("LotesPageResponse", "LoteResumoDTO"), ("ArquivosPageResponse", "ArquivoDTO"), ("PendenciasPageResponse", "PendenciaDTO"), ("ResumosFundosPageResponse", "ResumoFundoDTO")]:
    obj(name, {"itens": array(ref(item), maxItems=100), "proximo_cursor": nullable(text()), "limit": integer(1, maximum=100)})
obj("ResultadosPageResponse", {"itens": array(ref("ResultadoDTO"), maxItems=100), "proximo_cursor": nullable(text()), "limit": integer(1, maximum=100), "snapshot_ate_sequencia": integer(), "arquivo_finalizado": BOOL}, description="Cursor fixa teto de sequência e filtros. Refazer primeira página para incluir resultados mais recentes. Não fornece total filtrado nem salto arbitrário de página.")

paths = {}
error_descriptions = {400: "Requisição ou cursor inválido.", 404: "Recurso ou versão não encontrado.", 409: "Conflito de estado, idempotência ou versão.", 413: "Limite de upload excedido.", 415: "Tipo de mídia não suportado.", 422: "Falha de validação do contrato.", 500: "Erro inesperado.", 503: "Infraestrutura indisponível; observar Retry-After quando presente."}


def endpoint(path, method, operation, response, status=200, request=None, query=None, idem=False, summary="", description="", errors=(404, 422, 500, 503)):
    parameters = []
    for component in path.split("/"):
        if component.startswith("{"):
            parameters.append({"name": component[1:-1], "in": "path", "required": True, "schema": UUID})
    if query:
        for name, schema in S[query]["properties"].items():
            parameters.append({"name": name, "in": "query", "required": False, "schema": schema})
    if idem:
        parameters.append({"name": "Idempotency-Key", "in": "header", "required": True, "schema": UUID, "description": "UUID por operação lógica; repetir em retry do mesmo conteúdo. Escopo método + caminho + chave; retenção durante toda a vida do lote (regras: mínima de 24h)."})
    success_headers = {"X-Request-Id": {"schema": UUID, "description": "Identificador de correlação da requisição atual."}}
    if idem:
        success_headers["Idempotency-Replayed"] = {"schema": BOOL, "description": "true quando devolve o corpo/status originalmente persistidos."}
    responses = {str(status): {"description": "Sucesso.", "headers": success_headers, "content": {"application/json": {"schema": ref(response)}}}}
    for code in errors:
        responses[str(code)] = {"description": error_descriptions[code], "headers": {"X-Request-Id": {"schema": UUID}, "Retry-After": {"schema": integer(), "description": "Segundos; somente quando retry automático for apropriado."}}, "content": {"application/json": {"schema": ref("ErroResponse")}}}
    data = {"operationId": operation, "summary": summary, "description": description, "tags": [path.split("/")[1]], "parameters": parameters, "responses": responses}
    if request:
        media = "multipart/form-data" if request == "EnviarBatchRequest" else "application/json"
        data["requestBody"] = {"required": True, "content": {media: {"schema": ref(request)}}}
        if media == "multipart/form-data":
            data["requestBody"]["content"][media]["encoding"] = {"metadados": {"contentType": "text/plain"}, "arquivos": {"style": "form", "explode": True}}
    paths.setdefault(path, {})[method] = data


endpoint("/health/live", "get", "verificarVida", "SaudeResponse", summary="Verificar processo", errors=(500,))
endpoint("/health/ready", "get", "verificarProntidao", "SaudeResponse", summary="Verificar banco e armazenamento", errors=(500, 503))
endpoint("/capacidades", "get", "obterCapacidades", "CapacidadesResponse", summary="Limites e recursos do MVP", errors=(500, 503))
endpoint("/cadastro/status", "get", "obterStatusCadastro", "BaseCadastralStatusResponse", summary="Disponibilidade da base cadastral", errors=(500, 503))
endpoint("/fundos", "get", "listarFundos", "FundosPageResponse", query="ListarFundosQuery", summary="Listar fundos cadastrados ou descobertos no estoque", errors=(400, 422, 500, 503))
endpoint("/fundos/{fundo_id}/regras", "get", "consultarRegrasFundo", "RegrasFundoResponse", query="ConsultarRegrasQuery", summary="Consultar versão atual ou histórica das regras")
endpoint("/fundos/{fundo_id}/regras", "put", "atualizarRegrasFundo", "RegrasFundoResponse", request="AtualizarRegrasRequest", idem=True, summary="Configurar um fundo ou publicar nova versão", description="Primeira configuração e atualização retornam 200. Não copia regras para outros fundos. Verifica versao_base; conflito retorna 409. Lote que já começou análise mantém seu snapshot.", errors=(404, 409, 415, 422, 500, 503))
endpoint("/lotes", "get", "listarLotes", "LotesPageResponse", query="ListarLotesQuery", summary="Histórico de lotes", errors=(400, 422, 500, 503))
endpoint("/lotes", "post", "criarLote", "CriarLoteResponse", status=201, request="CriarLoteRequest", idem=True, summary="Criar manifesto imutável", errors=(409, 415, 422, 500, 503))
endpoint("/lotes/{lote_id}", "get", "consultarLote", "LoteDTO", summary="Estado, progresso, resumo e ações disponíveis")
endpoint("/lotes/{lote_id}/batches", "post", "enviarBatch", "EnviarBatchResponse", status=201, request="EnviarBatchRequest", idem=True, summary="Receber até três arquivos, atomicamente", description="Até 67108864 bytes somados de conteúdo binário, sem overhead multipart. Formatos CSV/XLSX; ZIP não é upload válido. Metadados JSON string com arquivo_ids na ordem das partes arquivos. Aceita somente lote RECEBENDO. Todos os arquivos deste batch são confirmados ou nenhum é confirmado.", errors=(400, 404, 409, 413, 415, 422, 500, 503))
endpoint("/lotes/{lote_id}/processamento", "post", "solicitarProcessamento", "ProcessarLoteResponse", status=202, idem=True, summary="Selar uploads e iniciar ou retomar o worker", description="Sem corpo. Inicialmente exige todos os arquivos recebidos. Em BLOQUEADO permite nova tentativa após correção de cadastro/regras; em FALHOU somente se acoes.pode_retomar. Nunca descarta aprovações já persistidas. Não espera análise no HTTP.", errors=(404, 409, 422, 500, 503))
endpoint("/lotes/{lote_id}/arquivos", "get", "listarArquivosLote", "ArquivosPageResponse", query="PaginacaoQuery", summary="Listar arquivos em ordem de manifesto", errors=(400, 404, 422, 500, 503))
endpoint("/lotes/{lote_id}/pendencias", "get", "listarPendenciasLote", "PendenciasPageResponse", query="PaginacaoQuery", summary="Listar bloqueios com ação requerida", errors=(400, 404, 422, 500, 503))
endpoint("/lotes/{lote_id}/resumos-fundos", "get", "listarResumosFundos", "ResumosFundosPageResponse", query="PaginacaoQuery", summary="Consultar PL e resumo por fundo", errors=(400, 404, 422, 500, 503))
endpoint("/arquivos/{arquivo_id}", "get", "consultarArquivo", "ArquivoDTO", summary="Consultar estado de um arquivo")
endpoint("/arquivos/{arquivo_id}/resultados", "get", "listarResultados", "ResultadosPageResponse", query="ListarResultadosQuery", summary="Consultar resultados e diagnósticos por cursor", description="Filtros combinados com AND. motivo seleciona barramentos. tipo=ERRO_DADOS com status/motivo é inválido (422); APROVADO com motivo também. Cursor não pode ser reutilizado com outro arquivo, filtros ou limit.", errors=(400, 404, 422, 500, 503))

spec = {"openapi": "3.1.0", "info": {"title": "Antecipe — Contrato backend/frontend", "version": "1.0.0", "description": "Contrato de projeto; implementação ainda pendente. Fonte editável: scripts/gerar_contrato_api.py. Complementado por docs/contrato-api.md. Ambiente MVP de demonstração, sem autenticação. Não representa serviço publicado."}, "servers": [{"url": "/api/v1", "description": "Usar proxy de desenvolvimento ou VITE_API_BASE_URL."}], "security": [], "paths": paths, "components": {"schemas": S}}


def ts_type(schema):
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "oneOf" in schema or "anyOf" in schema:
        return " | ".join(ts_type(item) for item in schema.get("oneOf", schema.get("anyOf")))
    if "enum" in schema:
        return " | ".join(json.dumps(item, ensure_ascii=False) for item in schema["enum"])
    kind = schema.get("type")
    if kind == "null":
        return "null"
    if kind == "string":
        return "Blob" if schema.get("format") == "binary" else "string"
    if kind in ("integer", "number"):
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "array":
        return f"Array<{ts_type(schema['items'])}>"
    if kind == "object":
        if not schema.get("properties"):
            return "Record<string, never>"
        required = schema.get("required", [])
        return "{\n" + "".join(f"  {json.dumps(key)}{'' if key in required else '?'}: {ts_type(value)};\n" for key, value in schema["properties"].items()) + "}"
    raise ValueError(schema)


def examples():
    uid = lambda n: f"00000000-0000-4000-8000-{n:012d}"
    moment = "2026-10-24T18:00:00Z"
    fund = {"id": uid(1), "nome": "ANTECIPE FIDC", "cnpj": "92234400000180", "configurado": True, "versao_regras_atual": uid(2)}
    raw_config = json.loads((ROOT / "files" / "validadores_antecipe.json").read_text(encoding="utf-8-sig"), parse_float=Decimal)
    config = {"validadores": raw_config["validadores"], "precificacao": raw_config["precificacao"]}
    for validator in config["validadores"]:
        for key in ("valor_minimo", "percentual_maximo"):
            if key in validator["parametros"]:
                validator["parametros"][key] = str(validator["parametros"][key])
        if validator["codigo"].startswith("CONCENTRACAO"):
            validator["parametros"]["agrupamento"] = "RAIZ_CNPJ"
    config["precificacao"]["taxa_mensal_percentual"] = str(config["precificacao"]["taxa_mensal_percentual"])
    manifest = {"client_id": uid(10), "nome": "exemplo.csv", "formato": "CSV", "tamanho_bytes": 1024, "sha256": "a" * 64, "ordem": 0, "aba": None}
    file = {"id": uid(11), "lote_id": uid(12), **manifest, "bytes_recebidos": 0, "status": "AGUARDANDO_UPLOAD", "linhas_total": None, "linhas_processadas": 0, "aprovadas": 0, "barradas": 0, "erros_dados": 0, "recebido_em": None, "concluido_em": None, "erro": None}
    summary = {"definitivo": False, **{key: "0.00" for key in ["total_nominal", "total_nominal_aprovado", "total_nominal_barrado", "total_nominal_erro_dados", "total_desconto", "total_liquido"]}, "aprovadas": 0, "barradas": 0, "erros_dados": 0}
    lot = {"id": uid(12), "nome": "Demonstração de contrato", "status": "RECEBENDO", "criado_em": moment, "iniciado_em": None, "concluido_em": None, "atualizado_em": moment, "versao_cadastral": None,
           "progresso": {"fase": "AGUARDANDO", "arquivos_total": 1, "arquivos_recebidos": 0, "arquivos_falhos": 0, "bytes_esperados": 1024, "bytes_recebidos": 0, "linhas_lidas_primeira_passagem": 0, "linhas_total": None, "linhas_processadas": 0},
           "resumo": summary, "quantidade_pendencias": 0, "acoes": {"pode_enviar_arquivos": True, "pode_iniciar": False, "pode_retomar": False, "precisa_corrigir_configuracao": False, "precisa_recriar_lote": False}, "erro": None}
    title = {"fundo_id": uid(1), "nome_fundo": fund["nome"], "doc_fundo": fund["cnpj"], "nome_cedente": "Cedente de exemplo", "doc_cedente": "10062050000157", "raiz_cedente": "10062050", "nome_sacado": "Sacado de exemplo", "doc_sacado": "22144961000102", "raiz_sacado": "22144961", "nu_documento": "000351153", "tipo_recebivel": "Duplicata", "valor_nominal": "10000.00", "data_aquisicao": "2026-10-01", "data_vencimento_original": "2026-10-31", "prazo_dias": 30}
    original = {key: title[key.lower()] for key in fields}
    original.update(VALOR_NOMINAL="10000,00", DATA_AQUISICAO="01/10/2026", DATA_VENCIMENTO_ORIGINAL="31/10/2026")
    approved = {"id": uid(20), "lote_id": uid(12), "arquivo_id": uid(11), "sequencia": 1, "linha": 2, "dados_originais": original, "tipo": "ANALISE", "status": "APROVADO", "titulo": title, "motivos": [], "erros_dados": [], "desconto": "200.00", "valor_liquido": "9800.00"}
    barred = {**approved, "id": uid(21), "sequencia": 2, "linha": 3, "status": "BARRADO", "motivos": [{"codigo": "NOTA_DUPLICADA", "mensagem": "Título já aprovado para este cedente, sacado e documento.", "valor_observado": "000351153", "limite_aplicado": None}], "desconto": "0.00", "valor_liquido": "0.00"}
    data_error = {**approved, "id": uid(22), "sequencia": 3, "linha": 4, "dados_originais": {**original, "DATA_AQUISICAO": "31/02/2026"}, "tipo": "ERRO_DADOS", "status": None, "titulo": None, "erros_dados": [{"campo": "DATA_AQUISICAO", "codigo": "DATA_INVALIDA", "mensagem": "Data inexistente no calendário."}], "desconto": "0.00", "valor_liquido": "0.00"}
    pending_fund = {"id": uid(30), "nome": "FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS SAFIRA VAREJO RESPONSABILIDADE LIMITADA", "cnpj": "32482084000133", "configurado": False, "versao_regras_atual": None}
    blocked = {**lot, "status": "BLOQUEADO", "iniciado_em": moment, "quantidade_pendencias": 1, "progresso": {**lot["progresso"], "fase": "INDEXACAO", "arquivos_recebidos": 1, "bytes_recebidos": 1024, "linhas_lidas_primeira_passagem": 3, "linhas_total": 3}, "acoes": {"pode_enviar_arquivos": False, "pode_iniciar": False, "pode_retomar": True, "precisa_corrigir_configuracao": True, "precisa_recriar_lote": False}}
    values = [
        ("criar_lote", "CriarLoteRequest", {"nome": lot["nome"], "arquivos": [manifest]}),
        ("lote_criado", "CriarLoteResponse", {"lote": lot, "arquivos": [file]}),
        ("metadados_batch", "BatchMetadadosDTO", {"arquivo_ids": [uid(11)]}),
        ("batch_recebido", "EnviarBatchResponse", {"batch_id": uid(13), "lote_id": uid(12), "recebido_em": moment, "arquivos": [{"arquivo_id": uid(11), "client_id": uid(10), "sha256": "a" * 64, "bytes_recebidos": 1024, "status": "RECEBIDO"}]}),
        ("processamento_aceito", "ProcessarLoteResponse", {"lote_id": uid(12), "execucao_id": uid(14), "status": "NA_FILA", "aceito_em": moment, "status_url": f"/api/v1/lotes/{uid(12)}"}),
        ("lote_bloqueado", "LoteDTO", blocked),
        ("pendencias", "PendenciasPageResponse", {"itens": [{"codigo": "FUNDO_SEM_REGRAS", "mensagem": "Configure as regras deste fundo antes de analisar o lote.", "fundo": pending_fund, "arquivo_id": None, "linha": None, "campo": None, "acao": "CONFIGURAR_FUNDO"}], "proximo_cursor": None, "limit": 50}),
        ("configurar_fundo", "AtualizarRegrasRequest", {"versao_base": None, "configuracao": config}),
        ("regras_publicadas", "RegrasFundoResponse", {"fundo": fund, "versao": uid(2), "criada_em": moment, "configuracao": config}),
        ("resultados", "ResultadosPageResponse", {"itens": [approved, barred, data_error], "proximo_cursor": None, "limit": 50, "snapshot_ate_sequencia": 3, "arquivo_finalizado": True}),
        ("erro_versao", "ErroResponse", {"request_id": uid(99), "erro": {"codigo": "VERSAO_REGRAS_CONFLITANTE", "mensagem": "As regras foram alteradas por outra operação. Recarregue a configuração.", "retry_permitido": False, "detalhes": [], "versao_atual": uid(3)}}),
        ("capacidades", "CapacidadesResponse", {"versao_contrato": "1.0.0", "autenticacao": "SEM_AUTENTICACAO_DEMO", "formatos": ["CSV", "XLSX"], "max_arquivos_lote": 100, "max_arquivos_batch": 3, "max_bytes_arquivo": 67108864, "max_bytes_batch": 67108864, "max_linhas_lote": 500000, "max_pagina": 100, "polling_intervalo_ms": 2000, "permite_exportacao": False, "permite_cancelamento": False}),
        ("cadastro_disponivel", "BaseCadastralStatusResponse", {"disponivel": True, "versao": uid(40), "sha256": "522ba08c9685a48d2c2a5b20bfde0773f58bb15b095e03cf605b44c224ca6916", "quantidade_cnpjs": 3041, "importado_em": moment}),
    ]
    return {"aviso": "Fixtures ilustrativas de cenários independentes, não execução do estoque; hash aaaa/arquivo de 1024 bytes são placeholders de contrato, não arquivo real.", "exemplos": [{"nome": name, "schema": name_schema, "valor": value} for name, name_schema, value in values]}


def main():
    directory = ROOT / "docs" / "contratos"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    types = "// GERADO por scripts/gerar_contrato_api.py. Não editar manualmente.\n// Contrato planejado v1.0.0; tipos estáticos não substituem validação em runtime.\n\n"
    for name, schema in S.items():
        if schema.get("description"):
            types += "/** " + schema["description"] + " */\n"
        types += f"export type {name} = {ts_type(schema)};\n\n"
    (directory / "api-types.ts").write_text(types, encoding="utf-8")
    catalog = "# Catálogo gerado de DTOs\n\nFonte editável: `scripts/gerar_contrato_api.py`. Regras de fluxo: [contrato-api.md](../contrato-api.md).\n\n"
    for name, schema in S.items():
        catalog += f"## {name}\n\n"
        if schema.get("description"):
            catalog += schema["description"] + "\n\n"
        if schema.get("type") == "object":
            catalog += "| Campo | Tipo | Obrigatório | Descrição |\n|---|---|---|---|\n"
            for field, definition in schema["properties"].items():
                typename = ts_type(definition).replace("|", "\\|").replace("\n", " ")
                description = definition.get("description", "—").replace("|", "\\|")
                catalog += f"| `{field}` | `{typename}` | {'sim' if field in schema['required'] else 'não'} | {description} |\n"
            if not schema["properties"]:
                catalog += "| — | objeto vazio | — | Não aceita propriedades. |\n"
        else:
            catalog += "```typescript\n" + ts_type(schema) + "\n```\n"
        catalog += "\n"
    (directory / "dtos.md").write_text(catalog, encoding="utf-8")
    (directory / "exemplos.json").write_text(json.dumps(examples(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from gerar_handoff_frontend import gerar_handoff
    gerar_handoff()
    print(f"Gerados {len(S)} schemas, {sum(len(methods) for methods in paths.values())} operações e tipos TypeScript.")


if __name__ == "__main__":
    main()
