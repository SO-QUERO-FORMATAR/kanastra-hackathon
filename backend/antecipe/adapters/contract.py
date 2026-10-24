import json
from pathlib import Path
from functools import lru_cache
from jsonschema import Draft202012Validator, FormatChecker
from antecipe.application.errors import AppError

ROOT = Path(__file__).resolve().parents[3]
SPEC = json.loads((ROOT / "docs/contratos/openapi.json").read_text(encoding="utf8"))


@lru_cache
def validator(name):
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": SPEC["components"]},
        format_checker=FormatChecker(),
    )


def validate(name, value):
    errors = list(validator(name).iter_errors(value))
    if errors:
        raise AppError(
            "VALIDACAO_REQUISICAO",
            "Requisição inválida",
            details=[
                {
                    "campo": "/" + "/".join(map(str, e.absolute_path)),
                    "codigo": "INVALIDO",
                    "mensagem": e.message,
                }
                for e in errors[:30]
            ],
        )
    return value
