from collections import defaultdict
from decimal import Decimal, localcontext
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
                reasons.append(
                    Reason(
                        rule.code,
                        f"Exposição projetada {projected} excede limite {limit}.",
                        str(projected),
                        str(limit),
                    )
                )
    return tuple(reasons)
