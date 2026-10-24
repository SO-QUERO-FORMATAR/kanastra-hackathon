"""SQLAlchemy Core relational model; money never passes through a float."""

from sqlalchemy import (
    MetaData,
    Table,
    Column as C,
    Text,
    Integer,
    BigInteger,
    Boolean,
    Numeric,
    DateTime,
    Uuid,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()
UUID = Uuid(as_uuid=False)
MONEY = Numeric(38, 2)


def id_column():
    return C("id", UUID, primary_key=True)


def stamp(name="created_at"):
    return C(name, DateTime(timezone=True), nullable=False, server_default=func.now())


funds = Table(
    "funds",
    metadata,
    id_column(),
    C("cnpj", Text, nullable=False, unique=True),
    C("name", Text, nullable=False),
    C("active_rule", UUID),
    CheckConstraint("cnpj ~ '^[0-9]{14}$'"),
)
rules = Table(
    "rules",
    metadata,
    id_column(),
    C("fund_id", UUID, ForeignKey("funds.id"), nullable=False),
    C("configuration", JSONB, nullable=False),
    stamp(),
)
loads = Table(
    "registry_loads",
    metadata,
    id_column(),
    C("sha256", Text, unique=True, nullable=False),
    C("count", Integer, nullable=False),
    C("active", Boolean, nullable=False, server_default="true"),
    stamp(),
)
Index("one_active_registry", loads.c.active, unique=True, postgresql_where=loads.c.active.is_(True))
registry = Table(
    "registry",
    metadata,
    C("load_id", UUID, ForeignKey("registry_loads.id"), primary_key=True),
    C("document", Text, primary_key=True),
    C("situation", Text, nullable=False),
    CheckConstraint("document ~ '^[0-9]{14}$'"),
)
lots = Table(
    "lots",
    metadata,
    id_column(),
    C("name", Text, nullable=False),
    C("status", Text, nullable=False, server_default="RECEBENDO"),
    stamp(),
    stamp("updated_at"),
    C("started_at", DateTime(timezone=True)),
    C("completed_at", DateTime(timezone=True)),
    C("load_id", UUID, ForeignKey("registry_loads.id")),
    C("indexed", Boolean, server_default="false", nullable=False),
    C("lines_read", Integer, nullable=False, server_default="0"),
    C("total_lines", Integer),
    C("processed", Integer, nullable=False, server_default="0"),
    C("error", JSONB),
    C("pending_revision", Integer, nullable=False, server_default="0"),
)
Index("lots_history", lots.c.created_at.desc(), lots.c.id.desc())
files = Table(
    "files",
    metadata,
    id_column(),
    C("lot_id", UUID, ForeignKey("lots.id"), nullable=False),
    C("client_id", UUID, nullable=False),
    C("position", Integer, nullable=False),
    C("name", Text, nullable=False),
    C("format", Text, nullable=False),
    C("sheet", Text),
    C("size", BigInteger, nullable=False),
    C("sha256", Text, nullable=False),
    C("path", Text),
    C("status", Text, nullable=False, server_default="AGUARDANDO_UPLOAD"),
    C("received_at", DateTime(timezone=True)),
    C("completed_at", DateTime(timezone=True)),
    C("total_lines", Integer),
    C("processed", Integer, nullable=False, server_default="0"),
    C("error", JSONB),
    UniqueConstraint("lot_id", "client_id"),
    UniqueConstraint("lot_id", "position"),
    UniqueConstraint("id", "lot_id"),
)
contexts = Table(
    "contexts",
    metadata,
    C("lot_id", UUID, ForeignKey("lots.id"), primary_key=True),
    C("fund_id", UUID, ForeignKey("funds.id"), primary_key=True),
    C("pl", MONEY, nullable=False),
    C("rule_id", UUID, ForeignKey("rules.id")),
)
staging = Table(
    "staging",
    metadata,
    C("file_id", UUID, ForeignKey("files.id"), primary_key=True),
    C("line", Integer, primary_key=True),
    C("sequence", Integer, nullable=False),
    C("fund_id", UUID, ForeignKey("funds.id")),
    C("nominal", MONEY),
    C("payload", JSONB, nullable=False),
    C("errors", JSONB, nullable=False),
    C("blocks_pl", Boolean, nullable=False, server_default="false"),
)
results = Table(
    "results",
    metadata,
    id_column(),
    C("lot_id", UUID, ForeignKey("lots.id"), nullable=False),
    C("file_id", UUID, ForeignKey("files.id"), nullable=False),
    C("sequence", Integer, nullable=False),
    C("line", Integer, nullable=False),
    C("fund_id", UUID, ForeignKey("funds.id")),
    C("type", Text, nullable=False),
    C("status", Text),
    C("nominal", MONEY, nullable=False, server_default="0"),
    C("discount", MONEY, nullable=False, server_default="0"),
    C("net", MONEY, nullable=False, server_default="0"),
    C("payload", JSONB, nullable=False),
    UniqueConstraint("file_id", "line"),
    UniqueConstraint("file_id", "sequence"),
    CheckConstraint(
        "(type = 'ERRO_DADOS' AND status IS NULL) OR (type = 'ANALISE' AND status IN ('APROVADO','BARRADO'))"
    ),
)
Index("results_filter", results.c.file_id, results.c.status, results.c.sequence)
Index("results_type", results.c.file_id, results.c.type, results.c.sequence)
reasons = Table(
    "reasons",
    metadata,
    C("result_id", UUID, ForeignKey("results.id"), primary_key=True),
    C("code", Text, primary_key=True),
    C("file_id", UUID, ForeignKey("files.id"), nullable=False),
    C("sequence", Integer, nullable=False),
)
Index("reasons_page", reasons.c.file_id, reasons.c.code, reasons.c.sequence, postgresql_include=["result_id"])
Index("reasons_code", reasons.c.code, reasons.c.result_id)
approved = Table(
    "approved",
    metadata,
    C("seller", Text, primary_key=True),
    C("debtor", Text, primary_key=True),
    C("number", Text, primary_key=True),
    C("fund_id", UUID, ForeignKey("funds.id"), nullable=False),
    C("result_id", UUID, ForeignKey("results.id"), nullable=False, unique=True),
)
exposures = Table(
    "exposures",
    metadata,
    C("fund_id", UUID, ForeignKey("funds.id"), primary_key=True),
    C("side", Text, primary_key=True),
    C("root", Text, primary_key=True),
    C("amount", MONEY, nullable=False),
    CheckConstraint("side IN ('SACADO','CEDENTE')"),
    CheckConstraint("root ~ '^[0-9]{8}$'"),
)
executions = Table(
    "executions",
    metadata,
    id_column(),
    C("lot_id", UUID, ForeignKey("lots.id"), nullable=False),
    C("status", Text, nullable=False, server_default="QUEUED"),
    stamp(),
    C("heartbeat", DateTime(timezone=True)),
    C("owner", UUID),
    C("checkpoint", BigInteger, nullable=False, server_default="0"),
)
pending = Table(
    "pending",
    metadata,
    id_column(),
    C("lot_id", UUID, ForeignKey("lots.id"), nullable=False),
    C("code", Text, nullable=False),
    C("fund_id", UUID, ForeignKey("funds.id")),
    C("file_id", UUID, ForeignKey("files.id")),
    C("line", Integer),
    C("field", Text),
    C("message", Text, nullable=False),
    C("action", Text, nullable=False),
)
idempotency = Table(
    "idempotency",
    metadata,
    C("scope", Text, primary_key=True),
    C("key", UUID, primary_key=True),
    C("fingerprint", Text, nullable=False),
    C("status_code", Integer, nullable=False),
    C("response", JSONB, nullable=False),
    stamp(),
)
