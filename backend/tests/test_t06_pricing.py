from decimal import Decimal as D

import pytest

from antecipe.domain.pricing import price, money


@pytest.mark.parametrize(
    "nominal,rate,days,discount,net",
    [
        ("10000.00", "2", 30, "200.00", "9800.00"),
        ("10000.00", "0", 30, "0.00", "10000.00"),
        ("10000.00", "2", 0, "0.00", "10000.00"),
        ("10000.00", "2", -30, "-200.00", "10200.00"),
        ("100.00", "200", 30, "200.00", "-100.00"),
        ("1.00", "0.5", 30, "0.01", "0.99"),
        ("9999999999999999.99", "2", 30, "200000000000000.00", "9799999999999999.99"),
    ],
)
def test_decimal_pricing(nominal, rate, days, discount, net):
    result = price(D(nominal), D(rate), days, 30)
    assert result == (D(discount), D(net))
    assert sum(result) == D(nominal)
    assert money(result[0]) == discount
    assert money(result[1]) == net


def test_barred_zero():
    assert price(D("100"), D("2"), 30, 30, approved=False) == (D("0.00"), D("0.00"))
