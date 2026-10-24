import os
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://antecipe:antecipe@127.0.0.1:55432/antecipe"
        )
    )
    storage: Path = field(default_factory=lambda: Path(os.environ.get("STORAGE_PATH", "storage")).resolve())
    cursor_secret: str = field(
        default_factory=lambda: os.environ.get("CURSOR_SECRET", "local-demo-change-me")
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","))
    )

    @classmethod
    def for_tests(cls) -> "Settings":
        url = os.environ.get(
            "TEST_DATABASE_URL", "postgresql+psycopg://antecipe:antecipe@127.0.0.1:55432/antecipe_test"
        )
        if make_url(url).database != "antecipe_test" or not make_url(url).drivername.startswith("postgresql"):
            raise ValueError("Tests require dedicated PostgreSQL database antecipe_test")
        return cls(database_url=url)
