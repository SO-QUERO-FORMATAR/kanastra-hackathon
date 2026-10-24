import json
from decimal import Decimal
from pathlib import Path

from antecipe.domain.config import Configuration
from antecipe.domain.entities import normalize_document, document_root


def load_rules(path: Path) -> tuple[dict, Configuration]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"), parse_float=Decimal)
    fund = dict(raw["fundo"])
    fund["cnpj"] = normalize_document(fund["cnpj"])
    if document_root(fund["cnpj"]) is None:
        raise ValueError("Identidade de fundo inválida")
    for rule in raw["validadores"]:
        params = rule["parametros"]
        for key in {"valor_minimo", "percentual_maximo"} & params.keys():
            params[key] = str(params[key])
        if rule["codigo"].startswith("CONCENTRACAO_MAXIMA_"):
            params.setdefault("agrupamento", "RAIZ_CNPJ")
    raw["precificacao"]["taxa_mensal_percentual"] = str(raw["precificacao"]["taxa_mensal_percentual"])
    return fund, Configuration.from_dict({k: raw[k] for k in ["validadores", "precificacao"]})
