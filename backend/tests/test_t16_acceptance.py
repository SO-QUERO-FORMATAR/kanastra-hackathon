import json
from decimal import Decimal
from pathlib import Path

from antecipe.acceptance.compare import compare
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.worker import Worker
from antecipe.adapters.contract import validator
from test_t14_api import headers
from test_t03_config import config_dict
from test_t11_readers import values, csv_bytes
from test_t12_uploads import manifest


def test_comparator_missing_extra_id_reasons_and_duplicates():
    expected = [
        {"linha": 2, "id": "0001", "status": "APROVADO"},
        {"linha": 3, "id": "x", "status": "BARRADO", "barrado_por": ["VALOR_MINIMO"]},
        {"linha": 4, "id": "missing", "status": "APROVADO"},
    ]
    actual = [
        {"linha": 2, "id": "0001", "status": "APROVADO", "barrado_por": []},
        {"linha": 3, "id": "different", "status": "BARRADO", "barrado_por": ["PRAZO_MAXIMO"]},
        {"linha": 5, "id": "extra", "status": "APROVADO"},
    ]
    report = compare(expected, actual)
    assert report["missing"] == [4] and report["extra"] == [5]
    assert report["divergences"][0]["linha"] == 3
    assert set(report["divergences"][0]["fields"]) == {"id", "motivos"}
    assert compare(expected + [expected[0]], actual)["duplicate_expected_lines"] == [2]


def test_full_http_worker_all_refusals_and_totals(client, db):
    admin = PgAdmin(db)
    admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    fid, version = admin.import_rules(Path("../files/validadores_antecipe.json"))
    config = config_dict()
    for r in config["validadores"]:
        r["ativo"] = True
    response = client.put(
        "/api/v1/fundos/" + fid + "/regras",
        headers=headers(),
        json={"versao_base": version, "configuracao": config},
    )
    assert response.status_code == 200
    rows = [values() for _ in range(30)]
    for i, row in enumerate(rows):
        row[6] = f"{i:09d}"
    rows[1][6] = rows[0][6]
    rows[2][7] = "Cheque"
    rows[3][8] = "99,99"
    rows[4][5] = "22.144.961/0001-03"
    rows[5][9] = "30/09/2026"
    rows[6][9] = "02/10/2026"
    rows[7][9] = "30/10/2027"
    data = csv_bytes(rows)
    created = client.post("/api/v1/lotes", headers=headers(), json=manifest(data)).json()
    lid, aid = created["lote"]["id"], created["arquivos"][0]["id"]
    response = client.post(
        "/api/v1/lotes/" + lid + "/batches",
        headers=headers(),
        data={"metadados": json.dumps({"arquivo_ids": [aid]})},
        files={"arquivos": ("x.csv", data)},
    )
    assert response.status_code == 201
    h = headers()
    url = "/api/v1/lotes/" + lid + "/processamento"
    assert client.post(url, headers=h).status_code == 202
    assert client.post(url, headers=h).headers["Idempotency-Replayed"] == "true"
    Worker(db).run_once()
    output = client.get("/api/v1/arquivos/" + aid + "/resultados", params={"limit": 100}).json()
    validator("ResultadosPageResponse").validate(output)
    codes = {r["codigo"] for row in output["itens"] for r in row["motivos"]}
    assert codes == {
        "NOTA_DUPLICADA",
        "CNPJ_SACADO_VALIDO",
        "SITUACAO_CADASTRAL_SACADO",
        "TIPO_RECEBIVEL",
        "VALOR_MINIMO",
        "NAO_VENCIDA",
        "PRAZO_MINIMO",
        "PRAZO_MAXIMO",
        "CONCENTRACAO_MAXIMA_SACADO",
        "CONCENTRACAO_MAXIMA_CEDENTE",
    }
    assert output["itens"][0]["valor_liquido"] == "9800.00"
    summary = client.get("/api/v1/lotes/" + lid).json()["resumo"]
    assert summary["aprovadas"] == 2 and summary["barradas"] == 28
    assert Decimal(summary["total_nominal"]) == Decimal(summary["total_nominal_aprovado"]) + Decimal(
        summary["total_nominal_barrado"]
    )
    assert Decimal(summary["total_desconto"]) == Decimal("400.00")
