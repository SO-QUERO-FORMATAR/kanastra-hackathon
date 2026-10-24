"""Index rejection filters directly by file and sequence, avoiding scans over approved rows."""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.execute(
        "ALTER TABLE reasons ADD COLUMN file_id uuid REFERENCES files(id), ADD COLUMN sequence integer"
    )
    op.execute(
        "UPDATE reasons SET file_id=results.file_id, sequence=results.sequence FROM results WHERE results.id=reasons.result_id"
    )
    op.execute("ALTER TABLE reasons ALTER COLUMN file_id SET NOT NULL, ALTER COLUMN sequence SET NOT NULL")
    op.execute("CREATE INDEX reasons_page ON reasons(file_id,code,sequence) INCLUDE(result_id)")
    op.execute("CREATE INDEX results_lot_fund ON results(lot_id,fund_id,status)")


def downgrade():
    op.execute("DROP INDEX results_lot_fund")
    op.execute("DROP INDEX reasons_page")
    op.execute("ALTER TABLE reasons DROP COLUMN file_id, DROP COLUMN sequence")
