"""Explain reference contradictions by physical line without changing engine decisions."""

import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

from antecipe.domain.entities import normalize_document


def run():
    root = Path(__file__).resolve().parents[3]
    expected = json.loads((root / "files/resultado_esperado_100k.json").read_text(encoding="utf8"))
    by_line = {row["linha"]: row for row in expected}
    with (root / "files/cnpj_situacao_mock.csv").open(encoding="utf-8-sig") as stream:
        docs = {normalize_document(row["DOC"]) for row in csv.DictReader(stream, delimiter=";")}
    seen: dict[tuple[str, str, str], int] = {}
    duplicates = 0
    absent_antecipe = 0
    audit = json.loads((root / "docs/auditoria-insumos.json").read_text(encoding="utf8"))
    destination = root / "docs/execucao/divergencias-referencia.jsonl"
    with (
        destination.open("w", encoding="utf8") as output,
        ZipFile(root / "files/estoque_antecipe_100k.zip") as archive,
    ):
        reader = csv.DictReader(
            io.TextIOWrapper(archive.open("estoque_antecipe.csv"), encoding="utf-8-sig"), delimiter=";"
        )
        for line, row in enumerate(reader, 2):
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
                "arquivo": "estoque_antecipe.csv",
                "linha": line,
                "nu_documento": row["NU_DOCUMENTO"],
                "fundo": fund,
                "esperado": "APROVADO",
                "motor": "SEM_DECISAO_LOTE_BLOQUEADO",
                "configuracao_sha256": audit["sha256"]["validadores_antecipe.json"]
                if fund == "92234400000180"
                else None,
                "cadastro_sha256": audit["sha256"]["cnpj_situacao_mock.csv"],
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
    run()
