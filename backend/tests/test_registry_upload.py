from pathlib import Path
import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from antecipe.adapters.contract import validator
from antecipe.adapters.lot_store import LotStore
from antecipe.adapters.schema import loads, registry, lots, results
from antecipe.adapters.worker import Worker
from test_input_configurations import configuration
from test_t11_readers import csv_bytes, values
from test_t12_uploads import manifest

CSV = "DOC;SITUACAO_CADASTRAL\n22144961000102;ATIVA\n"
PATH = "/api/v1/cadastro/importacao"


def headers():
    return {"Idempotency-Key": str(uuid4())}


def test_rules_import_then_csv_unblocks_lot_and_persists_results(client, db, tmp_path):
    # This reproduces importing fund rules in the UI without having run the CLI.
    assert (
        client.post("/api/v1/fundos/regras/importacao", json=configuration(), headers=headers()).status_code
        == 200
    )
    assert not client.get("/api/v1/cadastro/status").json()["disponivel"]
    data = csv_bytes([values()])
    store = LotStore(db, tmp_path)
    created, _ = store.create(manifest(data), str(uuid4()))
    lid, aid = created["lote"]["id"], created["arquivos"][0]["id"]
    store.upload(lid, [aid], [data], str(uuid4()))
    store.enqueue(lid, str(uuid4()))
    Worker(db).run_once()
    pending = client.get(f"/api/v1/lotes/{lid}/pendencias").json()["itens"]
    assert [p["codigo"] for p in pending] == ["BASE_CADASTRAL_AUSENTE"]
    response = client.post(PATH, json={"csv": CSV}, headers=headers())
    assert response.status_code == 200, response.text
    validator("BaseCadastralStatusResponse").validate(response.json())
    version = response.json()["versao"]
    assert client.get("/api/v1/cadastro/status").json() == response.json()
    assert client.post(f"/api/v1/lotes/{lid}/processamento", headers=headers()).status_code == 202
    Worker(db).run_once()
    assert client.get(f"/api/v1/lotes/{lid}").json()["status"] == "CONCLUIDO"
    assert client.get(f"/api/v1/lotes/{lid}/pendencias").json()["itens"] == []
    assert len(client.get(f"/api/v1/arquivos/{aid}/resultados").json()["itens"]) == 1
    with db.connect() as c:
        assert c.scalar(select(lots.c.load_id)) == version
        assert c.scalar(select(registry.c.situation)) == "ATIVA"
        assert c.scalar(select(func.count()).select_from(results)) == 1


@pytest.mark.parametrize(
    "bad",
    [
        "{}",
        CSV.replace("ATIVA", "ATIVA\x00"),
        "\ud800",
        "DOC;SITUACAO_CADASTRAL\n",
        "DOC;SITUACAO_CADASTRAL\n123;ATIVA\n",
        CSV + "22144961000102;BAIXADA\n",
        CSV + "22144961000103\n",
        CSV + "22144961000103;ATIVA;extra\n",
        CSV + '"incompleto',
    ],
)
def test_invalid_csv_is_atomic_and_preserves_current_registry(client, db, bad):
    original = client.post(PATH, json={"csv": CSV}, headers=headers()).json()
    response = client.post(
        PATH, content=json.dumps({"csv": bad}), headers={**headers(), "Content-Type": "application/json"}
    )
    assert response.status_code == 422, response.text
    assert client.get("/api/v1/cadastro/status").json() == original
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(loads)) == 1
        assert c.scalar(select(func.count()).select_from(registry)) == 1


def test_registry_import_replay_size_limit_and_busy_protection(client, db, tmp_path):
    key = headers()
    original = client.post(PATH, json={"csv": CSV}, headers=key)
    replay = client.post(PATH, json={"csv": CSV}, headers=key)
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == original.json()
    changed = CSV.replace("ATIVA", "BAIXADA")
    assert client.post(PATH, json={"csv": changed}, headers=key).status_code == 409
    assert client.post(PATH, json={"csv": CSV}, headers=headers()).json() == original.json()
    assert client.post(PATH, json={"csv": "á" * 600000}, headers=headers()).status_code == 413
    data = csv_bytes()
    created, _ = LotStore(db, tmp_path).create(manifest(data), str(uuid4()))
    with db.begin() as c:
        c.execute(
            update(lots)
            .where(lots.c.id == created["lote"]["id"])
            .values(load_id=original.json()["versao"], status="BLOQUEADO")
        )
    response = client.post(PATH, json={"csv": changed}, headers=headers())
    assert response.status_code == 409
    assert response.json()["erro"]["codigo"] == "ESTADO_INVALIDO"
    assert client.get("/api/v1/cadastro/status").json() == original.json()


def test_delivered_registry_can_be_uploaded_without_cli(client):
    content = Path("../files/cnpj_situacao_mock.csv").read_bytes().decode("utf-8")
    response = client.post(PATH, json={"csv": content}, headers=headers())
    assert response.status_code == 200, response.text
    assert response.json()["quantidade_cnpjs"] > 0
