"""Structured diagnostics with an allowlist; never serialize requests or exception messages."""

import json
import logging
import math
import os
import re
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from inspect import signature
from pathlib import Path
from time import perf_counter
from uuid import UUID

from antecipe.application.errors import AppError

ROOT = Path(__file__).resolve().parent
CODE_FILES = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.py")}
CONTEXT: ContextVar[dict] = ContextVar("log_context", default={})
LOG = logging.getLogger("antecipe")
SERVICE = {"name": "antecipe", "version": "1.0.0", "environment": "local"}
LEVELS = {name: getattr(logging, name) for name in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")}
OPERATIONS = set(
    """verificarVida verificarProntidao obterCapacidades obterStatusCadastro importarCadastro importarRegrasFundos listarFundos
consultarRegrasFundo atualizarRegrasFundo listarLotes criarLote consultarLote enviarBatch
solicitarProcessamento listarArquivosLote listarPendenciasLote listarResumosFundos consultarArquivo
listarResultados migrate import-registry import-rules worker""".split()
)
ERROR_CODES = set(
    """VALIDACAO_REQUISICAO RECURSO_NAO_ENCONTRADO ESTADO_INVALIDO IDEMPOTENCIA_CONFLITANTE
REQUISICAO_EM_ANDAMENTO UPLOAD_INCOMPLETO LIMITE_UPLOAD_EXCEDIDO LIMITE_LOTE_EXCEDIDO
TIPO_ARQUIVO_NAO_SUPORTADO INTEGRIDADE_ARQUIVO ARQUIVO_FORA_MANIFESTO ARQUIVO_JA_RECEBIDO CURSOR_INVALIDO
VERSAO_REGRAS_CONFLITANTE CONFIGURACAO_INVALIDA ESTRUTURA_ARQUIVO_INVALIDA ARQUIVO_CORROMPIDO
DADOS_IMPEDEM_PL FUNDOS_SEM_REGRAS BASE_CADASTRAL_INDISPONIVEL INFRAESTRUTURA_INDISPONIVEL ERRO_INTERNO
FUNDO_SEM_REGRAS BASE_CADASTRAL_AUSENTE""".split()
)
REASONS = ERROR_CODES | set(
    """NOTA_DUPLICADA CNPJ_SACADO_VALIDO NAO_VENCIDA SITUACAO_CADASTRAL_SACADO
TIPO_RECEBIVEL VALOR_MINIMO PRAZO_MINIMO PRAZO_MAXIMO CONCENTRACAO_MAXIMA_SACADO
CONCENTRACAO_MAXIMA_CEDENTE""".split()
)
IDS = {"request_id", "lot_id", "execution_id", "file_id", "fund_id", "rule_version", "registry_version"}
COUNTS = {
    "file_count",
    "byte_count",
    "row_count",
    "error_count",
    "approved_count",
    "rejected_count",
    "pending_count",
    "checkpoint",
    "status_code",
    "duration_ms",
}
FLAGS = {"replayed", "recovered", "retry"}
ERROR_KINDS = {
    "AppError",
    "ValueError",
    "TypeError",
    "KeyError",
    "OSError",
    "FileError",
    "OperationalError",
    "IntegrityError",
    "DBAPIError",
    "SQLAlchemyError",
    "TimeoutError",
    "RuntimeError",
    "PermissionError",
    "FileNotFoundError",
    "UnexpectedError",
}
ENUMS = {
    "operation": OPERATIONS,
    "error_code": ERROR_CODES,
    "error_kind": ERROR_KINDS,
    "outcome": {"ready", "blocked", "observed", "CONCLUIDO", "CONCLUIDO_COM_ERROS", "FALHOU"},
}
BASE_EVENTS = {
    "lot.create",
    "lot.upload",
    "lot.enqueue",
    "rules.publish",
    "rules.import",
    "registry.import",
    "worker.lot",
    "worker.index",
    "worker.freeze",
    "cli.command",
}
EVENTS = {f"{base}.{suffix}" for base in BASE_EVENTS for suffix in ("started", "finished", "failed")}
EVENTS |= {
    "service.started",
    "service.stopped",
    "http.finished",
    "http.failed",
    "worker.claimed",
    "worker.lock_busy",
    "worker.checkpoint",
    "worker.chunk_committed",
    "worker.file_started",
    "worker.file_indexed",
    "worker.file_failed",
    "worker.file_finished",
    "worker.completed",
    "worker.limit_exceeded",
    "worker.no_valid_files",
    "worker.stage_committed",
    "worker.blocking",
    "worker.snapshot_reused",
    "worker.rules_frozen",
    "worker.failed",
    "idempotency.busy",
    "idempotency.conflict",
    "idempotency.replayed",
    "registry.reused",
    "registry.reactivation_selected",
    "registry.busy",
    "rules.reused",
    "rules.conflict",
    "runtime.log",
    "process.failed",
}


def safe_fields(fields):
    output: dict = {}
    for key, value in fields.items():
        if key in IDS and isinstance(value, (str, UUID)):
            try:
                output[key] = str(UUID(str(value)))
            except ValueError:
                pass
        elif key == "duration_ms" and type(value) in (int, float) and math.isfinite(value) and value >= 0:
            output[key] = round(value, 3)
        elif key == "status_code" and type(value) is int and 100 <= value <= 599:
            output[key] = value
        elif key in COUNTS - {"duration_ms", "status_code"} and type(value) is int and value >= 0:
            output[key] = value
        elif key in FLAGS and type(value) is bool:
            output[key] = value
        elif key in ENUMS and isinstance(value, str) and value in ENUMS[key]:
            output[key] = value
        elif key == "reason_counts" and isinstance(value, dict):
            output[key] = {
                code: count
                for code, count in value.items()
                if code in REASONS and type(count) is int and count >= 0
            }
        elif key == "locations" and isinstance(value, list):
            output[key] = [
                item
                for item in value[-8:]
                if isinstance(item, str)
                and item.rpartition(":")[0] in CODE_FILES
                and item.rpartition(":")[2].isdigit()
            ]
    return output


def exception_fields(error):
    kind = type(error).__name__
    data: dict = {"error_kind": kind if kind in ERROR_KINDS else "UnexpectedError"}
    locations = []
    trace = error.__traceback__
    while trace:
        try:
            relative = Path(trace.tb_frame.f_code.co_filename).resolve().relative_to(ROOT).as_posix()
            if relative in CODE_FILES:
                locations.append(f"{relative}:{trace.tb_lineno}")
        except ValueError:
            pass
        trace = trace.tb_next
    data["locations"] = locations[-8:]
    if isinstance(error, AppError):
        data.update(
            safe_fields({"error_code": error.code, "status_code": error.status, "retry": error.retry})
        )
    return data


class SafeFormatter(logging.Formatter):
    def format(self, record):
        # Foreign libraries may put URLs, SQL parameters or exception text in msg/args/exc_info.
        # Deliberately never call getMessage(), formatException() or formatStack().
        payload = getattr(record, "safe_event", {})
        payload = payload if isinstance(payload, dict) else {}
        name = payload.get("event")
        name = name if isinstance(name, str) and name in EVENTS else "runtime.log"
        fields = safe_fields(payload)
        if record.exc_info and record.exc_info[1]:
            fields.update(exception_fields(record.exc_info[1]))
        status = fields.get("status_code", 0)
        outcome = {
            "observed": "observed",
            "ready": "success",
            "blocked": "blocked",
            "CONCLUIDO": "success",
            "CONCLUIDO_COM_ERROS": "partial",
            "FALHOU": "failure",
        }.get(fields.pop("outcome", None))
        if outcome is None:
            if 400 <= status < 500 or name.endswith((".conflict", ".busy")):
                outcome = "rejected"
            elif status >= 500 or name.endswith(".failed") or record.levelno >= logging.ERROR:
                outcome = "failure"
            elif name.endswith(".blocking"):
                outcome = "blocked"
            elif name.endswith((".started", ".file_started")):
                outcome = "started"
            elif name.endswith((".finished", ".completed", "_committed", "_finished")):
                outcome = "success"
            else:
                outcome = "observed"
        output = {
            "schema_version": "1.0",
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "severity_text": next(
                (level for level, value in LEVELS.items() if value == record.levelno), "INFO"
            ),
            "service": dict(SERVICE),
            "event": {"name": name, "category": name.split(".")[0], "outcome": outcome},
        }
        groups = {
            "correlation": IDS - {"rule_version", "registry_version"},
            "versions": {"rule_version", "registry_version"},
            "counts": COUNTS - {"duration_ms", "status_code"},
            "decision": {"replayed", "recovered", "reason_counts"},
            "error": {"error_kind", "error_code", "retry", "locations"},
            "http": {"status_code"},
        }
        for group, keys in groups.items():
            selected = {key: fields[key] for key in sorted(keys) if key in fields}
            if selected:
                output[group] = selected
        for key in ("operation", "duration_ms"):
            if key in fields:
                output[key] = fields[key]
        return json.dumps(output, ensure_ascii=True, allow_nan=False)


class SafeHandler(logging.StreamHandler):
    def handleError(self, record):
        # A failed sink must not print a fallback traceback/record or alter a business transaction.
        pass


def event(name, *, level=logging.INFO, error=None, **fields):
    try:
        if name not in EVENTS:
            return
        payload = {"event": name, **safe_fields({**CONTEXT.get(), **fields})}
        if error is not None:
            payload.update(exception_fields(error))
        LOG.log(level, name, extra={"safe_event": payload})
    except Exception:
        # Observability is best effort; preserve the original application outcome.
        pass


@contextmanager
def log_context(**fields):
    token = CONTEXT.set({**CONTEXT.get(), **safe_fields(fields)})
    try:
        yield
    finally:
        CONTEXT.reset(token)


def observed(name, *, identifiers=None, summarize=None):
    """Log a returned result only after the function's transaction context has exited."""

    def decorate(function):
        sig = signature(function)

        @wraps(function)
        def wrapped(*args, **kwargs):
            bound = sig.bind(*args, **kwargs).arguments
            fields = {field: bound.get(arg) for arg, field in (identifiers or {}).items()}
            with log_context(**fields):
                start = perf_counter()
                event(name + ".started")
                try:
                    result = function(*args, **kwargs)
                except Exception as exc:
                    event(
                        name + ".failed",
                        level=logging.WARNING
                        if isinstance(exc, AppError) and exc.status < 500
                        else logging.ERROR,
                        error=exc,
                        duration_ms=(perf_counter() - start) * 1000,
                    )
                    raise
                try:
                    details = summarize(result) if summarize else {}
                except Exception:
                    details = {}
                event(name + ".finished", duration_ms=(perf_counter() - start) * 1000, **details)
                return result

        return wrapped

    return decorate


def configure_logging(service="antecipe"):
    SERVICE["name"] = (
        service if service in {"antecipe", "antecipe-api", "antecipe-worker", "antecipe-cli"} else "antecipe"
    )
    environment = os.environ.get("APP_ENV", "local")
    SERVICE["environment"] = (
        environment if environment in {"local", "test", "staging", "production"} else "local"
    )
    revision = os.environ.get("APP_REVISION", "")
    SERVICE.pop("revision", None)
    if re.fullmatch(r"[0-9a-f]{40}", revision):
        SERVICE["revision"] = revision
    level = LEVELS.get(os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    handler = SafeHandler()
    handler.setFormatter(SafeFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    logging.captureWarnings(True)
    for name in ("antecipe", "uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy", "alembic"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(level)
    # Access events are supplied by the middleware using operation IDs, never raw URLs/IPs.
    logging.getLogger("uvicorn.access").disabled = True
    sys.excepthook = lambda typ, error, trace: event("process.failed", level=logging.CRITICAL, error=error)
    threading.excepthook = lambda args: event("process.failed", level=logging.CRITICAL, error=args.exc_value)
