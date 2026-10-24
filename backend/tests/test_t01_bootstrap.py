import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


def test_application_and_config():
    from antecipe.adapters.http import create_app
    from antecipe.settings import Settings

    settings = Settings()
    response = TestClient(create_app(settings)).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["versao_api"] == "1.0.0"


def test_domain_independent_of_frameworks():
    root = Path("antecipe/domain")
    assert root.is_dir()
    for source in root.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    x.name.split(".")[0] not in {"fastapi", "sqlalchemy", "pydantic"} for x in node.names
                )
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {"fastapi", "sqlalchemy", "pydantic"}


def test_real_postgresql_isolated():
    from antecipe.settings import Settings
    from antecipe.adapters.database import make_engine

    settings = Settings.for_tests()
    assert settings.database_url.endswith("/antecipe_test")
    with make_engine(settings).connect() as conn:
        assert conn.scalar(text("select current_database()")) == "antecipe_test"
        assert int(conn.scalar(text("show server_version_num"))) >= 160000


def test_reject_non_test_database(monkeypatch):
    from antecipe.settings import Settings

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://localhost/production")
    with pytest.raises(ValueError, match="antecipe_test"):
        Settings.for_tests()
