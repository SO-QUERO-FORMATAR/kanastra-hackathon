import pytest
from sqlalchemy import text

from antecipe.adapters.database import make_engine
from antecipe.settings import Settings


@pytest.fixture(scope="session")
def db_engine():
    from antecipe.adapters.migrations import migrate

    engine = make_engine(Settings.for_tests())
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    from antecipe.adapters.schema import metadata

    with db_engine.begin() as conn:
        for table in reversed(metadata.sorted_tables):
            conn.execute(table.delete())
    return db_engine


@pytest.fixture
def client(db, tmp_path):
    from fastapi.testclient import TestClient
    from antecipe.adapters.http import create_app

    settings = Settings(database_url=db.url.render_as_string(hide_password=False), storage=tmp_path)
    with TestClient(create_app(settings)) as client:
        yield client
