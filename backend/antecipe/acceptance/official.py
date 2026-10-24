"""Run official stock through real HTTP/storage/worker; only TEST_DATABASE_URL is used."""

import json
from pathlib import Path

from antecipe.acceptance.inputs_run import process_input, reset_test_database
from antecipe.adapters.admin import PgAdmin
from antecipe.acceptance.compare import compare


def run():
    root = Path(__file__).resolve().parents[3]
    settings, engine = reset_test_database()
    admin = PgAdmin(engine)
    admin.import_registry(root / "files/cnpj_situacao_mock.csv")
    admin.import_rules(root / "files/validadores_antecipe.json")
    report = process_input(settings, engine, root / "files/estoque_antecipe_100k.zip")
    lot, problems = report["lot"], report["pending"]
    elapsed, count, pls = report["seconds"], report["confirmed_approvals"], report["pl_by_fund"]
    actual = report["results"]
    expected = json.loads((root / "files/resultado_esperado_100k.json").read_text(encoding="utf8"))
    comparison = compare(expected, actual)
    report = {
        "acceptance": "PENDENTE",
        "reason": "17 configurações próprias ausentes; nenhuma aprovação permitida antes de resolver todas",
        "seconds": elapsed,
        "lot": lot,
        "pending": problems,
        "pl_by_fund": pls,
        "confirmed_approvals": count,
        "comparison": comparison,
        "input_audit": json.loads((root / "docs/auditoria-insumos.json").read_text(encoding="utf8")),
        "context": {
            "initial_exposures": "NÃO FORNECIDAS; banco de teste vazio, sem concordância oficial certificada"
        },
    }
    destination = root / "docs/execucao/aceitacao-oficial.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    assert lot["status"] == "BLOQUEADO" and len(problems) == 17 and count == 0
    assert lot["progresso"]["linhas_total"] == 100554
    assert lot["resumo"]["total_nominal"] == "604931711.69"
    print(
        json.dumps(
            {
                "report": str(destination),
                "status": lot["status"],
                "pending": len(problems),
                "seconds": elapsed,
            }
        )
    )


if __name__ == "__main__":
    run()
