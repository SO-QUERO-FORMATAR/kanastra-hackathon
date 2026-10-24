from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from antecipe.domain.entities import Fund, Origin, Title, normalize_document, cnpj_valid, document_root


@pytest.mark.parametrize(
    "raw,normalized,valid",
    [
        ("01.000.171/0001-83", "01000171000183", True),
        ("01000171000183", "01000171000183", True),
        ("01.000.171/0001-84", "01000171000184", False),
        ("00000000000000", "00000000000000", False),
        ("11111111111111", "11111111111111", False),
        ("ABC01000171000183", "ABC01000171000183", False),
        ("123", "123", False),
    ],
)
def test_normalization_and_check_digits(raw, normalized, valid):
    assert normalize_document(raw) == normalized
    assert cnpj_valid(raw) is valid


def title():
    return Title(
        Fund("f", "Fundo", "92234400000180"),
        Origin("l", "a", 2, 1),
        "Cedente",
        "10.062.050/0001-57",
        "Sacado",
        "22.144.961/0001-02",
        "000351153",
        "Duplicata",
        Decimal("10000.00"),
        date(2024, 2, 28),
        date(2024, 3, 1),
        {"NU_DOCUMENTO": "000351153"},
    )


def test_roots_and_operational_identity():
    t = title()
    assert t.operational_key == ("10062050000157", "22144961000102", "000351153")
    assert replace(t, number="1-759172").operational_key[-1] == "1-759172"
    assert replace(t, debtor_document="01000171000183").operational_key != t.operational_key
    assert replace(t, seller_document="01000171000183").operational_key != t.operational_key
    assert document_root("10.062.050/0002-38") == document_root(t.seller_document) == "10062050"
    assert document_root("abc123") is None
    assert t.original["NU_DOCUMENTO"] == "000351153"


@pytest.mark.parametrize("end,days", [(date(2024, 3, 1), 2), (date(2024, 2, 28), 0), (date(2024, 2, 27), -1)])
def test_calendar_days(end, days):
    assert replace(title(), due_date=end).days == days
