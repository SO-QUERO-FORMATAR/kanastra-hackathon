"""Initial immutable schema SQL, PostgreSQL 16+."""

from pathlib import Path
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    sql = (Path(__file__).parent / "0001_schema.sql").read_text(encoding="utf8")
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    raise RuntimeError("Destructive downgrade unsupported; restore a tested backup instead.")
