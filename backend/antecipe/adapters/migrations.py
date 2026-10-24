from pathlib import Path

from alembic.config import Config
from alembic import command
from sqlalchemy.engine import Engine


def migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
