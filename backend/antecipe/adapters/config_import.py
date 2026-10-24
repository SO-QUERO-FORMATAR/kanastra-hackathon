import json
from decimal import Decimal
from pathlib import Path

from antecipe.adapters.contract import validator
from antecipe.domain.config import Configuration
from antecipe.domain.entities import normalize_document, document_root


def parse_rules(raw: dict, prefix: str) -> tuple[dict, Configuration]:
    if not isinstance(raw, dict):
        raise ValueError(f"{prefix}: esperado objeto de configuração")
    for field in ("fundo", "precificacao"):
        if not isinstance(raw.get(field), dict):
            raise ValueError(f"{prefix}.{field}: esperado objeto")
    fund = dict(raw["fundo"])
    for field in ("cnpj", "nome"):
        if not isinstance(fund.get(field), str) or not fund[field].strip():
            raise ValueError(f"{prefix}.fundo.{field}: esperado texto não vazio")
    fund["cnpj"] = normalize_document(fund["cnpj"])
    if document_root(fund["cnpj"]) is None:
        raise ValueError(f"{prefix}.fundo.cnpj: identidade de fundo inválida")
    if not isinstance(raw.get("validadores"), list):
        raise ValueError(f"{prefix}.validadores: esperado array")
    normalized = []
    for index, rule in enumerate(raw["validadores"]):
        field = f"{prefix}.validadores[{index}]"
        if not isinstance(rule, dict) or not isinstance(rule.get("parametros"), dict):
            raise ValueError(f"{field}.parametros: esperado objeto")
        params = dict(rule["parametros"])
        for key in {"valor_minimo", "percentual_maximo"} & params.keys():
            params[key] = str(params[key])
        if isinstance(rule.get("codigo"), str) and rule["codigo"] in {
            "CONCENTRACAO_MAXIMA_SACADO",
            "CONCENTRACAO_MAXIMA_CEDENTE",
        }:
            params.setdefault("agrupamento", "RAIZ_CNPJ")
        normalized.append({**rule, "parametros": params})
    pricing = dict(raw["precificacao"])
    if "taxa_mensal_percentual" in pricing:
        pricing["taxa_mensal_percentual"] = str(pricing["taxa_mensal_percentual"])
    data = {"validadores": normalized, "precificacao": pricing}
    error = next(validator("ConfiguracaoRegrasDTO").iter_errors(data), None)
    if error:
        location = ".".join(map(str, error.absolute_path))
        raise ValueError(f"{prefix}.{location or 'configuracao'}: {error.message}")
    try:
        return fund, Configuration.from_dict(data)
    except ValueError as exc:
        raise ValueError(f"{prefix}.configuracao: {exc}") from exc


def load_configurations(path: Path) -> list[tuple[dict, Configuration]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"), parse_float=Decimal)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("configuracoes: JSON inválido") from exc
    return parse_configurations(raw)


def parse_configurations(raw) -> list[tuple[dict, Configuration]]:
    items = raw if isinstance(raw, list) else [raw]
    if not items:
        raise ValueError("configuracoes: esperado pelo menos um item")
    configurations = []
    seen = set()
    for index, item in enumerate(items):
        prefix = f"configuracoes[{index}]"
        fund, configuration = parse_rules(item, prefix)
        if fund["cnpj"] in seen:
            raise ValueError(f"{prefix}.fundo.cnpj: CNPJ repetido {fund['cnpj']}")
        seen.add(fund["cnpj"])
        configurations.append((fund, configuration))
    return configurations


def load_rules(path: Path) -> tuple[dict, Configuration]:
    """Compatibility helper for callers that require exactly one configuration."""
    configurations = load_configurations(path)
    if len(configurations) != 1:
        raise ValueError("Esperada uma configuração; use load_configurations para múltiplos fundos")
    return configurations[0]
