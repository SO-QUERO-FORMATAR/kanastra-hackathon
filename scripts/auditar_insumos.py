"""Auditoria dos insumos entregues; não executa nem substitui o motor FIDC."""
from collections import Counter
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def normalizar(doc):
    return doc.translate(str.maketrans("", "", "./- "))


def main(argv=None):
    files = ROOT / "files"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=files / "estoque_antecipe_100k.zip")
    parser.add_argument("--member")
    parser.add_argument("--registry", type=Path, default=files / "cnpj_situacao_mock.csv")
    parser.add_argument("--rules", type=Path, default=files / "validadores_antecipe.json")
    parser.add_argument("--expected", type=Path, default=files / "resultado_esperado_100k.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/auditoria-insumos.json")
    args = parser.parse_args(argv)
    if args.input.suffix.lower() == ".zip":
        with zipfile.ZipFile(args.input) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()
                       and Path(info.filename).suffix.lower() == ".csv"
                       and (args.member is None or info.filename == args.member)]
            if len(members) != 1:
                parser.error("ZIP deve selecionar exatamente um CSV; use --member")
            content = archive.read(members[0]).decode("utf-8-sig")
    elif args.input.suffix.lower() == ".csv" and args.member is None:
        content = args.input.read_text(encoding="utf-8-sig")
    else:
        parser.error("Esperado CSV ou ZIP; --member só é válido para ZIP")
    reader = csv.DictReader(io.StringIO(content, newline=""), delimiter=";")
    columns = reader.fieldnames
    rows = list(reader)
    with args.registry.open(encoding="utf-8-sig", newline="") as source:
        cadastro = list(csv.DictReader(source, delimiter=";"))
    expected = json.loads(args.expected.read_text(encoding="utf-8-sig"))
    config = json.loads(args.rules.read_text(encoding="utf-8-sig"))
    configs = config if isinstance(config, list) else [config]
    if not configs:
        parser.error("Esperada pelo menos uma configuração")
    configured = {normalizar(item["fundo"]["cnpj"]) for item in configs}
    if len(configured) != len(configs):
        parser.error("CNPJ repetido nas configurações")
    by_line = {item["linha"]: item for item in expected}
    docs = {normalizar(row["DOC"]) for row in cadastro}
    funds = {}
    missing_docs, missing_rows, missing_approved = set(), [], []
    keys, approved_keys, repeated_approved = set(), {}, []
    mismatches = []
    for line, row in enumerate(rows, 2):
        fund = normalizar(row["DOC_FUNDO"])
        info = funds.setdefault(fund, {"nome": row["NOME_FUNDO"], "linhas": 0, "pl": Decimal(0)})
        info["linhas"] += 1
        info["pl"] += Decimal(row["VALOR_NOMINAL"].replace(".", "").replace(",", "."))
        target = by_line.get(line)
        if target is None or target["id"] != row["NU_DOCUMENTO"]:
            mismatches.append(line)
        key = (normalizar(row["DOC_CEDENTE"]), normalizar(row["DOC_SACADO"]), row["NU_DOCUMENTO"])
        keys.add(key)
        if target and target["status"] == "APROVADO":
            if key in approved_keys:
                repeated_approved.append({"primeira_linha": approved_keys[key], "linha": line, "fundo": fund, "id": row["NU_DOCUMENTO"]})
            else:
                approved_keys[key] = line
        if normalizar(row["DOC_SACADO"]) not in docs:
            missing_docs.add(normalizar(row["DOC_SACADO"]))
            item = {"linha": line, "doc_sacado": row["DOC_SACADO"], "fundo": fund, "id": row["NU_DOCUMENTO"]}
            missing_rows.append(item)
            if target and target["status"] == "APROVADO":
                missing_approved.append(item)
    rule_counts = {normalizar(item["fundo"]["cnpj"]): {
        "ativas": sum(rule["ativo"] for rule in item["validadores"]),
        "inativas": sum(not rule["ativo"] for rule in item["validadores"])
    } for item in configs}
    report = {
        "escopo": "Leitura integral, correlação e invariantes dos arquivos. Sem execução do motor de regras.",
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted({args.input, args.registry, args.rules, args.expected})},
        "colunas_estoque": columns,
        "linhas_estoque": len(rows),
        "linhas_referencia": len(expected),
        "linhas_referencia_repetidas": len(expected) - len(by_line),
        "linhas_referencia_ausentes": sorted(set(range(2, len(rows) + 2)) - set(by_line)),
        "linhas_referencia_extras": sorted(set(by_line) - set(range(2, len(rows) + 2))),
        "linhas_com_id_divergente": mismatches,
        "fundos": {key: {**value, "pl": str(value["pl"]), "configurado_no_json": key in configured} for key, value in sorted(funds.items())},
        "pl_total": str(sum(value["pl"] for value in funds.values())),
        "cadastro": {"linhas": len(cadastro), "cnpjs_distintos": len(docs), "situacoes": dict(Counter(row["SITUACAO_CADASTRAL"] for row in cadastro))},
        "sacados_ausentes": {"cnpjs_distintos": len(missing_docs), "linhas": len(missing_rows), "aprovados_na_referencia": len(missing_approved), "aprovados_antecipe": sum(item["fundo"] == "92234400000180" for item in missing_approved), "exemplos": missing_approved[:5]},
        "chaves_repetidas_apos_primeira_ocorrencia": len(rows) - len(keys),
        "aprovacoes_repetidas_na_referencia": {"quantidade": len(repeated_approved), "exemplos": repeated_approved[:5]},
        "status_referencia": dict(Counter(item["status"] for item in expected)),
        "motivos_referencia": dict(Counter(code for item in expected for code in item.get("barrado_por", []))),
        "regras": next(iter(rule_counts.values())) if len(configs) == 1 else rule_counts,
    }
    target = args.report
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Auditoria gravada: {target}")


if __name__ == "__main__":
    main()
