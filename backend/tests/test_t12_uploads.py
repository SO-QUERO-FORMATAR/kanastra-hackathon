import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import select

from antecipe.adapters.lot_store import LotStore
from antecipe.application.errors import AppError
from antecipe.adapters.schema import files
from test_t11_readers import csv_bytes


def manifest(data, count=1):
    return {
        "nome": "Teste",
        "arquivos": [
            {
                "client_id": str(uuid4()),
                "nome": "../same.csv",
                "formato": "CSV",
                "tamanho_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "ordem": i,
                "aba": None,
            }
            for i in range(count)
        ],
    }


def test_manifest_upload_replay_order_seal(db, tmp_path):
    service = LotStore(db, tmp_path)
    data = csv_bytes()
    body = manifest(data, 3)
    key = str(uuid4())
    created, replay = service.create(body, key)
    assert not replay and created["lote"]["status"] == "RECEBENDO"
    assert service.create(body, key) == (created, True)
    with pytest.raises(AppError):
        service.create({**body, "nome": "changed"}, key)
    lid = created["lote"]["id"]
    ids = [a["id"] for a in created["arquivos"]]
    upload_key = str(uuid4())
    received = service.upload(lid, [ids[2]], [data], upload_key)
    assert service.upload(lid, [ids[2]], [data], upload_key) == (received[0], True)
    with pytest.raises(AppError):
        service.enqueue(lid, str(uuid4()))
    service.upload(lid, ids[:2], [data, data], str(uuid4()))
    queued, _ = service.enqueue(lid, str(uuid4()))
    assert queued["status"] == "NA_FILA"
    with db.connect() as c:
        rows = c.execute(select(files).order_by(files.c.position)).mappings().all()
        assert [r["id"] for r in rows] == ids
        assert all(tmp_path in __import__("pathlib").Path(r["path"]).parents for r in rows)
    with pytest.raises(AppError):
        service.upload(lid, ids[:1], [data], str(uuid4()))


def test_batch_atomicity_limits_hash_and_disk_error(db, tmp_path):
    service = LotStore(db, tmp_path)
    data = csv_bytes()
    created, _ = service.create(manifest(data, 4), str(uuid4()))
    lid = created["lote"]["id"]
    ids = [a["id"] for a in created["arquivos"]]
    for selected, contents in [(ids, [data] * 4), (ids[:2], [data, b"wrong"]), ([str(uuid4())], [data])]:
        with pytest.raises(AppError):
            service.upload(lid, selected, contents, str(uuid4()))
    with db.connect() as c:
        assert set(c.scalars(select(files.c.status))) == {"AGUARDANDO_UPLOAD"}
    bad_storage = tmp_path / "file"
    bad_storage.write_text("not directory")
    with pytest.raises(OSError):
        LotStore(db, bad_storage).upload(lid, ids[:1], [data], str(uuid4()))
