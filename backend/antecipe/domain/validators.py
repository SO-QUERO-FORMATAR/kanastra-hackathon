from decimal import Decimal

from antecipe.domain.config import Configuration
from antecipe.domain.entities import Title, Reason, cnpj_valid


def money_text(value: Decimal) -> str:
    whole, _, fraction = format(value, ",f").partition(".")
    return "R$ " + whole.replace(",", ".") + "," + fraction.ljust(2, "0")


def validate_individual(title: Title, config: Configuration, situation: str | None) -> tuple[Reason, ...]:
    reasons = []
    for rule in config.rules:
        if not rule.active:
            continue
        p, code = rule.parameters, rule.code
        failed, observed, limit = False, None, None
        message = ""
        if code == "CNPJ_SACADO_VALIDO":
            failed, observed = not cnpj_valid(title.debtor_document), title.debtor_document
            message = (
                f"CNPJ do sacado inválido: o documento {title.debtor_document} não é um CNPJ válido. "
                "Confira os números informados."
            )
        elif code == "SITUACAO_CADASTRAL_SACADO":
            failed, observed, limit = (
                situation not in p["situacoes_aceitas"],
                situation,
                ", ".join(p["situacoes_aceitas"]),
            )
            message = (
                f"Sacado com situação irregular: o CNPJ {title.debtor_document} consta como "
                f"{situation or 'não encontrado no cadastro'}. "
                f"Só são aceitos sacados com situação {limit}."
            )
        elif code == "TIPO_RECEBIVEL":
            failed = title.receivable_type not in p["tipos_aceitos"]
            observed, limit = title.receivable_type, ", ".join(p["tipos_aceitos"])
            message = (
                f"Tipo de recebível não aceito: esta nota é do tipo {title.receivable_type}. "
                f"Este fundo aceita apenas {limit}."
            )
        elif code == "VALOR_MINIMO":
            failed = title.nominal < Decimal(p["valor_minimo"])
            observed, limit = str(title.nominal), p["valor_minimo"]
            message = (
                f"Valor abaixo do mínimo: esta nota tem valor de {money_text(title.nominal)}; "
                f"o mínimo é {money_text(Decimal(p['valor_minimo']))}."
            )
        elif code in {"NAO_VENCIDA", "PRAZO_MINIMO", "PRAZO_MAXIMO"}:
            days = (
                0
                if code == "NAO_VENCIDA"
                else p["prazo_minimo_dias" if code == "PRAZO_MINIMO" else "prazo_maximo_dias"]
            )
            if code == "NAO_VENCIDA":
                failed = title.days <= 0
                message = (
                    f"Nota já vencida: o vencimento ({title.due_date:%d/%m/%Y}) é igual ou anterior "
                    f"à data de aquisição ({title.acquisition_date:%d/%m/%Y})."
                )
            elif code == "PRAZO_MAXIMO":
                failed = title.days > days
                message = (
                    f"Prazo acima do limite: esta nota vence em {title.days} dias; "
                    f"o limite configurado é {days}."
                )
            else:
                failed = title.days < days
                message = (
                    f"Prazo abaixo do mínimo: esta nota vence em {title.days} dias; "
                    f"o mínimo é {days}."
                )
            observed, limit = str(title.days), str(days)
        if failed:
            reasons.append(
                Reason(
                    code,
                    message,
                    observed,
                    limit,
                )
            )
    return tuple(reasons)
