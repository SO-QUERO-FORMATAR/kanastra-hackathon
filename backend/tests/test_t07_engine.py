from dataclasses import replace
from decimal import Decimal as D

from antecipe.domain.engine import MemoryEngine
from antecipe.domain.config import Configuration
from antecipe.domain.concentration import exposure_keys
from test_t02_entities import title
from test_t03_config import config_dict


def engine(cedent=False):
    raw = config_dict()
    for r in raw["validadores"]:
        if r["codigo"] == "CONCENTRACAO_MAXIMA_CEDENTE":
            r["ativo"] = cedent
    return MemoryEngine({"f": Configuration.from_dict(raw)}, {"f": D("100000")}, {"22144961000102": "ATIVA"})


def test_duplicate_short_circuit_and_barred_does_not_reserve():
    e = engine()
    bad = replace(title(), nominal=D("99"))
    assert not e.process(bad).approved
    approved = e.process(title())
    assert approved.approved and approved.net == D("9986.67")
    duplicate = e.process(replace(bad, receivable_type="Cheque"))
    assert [r.code for r in duplicate.reasons] == ["NOTA_DUPLICADA"]
    assert duplicate.net == duplicate.discount == D("0")
    assert all(v == D("10000") for v in e.exposures.values())


def test_no_partial_exposure_and_multiple_reasons():
    e = engine(cedent=True)
    result = e.process(title())
    assert [r.code for r in result.reasons] == ["CONCENTRACAO_MAXIMA_CEDENTE"]
    assert e.exposures == {} and e.approved_keys == set()
    bad = replace(title(), nominal=D("99"), receivable_type="Cheque", debtor_document="bad")
    # A malformed root is an ingestion diagnostic; use an invalid DV with usable root here.
    bad = replace(bad, debtor_document="22144961000103")
    codes = {r.code for r in e.process(bad).reasons}
    assert {"VALOR_MINIMO", "TIPO_RECEBIVEL", "CNPJ_SACADO_VALIDO", "SITUACAO_CADASTRAL_SACADO"} <= codes


def test_determinism_and_disabled_concentration_still_tracks():
    a, b = engine(), engine()
    rows = [title(), title(), replace(title(), number="next")]
    assert [a.process(t) for t in rows] == [b.process(t) for t in rows]
    assert a.exposures[exposure_keys(title())["CEDENTE"]] == D("10000")
    historical = engine()
    historical.approved_keys.add(title().operational_key)
    assert historical.process(title()).reasons[0].code == "NOTA_DUPLICADA"
