"""Exercise arbitrary note inputs through HTTP/storage/worker in the dedicated test database."""

import argparse
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text, func

from antecipe.acceptance.compare import compare
from antecipe.acceptance.inputs import read_input
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.config_import import load_configurations
from antecipe.adapters.database import make_engine
from antecipe.adapters.http import create_app
from antecipe.adapters.migrations import migrate
from antecipe.adapters.schema import results, contexts, funds, approved
from antecipe.adapters.worker import Worker
from antecipe.settings import Settings


def reset_test_database():
    settings = Settings.for_tests()
    engine = make_engine(settings)
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    migrate(engine)
    return settings, engine


def process_input(settings, engine, path: Path, *, member=None, sheet=None):
    name, data = read_input(path, member)
    body = {
        "nome": f"Aceitação — {name}"[:120],
        "arquivos": [
            {
                "client_id": str(uuid4()),
                "nome": name,
                "formato": Path(name).suffix[1:].upper(),
                "tamanho_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "ordem": 0,
                "aba": sheet,
            }
        ],
    }

    def headers():
        return {"Idempotency-Key": str(uuid4())}

    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/lotes", json=body, headers=headers())
        response.raise_for_status()
        created = response.json()
        lid, aid = created["lote"]["id"], created["arquivos"][0]["id"]
        response = client.post(
            f"/api/v1/lotes/{lid}/batches",
            headers=headers(),
            data={"metadados": json.dumps({"arquivo_ids": [aid]})},
            files={"arquivos": (name, data)},
        )
        response.raise_for_status()
        client.post(f"/api/v1/lotes/{lid}/processamento", headers=headers()).raise_for_status()
        start = time.perf_counter()
        Worker(engine).run_once()
        elapsed = time.perf_counter() - start
        response = client.get(f"/api/v1/lotes/{lid}")
        response.raise_for_status()
        lot = response.json()
        problems = []
        cursor = None
        while True:
            params = {"limit": "100"}
            if cursor:
                params["cursor"] = cursor
            response = client.get(f"/api/v1/lotes/{lid}/pendencias", params=params)
            response.raise_for_status()
            page = response.json()
            problems.extend(page["itens"])
            cursor = page["proximo_cursor"]
            if not cursor:
                break
    with engine.connect() as c:
        actual = list(
            c.scalars(select(results.c.payload).where(results.c.lot_id == lid).order_by(results.c.sequence))
        )
        count = c.scalar(
            select(func.count())
            .select_from(approved)
            .join(results, approved.c.result_id == results.c.id)
            .where(results.c.lot_id == lid)
        )
        pls = {
            r.cnpj: str(r.pl)
            for r in c.execute(
                select(funds.c.cnpj, contexts.c.pl)
                .join(contexts, funds.c.id == contexts.c.fund_id)
                .where(contexts.c.lot_id == lid)
            )
        }
    return {
        "input": {"path": str(path), "name": name, "sha256": hashlib.sha256(data).hexdigest()},
        "seconds": elapsed,
        "lot": lot,
        "pending": problems,
        "pl_by_fund": pls,
        "confirmed_approvals": count,
        "results": actual,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("input", "rules", "registry", "report"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--member")
    parser.add_argument("--sheet")
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args(argv)
    # Detect input/JSON errors before resetting the dedicated database.
    read_input(args.input, args.member)
    load_configurations(args.rules)
    expected = json.loads(args.expected.read_text(encoding="utf-8-sig")) if args.expected else None
    settings, engine = reset_test_database()
    try:
        admin = PgAdmin(engine)
        admin.import_registry(args.registry)
        admin.import_rules(args.rules)
        with TemporaryDirectory(prefix="antecipe-input-") as directory:
            report = process_input(
                replace(settings, storage=Path(directory)),
                engine,
                args.input,
                member=args.member,
                sheet=args.sheet,
            )
        if expected is not None:
            report["comparison"] = compare(expected, report["results"])
        report["initial_state"] = "Banco de teste vazio; exposições e aprovações zeradas"
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
        print(json.dumps({"report": str(args.report), "status": report["lot"]["status"]}))
        if report["lot"]["status"] not in {"CONCLUIDO", "CONCLUIDO_COM_ERROS"} or any(
            report.get("comparison", {}).values()
        ):
            raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
