import re
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping


PARAMETER_OPTIONS = {
    "situacoes_aceitas": ("ATIVA", "SUSPENSA", "INAPTA", "BAIXADA"),
    "tipos_aceitos": ("Duplicata", "Duplicata de Serviço", "Cheque", "CCB", "Nota Comercial"),
}


PARAMETERS: dict[str, dict[str, type]] = {
    "CNPJ_SACADO_VALIDO": {},
    "NAO_VENCIDA": {},
    "SITUACAO_CADASTRAL_SACADO": {"situacoes_aceitas": list},
    "TIPO_RECEBIVEL": {"tipos_aceitos": list},
    "VALOR_MINIMO": {"valor_minimo": str},
    "PRAZO_MINIMO": {"prazo_minimo_dias": int},
    "PRAZO_MAXIMO": {"prazo_maximo_dias": int},
    "CONCENTRACAO_MAXIMA_SACADO": {"percentual_maximo": str, "agrupamento": str},
    "CONCENTRACAO_MAXIMA_CEDENTE": {"percentual_maximo": str, "agrupamento": str},
}


def exact_decimal(value: Any) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]{1,8})?", value):
        raise ValueError("Decimal deve ser string não negativa com até oito casas")
    return Decimal(value)


@dataclass(frozen=True)
class Rule:
    code: str
    active: bool
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class Configuration:
    rules: tuple[Rule, ...]
    rate: Decimal
    base_days: int

    def rule(self, code: str) -> Rule:
        return next(r for r in self.rules if r.code == code)

    @classmethod
    def from_dict(cls, data: dict) -> "Configuration":
        try:
            if set(data) != {"validadores", "precificacao"} or len(data["validadores"]) != 9:
                raise ValueError("Exigidos nove validadores e precificação")
            rules = []
            for item in data["validadores"]:
                if set(item) != {"codigo", "ativo", "parametros"} or type(item["ativo"]) is not bool:
                    raise ValueError("Validador inválido")
                code, params = item["codigo"], item["parametros"]
                if code not in PARAMETERS or not isinstance(params, dict):
                    raise ValueError("Código/parâmetros inválidos")
                if item["ativo"] and set(params) != set(PARAMETERS[code]):
                    raise ValueError("Código/parâmetros inválidos")
                for key, typ in PARAMETERS[code].items() if item["ativo"] else []:
                    val: Any = params[key]
                    if type(val) is not typ:
                        raise ValueError("Tipo de parâmetro inválido")
                    if isinstance(val, int) and val < 0:
                        raise ValueError("Prazo negativo")
                    if isinstance(val, list) and (
                        not val or any(type(v) is not str or not v for v in val) or len(set(val)) != len(val)
                    ):
                        raise ValueError("Lista inválida")
                    if (
                        key in PARAMETER_OPTIONS
                        and isinstance(val, list)
                        and any(v not in PARAMETER_OPTIONS[key] for v in val)
                    ):
                        raise ValueError(f"{key}: use somente {', '.join(PARAMETER_OPTIONS[key])}")
                    if key in {"valor_minimo", "percentual_maximo"}:
                        number = exact_decimal(val)
                        if key == "percentual_maximo" and number > 100:
                            raise ValueError("Percentual excede 100")
                    if key == "agrupamento" and val != "RAIZ_CNPJ":
                        raise ValueError("Agrupamento inválido")
                rules.append(
                    Rule(
                        code,
                        item["ativo"],
                        MappingProxyType(
                            {k: tuple(v) if isinstance(v, list) else v for k, v in params.items()}
                        ),
                    )
                )
            if {r.code for r in rules} != set(PARAMETERS):
                raise ValueError("Código repetido")
            pricing = data["precificacao"]
            if set(pricing) != {"metodo", "taxa_mensal_percentual", "base_dias"}:
                raise ValueError("Precificação inválida")
            if pricing["metodo"] != "DESCONTO_SIMPLES" or type(pricing["base_dias"]) is not int:
                raise ValueError("Método/base inválidos")
            if not 1 <= pricing["base_dias"] <= 366:
                raise ValueError("Base deve estar entre 1 e 366")
            result = cls(tuple(rules), exact_decimal(pricing["taxa_mensal_percentual"]), pricing["base_dias"])
            if (
                result.rule("PRAZO_MINIMO").active
                and result.rule("PRAZO_MAXIMO").active
                and result.rule("PRAZO_MINIMO").parameters["prazo_minimo_dias"]
                > result.rule("PRAZO_MAXIMO").parameters["prazo_maximo_dias"]
            ):
                raise ValueError("Prazo mínimo maior que máximo")
            return result
        except (KeyError, TypeError, StopIteration) as exc:
            raise ValueError("Configuração incompleta") from exc

    def to_dict(self) -> dict:
        return {
            "validadores": [
                {
                    "codigo": r.code,
                    "ativo": r.active,
                    "parametros": {
                        k: list(v) if isinstance(v, tuple) else v for k, v in r.parameters.items()
                    },
                }
                for r in self.rules
            ],
            "precificacao": {
                "metodo": "DESCONTO_SIMPLES",
                "taxa_mensal_percentual": str(self.rate),
                "base_dias": self.base_days,
            },
        }
