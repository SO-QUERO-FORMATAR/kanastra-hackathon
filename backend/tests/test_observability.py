import io
import json
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from antecipe import observability as obs
from antecipe.adapters.lot_store import LotStore
from antecipe.adapters.queries import Queries
from antecipe.adapters.schema import lots
from antecipe.adapters.worker import Worker
from test_t11_readers import csv_bytes, values
from test_t12_uploads import manifest
from test_t13_worker import prepare
from test_t14_api import headers

SECRET = "Cliente-031.456.789-10-private@example.test"
SCHEMA = json.loads(Path("../docs/observability/log-event.schema.json").read_text(encoding="utf8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


@contextmanager
def captured():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(obs.SafeFormatter())
    logger = logging.getLogger()
    logger.addHandler(handler)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)


def records(stream, name=None):
    entries = [json.loads(line) for line in stream.getvalue().splitlines()]
    for entry in entries:
        VALIDATOR.validate(entry)
    return [entry for entry in entries if name is None or entry["event"]["name"] == name]


def assert_private(stream):
    text = stream.getvalue()
    for value in (
        SECRET,
        "031.456.789-10",
        "03145678910",
        "22144961000102",
        "Bearer secret-token",
        "password=secret-password",
        "dados_originais",
        "Traceback (most recent call last)",
    ):
        assert value not in text


def test_schema_catalog_matches_implementation():
    assert set(SCHEMA["properties"]["event"]["properties"]["name"]["enum"]) == obs.EVENTS


def test_json_allowlist_privacy_even_in_debug(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_REVISION", raising=False)
    obs.configure_logging("antecipe-api")
    rid = str(uuid4())
    with captured() as stream, obs.log_context(request_id=rid):
        obs.event(
            "http.finished",
            operation="criarLote",
            status_code=201,
            duration_ms=1.25,
            body={"nome": SECRET},
            path="/" + SECRET,
            authorization="Bearer secret-token",
            file_id=SECRET,
            reason_counts={SECRET: 10, "NOTA_DUPLICADA": 2},
            row_count=True,
            byte_count=float("nan"),
        )
        try:
            raise OperationalError(
                "SELECT " + SECRET, {"cpf": SECRET}, RuntimeError("password=secret-password")
            )
        except OperationalError:
            logging.getLogger("sqlalchemy.engine").exception("Bearer secret-token %s", SECRET)
        logging.getLogger("uvicorn.access").info("127.0.0.1 GET /?nome=%s", SECRET)
        obs.event("http.finished\n" + SECRET)
    assert_private(stream)
    entries = records(stream)
    assert len(entries) == 2
    assert entries[0]["service"] == {"name": "antecipe-api", "version": "1.0.0", "environment": "production"}
    assert entries[0]["correlation"] == {"request_id": rid}
    assert entries[0]["decision"]["reason_counts"] == {"NOTA_DUPLICADA": 2}
    assert "counts" not in entries[0]
    assert entries[1]["error"]["error_kind"] == "OperationalError"


def test_request_validation_logs_code_and_correlation_without_input(client):
    with captured() as stream:
        response = client.get(
            "/api/v1/fundos",
            params={"unexpected": SECRET},
            headers={"Authorization": "Bearer secret-token", "X-Request-Id": SECRET},
        )
    assert response.status_code == 422
    [error] = records(stream, "http.failed")
    assert error["operation"] == "listarFundos"
    assert error["correlation"]["request_id"] == response.headers["X-Request-Id"]
    assert error["error"]["error_code"] == "VALIDACAO_REQUISICAO"
    assert error["event"]["outcome"] == "rejected"
    assert_private(stream)


def test_database_error_is_safe_and_diagnostic(client, monkeypatch):
    def fail(*args):
        raise OperationalError(
            "SELECT " + SECRET, {"value": SECRET}, RuntimeError("password=secret-password")
        )

    monkeypatch.setattr(Queries, "get", fail)
    with captured() as stream:
        response = client.get("/api/v1/fundos")
    assert response.status_code == 503
    [error] = records(stream, "http.failed")
    assert error["error"]["error_kind"] == "OperationalError"
    assert error["error"]["error_code"] == "INFRAESTRUTURA_INDISPONIVEL"
    assert error["error"]["locations"]
    assert error["severity_text"] == "ERROR"
    assert_private(stream)


def test_concurrent_requests_keep_separate_contexts(client, monkeypatch):
    barrier = Barrier(2)
    original = LotStore.create

    def synchronized(*args, **kwargs):
        barrier.wait(timeout=10)
        return original(*args, **kwargs)

    monkeypatch.setattr(LotStore, "create", synchronized)
    body = manifest(csv_bytes())
    body["nome"] = SECRET
    with captured() as stream:
        with ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(lambda _: client.post("/api/v1/lotes", json=body, headers=headers()), range(2))
            )
        obs.event("service.started")
    mapping = {r.headers["X-Request-Id"]: r.json()["lote"]["id"] for r in responses}
    finished = records(stream, "lot.create.finished")
    assert len(mapping) == len(finished) == 2
    for entry in finished:
        assert mapping[entry["correlation"]["request_id"]] == entry["correlation"]["lot_id"]
    assert "correlation" not in records(stream, "service.started")[0]
    assert_private(stream)


def test_idempotency_replay_conflict_and_upload_error(client):
    body = manifest(csv_bytes())
    body["nome"] = SECRET
    key = headers()
    with captured() as stream:
        created = client.post("/api/v1/lotes", json=body, headers=key)
        replay = client.post("/api/v1/lotes", json=body, headers=key)
        conflict = client.post("/api/v1/lotes", json={**body, "nome": "different"}, headers=key)
        lid = created.json()["lote"]["id"]
        aid = created.json()["arquivos"][0]["id"]
        invalid = client.post(
            f"/api/v1/lotes/{lid}/batches",
            headers=headers(),
            data={"metadados": json.dumps({"arquivo_ids": [aid]})},
            files={"arquivos": (SECRET + ".csv", SECRET.encode())},
        )
    assert replay.status_code == 201 and conflict.status_code == 409 and invalid.status_code == 422
    assert len(records(stream, "idempotency.replayed")) == 1
    assert len(records(stream, "idempotency.conflict")) == 1
    [failure] = records(stream, "lot.upload.failed")
    assert failure["error"]["error_code"] == "INTEGRIDADE_ARQUIVO"
    assert failure["correlation"]["lot_id"] == lid
    assert_private(stream)


def test_commit_failure_never_logs_success(db, tmp_path, monkeypatch):
    obs.configure_logging()
    begin = db.begin

    @contextmanager
    def failed_commit():
        with begin() as connection:
            yield connection
            raise RuntimeError(SECRET)

    monkeypatch.setattr(db, "begin", failed_commit)
    with captured() as stream, pytest.raises(RuntimeError, match="Cliente"):
        LotStore(db, tmp_path).create(manifest(csv_bytes()), str(uuid4()))
    assert not records(stream, "lot.create.finished")
    assert len(records(stream, "lot.create.failed")) == 1
    with db.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(lots)) == 0
    assert_private(stream)


def test_worker_aggregates_committed_decisions_without_notes(db, tmp_path):
    obs.configure_logging("antecipe-worker")
    rows = [values() for _ in range(12)]
    rows[0][2] = SECRET
    _, lid, aid = prepare(db, tmp_path, rows)
    with captured() as stream:
        assert Worker(db, batch_size=4).run_once()
    chunks = records(stream, "worker.chunk_committed")
    assert len(chunks) == 3
    assert sum(e["counts"]["approved_count"] for e in chunks) == 1
    assert sum(e["counts"]["rejected_count"] for e in chunks) == 11
    for entry in chunks:
        assert entry["correlation"]["lot_id"] == lid
        assert entry["correlation"]["file_id"] == aid
        assert "execution_id" in entry["correlation"]
    assert records(stream, "worker.completed")[0]["event"]["outcome"] == "success"
    assert records(stream, "worker.rules_frozen")[0]["versions"]["rule_version"]
    assert_private(stream)


def test_blocked_worker_has_reason_counts(db, tmp_path):
    obs.configure_logging("antecipe-worker")
    prepare(db, tmp_path, rules=False)
    with captured() as stream:
        Worker(db).run_once()
    [blocked] = records(stream, "worker.blocking")
    assert blocked["decision"]["reason_counts"] == {"FUNDO_SEM_REGRAS": 1}
    assert records(stream, "worker.freeze.finished")[0]["event"]["outcome"] == "success"
    assert records(stream, "worker.chunk_committed")
    assert records(stream, "worker.completed")[0]["event"]["outcome"] == "blocked"


def test_failed_chunk_has_no_confirmation_and_safe_error(db, tmp_path):
    obs.configure_logging("antecipe-worker")
    prepare(db, tmp_path, [values() for _ in range(12)])

    def crash(phase):
        if phase == "before_commit":
            raise RuntimeError(SECRET)

    with captured() as stream, pytest.raises(RuntimeError):
        Worker(db, hook=crash).run_once()
    assert not records(stream, "worker.chunk_committed")
    [failure] = records(stream, "worker.failed")
    assert failure["error"]["retry"] is True
    assert failure["error"]["error_kind"] == "RuntimeError"
    assert_private(stream)


def test_worker_recovery_logs_existing_snapshot_and_checkpoint(db, tmp_path):
    obs.configure_logging("antecipe-worker")
    prepare(db, tmp_path, [values() for _ in range(12)])

    class ProcessCrash(BaseException):
        pass

    def crash(phase):
        if phase == "after_commit":
            raise ProcessCrash()

    with pytest.raises(ProcessCrash):
        Worker(db, batch_size=4, hook=crash).run_once()
    with captured() as stream:
        Worker(db, batch_size=4).run_once()
    [claimed] = records(stream, "worker.claimed")
    assert claimed["decision"]["recovered"] is True
    assert claimed["counts"]["checkpoint"] == 4
    assert records(stream, "worker.snapshot_reused")[0]["decision"]["recovered"] is True
    assert sum(r["counts"]["row_count"] for r in records(stream, "worker.chunk_committed")) == 8
    assert records(stream, "worker.completed")


def test_file_error_and_failed_index_are_not_reported_as_success(db, tmp_path, monkeypatch):
    from antecipe.adapters import worker
    from antecipe.adapters.readers import FileError

    obs.configure_logging("antecipe-worker")
    prepare(db, tmp_path)

    def invalid(*args):
        raise FileError(SECRET)

    monkeypatch.setattr(worker, "read_rows", invalid)
    with captured() as stream:
        Worker(db).run_once()
    assert records(stream, "worker.file_failed")[0]["error"]["error_kind"] == "FileError"
    assert records(stream, "worker.index.finished")[0]["event"]["outcome"] == "failure"
    assert records(stream, "worker.lot.finished")[0]["event"]["outcome"] == "observed"
    assert not records(stream, "worker.completed")
    assert_private(stream)


def test_environment_metadata_is_validated_and_health_success_is_debug(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", SECRET)
    monkeypatch.setenv("APP_REVISION", SECRET)
    obs.configure_logging("antecipe-api")
    with captured() as stream:
        client.get("/api/v1/health/live")
        obs.event("service.started")
    assert not records(stream, "http.finished")
    [started] = records(stream, "service.started")
    assert started["service"]["environment"] == "local"
    assert "revision" not in started["service"]
    assert_private(stream)


def test_logging_sink_failure_preserves_business_result(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError(SECRET)

    monkeypatch.setattr(obs.LOG, "log", unavailable)

    @obs.observed("lot.create")
    def operation():
        return "committed"

    assert operation() == "committed"
    assert obs.CONTEXT.get() == {}


def test_cli_uncaught_exception_has_no_traceback_or_path(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://antecipe:secret-password@127.0.0.1:1/antecipe_test"
    )
    result = subprocess.run(
        [sys.executable, "-m", "antecipe.cli", "worker", "--once"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    stream = io.StringIO(result.stderr)
    entries = records(stream, "process.failed")
    assert entries[0]["error"]["error_kind"] == "OperationalError"
    assert_private(stream)


def test_bulk_import_logs_each_fund_after_commit_and_replay(db, tmp_path):
    from antecipe.adapters.admin import PgAdmin
    from test_input_configurations import configuration, write_config

    obs.configure_logging("antecipe-cli")
    path = write_config(tmp_path, [configuration(), configuration("01392689000100")])
    admin = PgAdmin(db)
    with captured() as stream:
        imported = admin.import_rules(path)
        assert admin.import_rules(path) == imported
    published = records(stream, "rules.publish.finished")
    reused = records(stream, "rules.reused")
    for entries in (published, reused):
        assert len(entries) == 2
        assert {(r["correlation"]["fund_id"], r["versions"]["rule_version"]) for r in entries} == set(
            imported
        )
    assert all(r["decision"]["replayed"] is False for r in published)
    assert all(r["decision"]["replayed"] is True for r in reused)
    assert "92234400000180" not in stream.getvalue()
    assert "01392689000100" not in stream.getvalue()


def test_bulk_rollback_never_logs_partial_publication(db, tmp_path, monkeypatch):
    from antecipe.adapters import admin
    from test_input_configurations import configuration, write_config

    obs.configure_logging("antecipe-cli")
    path = write_config(tmp_path, [configuration(), configuration("01392689000100")])
    publish = admin.publish
    calls = []

    def fail_second(*args):
        calls.append(args[1])
        if len(calls) == 2:
            raise RuntimeError(SECRET)
        return publish(*args)

    monkeypatch.setattr(admin, "publish", fail_second)
    with captured() as stream, pytest.raises(RuntimeError):
        admin.PgAdmin(db).import_rules(path)
    assert records(stream, "rules.import.failed")
    assert not records(stream, "rules.publish.finished")
    assert not records(stream, "rules.import.finished")
    assert_private(stream)


@pytest.mark.parametrize("missing", [False, True])
def test_cli_validation_preserves_exit_code_and_safe_json(tmp_path, missing):
    from test_input_configurations import configuration, write_config

    payload = configuration()
    payload["precificacao"]["metodo"] = SECRET
    path = tmp_path / SECRET if missing else write_config(tmp_path, [payload])
    result = subprocess.run(
        [sys.executable, "-m", "antecipe.cli", "import-rules", str(path)], capture_output=True, text=True
    )
    assert result.returncode == 2
    stream = io.StringIO(result.stderr)
    [failure] = records(stream, "cli.command.failed")
    assert failure["error"]["error_code"] == (
        "INFRAESTRUTURA_INDISPONIVEL" if missing else "CONFIGURACAO_INVALIDA"
    )
    assert not records(stream, "process.failed")
    assert_private(stream)


def test_real_uvicorn_uses_json_and_never_logs_raw_url():
    code = """
import socket
import threading
import time
import urllib.request
import urllib.error
import uvicorn
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
server = uvicorn.Server(uvicorn.Config("antecipe.adapters.http:app", log_level="debug"))
thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
thread.start()
try:
    deadline = time.monotonic() + 10
    while not server.started:
        assert thread.is_alive() and time.monotonic() < deadline
        time.sleep(0.02)
    url = "http://127.0.0.1:" + str(sock.getsockname()[1]) + "/private@example.test?token=secret-token"
    try:
        urllib.request.urlopen(url, timeout=5)
    except urllib.error.HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError("Expected unknown route")
finally:
    server.should_exit = True
    thread.join(timeout=10)
    sock.close()
assert not thread.is_alive()
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    stream = io.StringIO(result.stderr)
    assert records(stream, "service.started")
    assert records(stream, "service.stopped")
    [error] = records(stream, "http.failed")
    assert error["http"]["status_code"] == 404
    assert "private@example.test" not in result.stderr and "secret-token" not in result.stderr
