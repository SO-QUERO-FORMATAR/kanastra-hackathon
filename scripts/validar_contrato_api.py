"""Valida o contrato planejado e suas fixtures, sem executar backend."""
from copy import deepcopy
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

import gerar_contrato_api


def main():
    directory = Path(__file__).resolve().parents[1] / "docs" / "contratos"
    spec = json.loads((directory / "openapi.json").read_text(encoding="utf-8"))
    if spec != gerar_contrato_api.spec:
        raise AssertionError("OpenAPI desatualizado: execute scripts/gerar_contrato_api.py")
    validate(spec)
    for schema in spec["components"]["schemas"].values():
        Draft202012Validator.check_schema(schema)

    def validator(name):
        return Draft202012Validator({"$ref": f"#/components/schemas/{name}", "components": spec["components"]}, format_checker=FormatChecker())

    example_file = json.loads((directory / "exemplos.json").read_text(encoding="utf-8"))
    if example_file != gerar_contrato_api.examples():
        raise AssertionError("Exemplos desatualizados: execute scripts/gerar_contrato_api.py")
    examples = example_file["exemplos"]
    by_name = {}
    for example in examples:
        validator(example["schema"]).validate(example["valor"])
        by_name[example["nome"]] = example["valor"]

    bad_request = deepcopy(by_name["criar_lote"])
    bad_request["campo_inventado"] = "erro"
    missing_request = deepcopy(by_name["criar_lote"])
    del missing_request["arquivos"]
    bad_hash = deepcopy(by_name["criar_lote"])
    bad_hash["arquivos"][0]["sha256"] = "hash-invalido"
    bad_rules = deepcopy(by_name["configurar_fundo"])
    bad_rules["configuracao"]["validadores"] = [bad_rules["configuracao"]["validadores"][0]] * 9
    bad_params = deepcopy(by_name["configurar_fundo"])
    bad_params["configuracao"]["validadores"][0]["parametros"] = {"valor_minimo": "10.00"}
    approved, barred, diagnostic = deepcopy(by_name["resultados"]["itens"])
    approved["titulo"] = None
    barred["motivos"] = []
    diagnostic["status"] = "BARRADO"
    invalid = [
        ("Dinheiro", 9800.0), ("Dinheiro", "9.800,00"), ("Dinheiro", "9800"),
        ("DecimalNaoNegativo", "-2.0"), ("DecimalNaoNegativo", 2.0),
        ("CriarLoteRequest", bad_request), ("CriarLoteRequest", missing_request), ("CriarLoteRequest", bad_hash),
        ("AtualizarRegrasRequest", bad_rules), ("AtualizarRegrasRequest", bad_params),
        ("ResultadoDTO", approved), ("ResultadoDTO", barred), ("ResultadoDTO", diagnostic),
        ("ListarResultadosQuery", {"limit": 101}), ("ListarResultadosQuery", {"status": "EM_ANALISE"}),
        ("BatchMetadadosDTO", {"arquivo_ids": []}),
    ]
    for name, value in invalid:
        if validator(name).is_valid(value):
            raise AssertionError(f"Schema {name} aceitou caso inválido: {value}")
    operations = [operation["operationId"] for methods in spec["paths"].values() for operation in methods.values()]
    if len(operations) != len(set(operations)):
        raise AssertionError("operationId duplicado")
    handoff = (directory.parent / "handoff-frontend.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", handoff, re.DOTALL)
    if len(blocks) != 3:
        raise AssertionError("O prompt deve conter OpenAPI, exemplos por DTO e fixtures completos")
    embedded_spec, dto_examples, embedded_fixtures = map(json.loads, blocks)
    if embedded_spec != spec or embedded_fixtures != example_file:
        raise AssertionError("Prompt divergente dos contratos canônicos")
    if set(dto_examples) != set(spec["components"]["schemas"]):
        raise AssertionError("Faltam exemplos de DTOs no prompt")
    for name, value in dto_examples.items():
        validator(name).validate(value)
    for match in re.finditer(r'"\$ref"\s*:\s*"([^"]+)"', blocks[0]):
        if not match.group(1).startswith("#/components/schemas/"):
            raise AssertionError("Prompt contém referência de schema externa")
    print(f"OK: OpenAPI 3.1, {len(spec['components']['schemas'])} schemas, {len(operations)} operações, {len(examples)} cenários, {len(invalid)} rejeições esperadas e {len(dto_examples)} exemplos de DTOs no prompt autocontido.")


if __name__ == "__main__":
    main()
