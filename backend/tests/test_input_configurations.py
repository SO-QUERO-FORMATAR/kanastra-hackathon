import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from antecipe.acceptance.inputs import read_input
from antecipe.acceptance.inputs_run import process_input
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.config_import import load_configurations
from antecipe.adapters.lot_store import LotStore
from antecipe.adapters.schema import funds, rules, files
from antecipe.cli import main
from antecipe.settings import Settings
from test_t11_readers import COLUMNS, csv_bytes, values
from test_t12_uploads import manifest


def configuration(cnpj="92.234.400/0001-80", minimum=100, rate=2):
    raw = json.loads(Path("../files/validadores_antecipe.json").read_text(encoding="utf-8-sig"))
    raw["fundo"] = {"nome": "Fundo " + cnpj, "cnpj": cnpj}
    for rule in raw["validadores"]:
        rule["ativo"] = rule["codigo"] == "VALOR_MINIMO"
        if rule["codigo"] == "VALOR_MINIMO":
            rule["parametros"]["valor_minimo"] = minimum
    raw["precificacao"]["taxa_mensal_percentual"] = rate
    return raw


def write_config(tmp_path, payload):
    path = tmp_path / "parâmetros novos.json"
    path.write_text(json.dumps(payload), encoding="utf-8-sig")
    return path


@pytest.mark.parametrize("as_array", [False, True])
def test_single_object_and_single_element_array(tmp_path, as_array):
    raw = configuration()
    [(fund, config)] = load_configurations(write_config(tmp_path, [raw] if as_array else raw))
    assert fund["cnpj"] == "92234400000180"
    assert config.to_dict()["precificacao"]["taxa_mensal_percentual"] == "2"
    assert config.rule("CONCENTRACAO_MAXIMA_CEDENTE").parameters["agrupamento"] == "RAIZ_CNPJ"


@pytest.mark.parametrize("payload", [[], None, True, 1, "config", [None], [[]], [{}]])
def test_invalid_roots_and_items(tmp_path, payload):
    with pytest.raises(ValueError, match="configuracoes"):
        load_configurations(write_config(tmp_path, payload))


@pytest.mark.parametrize(
    "field,value,location",
    [
        ("fundo", {"nome": "X", "cnpj": 92234400000180}, "fundo.cnpj"),
        ("fundo", {"nome": " ", "cnpj": "92234400000180"}, "fundo.nome"),
        ("fundo", {"nome": "X", "cnpj": "ABC"}, "fundo.cnpj"),
        ("validadores", None, "validadores"),
        ("validadores", [{"codigo": [], "parametros": {}}], "validadores"),
        ("precificacao", {}, "precificacao"),
    ],
)
def test_error_identifies_second_item_and_field(tmp_path, field, value, location):
    other = configuration("01392689000100")
    other[field] = value
    with pytest.raises(ValueError) as error:
        load_configurations(write_config(tmp_path, [configuration(), other]))
    assert "configuracoes[1]" in str(error.value) and location in str(error.value)


def test_duplicate_normalized_cnpj_and_malformed_json(tmp_path):
    with pytest.raises(ValueError, match=r"configuracoes\[1\].fundo.cnpj: CNPJ repetido"):
        load_configurations(write_config(tmp_path, [configuration(), configuration("92234400000180")]))
    path = tmp_path / "bad.json"
    path.write_text("[{", encoding="utf8")
    with pytest.raises(ValueError, match="JSON inválido"):
        load_configurations(path)


def test_bulk_import_order_replay_and_independent_versions(db, tmp_path):
    admin = PgAdmin(db)
    payload = [configuration(), configuration("01392689000100")]
    path = write_config(tmp_path, payload)
    first = admin.import_rules(path)
    assert len(first) == 2
    assert admin.import_rules(path) == first
    assert admin.import_rules(write_config(tmp_path, list(reversed(payload)))) == list(reversed(first))
    with db.connect() as c:
        assert [c.scalar(select(funds.c.cnpj).where(funds.c.id == fid)) for fid, _ in first] == [
            "92234400000180",
            "01392689000100",
        ]
        assert c.scalar(select(func.count()).select_from(rules)) == 2
    payload[1]["precificacao"]["taxa_mensal_percentual"] = 3
    updated = admin.import_rules(write_config(tmp_path, payload))
    assert updated[0] == first[0]
    assert updated[1][0] == first[1][0] and updated[1][1] != first[1][1]
    assert admin.get_rules(*first[1])["configuration"]["precificacao"]["taxa_mensal_percentual"] == "2"


def test_invalid_item_does_not_create_or_update_any_fund(db, tmp_path):
    admin = PgAdmin(db)
    first = admin.import_rules(write_config(tmp_path, configuration()))
    changed = configuration(rate=3)
    with pytest.raises(ValueError):
        admin.import_rules(write_config(tmp_path, [changed, {"fundo": {}}]))
    assert admin.get_rules(first[0][0])["id"] == first[0][1]
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(funds)) == 1
        assert c.scalar(select(func.count()).select_from(rules)) == 1


def test_database_failure_rolls_back_whole_import(db, tmp_path, monkeypatch):
    from antecipe.adapters import admin as module

    original = module.publish
    calls = []

    def fail_second(*args):
        calls.append(args[1])
        if len(calls) == 2:
            raise RuntimeError("simulated persistence failure")
        return original(*args)

    monkeypatch.setattr(module, "publish", fail_second)
    with pytest.raises(RuntimeError, match="persistence"):
        PgAdmin(db).import_rules(write_config(tmp_path, [configuration(), configuration("01392689000100")]))
    with db.connect() as c:
        assert c.scalar(select(func.count()).select_from(funds)) == 0
        assert c.scalar(select(func.count()).select_from(rules)) == 0


@pytest.mark.parametrize("count", [1, 2])
def test_cli_import_single_and_multiple_configs(db, tmp_path, monkeypatch, capsys, count):
    monkeypatch.setenv("DATABASE_URL", db.url.render_as_string(hide_password=False))
    payload = [configuration(), configuration("01392689000100")][:count]
    path = write_config(tmp_path, payload[0] if count == 1 else payload)
    main(["import-rules", str(path)])
    output = json.loads(capsys.readouterr().out)
    items = [output] if count == 1 else output["configuracoes"]
    assert len(items) == count
    assert all(PgAdmin(db).get_rules(item["fundo_id"])["id"] == item["versao"] for item in items)


def test_cli_invalid_array_has_actionable_error(db, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", db.url.render_as_string(hide_password=False))
    with pytest.raises(SystemExit) as error:
        main(["import-rules", str(write_config(tmp_path, []))])
    assert error.value.code == 2
    events = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    failure = next(event for event in events if event["event"]["name"] == "cli.command.failed")
    assert failure["error"]["error_code"] == "CONFIGURACAO_INVALIDA"


@pytest.mark.parametrize("name", ["notas.csv", "Notas Outubro 2026.CSV", "operações (2).csv", "outro.XLSX"])
@pytest.mark.parametrize("nominal,expected_net", [("10000,00", "9800.00"), ("25000,00", "24500.00")])
def test_variable_filenames_and_contents_through_http_worker(db, tmp_path, name, nominal, expected_net):
    admin = PgAdmin(db)
    admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    admin.import_rules(write_config(tmp_path, configuration()))
    row = values()
    row[8] = nominal
    path = tmp_path / name
    if path.suffix.lower() == ".csv":
        path.write_bytes(csv_bytes([row]))
    else:
        book = Workbook()
        book.active.append(COLUMNS)
        book.active.append(row)
        book.save(path)
        book.close()
    settings = Settings(database_url=db.url.render_as_string(hide_password=False), storage=tmp_path / "store")
    report = process_input(settings, db, path)
    assert report["lot"]["status"] == "CONCLUIDO"
    [result] = report["results"]
    assert result["status"] == "APROVADO" and result["valor_liquido"] == expected_net
    assert report["confirmed_approvals"] == 1
    with db.connect() as c:
        stored = c.execute(select(files)).mappings().one()
        assert stored["name"] == name
        assert Path(stored["path"]).name == stored["id"]
        assert Path(stored["path"]).read_bytes() == path.read_bytes()


def test_same_filename_does_not_overwrite_distinct_uploads(db, tmp_path):
    data = csv_bytes()
    other = values()
    other[6] = "other-note"
    other_data = csv_bytes([other])
    body = manifest(data, 2)
    for item in body["arquivos"]:
        item["nome"] = "notas.csv"
    body["arquivos"][1].update(tamanho_bytes=len(other_data), sha256=hashlib.sha256(other_data).hexdigest())
    store = LotStore(db, tmp_path)
    created, _ = store.create(body, str(uuid4()))
    ids = [item["id"] for item in created["arquivos"]]
    store.upload(created["lote"]["id"], ids, [data, other_data], str(uuid4()))
    with db.connect() as c:
        paths = list(c.scalars(select(files.c.path).order_by(files.c.position)))
    assert paths[0] != paths[1]
    assert [Path(p).read_bytes() for p in paths] == [data, other_data]


@pytest.mark.parametrize("missing", [False, True])
def test_notes_use_only_their_own_fund_configuration(db, tmp_path, missing):
    admin = PgAdmin(db)
    admin.import_registry(Path("../files/cnpj_situacao_mock.csv"))
    payload = [configuration(), configuration("01.392.689/0001-00", minimum=15000, rate=3)]
    imported = admin.import_rules(write_config(tmp_path, payload[:1] if missing else payload))
    rows = [values() for _ in range(3)]
    for index, row in enumerate(rows):
        row[6] = f"note-{index}"
    rows[1][1] = rows[2][1] = "01392689000100"
    rows[2][8] = "20000,00"
    path = tmp_path / "vários fundos.csv"
    path.write_bytes(csv_bytes(rows))
    settings = Settings(database_url=db.url.render_as_string(hide_password=False), storage=tmp_path / "store")
    report = process_input(settings, db, path)
    if missing:
        assert report["lot"]["status"] == "BLOQUEADO"
        assert report["results"] == []
        assert any(p["codigo"] == "FUNDO_SEM_REGRAS" for p in report["pending"])
    else:
        assert report["lot"]["status"] == "CONCLUIDO"
        first, second, third = report["results"]
        assert first["titulo"]["fundo_id"] == imported[0][0]
        assert second["titulo"]["fundo_id"] == third["titulo"]["fundo_id"] == imported[1][0]
        assert [r["status"] for r in report["results"]] == ["APROVADO", "BARRADO", "APROVADO"]
        assert first["valor_liquido"] == "9800.00" and third["valor_liquido"] == "19400.00"
        assert [r["codigo"] for r in second["motivos"]] == ["VALOR_MINIMO"]


def test_zip_names_member_selection_and_ambiguity(tmp_path):
    path = tmp_path / "novo lote.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("pasta/notas RENOMEADAS.CSV", csv_bytes())
        archive.writestr("README.txt", "Informações")
    assert read_input(path) == ("notas RENOMEADAS.CSV", csv_bytes())
    with ZipFile(path, "a") as archive:
        archive.writestr("outras.csv", b"other content")
    with pytest.raises(ValueError, match="exatamente um"):
        read_input(path)
    assert read_input(path, "outras.csv") == ("outras.csv", b"other content")
    with pytest.raises(ValueError, match="exatamente um"):
        read_input(path, "missing.csv")


def test_configuration_parsing_preserves_input_objects():
    from antecipe.adapters.config_import import parse_rules

    raw = configuration()
    original = deepcopy(raw)
    parse_rules(raw, "configuracoes[0]")
    assert raw == original


@pytest.mark.parametrize("expected_status", [None, "APROVADO", "BARRADO"])
def test_generic_runner_uses_renamed_zip_and_optional_reference(db, tmp_path, monkeypatch, expected_status):
    from antecipe.acceptance import inputs_run

    settings = Settings(database_url=db.url.render_as_string(hide_password=False), storage=tmp_path / "store")
    monkeypatch.setattr(inputs_run, "reset_test_database", lambda: (settings, db))
    path = tmp_path / "input diferente.ZIP"
    with ZipFile(path, "w") as archive:
        archive.writestr("subpasta/novo nome.csv", csv_bytes())
    report_path = tmp_path / "resultado.json"
    args = [
        "--input",
        str(path),
        "--rules",
        str(write_config(tmp_path, [configuration()])),
        "--registry",
        "../files/cnpj_situacao_mock.csv",
        "--report",
        str(report_path),
    ]
    if expected_status:
        expected = tmp_path / "gabarito.json"
        expected.write_text(json.dumps([{"linha": 2, "id": values()[6], "status": expected_status}]))
        args += ["--expected", str(expected)]
    if expected_status == "BARRADO":
        with pytest.raises(SystemExit) as error:
            inputs_run.main(args)
        assert error.value.code == 1
    else:
        inputs_run.main(args)
    report = json.loads(report_path.read_text(encoding="utf8"))
    assert report["input"]["name"] == "novo nome.csv"
    assert report["lot"]["status"] == "CONCLUIDO"
    assert report["results"][0]["valor_liquido"] == "9800.00"
    if expected_status:
        assert bool(report["comparison"]["divergences"]) == (expected_status == "BARRADO")
    else:
        assert "comparison" not in report


def test_audits_accept_variable_paths_and_configuration_array(tmp_path, capsys):
    from antecipe.acceptance.audit import run

    rows = [values(), values()]
    rows[1][1] = "01392689000100"
    stock = tmp_path / "notas para auditoria.csv"
    stock.write_bytes(csv_bytes(rows))
    expected = tmp_path / "referencia.json"
    expected.write_text(
        json.dumps([{"linha": line, "id": values()[6], "status": "APROVADO"} for line in (2, 3)])
    )
    rules_path = write_config(tmp_path, [configuration(), configuration("01392689000100")])
    registry_path = tmp_path / "cadastro renomeado.csv"
    registry_path.write_bytes(Path("../files/cnpj_situacao_mock.csv").read_bytes())
    report_path = tmp_path / "divergencias.jsonl"
    run(stock, expected, registry_path, rules_path, report_path)
    report = json.loads(capsys.readouterr().out)
    assert report["aprovacoes_repetidas"] == 1
    [entry] = [json.loads(line) for line in report_path.read_text(encoding="utf8").splitlines()]
    assert entry["arquivo"] == stock.name and entry["configuracao_sha256"] is not None
    assert entry["regra"] == "NOTA_DUPLICADA" and entry["motor"] == "NAO_EXECUTADO"
    summary_path = tmp_path / "auditoria.json"
    result = subprocess.run(
        [
            sys.executable,
            "../scripts/auditar_insumos.py",
            "--input",
            str(stock),
            "--expected",
            str(expected),
            "--rules",
            str(rules_path),
            "--registry",
            str(registry_path),
            "--report",
            str(summary_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(summary_path.read_text(encoding="utf8"))
    assert summary["linhas_estoque"] == 2
    assert all(fund["configurado_no_json"] for fund in summary["fundos"].values())
    assert set(summary["regras"]) == {"92234400000180", "01392689000100"}
