from decimal import Decimal, ROUND_HALF_UP, localcontext

CENT = Decimal("0.01")


def money(value: Decimal) -> str:
    with localcontext() as ctx:
        ctx.prec = 38
        return format(value.quantize(CENT, rounding=ROUND_HALF_UP), ".2f")


def price(
    nominal: Decimal, monthly_rate: Decimal, days: int, base_days: int, approved: bool = True
) -> tuple[Decimal, Decimal]:
    if not approved:
        return Decimal("0.00"), Decimal("0.00")
    with localcontext() as ctx:
        ctx.prec = 38
        discount = (nominal * monthly_rate * days / (100 * base_days)).quantize(CENT, rounding=ROUND_HALF_UP)
        return discount, nominal - discount
