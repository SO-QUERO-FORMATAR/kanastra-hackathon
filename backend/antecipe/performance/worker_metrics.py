import json
import sys
from pathlib import Path
from sqlalchemy import event
from antecipe.settings import Settings
from antecipe.adapters.database import make_engine
from antecipe.adapters.worker import Worker

engine = make_engine(Settings())
metrics = {"registry_queries": 0, "write_statements": 0, "statements": 0}


@event.listens_for(engine, "before_cursor_execute")
def measure(conn, cursor, statement, parameters, context, executemany):
    metrics["statements"] += 1
    if "FROM registry " in statement or "FROM registry\n" in statement:
        metrics["registry_queries"] += 1
    if statement.startswith(("INSERT", "UPDATE")):
        metrics["write_statements"] += 1


Worker(engine).run_once()
Path(sys.argv[1]).write_text(json.dumps(metrics), encoding="utf8")
