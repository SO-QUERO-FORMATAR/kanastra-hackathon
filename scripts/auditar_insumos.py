"""Auditoria dos insumos entregues; não executa nem substitui o motor FIDC."""
from collections import Counter
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


def main():
    files = ROOT / "files"
    with zipfile.ZipFile(files / "estoque_antecipe_100k.zip") as archive:
        with archive.open("estoque_antecipe.csv") as source:
            reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig"), delimiter=";")
            columns = reader.fieldnames
            rows = list(reader)
    with (files / "cnpj_situacao_mock.csv").open(encoding="utf-8-sig", newline="") as source:
        cadastro = list(csv.DictReader(source, delimiter=";"))
    expected = json.loads((files / "resultado_esperado_100k.json").read_text(encoding="utf-8-sig"))
    config = json.loads((files / "validadores_antecipe.json").read_text(encoding="utf-8-sig"))
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
    configured = normalizar(config["fundo"]["cnpj"])
    report = {
        "escopo": "Leitura integral, correlação e invariantes dos arquivos. Sem execução do motor de regras.",
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files.iterdir()) if p.is_file()},
        "colunas_estoque": columns,
        "linhas_estoque": len(rows),
        "linhas_referencia": len(expected),
        "linhas_referencia_repetidas": len(expected) - len(by_line),
        "linhas_referencia_ausentes": sorted(set(range(2, len(rows) + 2)) - set(by_line)),
        "linhas_referencia_extras": sorted(set(by_line) - set(range(2, len(rows) + 2))),
        "linhas_com_id_divergente": mismatches,
        "fundos": {key: {**value, "pl": str(value["pl"]), "configurado_no_json": key == configured} for key, value in sorted(funds.items())},
        "pl_total": str(sum(value["pl"] for value in funds.values())),
        "cadastro": {"linhas": len(cadastro), "cnpjs_distintos": len(docs), "situacoes": dict(Counter(row["SITUACAO_CADASTRAL"] for row in cadastro))},
        "sacados_ausentes": {"cnpjs_distintos": len(missing_docs), "linhas": len(missing_rows), "aprovados_na_referencia": len(missing_approved), "aprovados_antecipe": sum(item["fundo"] == configured for item in missing_approved), "exemplos": missing_approved[:5]},
        "chaves_repetidas_apos_primeira_ocorrencia": len(rows) - len(keys),
        "aprovacoes_repetidas_na_referencia": {"quantidade": len(repeated_approved), "exemplos": repeated_approved[:5]},
        "status_referencia": dict(Counter(item["status"] for item in expected)),
        "motivos_referencia": dict(Counter(code for item in expected for code in item.get("barrado_por", []))),
        "regras": {"ativas": sum(item["ativo"] for item in config["validadores"]), "inativas": sum(not item["ativo"] for item in config["validadores"])},
    }
    target = ROOT / "docs" / "auditoria-insumos.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Auditoria gravada: {target}")


if __name__ == "__main__":
    main()
