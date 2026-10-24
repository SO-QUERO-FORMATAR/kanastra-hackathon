from antecipe.adapters.worker import Worker
from antecipe.adapters.contract import validator
from test_t13_worker import prepare
from test_t11_readers import values


def test_results_contract_filters_cursor(db, tmp_path, client):
    rows = [values() for _ in range(12)]
    for i, r in enumerate(rows):
        r[6] = str(i)
    rows[-1][10] = "31/02/2026"
    _, lid, aid = prepare(db, tmp_path, rows)
    Worker(db).run_once()
    path = "/api/v1/arquivos/" + aid + "/resultados"
    response = client.get(path, params={"limit": 3})
    assert response.status_code == 200
    first = response.json()
    validator("ResultadosPageResponse").validate(first)
    assert first["snapshot_ate_sequencia"] == 12 and first["arquivo_finalizado"]
    collected = first["itens"]
    current = first
    while current["proximo_cursor"]:
        current = client.get(path, params={"limit": 3, "cursor": current["proximo_cursor"]}).json()
        validator("ResultadosPageResponse").validate(current)
        collected.extend(current["itens"])
    assert [r["sequencia"] for r in collected] == list(range(1, 13))
    assert len({r["id"] for r in collected}) == 12
    for filters, count in [
        ({"status": "APROVADO"}, 1),
        ({"tipo": "ERRO_DADOS"}, 1),
        ({"motivo": "CONCENTRACAO_MAXIMA_SACADO"}, 10),
    ]:
        page = client.get(path, params=filters).json()
        validator("ResultadosPageResponse").validate(page)
        assert len(page["itens"]) == count
    for params, code in [
        ({"cursor": "invalid"}, 400),
        ({"limit": 4, "cursor": first["proximo_cursor"]}, 400),
        ({"tipo": "ERRO_DADOS", "status": "BARRADO"}, 422),
        ({"status": "APROVADO", "motivo": "VALOR_MINIMO"}, 422),
        ({"limit": 101}, 422),
    ]:
        r = client.get(path, params=params)
        assert r.status_code == code
        validator("ErroResponse").validate(r.json())


def test_live_snapshot_excludes_future_rows(db, tmp_path, client):
    rows = [values() for _ in range(12)]
    for i, r in enumerate(rows):
        r[6] = str(i)
    _, _, aid = prepare(db, tmp_path, rows)

    class Stop(BaseException):
        pass

    def hook(phase):
        if phase == "after_commit":
            raise Stop()

    try:
        Worker(db, batch_size=3, hook=hook).run_once()
    except Stop:
        pass
    path = "/api/v1/arquivos/" + aid + "/resultados"
    first = client.get(path, params={"limit": 2}).json()
    assert first["snapshot_ate_sequencia"] == 3 and not first["arquivo_finalizado"]
    Worker(db).run_once()
    second = client.get(path, params={"limit": 2, "cursor": first["proximo_cursor"]}).json()
    assert [r["sequencia"] for r in second["itens"]] == [3]
    assert second["proximo_cursor"] is None
    assert client.get(path).json()["snapshot_ate_sequencia"] == 12
