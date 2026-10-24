import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from antecipe.adapters.http import create_app
from antecipe.adapters.contract import SPEC, validator
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.worker import Worker
from antecipe.settings import Settings
from test_t03_config import config_dict
from test_t11_readers import csv_bytes
from test_t12_uploads import manifest


@pytest.fixture
def client(db, tmp_path):
    settings = Settings(database_url=str(db.url.render_as_string(hide_password=False)), storage=tmp_path)
    with TestClient(create_app(settings)) as c:
        yield c


def headers():
    return {"Idempotency-Key": str(uuid4())}


def checked(client, method, path, operation_path, **kwargs):
    response = client.request(method, "/api/v1" + path, **kwargs)
    op = SPEC["paths"][operation_path][method.lower()]
    assert str(response.status_code) in op["responses"], response.text
    schema = op["responses"][str(response.status_code)]["content"]["application/json"]["schema"][
        "$ref"
    ].split("/")[-1]
    validator(schema).validate(response.json())
    assert response.headers["X-Request-Id"]
    return response


def test_all_infrastructure_operations_contract(client, db):
    for path in ["/health/live", "/health/ready", "/capacidades", "/cadastro/status", "/fundos", "/lotes"]:
        assert checked(client, "GET", path, path).status_code == 200
    fid, version = PgAdmin(db).import_rules(Path("../files/validadores_antecipe.json"))
    checked(client, "GET", f"/fundos/{fid}/regras", "/fundos/{fundo_id}/regras")
    updated = checked(
        client,
        "PUT",
        f"/fundos/{fid}/regras",
        "/fundos/{fundo_id}/regras",
        headers=headers(),
        json={"versao_base": version, "configuracao": config_dict()},
    )
    assert updated.status_code == 200
    assert (
        checked(
            client,
            "PUT",
            f"/fundos/{fid}/regras",
            "/fundos/{fundo_id}/regras",
            headers=headers(),
            json={"versao_base": version, "configuracao": config_dict()},
        ).status_code
        == 409
    )
    data = csv_bytes()
    body = manifest(data)
    h = headers()
    response = checked(client, "POST", "/lotes", "/lotes", headers=h, json=body)
    assert response.status_code == 201
    replay = checked(client, "POST", "/lotes", "/lotes", headers=h, json=body)
    assert replay.json() == response.json() and replay.headers["Idempotency-Replayed"] == "true"
    created = response.json()
    lid = created["lote"]["id"]
    aid = created["arquivos"][0]["id"]
    for path, op in [(f"/lotes/{lid}", "/lotes/{lote_id}"), (f"/arquivos/{aid}", "/arquivos/{arquivo_id}")]:
        assert checked(client, "GET", path, op).status_code == 200
    for suffix in ["arquivos", "pendencias", "resumos-fundos"]:
        assert (
            checked(client, "GET", f"/lotes/{lid}/{suffix}", "/lotes/{lote_id}/" + suffix).status_code == 200
        )
    sent = checked(
        client,
        "POST",
        f"/lotes/{lid}/batches",
        "/lotes/{lote_id}/batches",
        headers=headers(),
        data={"metadados": json.dumps({"arquivo_ids": [aid]})},
        files=[("arquivos", ("same.csv", data, "text/csv"))],
    )
    assert sent.status_code == 201
    assert (
        checked(
            client, "POST", f"/lotes/{lid}/processamento", "/lotes/{lote_id}/processamento", headers=headers()
        ).status_code
        == 202
    )
    Worker(db).run_once()
    assert checked(client, "GET", f"/lotes/{lid}", "/lotes/{lote_id}").json()["status"] == "BLOQUEADO"
    checked(client, "GET", f"/lotes/{lid}/pendencias", "/lotes/{lote_id}/pendencias")
    checked(client, "GET", f"/lotes/{lid}/resumos-fundos", "/lotes/{lote_id}/resumos-fundos")
    assert client.get("/openapi.json").json() == SPEC


@pytest.mark.parametrize("body", [{}, {"nome": "x", "arquivos": [], "extra": 1}, None])
def test_invalid_payload_envelope(client, body):
    assert checked(client, "POST", "/lotes", "/lotes", headers=headers(), json=body).status_code in [415, 422]


def test_invalid_ids_queries_header_media_and_cors(client):
    for path in ["/lotes/not-uuid", "/fundos?limit=101", "/fundos?extra=1", "/fundos?configurado=null"]:
        response = client.get("/api/v1" + path)
        assert response.status_code == 422
        validator("ErroResponse").validate(response.json())
    response = client.post("/api/v1/lotes", json=manifest(csv_bytes()))
    assert response.status_code == 422
    assert client.post("/api/v1/lotes", headers=headers(), content="text").status_code == 415
    assert client.get("/api/v1/lotes/" + str(uuid4())).status_code == 404
    response = client.options(
        "/api/v1/lotes",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Idempotency-Key,Content-Type",
        },
    )
    assert response.status_code == 200
