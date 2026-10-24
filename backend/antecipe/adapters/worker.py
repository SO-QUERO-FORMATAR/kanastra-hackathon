import logging
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, update, insert, delete, func, text

from antecipe.adapters.schema import (
    lots,
    files,
    executions,
    staging,
    contexts,
    funds,
    rules,
    loads,
    registry,
    pending,
    results,
)
from antecipe.adapters.admin import discover, REGISTRY_LOCK
from antecipe.adapters.processor import PgProcessor, lock_id
from antecipe.adapters.readers import read_rows, parse_row, as_title, FileError
from antecipe.application.errors import AppError
from antecipe.domain.config import Configuration
from antecipe.domain.entities import Origin, normalize_document, document_root

log = logging.getLogger("antecipe.worker")


class Worker:
    def __init__(self, engine, batch_size=2000, hook=None):
        self.engine, self.batch_size, self.hook = engine, batch_size, hook

    def event(self, phase):
        if self.hook:
            self.hook(phase)

    def run_once(self) -> bool:
        # Session lock survives chunk commits and disappears automatically on connection/process death.
        with self.engine.connect() as owner:
            candidates = (
                owner.execute(
                    select(executions)
                    .where(executions.c.status.in_(["QUEUED", "RUNNING"]))
                    .order_by(executions.c.created_at)
                    .limit(100)
                )
                .mappings()
                .all()
            )
            owner.commit()
            for candidate in candidates:
                key = lock_id("job:" + candidate["lot_id"])
                acquired = owner.scalar(text("select pg_try_advisory_lock(:key)"), {"key": key})
                owner.commit()
                if not acquired:
                    continue
                try:
                    with owner.begin():
                        job = (
                            owner.execute(
                                select(executions).where(executions.c.id == candidate["id"]).with_for_update()
                            )
                            .mappings()
                            .one()
                        )
                        if job["status"] not in ["QUEUED", "RUNNING"]:
                            continue
                        owner.execute(
                            update(executions)
                            .where(executions.c.id == job["id"])
                            .values(status="RUNNING", owner=str(uuid4()), heartbeat=func.now())
                        )
                    try:
                        self.process_lot(job["lot_id"], job["id"])
                    except Exception:
                        log.exception("Falha técnica lote=%s execução=%s", job["lot_id"], job["id"])
                        with self.engine.begin() as c:
                            error = AppError("ERRO_INTERNO", "Falha técnica; retome o lote", 500, True).dto()
                            c.execute(
                                update(lots)
                                .where(lots.c.id == job["lot_id"])
                                .values(status="FALHOU", error=error, updated_at=func.now())
                            )
                            c.execute(
                                update(executions).where(executions.c.id == job["id"]).values(status="FAILED")
                            )
                        raise
                    return True
                finally:
                    owner.execute(text("select pg_advisory_unlock(:key)"), {"key": key})
                    owner.commit()
        return False

    def process_lot(self, lid, eid):
        with self.engine.connect() as c:
            lot = c.execute(select(lots).where(lots.c.id == lid)).mappings().one()
        if not lot["indexed"]:
            if not self.index(lid, eid):
                return
        if not self.freeze(lid, eid):
            return
        with self.engine.connect() as c:
            load_id = c.scalar(select(lots.c.load_id).where(lots.c.id == lid))
            context = {
                r.fund_id: (Configuration.from_dict(r.configuration), r.pl)
                for r in c.execute(
                    select(contexts.c.fund_id, contexts.c.pl, rules.c.configuration)
                    .join(rules, contexts.c.rule_id == rules.c.id)
                    .where(contexts.c.lot_id == lid)
                )
            }
            fs = (
                c.execute(
                    select(files)
                    .where(files.c.lot_id == lid, files.c.status != "FALHOU")
                    .order_by(files.c.position)
                )
                .mappings()
                .all()
            )
        for file in fs:
            while True:
                with self.engine.begin() as c:
                    # The result/checkpoint commit is the only progress boundary.
                    checkpoint = c.scalar(
                        select(func.coalesce(func.max(results.c.sequence), 0)).where(
                            results.c.file_id == file["id"]
                        )
                    )
                    rows = (
                        c.execute(
                            select(staging)
                            .where(staging.c.file_id == file["id"], staging.c.sequence > checkpoint)
                            .order_by(staging.c.sequence)
                            .limit(self.batch_size)
                        )
                        .mappings()
                        .all()
                    )
                    if not rows:
                        break
                    titles, diagnostics = [], []
                    for row in rows:
                        parsed = row["payload"]
                        errors = list(parsed["errors"])
                        config, _ = context[row["fund_id"]]
                        for side, field in [("SACADO", "DOC_SACADO"), ("CEDENTE", "DOC_CEDENTE")]:
                            if (
                                config.rule("CONCENTRACAO_MAXIMA_" + side).active
                                and document_root(parsed["raw"].get(field) or "") is None
                            ):
                                errors.append(
                                    {
                                        "campo": field,
                                        "codigo": "DOCUMENTO_SEM_RAIZ",
                                        "mensagem": "Documento sem raiz utilizável",
                                    }
                                )
                        if errors:
                            rid = str(uuid4())
                            dto = {
                                "id": rid,
                                "lote_id": lid,
                                "arquivo_id": file["id"],
                                "sequencia": row["sequence"],
                                "linha": row["line"],
                                "dados_originais": parsed["raw"],
                                "tipo": "ERRO_DADOS",
                                "status": None,
                                "titulo": None,
                                "motivos": [],
                                "erros_dados": errors,
                                "desconto": "0.00",
                                "valor_liquido": "0.00",
                            }
                            diagnostics.append(
                                dict(
                                    id=rid,
                                    lot_id=lid,
                                    file_id=file["id"],
                                    sequence=row["sequence"],
                                    line=row["line"],
                                    fund_id=row["fund_id"],
                                    type="ERRO_DADOS",
                                    status=None,
                                    nominal=row["nominal"],
                                    discount=Decimal(0),
                                    net=Decimal(0),
                                    payload=dto,
                                )
                            )
                        else:
                            titles.append(
                                as_title(
                                    parsed,
                                    row["fund_id"],
                                    Origin(lid, file["id"], row["line"], row["sequence"]),
                                )
                            )
                    docs = {normalize_document(t.debtor_document) for t in titles}
                    situations = (
                        dict(
                            c.execute(
                                select(registry.c.document, registry.c.situation).where(
                                    registry.c.load_id == load_id, registry.c.document.in_(docs)
                                )
                            ).all()
                        )
                        if docs
                        else {}
                    )
                    PgProcessor(self.engine).process(
                        titles, context, situations, connection=c, execution_id=eid, diagnostics=diagnostics
                    )
                    c.execute(update(files).where(files.c.id == file["id"]).values(status="ANALISANDO"))
                    self.event("before_commit")
                self.event("after_commit")
                log.info(
                    "lote=%s arquivo=%s fase=ANALISE linha=%s cadastro=%s",
                    lid,
                    file["id"],
                    rows[-1]["line"],
                    load_id,
                )
            with self.engine.begin() as c:
                errors = c.scalar(
                    select(func.count())
                    .select_from(results)
                    .where(results.c.file_id == file["id"], results.c.type == "ERRO_DADOS")
                )
                c.execute(
                    update(files)
                    .where(files.c.id == file["id"])
                    .values(status="CONCLUIDO_COM_ERROS" if errors else "CONCLUIDO", completed_at=func.now())
                )
        with self.engine.begin() as c:
            errors = c.scalar(
                select(func.count())
                .select_from(files)
                .where(files.c.lot_id == lid, files.c.status.in_(["FALHOU", "CONCLUIDO_COM_ERROS"]))
            )
            c.execute(
                update(lots)
                .where(lots.c.id == lid)
                .values(
                    status="CONCLUIDO_COM_ERROS" if errors else "CONCLUIDO",
                    completed_at=func.now(),
                    updated_at=func.now(),
                )
            )
            c.execute(
                update(executions).where(executions.c.id == eid).values(status="DONE", heartbeat=func.now())
            )

    def index(self, lid, eid):
        with self.engine.begin() as c:
            fs = (
                c.execute(select(files).where(files.c.lot_id == lid).order_by(files.c.position))
                .mappings()
                .all()
            )
            c.execute(delete(staging).where(staging.c.file_id.in_([f["id"] for f in fs])))
            c.execute(delete(contexts).where(contexts.c.lot_id == lid))
            c.execute(
                update(lots)
                .where(lots.c.id == lid)
                .values(
                    status="INDEXANDO", lines_read=0, started_at=func.coalesce(lots.c.started_at, func.now())
                )
            )
        read_count = 0
        fund_cache = {}
        for file in fs:
            batch = []
            sequence = 0
            try:
                for line, raw in read_rows(Path(file["path"]), file["format"], file["sheet"]):
                    read_count += 1
                    sequence += 1
                    if read_count > 500000:
                        with self.engine.begin() as c:
                            c.execute(
                                update(lots)
                                .where(lots.c.id == lid)
                                .values(
                                    status="FALHOU",
                                    lines_read=read_count,
                                    error=AppError(
                                        "LIMITE_LOTE_EXCEDIDO",
                                        "Lote excede 500000 linhas; crie novo lote",
                                        422,
                                    ).dto(),
                                )
                            )
                            c.execute(update(executions).where(executions.c.id == eid).values(status="DONE"))
                        return False
                    parsed = parse_row(raw)
                    doc = parsed["fund_document"]
                    fid = None
                    if doc:
                        if doc not in fund_cache:
                            with self.engine.begin() as c:
                                fund_cache[doc] = discover(c, doc, raw["NOME_FUNDO"] or doc)
                        fid = fund_cache[doc]
                    batch.append(
                        dict(
                            file_id=file["id"],
                            line=line,
                            sequence=sequence,
                            fund_id=fid,
                            nominal=Decimal(parsed["nominal"]) if parsed["nominal"] is not None else None,
                            payload=parsed,
                            errors=parsed["errors"],
                            blocks_pl=parsed["blocks_pl"],
                        )
                    )
                    if len(batch) >= self.batch_size:
                        self.write_stage(batch, lid, read_count)
                        batch = []
                if batch:
                    self.write_stage(batch, lid, read_count)
                with self.engine.begin() as c:
                    c.execute(
                        update(files)
                        .where(files.c.id == file["id"])
                        .values(status="PRONTO", total_lines=sequence, error=None)
                    )
            except FileError as exc:
                with self.engine.begin() as c:
                    c.execute(delete(staging).where(staging.c.file_id == file["id"]))
                    c.execute(
                        update(files)
                        .where(files.c.id == file["id"])
                        .values(
                            status="FALHOU",
                            total_lines=None,
                            error=AppError("ESTRUTURA_ARQUIVO_INVALIDA", str(exc)).dto(),
                        )
                    )
        with self.engine.begin() as c:
            valid = c.scalar(
                select(func.count())
                .select_from(files)
                .where(files.c.lot_id == lid, files.c.status == "PRONTO")
            )
            if not valid:
                c.execute(
                    update(lots)
                    .where(lots.c.id == lid)
                    .values(
                        status="FALHOU",
                        error=AppError("ESTRUTURA_ARQUIVO_INVALIDA", "Nenhum arquivo utilizável").dto(),
                    )
                )
                c.execute(update(executions).where(executions.c.id == eid).values(status="DONE"))
                return False
            data = staging.join(files, staging.c.file_id == files.c.id)
            totals = c.execute(
                select(staging.c.fund_id, func.coalesce(func.sum(staging.c.nominal), 0))
                .select_from(data)
                .where(files.c.lot_id == lid, staging.c.fund_id.is_not(None))
                .group_by(staging.c.fund_id)
            ).all()
            if totals:
                c.execute(insert(contexts), [{"lot_id": lid, "fund_id": f, "pl": p} for f, p in totals])
            total = c.scalar(select(func.count()).select_from(data).where(files.c.lot_id == lid))
            c.execute(
                update(lots)
                .where(lots.c.id == lid)
                .values(indexed=True, total_lines=total, lines_read=read_count)
            )
        return True

    def write_stage(self, batch, lid, count):
        with self.engine.begin() as c:
            c.execute(insert(staging), batch)
            c.execute(update(lots).where(lots.c.id == lid).values(lines_read=count, updated_at=func.now()))

    def freeze(self, lid, eid):
        with self.engine.begin() as c:
            c.execute(text("select pg_advisory_xact_lock(:key)"), {"key": REGISTRY_LOCK})
            lot = c.execute(select(lots).where(lots.c.id == lid).with_for_update()).mappings().one()
            if lot["load_id"]:
                c.execute(update(lots).where(lots.c.id == lid).values(status="ANALISANDO"))
                return True
            c.execute(delete(pending).where(pending.c.lot_id == lid))
            c.execute(
                update(lots).where(lots.c.id == lid).values(pending_revision=lots.c.pending_revision + 1)
            )
            problems = []

            def problem(code, action, message, fund_id=None, file_id=None, line=None, field=None):
                problems.append(
                    dict(
                        id=str(uuid4()),
                        lot_id=lid,
                        code=code,
                        action=action,
                        message=message,
                        fund_id=fund_id,
                        file_id=file_id,
                        line=line,
                        field=field,
                    )
                )

            configured = (
                c.execute(
                    select(funds)
                    .join(contexts, contexts.c.fund_id == funds.c.id)
                    .where(contexts.c.lot_id == lid)
                    .order_by(funds.c.id)
                    .with_for_update(of=funds)
                )
                .mappings()
                .all()
            )
            for fund in configured:
                if not fund["active_rule"]:
                    problem(
                        "FUNDO_SEM_REGRAS",
                        "CONFIGURAR_FUNDO",
                        "Configure regras próprias deste fundo",
                        fund["id"],
                    )
            load = c.scalar(select(loads.c.id).where(loads.c.active))
            if not load:
                problem("BASE_CADASTRAL_AUSENTE", "IMPORTAR_BASE_CADASTRAL", "Importe a base cadastral")
            invalid = c.execute(
                select(staging)
                .join(files, staging.c.file_id == files.c.id)
                .where(files.c.lot_id == lid, staging.c.blocks_pl)
            ).mappings()
            for row in invalid:
                for field in ["DOC_FUNDO", "VALOR_NOMINAL"]:
                    if any(e["campo"] == field for e in row["errors"]):
                        problem(
                            "DADOS_IMPEDEM_PL",
                            "RECRIAR_LOTE",
                            "Dado impede PL confiável",
                            row["fund_id"],
                            row["file_id"],
                            row["line"],
                            field,
                        )
            if problems:
                c.execute(insert(pending), problems)
                c.execute(
                    update(lots)
                    .where(lots.c.id == lid)
                    .values(
                        status="BLOQUEADO",
                        updated_at=func.now(),
                    )
                )
                c.execute(update(executions).where(executions.c.id == eid).values(status="DONE"))
                return False
            self.event("before_freeze")
            for fund in configured:
                c.execute(
                    update(contexts)
                    .where(contexts.c.lot_id == lid, contexts.c.fund_id == fund["id"])
                    .values(rule_id=fund["active_rule"])
                )
            c.execute(
                update(lots)
                .where(lots.c.id == lid)
                .values(status="ANALISANDO", load_id=load, updated_at=func.now())
            )
        return True
