from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from typing import Mapping

from antecipe.domain.config import Configuration
from antecipe.domain.concentration import ExposureKey, concentration_reasons, exposure_keys
from antecipe.domain.entities import Title, Decision, Reason, normalize_document
from antecipe.domain.pricing import price
from antecipe.domain.validators import validate_individual


def evaluate(
    title: Title,
    config: Configuration,
    pl: Decimal,
    situation: str | None,
    exposures: Mapping[ExposureKey, Decimal],
    duplicate: bool,
) -> Decision:
    if duplicate:
        return Decision(
            title,
            (Reason("NOTA_DUPLICADA", "Título já aprovado para cedente, sacado e documento.", title.number),),
        )
    reasons = validate_individual(title, config, situation) + concentration_reasons(
        title, config, pl, exposures
    )
    discount, net = price(title.nominal, config.rate, title.days, config.base_days, approved=not reasons)
    return Decision(title, reasons, discount, net)


@dataclass
class MemoryEngine:
    configurations: Mapping[str, Configuration]
    pl: Mapping[str, Decimal]
    registry: Mapping[str, str]
    exposures: dict[ExposureKey, Decimal] = field(default_factory=dict)
    approved_keys: set[tuple[str, str, str]] = field(default_factory=set)

    def process(self, title: Title) -> Decision:
        result = evaluate(
            title,
            self.configurations[title.fund.id],
            self.pl[title.fund.id],
            self.registry.get(normalize_document(title.debtor_document)),
            self.exposures,
            title.operational_key in self.approved_keys,
        )
        if result.approved:
            self.approved_keys.add(title.operational_key)
            with localcontext() as ctx:
                ctx.prec = 38
                for key in exposure_keys(title).values():
                    self.exposures[key] = self.exposures.get(key, Decimal(0)) + title.nominal
        return result
