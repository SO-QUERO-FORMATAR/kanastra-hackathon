from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from antecipe.settings import Settings


def make_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=10,
        connect_args={"connect_timeout": 5},
    )
