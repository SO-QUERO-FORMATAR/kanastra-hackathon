from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select, func

from antecipe.adapters.worker import Worker
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.lot_store import LotStore
from antecipe.adapters.schema import lots, results, approved, pending, contexts
from test_t11_readers import csv_bytes, values
from test_t12_uploads import manifest


def prepare(db, tmp_path, rows=None, rules=True):
    admin = PgAdmin(db)
    admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    if rules:
        admin.import_rules(Path("../files/validadores_antecipe.json"))
    data = csv_bytes(rows)
    store = LotStore(db, tmp_path)
    created, _ = store.create(manifest(data), str(uuid4()))
    lid = created["lote"]["id"]
    aid = created["arquivos"][0]["id"]
    store.upload(lid, [aid], [data], str(uuid4()))
    store.enqueue(lid, str(uuid4()))
    return store, lid, aid


def test_block_then_resume_snapshot_and_full_pl(db, tmp_path):
    rows = [values() for _ in range(12)]
    for i, row in enumerate(rows):
        row[6] = str(i)
    store, lid, aid = prepare(db, tmp_path, rows, rules=False)
    assert Worker(db, batch_size=3).run_once()
    with db.connect() as c:
        assert c.scalar(select(lots.c.status)) == "BLOQUEADO"
        assert c.scalar(select(func.count()).select_from(results)) == 0
        assert c.scalar(select(pending.c.code)) == "FUNDO_SEM_REGRAS"
    [(fid, version)] = PgAdmin(db).import_rules(Path("../files/validadores_antecipe.json"))
    store.enqueue(lid, str(uuid4()))
    Worker(db, batch_size=3).run_once()
    with db.connect() as c:
        assert c.scalar(select(lots.c.status)) == "CONCLUIDO"
        assert c.scalar(select(lots.c.processed)) == 12
        assert c.scalar(select(contexts.c.pl)) == 120000
        assert c.scalar(select(contexts.c.rule_id)) == version


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_crash_recovery_no_duplicate_effects(db, tmp_path, phase):
    rows = [values() for _ in range(12)]
    for i, row in enumerate(rows):
        row[6] = str(i)
    _, lid, _ = prepare(db, tmp_path, rows)

    class Crash(BaseException):
        pass

    def hook(at):
        if at == phase:
            raise Crash()

    with pytest.raises(Crash):
        Worker(db, batch_size=3, hook=hook).run_once()
    Worker(db, batch_size=2).run_once()
    with db.connect() as c:
        assert c.scalar(select(lots.c.processed)) == 12
        assert c.scalar(select(func.count()).select_from(results)) == 12
        assert c.scalar(select(func.count()).select_from(approved)) == 1
        assert c.scalar(select(results.c.status).where(results.c.sequence == 1)) == "APROVADO"


def test_date_error_in_pl_unreadable_blocks_and_two_workers(db, tmp_path):
    rows = [values() for _ in range(12)]
    rows[0][10] = "31/02/2026"
    _, lid, _ = prepare(db, tmp_path, rows)
    barrier = Barrier(2)

    def run(_):
        barrier.wait(timeout=10)
        return Worker(db).run_once()

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(run, range(2)))
    with db.connect() as c:
        assert c.scalar(select(lots.c.status)) == "CONCLUIDO_COM_ERROS"
        assert c.scalar(select(contexts.c.pl)) == 120000
        assert c.scalar(select(func.count()).select_from(results)) == 12
    rows[0][8] = "NaN"
    store = LotStore(db, tmp_path)
    data = csv_bytes(rows)
    created, _ = store.create(manifest(data), str(uuid4()))
    lid = created["lote"]["id"]
    store.upload(lid, [created["arquivos"][0]["id"]], [data], str(uuid4()))
    store.enqueue(lid, str(uuid4()))
    Worker(db).run_once()
    with db.connect() as c:
        assert c.scalar(select(lots.c.status).where(lots.c.id == lid)) == "BLOQUEADO"
        assert c.scalar(select(pending.c.code).where(pending.c.lot_id == lid)) == "DADOS_IMPEDEM_PL"
