from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from antecipe.domain.config import Configuration
from antecipe.domain.validators import validate_individual
from test_t02_entities import title
from test_t03_config import config_dict


@pytest.mark.parametrize(
    "code,bad,good",
    [
        ("CNPJ_SACADO_VALIDO", {"debtor_document": "22144961000103"}, {}),
        ("SITUACAO_CADASTRAL_SACADO", {"situation": None}, {"situation": "ATIVA"}),
        ("SITUACAO_CADASTRAL_SACADO", {"situation": "INAPTA"}, {"situation": "ATIVA"}),
        ("TIPO_RECEBIVEL", {"receivable_type": "Cheque"}, {"receivable_type": "Duplicata de Serviço"}),
        ("VALOR_MINIMO", {"nominal": Decimal("99.99")}, {"nominal": Decimal("100.00")}),
        ("NAO_VENCIDA", {"days": -1}, {"days": 1}),
        ("NAO_VENCIDA", {"days": 0}, {"days": 1}),
        ("PRAZO_MINIMO", {"days": 29}, {"days": 30}),
        ("PRAZO_MINIMO", {"days": 0}, {"days": 31}),
        ("PRAZO_MAXIMO", {"days": 181}, {"days": 180}),
        ("PRAZO_MAXIMO", {"days": 181}, {"days": 179}),
    ],
)
def test_rule_boundaries_and_disabled(code, bad, good):
    raw = config_dict()
    for r in raw["validadores"]:
        r["ativo"] = r["codigo"] == code
    config = Configuration.from_dict(raw)

    def run(changes):
        values = dict(changes)
        situation = values.pop("situation", "ATIVA")
        if "days" in values:
            values["due_date"] = title().acquisition_date + timedelta(days=values.pop("days"))
        return validate_individual(replace(title(), **values), config, situation)

    reasons = run(bad)
    assert [r.code for r in reasons] == [code]
    assert reasons[0].message
    assert run(good) == ()
    for r in raw["validadores"]:
        r["ativo"] = False
    config = Configuration.from_dict(raw)
    assert run(bad) == ()
