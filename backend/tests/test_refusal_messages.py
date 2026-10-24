from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.schema import results
from antecipe.adapters.worker import Worker
from antecipe.domain.config import Configuration
from antecipe.domain.concentration import concentration_reasons
from antecipe.domain.validators import money_text, validate_individual
from test_t02_entities import title
from test_t03_config import config_dict
from test_t11_readers import values
from test_t13_worker import prepare


@pytest.mark.parametrize(
    "code,changes,situation,expected",
    [
        (
            "CNPJ_SACADO_VALIDO",
            {"debtor_document": "22144961000103"},
            "ATIVA",
            "CNPJ do sacado inválido: o documento 22144961000103 não é um CNPJ válido. Confira os números informados.",
        ),
        (
            "SITUACAO_CADASTRAL_SACADO",
            {},
            "INAPTA",
            "Sacado com situação irregular: o CNPJ 22.144.961/0001-02 consta como INAPTA. "
            "Só são aceitos sacados com situação ATIVA.",
        ),
        (
            "SITUACAO_CADASTRAL_SACADO",
            {},
            None,
            "Sacado com situação irregular: o CNPJ 22.144.961/0001-02 consta como não encontrado no cadastro. "
            "Só são aceitos sacados com situação ATIVA.",
        ),
        (
            "TIPO_RECEBIVEL",
            {"receivable_type": "Cheque"},
            "ATIVA",
            "Tipo de recebível não aceito: esta nota é do tipo Cheque. "
            "Este fundo aceita apenas Duplicata, Duplicata de Serviço.",
        ),
        (
            "VALOR_MINIMO",
            {"nominal": D("99.99")},
            "ATIVA",
            "Valor abaixo do mínimo: esta nota tem valor de R$ 99,99; o mínimo é R$ 100,00.",
        ),
        (
            "NAO_VENCIDA",
            {"due_date": title().acquisition_date},
            "ATIVA",
            "Nota já vencida: o vencimento (28/02/2024) é igual ou anterior à data de aquisição (28/02/2024).",
        ),
        ("PRAZO_MINIMO", {}, "ATIVA", "Prazo abaixo do mínimo: esta nota vence em 2 dias; o mínimo é 30."),
        (
            "PRAZO_MAXIMO",
            {"due_date": title().acquisition_date + timedelta(days=181)},
            "ATIVA",
            "Prazo acima do limite: esta nota vence em 181 dias; o limite configurado é 180.",
        ),
    ],
)
def test_individual_customer_messages_and_disabled_rules(code, changes, situation, expected):
    raw = config_dict()
    for rule in raw["validadores"]:
        rule["ativo"] = rule["codigo"] == code
    reasons = validate_individual(replace(title(), **changes), Configuration.from_dict(raw), situation)
    assert len(reasons) == 1
    assert reasons[0].message == expected
    for rule in raw["validadores"]:
        rule["ativo"] = False
    assert validate_individual(replace(title(), **changes), Configuration.from_dict(raw), situation) == ()


def test_concentration_messages_show_percentage_and_root():
    raw = config_dict()
    for rule in raw["validadores"]:
        rule["ativo"] = rule["codigo"].startswith("CONCENTRACAO")
    config = Configuration.from_dict(raw)
    reasons = concentration_reasons(title(), config, D("50000"), {})
    assert [r.message for r in reasons] == [
        "Concentração acima do limite: com esta nota, o sacado (raiz do CNPJ 22144961) "
        "chegaria a 20% do patrimônio do fundo; o limite é 10,0%.",
        "Concentração do cedente acima do limite: o cedente chegaria a 20% "
        "do patrimônio do fundo; o limite é 8,0%.",
    ]
    assert reasons[0].observed == "10000.00" and D(reasons[0].limit) == D("5000")
    assert all(
        "não é possível calcular" in r.message for r in concentration_reasons(title(), config, D(0), {})
    )
    # A fractional excess must not display the same percentage as the allowed limit.
    near = replace(title(), nominal=D("10000.00000000001"))
    assert "10,00000001%" in concentration_reasons(near, config, D("100000"), {})[0].message
    huge = replace(title(), nominal=D("999999999999999999999999999999999999.99"))
    assert concentration_reasons(huge, config, D("0.01"), {})


def test_money_message_keeps_configured_fractional_cents():
    assert money_text(D("1234.56789")) == "R$ 1.234,56789"
    assert money_text(D("100")) == "R$ 100,00"


def test_worker_persists_all_failed_requirements_and_api_returns_them(client, db, tmp_path):
    row = values()
    row[5], row[7], row[8], row[9] = "22144961000103", "Cheque", "99,99", row[10]
    _, _, aid = prepare(db, tmp_path, [row])
    admin = PgAdmin(db)
    fid = admin.discover_fund("92234400000180", "Fundo")
    path = f"/api/v1/fundos/{fid}/regras"
    version = client.get(path).json()["versao"]
    raw = config_dict()
    for rule in raw["validadores"]:
        rule["ativo"] = True
    admin.publish_rules(fid, raw, version)
    assert Worker(db).run_once()
    response = client.get(f"/api/v1/arquivos/{aid}/resultados")
    assert response.status_code == 200, response.text
    item = response.json()["itens"][0]
    assert item["status"] == "BARRADO"
    expected = {
        "CNPJ_SACADO_VALIDO",
        "SITUACAO_CADASTRAL_SACADO",
        "TIPO_RECEBIVEL",
        "VALOR_MINIMO",
        "NAO_VENCIDA",
        "PRAZO_MINIMO",
        "CONCENTRACAO_MAXIMA_SACADO",
        "CONCENTRACAO_MAXIMA_CEDENTE",
    }
    assert {r["codigo"] for r in item["motivos"]} == expected
    assert len(item["motivos"]) == 8
    assert all("observado" not in r["mensagem"] and "{" not in r["mensagem"] for r in item["motivos"])
    with db.connect() as conn:
        assert conn.scalar(select(results.c.payload)) == item
    assert client.get(f"/api/v1/arquivos/{aid}/resultados").json()["itens"][0] == item
