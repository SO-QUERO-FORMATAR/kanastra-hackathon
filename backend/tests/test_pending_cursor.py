from uuid import uuid4

from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.worker import Worker
from test_t11_readers import values
from test_t13_worker import prepare
from test_t03_config import config_dict


def test_pending_cursor_invalidates_after_resolution(db, tmp_path, client):
    rows = [values(), values()]
    for i, row in enumerate(rows):
        row[1] = f"{i + 1:08d}000100"
        row[0] = f"Fundo sintético {i}"
    store, lid, _ = prepare(db, tmp_path, rows, rules=False)
    Worker(db).run_once()
    url = f"/api/v1/lotes/{lid}/pendencias"
    page = client.get(url, params={"limit": 1}).json()
    assert page["proximo_cursor"]
    all_pending = client.get(url).json()["itens"]
    for i, pending in enumerate(all_pending):
        config = config_dict()
        config["precificacao"]["taxa_mensal_percentual"] = str(i + 1)
        PgAdmin(db).publish_rules(pending["fundo"]["id"], config, None)
    store.enqueue(lid, str(uuid4()))
    Worker(db).run_once()
    response = client.get(url, params={"limit": 1, "cursor": page["proximo_cursor"]})
    assert response.status_code == 400
    assert response.json()["erro"]["codigo"] == "CURSOR_INVALIDO"
