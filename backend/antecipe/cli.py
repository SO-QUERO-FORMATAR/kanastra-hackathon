"""Administrative commands: configuration and registry never enter through note upload."""

import argparse
import json
import logging
from pathlib import Path

from antecipe.settings import Settings
from antecipe.adapters.database import make_engine
from antecipe.adapters.migrations import migrate
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.worker import Worker
from antecipe.application.admin import Admin
from antecipe.application.worker import serve


def batch_size(value):
    number = int(value)
    if not 1000 <= number <= 5000:
        raise argparse.ArgumentTypeError("batch-size deve estar entre 1000 e 5000")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="Operação do backend Antecipe")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate")
    for command in ["import-registry", "import-rules"]:
        commands.add_parser(command).add_argument("path", type=Path)
    worker = commands.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--batch-size", type=batch_size, default=2000)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = make_engine(Settings())
    try:
        if args.command == "migrate":
            migrate(engine)
            print("Migrações aplicadas")
        elif args.command == "import-registry":
            print(json.dumps({"versao_cadastral": Admin(PgAdmin(engine)).import_registry(args.path)}))
        elif args.command == "import-rules":
            imported = Admin(PgAdmin(engine)).import_rules(args.path)
            output = [{"fundo_id": fid, "versao": version} for fid, version in imported]
            if len(output) == 1:
                print(json.dumps(output[0]))
            else:
                print(json.dumps({"configuracoes": output}))
        elif args.command == "worker":
            serve(Worker(engine, batch_size=args.batch_size), once=args.once)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
