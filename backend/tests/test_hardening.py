from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select, func
from openpyxl import Workbook

from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.worker import Worker
from antecipe.adapters.schema import lots, contexts, results
from antecipe.adapters.readers import read_rows, COLUMNS, parse_row
from antecipe.application.errors import AppError
from test_t13_worker import prepare
from test_t11_readers import values
from test_t03_config import config_dict


def test_calamine_path_and_numeric_excel_identifier_diagnostic(tmp_path, monkeypatch):
    import antecipe.adapters.readers as readers

    path = tmp_path / "small.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(COLUMNS)
    ws.append(values())
    ws["G2"] = 351153
    wb.save(path)
    called = []
    original = readers.read_calamine

    def spy(*args):
        called.append(True)
        yield from original(*args)

    monkeypatch.setattr(readers, "read_calamine", spy)
    parsed = parse_row(list(read_rows(path, "XLSX"))[0][1])
    assert called and any(e["campo"] == "NU_DOCUMENTO" for e in parsed["errors"])


def test_registry_publication_races_freeze_and_snapshot_survives_rule_update(db, tmp_path):
    rows = [values() for _ in range(12)]
    for i, r in enumerate(rows):
        r[6] = str(i)
    _, lid, _ = prepare(db, tmp_path, rows)
    barrier = Barrier(2)
    replacement = tmp_path / "replacement.csv"
    replacement.write_text("DOC;SITUACAO_CADASTRAL\n22144961000102;INAPTA\n", encoding="utf8")

    class Stop(BaseException):
        pass

    def hook(phase):
        if phase == "before_freeze":
            barrier.wait(timeout=10)
        if phase == "after_commit":
            raise Stop()

    def importing():
        barrier.wait(timeout=10)
        with pytest.raises(AppError) as error:
            PgAdmin(db).import_registry(replacement)
        assert error.value.status == 409

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(importing)
        with pytest.raises(Stop):
            Worker(db, batch_size=3, hook=hook).run_once()
        future.result(timeout=20)
    with db.connect() as c:
        context = c.execute(select(contexts)).mappings().one()
    config = config_dict()
    config["precificacao"]["taxa_mensal_percentual"] = "9"
    PgAdmin(db).publish_rules(context["fund_id"], config, context["rule_id"])
    Worker(db).run_once()
    with db.connect() as c:
        assert c.scalar(select(contexts.c.rule_id)) == context["rule_id"]
        assert c.scalar(select(results.c.discount).where(results.c.status == "APROVADO")) == 200


def test_structural_failure_discards_partial_pl_and_other_file_completes(db, tmp_path):
    from test_t12_uploads import manifest
    from test_t11_readers import csv_bytes
    from antecipe.adapters.lot_store import LotStore

    admin = PgAdmin(db)
    admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    admin.import_rules(Path("../files/validadores_antecipe.json"))
    data = csv_bytes([values() for _ in range(12)])
    bad = csv_bytes() + b"wrong;columns\n"
    body = manifest(data)
    item = manifest(bad)["arquivos"][0]
    item["ordem"] = 1
    body["arquivos"].append(item)
    store = LotStore(db, tmp_path)
    created, _ = store.create(body, str(uuid4()))
    lid = created["lote"]["id"]
    store.upload(lid, [f["id"] for f in created["arquivos"]], [data, bad], str(uuid4()))
    store.enqueue(lid, str(uuid4()))
    Worker(db, batch_size=1).run_once()
    with db.connect() as c:
        assert c.scalar(select(lots.c.status)) == "CONCLUIDO_COM_ERROS"
        assert c.scalar(select(contexts.c.pl)) == 120000
        assert c.scalar(select(lots.c.total_lines)) == 12
        assert c.scalar(select(func.count()).select_from(results)) == 12


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_worker_process_death_recovers_postgres_session(db, tmp_path, phase):
    import subprocess
    import sys
    import os

    rows = [values() for _ in range(12)]
    for i, row in enumerate(rows):
        row[6] = str(i)
    prepare(db, tmp_path, rows)
    code = """import os,sys
from antecipe.settings import Settings
from antecipe.adapters.database import make_engine
from antecipe.adapters.worker import Worker
def hook(phase):
    if phase == sys.argv[1]: os._exit(42)
Worker(make_engine(Settings.for_tests()),batch_size=3,hook=hook).run_once()
"""
    env = dict(os.environ, TEST_DATABASE_URL=db.url.render_as_string(hide_password=False))
    result = subprocess.run([sys.executable, "-c", code, phase], env=env, timeout=30)
    assert result.returncode == 42
    Worker(db, batch_size=2).run_once()
    with db.connect() as c:
        assert c.scalar(select(lots.c.processed)) == 12
        assert c.scalar(select(func.count()).select_from(results)) == 12
        assert c.scalar(select(results.c.status).where(results.c.sequence == 1)) == "APROVADO"


def test_technical_failure_exposes_retry_and_resumes_committed_batch(db, tmp_path, client):
    from antecipe.adapters.schema import approved, exposures

    rows = [values() for _ in range(12)]
    for i, row in enumerate(rows):
        row[6] = str(i)
    _, lid, _ = prepare(db, tmp_path, rows)

    def fail(phase):
        if phase == "after_commit":
            raise RuntimeError("interrupção técnica sintética")

    with pytest.raises(RuntimeError):
        Worker(db, batch_size=3, hook=fail).run_once()
    lot = client.get(f"/api/v1/lotes/{lid}").json()
    assert lot["status"] == "FALHOU"
    assert lot["acoes"]["pode_retomar"] and lot["erro"]["retry_permitido"]
    assert lot["progresso"]["linhas_processadas"] == 3
    response = client.post(f"/api/v1/lotes/{lid}/processamento", headers={"Idempotency-Key": str(uuid4())})
    assert response.status_code == 202
    Worker(db, batch_size=2).run_once()
    lot = client.get(f"/api/v1/lotes/{lid}").json()
    assert lot["status"] == "CONCLUIDO" and lot["progresso"]["linhas_processadas"] == 12
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(approved)) == 1
        assert c.execute(select(exposures.c.amount)).scalars().all() == [10000, 10000]


def test_reason_index_migration_backfills_existing_results(db, tmp_path, client):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text
    from antecipe.adapters.migrations import migrate
    from antecipe.adapters.schema import reasons

    _, _, aid = prepare(db, tmp_path, [values() for _ in range(12)])
    Worker(db).run_once()
    url = f"/api/v1/arquivos/{aid}/resultados"
    before = client.get(url, params={"motivo": "NOTA_DUPLICADA"}).json()
    assert len(before["itens"]) == 11
    config = Config()
    config.set_main_option("script_location", str(Path("migrations").resolve()))
    with db.begin() as c:
        config.attributes["connection"] = c
        command.downgrade(config, "0001")
        assert c.scalar(text("select count(*) from reasons")) == 11
    migrate(db)
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(reasons).where(reasons.c.file_id == aid)) == 11
    assert client.get(url, params={"motivo": "NOTA_DUPLICADA"}).json() == before


def test_fund_summary_preserves_precision_above_default_decimal_context(db, tmp_path, client):
    rows = [values() for _ in range(12)]
    for i, row in enumerate(rows):
        row[6] = str(i)
        row[8] = "10000000000000000000000000001,00"
    _, lid, _ = prepare(db, tmp_path, rows)
    admin = PgAdmin(db)
    [(fid, version)] = admin.import_rules(Path("../files/validadores_antecipe.json"))
    config = config_dict()
    for rule in config["validadores"]:
        if rule["codigo"] == "CONCENTRACAO_MAXIMA_CEDENTE":
            rule["ativo"] = True
            rule["parametros"]["percentual_maximo"] = "20"
    admin.publish_rules(fid, config, version)
    Worker(db).run_once()
    response = client.get(f"/api/v1/lotes/{lid}/resumos-fundos")
    assert response.status_code == 200
    summary = response.json()["itens"][0]
    assert summary["pl"] == "120000000000000000000000000012.00"
    assert summary["limite_sacado"] == "12000000000000000000000000001.20"
    assert summary["limite_cedente"] == "24000000000000000000000000002.40"
