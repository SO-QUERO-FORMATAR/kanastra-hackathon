from dataclasses import replace
from decimal import Decimal as D

from antecipe.domain.concentration import calculate_pl, concentration_reasons, exposure_keys
from antecipe.domain.config import Configuration
from test_t02_entities import title
from test_t03_config import config_dict


def test_full_pl_multi_fund_and_files():
    a = title()
    b = replace(a, fund=replace(a.fund, id="other"), nominal=D("99.99"))
    c = replace(a, origin=replace(a.origin, file_id="other"), nominal=D("0.01"))
    assert calculate_pl([a, b, c]) == {"f": D("10000.01"), "other": D("99.99")}


def test_exact_limit_excess_and_prior_exposure_no_mutation():
    cfg = Configuration.from_dict(config_dict())
    t = replace(title(), nominal=D("100.00"))
    key = exposure_keys(t)["SACADO"]
    prior = {key: D("900.00")}
    assert concentration_reasons(t, cfg, D("10000.00"), prior) == ()
    reasons = concentration_reasons(replace(t, nominal=D("100.01")), cfg, D("10000.00"), prior)
    assert [r.code for r in reasons] == ["CONCENTRACAO_MAXIMA_SACADO"]
    assert prior == {key: D("900.00")}
    assert exposure_keys(replace(t, debtor_document="22144961000200"))["SACADO"] == key
    assert exposure_keys(replace(t, fund=replace(t.fund, id="other")))["SACADO"] != key
