from collections import defaultdict
from decimal import Decimal, ROUND_CEILING, localcontext
from typing import Iterable, Mapping

from antecipe.domain.config import Configuration
from antecipe.domain.entities import Title, Reason, document_root

ExposureKey = tuple[str, str, str]


def exposure_keys(title: Title) -> dict[str, ExposureKey]:
    keys = {}
    for side, document in [("SACADO", title.debtor_document), ("CEDENTE", title.seller_document)]:
        root = document_root(document)
        if root is not None:
            keys[side] = (title.fund.id, side, root)
    return keys


def calculate_pl(titles: Iterable[Title]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    with localcontext() as ctx:
        ctx.prec = 38
        for title in titles:
            totals[title.fund.id] += title.nominal
    return dict(totals)


def concentration_reasons(
    title: Title, config: Configuration, pl: Decimal, exposures: Mapping[ExposureKey, Decimal]
) -> tuple[Reason, ...]:
    reasons = []
    with localcontext() as ctx:
        ctx.prec = 38
        for side in ["SACADO", "CEDENTE"]:
            rule = config.rule(f"CONCENTRACAO_MAXIMA_{side}")
            if not rule.active:
                continue
            keys = exposure_keys(title)
            if side not in keys:
                raise ValueError("DOCUMENTO_SEM_RAIZ")
            projected = exposures.get(keys[side], Decimal(0)) + title.nominal
            limit = pl * Decimal(rule.parameters["percentual_maximo"]) / 100
            if projected > limit:
                maximum = str(rule.parameters["percentual_maximo"]).replace(".", ",")
                if pl > 0:
                    # Round upward only for display, so a real excess never appears equal to the limit.
                    percent = projected / pl * 100
                    with localcontext() as display_context:
                        display_context.prec = max(38, percent.adjusted() + 10)
                        percent = percent.quantize(Decimal("0.00000001"), rounding=ROUND_CEILING)
                    displayed = format(percent, "f").rstrip("0").rstrip(".").replace(".", ",")
                    if side == "SACADO":
                        message = (
                            "Concentração acima do limite: com esta nota, o sacado "
                            f"(raiz do CNPJ {keys[side][2]}) chegaria a {displayed}% "
                            f"do patrimônio do fundo; o limite é {maximum}%."
                        )
                    else:
                        message = (
                            "Concentração do cedente acima do limite: o cedente chegaria a "
                            f"{displayed}% do patrimônio do fundo; o limite é {maximum}%."
                        )
                else:
                    message = (
                        f"Concentração {'do sacado' if side == 'SACADO' else 'do cedente'} acima do limite: "
                        "o patrimônio do fundo é zero ou negativo, portanto não é possível calcular "
                        f"o percentual; o limite configurado é {maximum}%."
                    )
                reasons.append(
                    Reason(
                        rule.code,
                        message,
                        str(projected),
                        str(limit),
                    )
                )
    return tuple(reasons)
