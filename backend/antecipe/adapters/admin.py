import csv
import hashlib
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, insert, update, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from antecipe.adapters.schema import funds, rules, registry, loads, lots
from antecipe.adapters.config_import import load_configurations
from antecipe.application.errors import AppError
from antecipe.domain.config import Configuration
from antecipe.domain.entities import normalize_document, document_root

REGISTRY_LOCK = 601001


def discover(c, cnpj: str, name: str) -> str:
    cnpj = normalize_document(cnpj)
    if document_root(cnpj) is None:
        raise ValueError("Fundo sem identidade interpretável")
    c.execute(
        pg_insert(funds)
        .values(id=str(uuid4()), cnpj=cnpj, name=name)
        .on_conflict_do_nothing(index_elements=["cnpj"])
    )
    return c.scalar(select(funds.c.id).where(funds.c.cnpj == cnpj))


def publish(c, fund_id: str, data: dict, base: str | None) -> str:
    Configuration.from_dict(data)
    fund = c.execute(select(funds).where(funds.c.id == fund_id).with_for_update()).mappings().first()
    if not fund:
        raise AppError("RECURSO_NAO_ENCONTRADO", "Fundo não encontrado", 404)
    if fund["active_rule"] != base:
        raise AppError(
            "VERSAO_REGRAS_CONFLITANTE",
            "Regras alteradas por outra operação",
            409,
            current_version=fund["active_rule"],
        )
    version = str(uuid4())
    c.execute(insert(rules).values(id=version, fund_id=fund_id, configuration=data))
    c.execute(update(funds).where(funds.c.id == fund_id).values(active_rule=version))
    return version


class PgAdmin:
    def __init__(self, engine):
        self.engine = engine

    def discover_fund(self, cnpj, name):
        with self.engine.begin() as c:
            return discover(c, cnpj, name)

    def publish_rules(self, fund_id, data, base):
        with self.engine.begin() as c:
            return publish(c, fund_id, data, base)

    def get_rules(self, fund_id, version=None):
        with self.engine.connect() as c:
            if version is None:
                version = c.scalar(select(funds.c.active_rule).where(funds.c.id == fund_id))
            row = (
                c.execute(select(rules).where(rules.c.id == version, rules.c.fund_id == fund_id))
                .mappings()
                .first()
            )
            return dict(row) if row else None

    def import_rules(self, path: Path) -> list[tuple[str, str]]:
        configurations = load_configurations(path)
        imported = {}
        with self.engine.begin() as c:
            # Deterministic order prevents competing multi-fund imports from locking in reverse order.
            for fund, configuration in sorted(configurations, key=lambda item: item[0]["cnpj"]):
                fid = discover(c, fund["cnpj"], fund["nome"])
                base = c.scalar(select(funds.c.active_rule).where(funds.c.id == fid).with_for_update())
                current = c.scalar(select(rules.c.configuration).where(rules.c.id == base)) if base else None
                version = (
                    base
                    if current == configuration.to_dict()
                    else publish(c, fid, configuration.to_dict(), base)
                )
                imported[fund["cnpj"]] = (fid, version)
        return [imported[fund["cnpj"]] for fund, _ in configurations]

    def import_registry(self, path: Path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        documents: dict[str, str] = {}
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=";")
            if reader.fieldnames != ["DOC", "SITUACAO_CADASTRAL"]:
                raise ValueError("Cabeçalho cadastral inválido")
            for row in reader:
                doc, situation = normalize_document(row["DOC"]), row["SITUACAO_CADASTRAL"].strip()
                if document_root(doc) is None or not situation:
                    raise ValueError("Cadastro inválido")
                if doc in documents and documents[doc] != situation:
                    raise ValueError("Situações conflitantes para o mesmo CNPJ")
                documents[doc] = situation
        with self.engine.begin() as c:
            c.execute(text("select pg_advisory_xact_lock(:key)"), {"key": REGISTRY_LOCK})
            existing = c.scalar(select(loads.c.id).where(loads.c.sha256 == digest, loads.c.active))
            if existing:
                return existing
            busy = c.scalar(
                select(lots.c.id)
                .where(
                    lots.c.load_id.is_not(None), lots.c.status.not_in(["CONCLUIDO", "CONCLUIDO_COM_ERROS"])
                )
                .limit(1)
            )
            if busy:
                raise AppError(
                    "ESTADO_INVALIDO", "Há lotes vinculados à base atual; recupere-os antes da carga", 409
                )
            c.execute(update(loads).values(active=False))
            existing = c.scalar(select(loads.c.id).where(loads.c.sha256 == digest))
            if existing:
                c.execute(update(loads).where(loads.c.id == existing).values(active=True))
                return existing
            version = str(uuid4())
            c.execute(insert(loads).values(id=version, sha256=digest, count=len(documents), active=True))
            items = list(documents.items())
            for offset in range(0, len(items), 2000):
                c.execute(
                    insert(registry),
                    [
                        {"load_id": version, "document": d, "situation": s}
                        for d, s in items[offset : offset + 2000]
                    ],
                )
            return version

    def situations(self, load_id, documents):
        if not documents:
            return {}
        with self.engine.connect() as c:
            return dict(
                c.execute(
                    select(registry.c.document, registry.c.situation).where(
                        registry.c.load_id == load_id, registry.c.document.in_(documents)
                    )
                ).all()
            )
