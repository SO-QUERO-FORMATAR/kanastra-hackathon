"""Administrative commands: configuration and registry never enter through note upload."""

import argparse
import json
import logging
from pathlib import Path
from time import perf_counter

from antecipe.settings import Settings
from antecipe.adapters.database import make_engine
from antecipe.adapters.migrations import migrate
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.worker import Worker
from antecipe.application.admin import Admin
from antecipe.application.worker import serve
from antecipe.observability import configure_logging, event


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
    configure_logging("antecipe-worker" if args.command == "worker" else "antecipe-cli")
    started = perf_counter()
    event("cli.command.started", operation=args.command)
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
        code = (
            "CONFIGURACAO_INVALIDA"
            if isinstance(exc, ValueError) and args.command == "import-rules"
            else "VALIDACAO_REQUISICAO"
            if isinstance(exc, ValueError)
            else "INFRAESTRUTURA_INDISPONIVEL"
        )
        event(
            "cli.command.failed",
            level=logging.WARNING if isinstance(exc, ValueError) else logging.ERROR,
            operation=args.command,
            error=exc,
            error_code=code,
            duration_ms=(perf_counter() - started) * 1000,
        )
        # Preserve the CLI's validation exit code without echoing raw input or paths to stderr.
        parser.exit(2)
    except Exception as exc:
        event(
            "cli.command.failed",
            level=logging.ERROR,
            operation=args.command,
            error=exc,
            duration_ms=(perf_counter() - started) * 1000,
        )
        raise
    else:
        event("cli.command.finished", operation=args.command, duration_ms=(perf_counter() - started) * 1000)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
