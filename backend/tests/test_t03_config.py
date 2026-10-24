from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from antecipe.adapters.config_import import load_rules
from antecipe.domain.config import Configuration


def config_dict():
    return load_rules(Path("../files/validadores_antecipe.json"))[1].to_dict()


def test_delivered_configuration():
    fund, config = load_rules(Path("../files/validadores_antecipe.json"))
    assert fund["cnpj"] == "92234400000180"
    assert sum(r.active for r in config.rules) == 7
    assert len(config.rules) == 9
    assert config.rule("CONCENTRACAO_MAXIMA_CEDENTE").parameters["agrupamento"] == "RAIZ_CNPJ"
    assert config.rate == Decimal("2.0")
    assert config.to_dict()["precificacao"]["taxa_mensal_percentual"] == "2.0"
    assert config.rule("PRAZO_MINIMO").parameters["prazo_minimo_dias"] == 30
    with pytest.raises(TypeError):
        config.rule("PRAZO_MINIMO").parameters["prazo_minimo_dias"] = 0


@pytest.mark.parametrize(
    "case", ["unknown", "duplicate", "missing", "bool", "rate_float", "method", "base", "range", "percentage"]
)
def test_invalid_configuration(case):
    raw = deepcopy(config_dict())
    if case == "unknown":
        raw["validadores"][0]["codigo"] = "INVENTADO"
    if case == "duplicate":
        raw["validadores"][1] = raw["validadores"][0]
    if case == "missing":
        raw["validadores"][1]["parametros"] = {}
    if case == "bool":
        raw["validadores"][0]["ativo"] = "true"
    if case == "rate_float":
        raw["precificacao"]["taxa_mensal_percentual"] = 2.0
    if case == "method":
        raw["precificacao"]["metodo"] = "COMPOSTO"
    if case == "base":
        raw["precificacao"]["base_dias"] = 0
    if case == "range":
        raw["validadores"][7]["ativo"] = True
        raw["validadores"][7]["parametros"]["prazo_minimo_dias"] = 181
    if case == "percentage":
        raw["validadores"][6]["parametros"]["percentual_maximo"] = "100.01"
    with pytest.raises(ValueError):
        Configuration.from_dict(raw)


def test_inactive_parameters_are_not_validated():
    raw = config_dict()
    for rule in raw["validadores"]:
        rule["ativo"] = False
        rule["parametros"] = {}
    assert not any(rule.active for rule in Configuration.from_dict(raw).rules)
    minimum = next(r for r in raw["validadores"] if r["codigo"] == "PRAZO_MINIMO")
    maximum = next(r for r in raw["validadores"] if r["codigo"] == "PRAZO_MAXIMO")
    minimum.update(ativo=True, parametros={"prazo_minimo_dias": 200})
    maximum["parametros"] = {"prazo_maximo_dias": -1}
    Configuration.from_dict(raw)
    maximum["ativo"] = True
    with pytest.raises(ValueError):
        Configuration.from_dict(raw)


def test_exact_rate_and_missing_fund():
    raw = config_dict()
    raw["precificacao"]["taxa_mensal_percentual"] = "2.12345678"
    cfg = Configuration.from_dict(raw)
    assert cfg.rate == Decimal("2.12345678")
    assert "NOTA_DUPLICADA" not in [r.code for r in cfg.rules]
    assert {"92234400000180": cfg}.get("01392689000100") is None
