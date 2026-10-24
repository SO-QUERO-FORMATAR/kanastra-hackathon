import json
import logging
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile
from uuid import uuid4
from time import perf_counter
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from jsonschema import Draft202012Validator, FormatChecker

from antecipe.settings import Settings
from antecipe.adapters.database import make_engine
from antecipe.adapters.contract import SPEC, validate
from antecipe.adapters.lot_store import LotStore, MAX_BYTES
from antecipe.adapters.queries import Queries
from antecipe.adapters.views import registry_dto, fund_dto, require, instant
from antecipe.adapters.admin import publish
from antecipe.adapters.schema import funds, rules
from antecipe.adapters.idempotency import execute
from antecipe.application.errors import AppError
from antecipe.observability import configure_logging, event, log_context

CAPACITIES = dict(
    versao_contrato="1.0.0",
    autenticacao="SEM_AUTENTICACAO_DEMO",
    formatos=["CSV", "XLSX"],
    max_arquivos_lote=100,
    max_arquivos_batch=3,
    max_bytes_arquivo=MAX_BYTES,
    max_bytes_batch=MAX_BYTES,
    max_linhas_lote=500000,
    max_pagina=100,
    polling_intervalo_ms=2000,
    permite_exportacao=False,
    permite_cancelamento=False,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging("antecipe-api")
    settings = settings or Settings()
    engine = make_engine(settings)

    @asynccontextmanager
    async def lifespan(app):
        # Uvicorn may apply its own logging configuration after receiving an app instance.
        configure_logging("antecipe-api")
        event("service.started")
        try:
            yield
        finally:
            event("service.stopped")

    app = FastAPI(title="Antecipe", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    store = LotStore(engine, settings.storage)
    queries = Queries(engine, settings.cursor_secret)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key"],
        expose_headers=["X-Request-Id", "Idempotency-Replayed", "Retry-After"],
    )

    def error_response(request, error, cause=None):
        event(
            "http.failed",
            level=logging.ERROR if error.status >= 500 else logging.WARNING,
            operation=getattr(request.state, "operation", None),
            error_code=error.code,
            status_code=error.status,
            retry=error.retry,
            error=cause if cause is not None else error,
        )
        headers = {"Retry-After": "2"} if error.retry else {}
        return JSONResponse(
            {"request_id": request.state.request_id, "erro": error.dto()},
            status_code=error.status,
            headers=headers,
        )

    @app.middleware("http")
    async def correlation(request, call_next):
        request.state.request_id = str(uuid4())
        start = perf_counter()
        with log_context(request_id=request.state.request_id):
            try:
                response = await call_next(request)
            except AppError as exc:
                response = error_response(request, exc)
            except SQLAlchemyError as exc:
                response = error_response(
                    request,
                    AppError("INFRAESTRUTURA_INDISPONIVEL", "Banco indisponível", 503, True),
                    cause=exc,
                )
            except Exception as exc:
                response = error_response(
                    request, AppError("ERRO_INTERNO", "Erro interno", 500, True), cause=exc
                )
            operation = getattr(request.state, "operation", None)
            level = logging.DEBUG if operation in {"verificarVida", "verificarProntidao"} else logging.INFO
            event(
                "http.finished",
                level=level
                if response.status_code < 400
                else logging.ERROR
                if response.status_code >= 500
                else logging.WARNING,
                operation=operation,
                status_code=response.status_code,
                duration_ms=(perf_counter() - start) * 1000,
                replayed=response.headers.get("Idempotency-Replayed") == "true",
            )
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.exception_handler(AppError)
    async def app_error(request, exc):
        return error_response(request, exc)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(
            request, AppError("RECURSO_NAO_ENCONTRADO", "Rota não encontrada", exc.status_code)
        )

    def dispatch(operation, paths, q, body, key):
        op = operation["operationId"]
        if op in ["verificarVida", "verificarProntidao"]:
            if op == "verificarProntidao":
                with engine.connect() as c:
                    c.execute(text("select 1"))
                try:
                    settings.storage.mkdir(parents=True, exist_ok=True)
                    with NamedTemporaryFile(dir=settings.storage):
                        pass
                except OSError as exc:
                    raise AppError(
                        "INFRAESTRUTURA_INDISPONIVEL", "Armazenamento indisponível", 503, True
                    ) from exc
            return {
                "status": "OK",
                "servico": "antecipe-api",
                "versao_api": "1.0.0",
                "verificado_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }, False
        if op == "obterCapacidades":
            return CAPACITIES, False
        if op == "obterStatusCadastro":
            with engine.connect() as c:
                return registry_dto(c), False
        if op == "criarLote":
            return store.create(body, key)
        if op == "enviarBatch":
            return store.upload(paths["lote_id"], body[0], body[1], key)
        if op == "solicitarProcessamento":
            return store.enqueue(paths["lote_id"], key)
        if op == "atualizarRegrasFundo":
            fid = paths["fundo_id"]
            with engine.begin() as c:

                def action():
                    try:
                        version = publish(c, fid, body["configuracao"], body["versao_base"])
                    except ValueError as exc:
                        raise AppError("CONFIGURACAO_INVALIDA", str(exc)) from exc
                    fund = require(c, funds, fid)
                    rule = require(c, rules, version)
                    return {
                        "fundo": fund_dto(fund),
                        "versao": version,
                        "criada_em": instant(rule["created_at"]),
                        "configuracao": rule["configuration"],
                    }

                result = execute(c, f"PUT /fundos/{fid}/regras", key, body, 200, action)
            event("rules.publish.finished", fund_id=fid, rule_version=result[0]["versao"], replayed=result[1])
            return result
        return queries.get(op, paths, q), False

    def make_endpoint(operation):
        async def handle(request: Request):
            params = operation.get("parameters", [])
            q = {}
            key = None
            allowed = {p["name"] for p in params if p["in"] == "query"}
            if set(request.query_params) - allowed:
                raise AppError("VALIDACAO_REQUISICAO", "Parâmetro de query desconhecido")
            for p in params:
                name = p["name"]
                source = p["in"]
                schema = p["schema"]
                value = (
                    request.path_params.get(name)
                    if source == "path"
                    else request.headers.get(name)
                    if source == "header"
                    else request.query_params.get(name)
                )
                if value is None:
                    if p.get("required"):
                        raise AppError("VALIDACAO_REQUISICAO", "Campo obrigatório: " + name)
                    continue
                try:
                    if source == "query":
                        if len(request.query_params.getlist(name)) != 1:
                            raise ValueError()
                        if schema.get("type") == "integer":
                            value = int(value)
                        if schema.get("type") == "boolean":
                            if value not in ["true", "false"]:
                                raise ValueError()
                            value = value == "true"
                    Draft202012Validator(
                        {**schema, "components": SPEC["components"]}, format_checker=FormatChecker()
                    ).validate(value)
                except Exception as exc:
                    raise AppError(
                        "VALIDACAO_REQUISICAO",
                        "Campo inválido: " + name,
                        details=[
                            {"campo": source + "." + name, "codigo": "INVALIDO", "mensagem": "Valor inválido"}
                        ],
                    ) from exc
                if source == "query":
                    q[name] = value
                if source == "header":
                    key = value
            body = None
            expected = operation.get("requestBody")
            if expected:
                media = request.headers.get("content-type", "").split(";")[0]
                if media not in expected["content"]:
                    raise AppError("TIPO_ARQUIVO_NAO_SUPORTADO", "Content-Type incompatível", 415)
                if media == "application/json":
                    try:
                        body = json.loads(await request.body())
                    except (ValueError, UnicodeError) as exc:
                        raise AppError("VALIDACAO_REQUISICAO", "JSON inválido") from exc
                    validate(expected["content"][media]["schema"]["$ref"].split("/")[-1], body)
                else:
                    if int(request.headers.get("content-length", "0")) > MAX_BYTES + 1048576:
                        raise AppError("LIMITE_UPLOAD_EXCEDIDO", "Multipart excede limite", 413)
                    async with request.form(max_files=100, max_fields=10, max_part_size=1048576) as form:
                        if set(form) != {"metadados", "arquivos"} or len(form.getlist("metadados")) != 1:
                            raise AppError("VALIDACAO_REQUISICAO", "Multipart inválido")
                        try:
                            raw_metadata = form["metadados"]
                            if not isinstance(raw_metadata, str):
                                raise ValueError("Metadados devem ser texto")
                            metadata = json.loads(raw_metadata)
                        except (ValueError, TypeError) as exc:
                            raise AppError("VALIDACAO_REQUISICAO", "Metadados malformados", 400) from exc
                        parts = form.getlist("arquivos")
                        if len(parts) > 3:
                            raise AppError("LIMITE_UPLOAD_EXCEDIDO", "Máximo três arquivos", 413)
                        validate("BatchMetadadosDTO", metadata)
                        contents = []
                        for part in parts:
                            if not hasattr(part, "read"):
                                raise AppError("VALIDACAO_REQUISICAO", "Parte binária exigida")
                            contents.append(await part.read(MAX_BYTES + 1))
                        body = metadata["arquivo_ids"], contents
            elif await request.body():
                raise AppError("VALIDACAO_REQUISICAO", "Esta operação não aceita corpo")
            response, replay = await run_in_threadpool(dispatch, operation, request.path_params, q, body, key)
            status = next(int(s) for s in operation["responses"] if s.startswith("2"))
            return JSONResponse(
                response,
                status_code=status,
                headers={"Idempotency-Replayed": "true" if replay else "false"} if key else {},
            )

        async def endpoint(request: Request):
            request.state.operation = operation["operationId"]
            with log_context(
                operation=operation["operationId"],
                lot_id=request.path_params.get("lote_id"),
                file_id=request.path_params.get("arquivo_id"),
                fund_id=request.path_params.get("fundo_id"),
            ):
                return await handle(request)

        return endpoint

    for path, methods in SPEC["paths"].items():
        for method, operation in methods.items():
            app.add_api_route(
                "/api/v1" + path,
                make_endpoint(operation),
                methods=[method.upper()],
                operation_id=operation["operationId"],
            )
    app.openapi = lambda: SPEC  # type: ignore[method-assign]
    return app


app = create_app()
