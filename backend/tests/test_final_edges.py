from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from antecipe.adapters.lot_store import LotStore, MAX_BYTES
from antecipe.application.errors import AppError
from antecipe.adapters.readers import parse_row, NUMERIC_ID
from test_t11_readers import csv_bytes, values, COLUMNS
from test_t12_uploads import manifest


def test_original_numeric_excel_value_preserved():
    raw = dict(zip(COLUMNS, values()))
    raw["NU_DOCUMENTO"] = NUMERIC_ID + "351153"
    parsed = parse_row(raw)
    assert parsed["raw"]["NU_DOCUMENTO"] == "351153"
    assert any(e["campo"] == "NU_DOCUMENTO" for e in parsed["errors"])


def test_exact_64mib_and_excess_and_concurrent_replay(db, tmp_path):
    store = LotStore(db, tmp_path)
    data = b"0" * MAX_BYTES
    created, _ = store.create(manifest(data), str(uuid4()))
    lid = created["lote"]["id"]
    aid = created["arquivos"][0]["id"]
    with pytest.raises(AppError) as error:
        store.upload(lid, [aid], [data + b"0"], str(uuid4()))
    assert error.value.status == 413
    assert store.upload(lid, [aid], [data], str(uuid4()))[0]["arquivos"][0]["bytes_recebidos"] == MAX_BYTES
    data = csv_bytes()
    created, _ = store.create(manifest(data), str(uuid4()))
    lid = created["lote"]["id"]
    aid = created["arquivos"][0]["id"]
    barrier = Barrier(2)
    key = str(uuid4())

    def run(_):
        barrier.wait(timeout=10)
        try:
            return store.upload(lid, [aid], [data], key)
        except AppError as exc:
            assert exc.code == "REQUISICAO_EM_ANDAMENTO"
            return None

    with ThreadPoolExecutor(2) as pool:
        output = list(pool.map(run, range(2)))
    successes = [r for r in output if r]
    assert successes
    replay = store.upload(lid, [aid], [data], key)
    assert replay[1] and replay[0] == successes[0][0]


def test_all_operation_ids_registered(client):
    from antecipe.adapters.contract import SPEC

    assert {r.operation_id for r in client.app.routes if hasattr(r, "operation_id")} == {
        op["operationId"] for methods in SPEC["paths"].values() for op in methods.values()
    }
