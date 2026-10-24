from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, insert, func

from antecipe.application.admin import Admin
from antecipe.adapters.admin import PgAdmin
from antecipe.application.errors import AppError
from antecipe.adapters.schema import registry, loads, lots, rules
from test_t03_config import config_dict


def test_real_registry_import_idempotence_and_batch_lookup(db):
    admin = Admin(PgAdmin(db))
    first = admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    assert admin.import_registry(Path("../files/cnpj_situacao_mock.csv")) == first
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(registry)) == 3041
        assert c.scalar(select(func.count()).select_from(loads)) == 1
    assert admin.situations(first, {"01000171000183", "absent"}) == {"01000171000183": "ATIVA"}


def test_conflict_rollback_and_active_job_protection(db, tmp_path):
    admin = Admin(PgAdmin(db))
    current = admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    path = tmp_path / "bad.csv"
    path.write_text("DOC;SITUACAO_CADASTRAL\n01000171000183;ATIVA\n01000171000183;INAPTA\n", encoding="utf8")
    with pytest.raises(ValueError, match="conflitantes"):
        admin.import_registry(path)
    path.write_text("DOC;SITUACAO_CADASTRAL\n01000171000183;ATIVA\n", encoding="utf8")
    with db.begin() as c:
        c.execute(insert(lots).values(id=str(uuid4()), name="recoverable", status="FALHOU", load_id=current))
    with pytest.raises(AppError, match="vinculados"):
        admin.import_registry(path)
    with db.connect() as c:
        assert c.scalar(select(loads.c.id).where(loads.c.active)) == current


def test_fund_rules_versions_and_no_inheritance(db):
    admin = Admin(PgAdmin(db))
    [(fid, version)] = admin.import_rules(Path("../files/validadores_antecipe.json"))
    other = admin.discover_fund("01392689000100", "Other")
    assert admin.get_rules(other) is None
    newer = admin.publish_rules(fid, config_dict(), version)
    assert newer != version
    with pytest.raises(AppError) as error:
        admin.publish_rules(fid, config_dict(), version)
    assert error.value.code == "VERSAO_REGRAS_CONFLITANTE"
    assert admin.get_rules(fid, version)["id"] == version
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(rules)) == 2
