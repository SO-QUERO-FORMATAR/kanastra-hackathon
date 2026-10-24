from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, inspect
from sqlalchemy.exc import IntegrityError

from antecipe.adapters.schema import funds, approved, exposures, lots, files, results


def uid():
    return str(uuid4())


def test_migrations_and_exact_numeric(db):
    assert {
        "funds",
        "rules",
        "registry",
        "lots",
        "files",
        "staging",
        "results",
        "approved",
        "exposures",
        "executions",
        "contexts",
        "idempotency",
        "pending",
    } <= set(inspect(db).get_table_names())
    fid = uid()
    with db.begin() as c:
        c.execute(insert(funds).values(id=fid, cnpj="01000171000183", name="F"))
        c.execute(
            insert(exposures).values(
                fund_id=fid, side="SACADO", root="01000171", amount=D("12345678901234567890.01")
            )
        )
    with db.connect() as c:
        assert c.scalar(select(exposures.c.amount)) == D("12345678901234567890.01")


def setup_origin(c):
    lid, aid, fid = uid(), uid(), uid()
    c.execute(insert(funds).values(id=fid, cnpj="01000171000183", name="F"))
    c.execute(insert(lots).values(id=lid, name="L"))
    c.execute(
        insert(files).values(
            id=aid,
            lot_id=lid,
            client_id=uid(),
            position=0,
            name="a.csv",
            format="CSV",
            size=1,
            sha256="a" * 64,
        )
    )
    return lid, aid, fid


def test_unique_operational_key_origin_and_rollback(db):
    with db.begin() as c:
        lid, aid, fid = setup_origin(c)
        rid = uid()
        c.execute(
            insert(results).values(
                id=rid,
                lot_id=lid,
                file_id=aid,
                sequence=1,
                line=2,
                type="ANALISE",
                status="APROVADO",
                payload={},
            )
        )
        row = dict(
            seller="00000000000001", debtor="00000000000002", number="000351153", result_id=rid, fund_id=fid
        )
        c.execute(insert(approved).values(**row))
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(insert(approved).values(**row))
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(
            insert(results).values(
                id=uid(),
                lot_id=lid,
                file_id=aid,
                sequence=2,
                line=2,
                type="ANALISE",
                status="BARRADO",
                payload={},
            )
        )
    with db.begin() as c:
        for seq in [2, 3]:
            c.execute(
                insert(results).values(
                    id=uid(),
                    lot_id=lid,
                    file_id=aid,
                    sequence=seq,
                    line=seq + 1,
                    type="ANALISE",
                    status="BARRADO",
                    payload={"key": "same"},
                )
            )
    with pytest.raises(RuntimeError), db.begin() as c:
        c.execute(insert(exposures).values(fund_id=fid, side="SACADO", root="00000000", amount=D("100")))
        raise RuntimeError("simulated crash")
    with db.connect() as c:
        assert c.scalar(select(exposures.c.amount)) is None
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(insert(exposures).values(fund_id=uid(), side="SACADO", root="00000000", amount=1))
