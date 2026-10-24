import hashlib
from collections import Counter
from decimal import Decimal, localcontext
from uuid import uuid4

from sqlalchemy import select, insert, update, text, func, values, column, Text, Uuid, Integer
from sqlalchemy.dialects.postgresql import insert as pg_insert

from antecipe.adapters.schema import results, approved, exposures, reasons, files, lots, executions
from antecipe.adapters.serialization import decision_dto
from antecipe.domain.concentration import exposure_keys
from antecipe.domain.engine import evaluate
from antecipe.domain.entities import normalize_document


def lock_id(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)


class PgProcessor:
    def __init__(self, engine):
        self.engine = engine

    def process(
        self, titles, contexts, registry, fault=None, connection=None, execution_id=None, diagnostics=()
    ):
        if connection is None:
            with self.engine.begin() as c:
                return self.process(titles, contexts, registry, fault, c, execution_id, diagnostics)
        c = connection
        # Acquire every advisory lock in a single globally ordered set, including cross-fund note identities.
        resources = {lock_id("fund:" + t.fund.id) for t in titles}
        resources |= {lock_id("note:" + repr(t.operational_key)) for t in titles}
        resources |= {lock_id("origin:" + t.origin.file_id) for t in titles}
        resources |= {lock_id("origin:" + d["file_id"]) for d in diagnostics}
        if resources:
            c.execute(
                text(
                    "SELECT pg_advisory_xact_lock(k) FROM (SELECT unnest(CAST(:keys AS bigint[])) AS k ORDER BY k) s"
                ),
                {"keys": sorted(resources)},
            )
        origins = {(t.origin.file_id, t.origin.line) for t in titles} | {
            (d["file_id"], d["line"]) for d in diagnostics
        }
        wanted_origins = values(
            column("file_id", Uuid(as_uuid=False)), column("line", Integer), name="wanted_origins"
        ).data(sorted(origins))
        existing = (
            {
                (r.file_id, r.line): r.payload
                for r in c.execute(
                    select(results.c.file_id, results.c.line, results.c.payload).join(
                        wanted_origins,
                        (results.c.file_id == wanted_origins.c.file_id)
                        & (results.c.line == wanted_origins.c.line),
                    )
                )
            }
            if origins
            else {}
        )
        fund_ids = {t.fund.id for t in titles}
        balances = {
            (r.fund_id, r.side, r.root): r.amount
            for r in c.execute(select(exposures).where(exposures.c.fund_id.in_(fund_ids)))
        }
        keys = {t.operational_key for t in titles}
        wanted_keys = values(
            column("seller", Text), column("debtor", Text), column("number", Text), name="wanted_keys"
        ).data(sorted(keys))
        known = (
            set(
                c.execute(
                    select(approved.c.seller, approved.c.debtor, approved.c.number).join(
                        wanted_keys,
                        (approved.c.seller == wanted_keys.c.seller)
                        & (approved.c.debtor == wanted_keys.c.debtor)
                        & (approved.c.number == wanted_keys.c.number),
                    )
                ).all()
            )
            if keys
            else set()
        )
        new_results: list[dict] = []
        new_approved: list[dict] = []
        new_reasons: list[dict] = []
        output: list[dict] = []
        changed = set()
        for title in titles:
            origin = (title.origin.file_id, title.origin.line)
            if origin in existing:
                output.append(existing[origin])
                continue
            config, pl = contexts[title.fund.id]
            result = evaluate(
                title,
                config,
                pl,
                registry.get(normalize_document(title.debtor_document)),
                balances,
                title.operational_key in known,
            )
            rid = str(uuid4())
            dto = decision_dto(result, rid)
            output.append(dto)
            new_results.append(
                dict(
                    id=rid,
                    lot_id=title.origin.lot_id,
                    file_id=title.origin.file_id,
                    sequence=title.origin.sequence,
                    line=title.origin.line,
                    fund_id=title.fund.id,
                    type="ANALISE",
                    status=dto["status"],
                    nominal=title.nominal,
                    discount=result.discount,
                    net=result.net,
                    payload=dto,
                )
            )
            new_reasons.extend(
                {
                    "result_id": rid,
                    "code": r.code,
                    "file_id": title.origin.file_id,
                    "sequence": title.origin.sequence,
                }
                for r in result.reasons
            )
            if result.approved:
                known.add(title.operational_key)
                seller, debtor, number = title.operational_key
                new_approved.append(
                    dict(seller=seller, debtor=debtor, number=number, fund_id=title.fund.id, result_id=rid)
                )
                with localcontext() as ctx:
                    ctx.prec = 38
                    for key in exposure_keys(title).values():
                        balances[key] = balances.get(key, Decimal(0)) + title.nominal
                        changed.add(key)
        for diagnostic in diagnostics:
            if (diagnostic["file_id"], diagnostic["line"]) not in existing:
                new_results.append(diagnostic)
                output.append(diagnostic["payload"])
        if new_results:
            c.execute(insert(results), new_results)
        if new_approved:
            c.execute(insert(approved), new_approved)
        if fault:
            fault()
        if new_reasons:
            c.execute(insert(reasons), new_reasons)
        if changed:
            stmt = pg_insert(exposures).values(
                [
                    {"fund_id": f, "side": s, "root": r, "amount": balances[(f, s, r)]}
                    for f, s, r in sorted(changed)
                ]
            )
            c.execute(
                stmt.on_conflict_do_update(
                    index_elements=["fund_id", "side", "root"], set_={"amount": stmt.excluded.amount}
                )
            )
        for fid, count in Counter(r["file_id"] for r in new_results).items():
            c.execute(update(files).where(files.c.id == fid).values(processed=files.c.processed + count))
        for lid, count in Counter(r["lot_id"] for r in new_results).items():
            c.execute(
                update(lots)
                .where(lots.c.id == lid)
                .values(processed=lots.c.processed + count, updated_at=func.now())
            )
        if execution_id and new_results:
            c.execute(
                update(executions)
                .where(executions.c.id == execution_id)
                .values(checkpoint=executions.c.checkpoint + len(new_results), heartbeat=func.now())
            )
        return sorted(output, key=lambda r: (r["arquivo_id"], r["sequencia"]))
