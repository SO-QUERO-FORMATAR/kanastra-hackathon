import json
from copy import deepcopy
from itertools import product
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.contract import SPEC
from antecipe.adapters.schema import contexts, rules, results, approved
from antecipe.adapters.worker import Worker
from antecipe.domain.config import Configuration, PARAMETER_OPTIONS
from test_input_configurations import configuration
from test_t03_config import config_dict
from test_t11_readers import csv_bytes, values
from test_t12_uploads import manifest


def headers():
    return {"Idempotency-Key": str(uuid4())}


def options_configuration(situations, types):
    config = config_dict()
    for rule in config["validadores"]:
        if rule["codigo"] == "SITUACAO_CADASTRAL_SACADO":
            rule.update(ativo=True, parametros={"situacoes_aceitas": situations})
        elif rule["codigo"] == "TIPO_RECEBIVEL":
            rule.update(ativo=True, parametros={"tipos_aceitos": types})
        else:
            rule.update(
                ativo=False,
                parametros={"agrupamento": "RAIZ_CNPJ"} if rule["codigo"].startswith("CONCENTRACAO_") else {},
            )
    return config


def test_contract_options_match_domain():
    for schema, key in [
        ("ParametrosSituacaoDTO", "situacoes_aceitas"),
        ("ParametrosTipoDTO", "tipos_aceitos"),
    ]:
        assert SPEC["components"]["schemas"][schema]["properties"][key]["items"]["enum"] == list(
            PARAMETER_OPTIONS[key]
        )


@pytest.mark.parametrize(
    "key,code", [("situacoes_aceitas", "SITUACAO_CADASTRAL_SACADO"), ("tipos_aceitos", "TIPO_RECEBIVEL")]
)
def test_unknown_options_rejected_without_changing_persisted_rules(client, db, key, code):
    fid = PgAdmin(db).discover_fund("92234400000180", "Fundo de teste")
    valid = options_configuration(["ATIVA"], ["Duplicata"])
    path = f"/api/v1/fundos/{fid}/regras"
    saved = client.put(path, json={"versao_base": None, "configuracao": valid}, headers=headers())
    assert saved.status_code == 200, saved.text
    version = saved.json()["versao"]
    invalid = deepcopy(valid)
    target = next(r for r in invalid["validadores"] if r["codigo"] == code)
    target["parametros"][key].append("OPÇÃO INVENTADA")
    with pytest.raises(ValueError, match=key):
        Configuration.from_dict(invalid)
    with pytest.raises(ValueError, match=key):
        PgAdmin(db).publish_rules(fid, invalid, version)
    assert (
        client.put(
            path, json={"versao_base": version, "configuracao": invalid}, headers=headers()
        ).status_code
        == 422
    )
    other = configuration("01392689000100")
    raw = {"fundo": {"nome": "Fundo de teste", "cnpj": "92234400000180"}, **invalid}
    response = client.post("/api/v1/fundos/regras/importacao", json=[other, raw], headers=headers())
    assert response.status_code == 422, response.text
    assert client.get(path).json()["versao"] == version
    assert client.get(path).json()["configuracao"] == valid
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(rules)) == 1
    # Disabled parameters retain the previously requested validation behavior.
    target["ativo"] = False
    assert (
        client.put(
            path, json={"versao_base": version, "configuracao": invalid}, headers=headers()
        ).status_code
        == 200
    )


def test_saved_options_persist_and_control_worker_results(client, db, tmp_path):
    situations = ["ATIVA", "SUSPENSA", "INAPTA", "BAIXADA"]
    types = ["Duplicata", "Duplicata de Serviço", "Cheque", "CCB", "Nota Comercial"]
    documents = [f"{i:08d}000100" for i in range(1, 5)]
    registry = tmp_path / "cadastro.csv"
    registry.write_text(
        "DOC;SITUACAO_CADASTRAL\n" + "\n".join(f"{doc};{s}" for doc, s in zip(documents, situations)),
        encoding="utf8",
    )
    admin = PgAdmin(db)
    admin.import_registry(registry)
    fid = admin.discover_fund("92234400000180", "Fundo de teste")
    path = f"/api/v1/fundos/{fid}/regras"

    def run_lot(prefix, version, accepted_situations, accepted_types):
        rows = []
        combinations = list(product(range(4), types))
        for i, (s, receivable_type) in enumerate(combinations):
            row = values()
            row[5], row[6], row[7] = documents[s], f"{prefix}-{i}", receivable_type
            rows.append(row)
        data = csv_bytes(rows)
        created = client.post("/api/v1/lotes", json=manifest(data), headers=headers()).json()
        lid, aid = created["lote"]["id"], created["arquivos"][0]["id"]
        sent = client.post(
            f"/api/v1/lotes/{lid}/batches",
            headers=headers(),
            data={"metadados": json.dumps({"arquivo_ids": [aid]})},
            files={"arquivos": ("notas.csv", data, "text/csv")},
        )
        assert sent.status_code == 201, sent.text
        assert client.post(f"/api/v1/lotes/{lid}/processamento", headers=headers()).status_code == 202
        Worker(db, batch_size=3).run_once()
        output = client.get(f"/api/v1/arquivos/{aid}/resultados?limit=100").json()["itens"]
        assert len(output) == 20
        assert client.get(f"/api/v1/lotes/{lid}").json()["status"] == "CONCLUIDO"
        for result, (s, receivable_type) in zip(output, combinations):
            expected = set()
            if situations[s] not in accepted_situations:
                expected.add("SITUACAO_CADASTRAL_SACADO")
            if receivable_type not in accepted_types:
                expected.add("TIPO_RECEBIVEL")
            assert {m["codigo"] for m in result["motivos"]} == expected
            assert result["status"] == ("BARRADO" if expected else "APROVADO")
        with db.connect() as c:
            assert c.scalar(select(contexts.c.rule_id).where(contexts.c.lot_id == lid)) == version
            persisted = c.scalars(
                select(results.c.payload).where(results.c.lot_id == lid).order_by(results.c.sequence)
            ).all()
            assert persisted == output
        return lid

    config = options_configuration(["SUSPENSA", "BAIXADA"], ["CCB", "Nota Comercial"])
    response = client.put(path, json={"versao_base": None, "configuracao": config}, headers=headers())
    assert response.status_code == 200, response.text
    first = response.json()["versao"]
    assert client.get(path).json()["configuracao"] == config
    with db.connect() as c:
        assert c.scalar(select(rules.c.configuration).where(rules.c.id == first)) == config
    run_lot("restrito", first, ["SUSPENSA", "BAIXADA"], ["CCB", "Nota Comercial"])

    # Import a changed configuration, then fetch it again and process a new lot.
    expanded = options_configuration(situations, types)
    imported = client.post(
        "/api/v1/fundos/regras/importacao",
        json={"fundo": {"nome": "Fundo de teste", "cnpj": "92234400000180"}, **expanded},
        headers=headers(),
    )
    assert imported.status_code == 200, imported.text
    second = client.get(path).json()["versao"]
    assert second != first
    assert client.get(path).json()["configuracao"] == expanded
    run_lot("ampliado", second, situations, types)
    with db.connect() as c:
        assert c.scalar(select(rules.c.configuration).where(rules.c.id == first)) == config
        assert c.scalar(select(func.count()).select_from(approved)) == 24
