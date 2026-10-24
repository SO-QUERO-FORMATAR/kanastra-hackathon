"""Explain reference contradictions by physical line without changing engine decisions."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from antecipe.acceptance.inputs import read_input
from antecipe.adapters.config_import import load_configurations
from antecipe.adapters.readers import read_rows
from antecipe.domain.entities import normalize_document


def run(stock=None, expected_path=None, registry_path=None, rules_path=None, destination=None, member=None):
    root = Path(__file__).resolve().parents[3]
    official = all(value is None for value in (stock, expected_path, registry_path, rules_path, member))
    stock = stock or root / "files/estoque_antecipe_100k.zip"
    expected_path = expected_path or root / "files/resultado_esperado_100k.json"
    registry_path = registry_path or root / "files/cnpj_situacao_mock.csv"
    rules_path = rules_path or root / "files/validadores_antecipe.json"
    destination = destination or root / "docs/execucao/divergencias-referencia.jsonl"
    expected = json.loads(expected_path.read_text(encoding="utf-8-sig"))
    by_line = {row["linha"]: row for row in expected}
    with registry_path.open(encoding="utf-8-sig") as stream:
        docs = {normalize_document(row["DOC"]) for row in csv.DictReader(stream, delimiter=";")}
    seen: dict[tuple[str, str, str], int] = {}
    duplicates = 0
    absent_antecipe = 0
    configured = {fund["cnpj"] for fund, _ in load_configurations(rules_path)}
    rules_hash = hashlib.sha256(rules_path.read_bytes()).hexdigest()
    registry_hash = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    name, data = read_input(stock, member)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as directory, destination.open("w", encoding="utf8") as output:
        source = Path(directory) / "input"
        source.write_bytes(data)
        for line, row in read_rows(source, Path(name).suffix[1:].upper()):
            reference = by_line.get(line)
            if not reference or reference["status"] != "APROVADO":
                continue
            fund = normalize_document(row["DOC_FUNDO"])
            key = (
                normalize_document(row["DOC_CEDENTE"]),
                normalize_document(row["DOC_SACADO"]),
                row["NU_DOCUMENTO"],
            )
            common = {
                "arquivo": name,
                "linha": line,
                "nu_documento": row["NU_DOCUMENTO"],
                "fundo": fund,
                "esperado": "APROVADO",
                "motor": "SEM_DECISAO_LOTE_BLOQUEADO" if official else "NAO_EXECUTADO",
                "configuracao_sha256": rules_hash if fund in configured else None,
                "cadastro_sha256": registry_hash,
                "estado_inicial": "NAO_FORNECIDO",
            }
            if key in seen:
                duplicates += 1
                output.write(
                    json.dumps(
                        {**common, "regra": "NOTA_DUPLICADA", "primeira_aprovacao_referencia": seen[key]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            else:
                seen[key] = line
            if fund == "92234400000180" and key[1] not in docs:
                absent_antecipe += 1
                output.write(
                    json.dumps(
                        {**common, "regra": "SITUACAO_CADASTRAL_SACADO", "sacado_ausente": key[1]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    if official:
        assert duplicates == 4941 and absent_antecipe == 712
    print(
        json.dumps(
            {
                "report": str(destination),
                "aprovacoes_repetidas": duplicates,
                "aprovacoes_antecipe_sem_cadastro": absent_antecipe,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("input", "expected", "registry", "rules", "report"):
        parser.add_argument("--" + flag, type=Path)
    parser.add_argument("--member")
    args = parser.parse_args()
    run(args.input, args.expected, args.registry, args.rules, args.report, args.member)
