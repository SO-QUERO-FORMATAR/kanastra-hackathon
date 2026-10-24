from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal as D
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select, insert, func

from antecipe.adapters.processor import PgProcessor
from antecipe.adapters.schema import funds, lots, files, results, approved, exposures
from antecipe.domain.config import Configuration
from antecipe.domain.entities import Fund, Origin
from test_t02_entities import title
from test_t03_config import config_dict


def origins(db, different_funds=False):
    lid, fid = str(uuid4()), str(uuid4())
    output = []
    with db.begin() as c:
        c.execute(insert(lots).values(id=lid, name="L"))
        c.execute(insert(funds).values(id=fid, cnpj="92234400000180", name="F"))
        for i in range(2):
            if i and different_funds:
                fid = str(uuid4())
                c.execute(insert(funds).values(id=fid, cnpj="01392689000100", name="G"))
            aid = str(uuid4())
            c.execute(
                insert(files).values(
                    id=aid,
                    lot_id=lid,
                    client_id=str(uuid4()),
                    position=i,
                    name="a.csv",
                    format="CSV",
                    size=1,
                    sha256="a" * 64,
                )
            )
            output.append(
                replace(title(), fund=Fund(fid, "F", "92234400000180"), origin=Origin(lid, aid, 2, 1))
            )
    return output


@pytest.mark.parametrize("same_key,different_funds", [(True, False), (True, True), (False, False)])
def test_real_concurrency(db, same_key, different_funds):
    a, b = origins(db, different_funds)
    if not same_key:
        b = replace(b, number="other")
    barrier = Barrier(2)
    cfg = Configuration.from_dict(config_dict())

    def run(t):
        barrier.wait(timeout=10)
        return PgProcessor(db).process([t], {t.fund.id: (cfg, D("100000"))}, {"22144961000102": "ATIVA"})

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(run, [a, b]))
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(approved)) == 1
        assert c.scalar(select(func.count()).select_from(results)) == 2
        assert c.scalar(select(func.max(exposures.c.amount))) == D("10000")


def test_retry_and_fault_atomicity(db):
    a, _ = origins(db)
    processor = PgProcessor(db)
    context = {a.fund.id: (Configuration.from_dict(config_dict()), D("100000"))}

    def crash():
        raise RuntimeError("after approval")

    with pytest.raises(RuntimeError):
        processor.process([a], context, {"22144961000102": "ATIVA"}, fault=crash)
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(approved)) == 0
        assert c.scalar(select(func.count()).select_from(results)) == 0
    first = processor.process([a], context, {"22144961000102": "ATIVA"})
    assert processor.process([a], context, {"22144961000102": "ATIVA"}) == first
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(approved)) == 1
        assert c.scalar(select(lots.c.processed)) == 1
