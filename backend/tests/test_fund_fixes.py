from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.contract import validator
from antecipe.adapters.schema import contexts, results, lots, funds, rules, approved, files
from antecipe.adapters.queries import Queries
from antecipe.adapters.worker import Worker
from test_input_configurations import configuration
from test_t03_config import config_dict
from test_t11_readers import values
from test_t13_worker import prepare


@pytest.mark.parametrize("many", [False, True])
def test_http_import_input_json_is_atomic_and_idempotent(client, db, many):
    path = "/api/v1/fundos/regras/importacao"
    body = [configuration(), configuration("01392689000100")] if many else configuration()
    headers = {"Idempotency-Key": str(uuid4())}
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200, response.text
    validator("ImportarRegrasResponse").validate(response.json())
    assert len(response.json()["fundos"]) == (2 if many else 1)
    replay = client.post(path, json=body, headers=headers)
    assert replay.json() == response.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    invalid = [configuration(rate=3), configuration("11111111000100")]
    invalid[1]["validadores"][0]["codigo"] = "DESCONHECIDO"
    assert client.post(path, json=invalid, headers={"Idempotency-Key": str(uuid4())}).status_code == 422
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(funds)) == (2 if many else 1)
        assert c.scalar(select(func.count()).select_from(rules)) == (2 if many else 1)


def test_http_accepts_inactive_empty_parameters_but_rejects_activation(client, db):
    fid = PgAdmin(db).discover_fund("92234400000180", "Fundo")
    config = config_dict()
    for rule in config["validadores"]:
        rule.update(ativo=False, parametros={})
    path = f"/api/v1/fundos/{fid}/regras"
    body = {"versao_base": None, "configuracao": config}
    response = client.put(path, json=body, headers={"Idempotency-Key": str(uuid4())})
    assert response.status_code == 200, response.text
    validator("RegrasFundoResponse").validate(response.json())
    body["versao_base"] = response.json()["versao"]
    next(r for r in config["validadores"] if r["codigo"] == "VALOR_MINIMO")["ativo"] = True
    assert client.put(path, json=body, headers={"Idempotency-Key": str(uuid4())}).status_code == 422


def test_mixed_funds_show_results_and_resume_only_missing_rules(db, tmp_path):
    rows = [values() for _ in range(3)]
    rows[0][0:2] = ["Fundo pendente", "01392689000100"]
    rows[0][6] = "pendente"
    rows[2][6] = "outro"
    store, lid, aid = prepare(db, tmp_path, rows)
    Worker(db, batch_size=1).run_once()
    query = Queries(db, "test")
    page = query.get("listarResultados", {"arquivo_id": aid}, {})
    validator("ResultadosPageResponse").validate(page)
    assert len(page["itens"]) == 3
    assert page["itens"][0]["erros_dados"][0]["mensagem"] == "Regras de fundo não configuradas"
    assert all(r["tipo"] == "ANALISE" for r in page["itens"][1:])
    original_ids = [r["id"] for r in page["itens"][1:]]
    with db.connect() as c:
        assert c.scalar(select(lots.c.status)) == "BLOQUEADO"
        snapshots = dict(c.execute(select(contexts.c.fund_id, contexts.c.rule_id)).all())
        original_approved = c.scalar(select(func.count()).select_from(approved))

    admin = PgAdmin(db)
    old_fid = next(fid for fid, version in snapshots.items() if version)
    changed = deepcopy(config_dict())
    changed["precificacao"]["taxa_mensal_percentual"] = "50"
    admin.publish_rules(old_fid, changed, snapshots[old_fid])
    missing_fid = next(fid for fid, version in snapshots.items() if version is None)
    new_config = config_dict()
    for rule in new_config["validadores"]:
        rule.update(ativo=False, parametros={})
    admin.publish_rules(missing_fid, new_config, None)
    store.enqueue(lid, str(uuid4()))

    class Crash(BaseException):
        pass

    def crash(phase):
        if phase == "after_commit":
            raise Crash()

    with pytest.raises(Crash):
        Worker(db, batch_size=1, hook=crash).run_once()
    Worker(db, batch_size=1).run_once()
    final = query.get("listarResultados", {"arquivo_id": aid}, {})
    assert final["itens"][0]["status"] == "APROVADO"
    assert [r["id"] for r in final["itens"][1:]] == original_ids
    with db.connect() as c:
        assert c.scalar(select(lots.c.status)) == "CONCLUIDO"
        assert c.scalar(select(lots.c.processed)) == 3
        assert c.scalar(select(files.c.processed)) == 3
        assert c.scalar(select(func.count()).select_from(results)) == 3
        assert c.scalar(select(func.count()).select_from(approved)) == original_approved + 1
        assert c.scalar(select(contexts.c.rule_id).where(contexts.c.fund_id == old_fid)) == snapshots[old_fid]
