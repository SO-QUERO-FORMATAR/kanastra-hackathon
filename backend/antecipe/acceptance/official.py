"""Run official stock through real HTTP/storage/worker; only TEST_DATABASE_URL is used."""

import hashlib
import json
import time
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile
from fastapi.testclient import TestClient
from sqlalchemy import text, select, func

from antecipe.settings import Settings
from antecipe.adapters.database import make_engine
from antecipe.adapters.migrations import migrate
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.http import create_app
from antecipe.adapters.worker import Worker
from antecipe.adapters.schema import results, contexts, funds, approved
from antecipe.acceptance.compare import compare


def reset_test_database():
    settings = Settings.for_tests()
    engine = make_engine(settings)
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    migrate(engine)
    return settings, engine


def run():
    root = Path(__file__).resolve().parents[3]
    settings, engine = reset_test_database()
    admin = PgAdmin(engine)
    admin.import_registry(root / "files/cnpj_situacao_mock.csv")
    admin.import_rules(root / "files/validadores_antecipe.json")
    with ZipFile(root / "files/estoque_antecipe_100k.zip") as archive:
        data = archive.read("estoque_antecipe.csv")
    body = {
        "nome": "Aceitação oficial — dados originais",
        "arquivos": [
            {
                "client_id": str(uuid4()),
                "nome": "estoque_antecipe.csv",
                "formato": "CSV",
                "tamanho_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "ordem": 0,
                "aba": None,
            }
        ],
    }
    with TestClient(create_app(settings)) as client:

        def key():
            return {"Idempotency-Key": str(uuid4())}

        response = client.post("/api/v1/lotes", json=body, headers=key())
        response.raise_for_status()
        created = response.json()
        lid = created["lote"]["id"]
        aid = created["arquivos"][0]["id"]
        response = client.post(
            f"/api/v1/lotes/{lid}/batches",
            headers=key(),
            data={"metadados": json.dumps({"arquivo_ids": [aid]})},
            files={"arquivos": ("estoque_antecipe.csv", data)},
        )
        response.raise_for_status()
        client.post(f"/api/v1/lotes/{lid}/processamento", headers=key()).raise_for_status()
        start = time.perf_counter()
        Worker(engine).run_once()
        elapsed = time.perf_counter() - start
        lot = client.get(f"/api/v1/lotes/{lid}").json()
        problems = client.get(f"/api/v1/lotes/{lid}/pendencias", params={"limit": 100}).json()
    expected = json.loads((root / "files/resultado_esperado_100k.json").read_text(encoding="utf8"))
    with engine.connect() as c:
        actual = list(c.scalars(select(results.c.payload)))
        count = c.scalar(select(func.count()).select_from(approved))
        pls = {
            r.cnpj: str(r.pl)
            for r in c.execute(
                select(funds.c.cnpj, contexts.c.pl).join(contexts, funds.c.id == contexts.c.fund_id)
            )
        }
    comparison = compare(expected, actual)
    report = {
        "acceptance": "PENDENTE",
        "reason": "17 configurações próprias ausentes; nenhuma aprovação permitida antes de resolver todas",
        "seconds": elapsed,
        "lot": lot,
        "pending": problems["itens"],
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
    assert lot["status"] == "BLOQUEADO" and len(problems["itens"]) == 17 and count == 0
    assert lot["progresso"]["linhas_total"] == 100554
    assert lot["resumo"]["total_nominal"] == "604931711.69"
    print(
        json.dumps(
            {
                "report": str(destination),
                "status": lot["status"],
                "pending": len(problems["itens"]),
                "seconds": elapsed,
            }
        )
    )


if __name__ == "__main__":
    run()
