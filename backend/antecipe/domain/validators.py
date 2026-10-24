from decimal import Decimal

from antecipe.domain.config import Configuration
from antecipe.domain.entities import Title, Reason, cnpj_valid


def validate_individual(title: Title, config: Configuration, situation: str | None) -> tuple[Reason, ...]:
    reasons = []
    for rule in config.rules:
        if not rule.active:
            continue
        p, code = rule.parameters, rule.code
        failed, observed, limit = False, None, None
        if code == "CNPJ_SACADO_VALIDO":
            failed, observed = not cnpj_valid(title.debtor_document), title.debtor_document
        elif code == "SITUACAO_CADASTRAL_SACADO":
            failed, observed, limit = (
                situation not in p["situacoes_aceitas"],
                situation,
                ", ".join(p["situacoes_aceitas"]),
            )
        elif code == "TIPO_RECEBIVEL":
            failed = title.receivable_type not in p["tipos_aceitos"]
            observed, limit = title.receivable_type, ", ".join(p["tipos_aceitos"])
        elif code == "VALOR_MINIMO":
            failed = title.nominal < Decimal(p["valor_minimo"])
            observed, limit = str(title.nominal), p["valor_minimo"]
        elif code in {"NAO_VENCIDA", "PRAZO_MINIMO", "PRAZO_MAXIMO"}:
            days = (
                0
                if code == "NAO_VENCIDA"
                else p["prazo_minimo_dias" if code == "PRAZO_MINIMO" else "prazo_maximo_dias"]
            )
            failed = title.days > days if code == "PRAZO_MAXIMO" else title.days < days
            observed, limit = str(title.days), str(days)
        if failed:
            reasons.append(
                Reason(
                    code,
                    f"{code}: observado {observed or 'ausente'}; exigido {limit or 'CNPJ válido'}.",
                    observed,
                    limit,
                )
            )
    return tuple(reasons)
