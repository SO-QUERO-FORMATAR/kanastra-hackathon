import hashlib
import json
import logging
from sqlalchemy import select, insert, text
from antecipe.adapters.schema import idempotency
from antecipe.adapters.processor import lock_id
from antecipe.application.errors import AppError
from antecipe.observability import event


def execute(c, scope, key, body, status, action):
    fingerprint = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    if not c.scalar(text("select pg_try_advisory_xact_lock(:key)"), {"key": lock_id(scope + key)}):
        event("idempotency.busy", level=logging.WARNING, error_code="REQUISICAO_EM_ANDAMENTO", retry=True)
        raise AppError("REQUISICAO_EM_ANDAMENTO", "Requisição equivalente em andamento", 409, True)
    row = (
        c.execute(select(idempotency).where(idempotency.c.scope == scope, idempotency.c.key == key))
        .mappings()
        .first()
    )
    if row:
        if row["fingerprint"] != fingerprint:
            event("idempotency.conflict", level=logging.WARNING, error_code="IDEMPOTENCIA_CONFLITANTE")
            raise AppError("IDEMPOTENCIA_CONFLITANTE", "Chave reutilizada com conteúdo diferente", 409)
        event("idempotency.replayed", replayed=True)
        return row["response"], True
    response = action()
    c.execute(
        insert(idempotency).values(
            scope=scope, key=key, fingerprint=fingerprint, status_code=status, response=response
        )
    )
    return response, False
