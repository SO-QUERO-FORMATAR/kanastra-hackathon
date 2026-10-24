from decimal import Decimal
from antecipe.performance.benchmark import generate, expected_totals
from antecipe.adapters.readers import read_rows, parse_row


def test_deterministic_volume_generator_both_formats(tmp_path):
    for fmt in ["CSV", "XLSX"]:
        paths = generate(tmp_path / fmt, 20, fmt, per_file=10)
        assert len(paths) == 2
        rows = [parse_row(raw) for p in paths for _, raw in read_rows(p, fmt)]
        assert len(rows) == 20 and all(not r["errors"] for r in rows)
        assert sum(Decimal(r["nominal"]) for r in rows) == Decimal("2000.20")
        assert sum(r["raw"]["TIPO_RECEBIVEL"] == "Cheque" for r in rows) == 2
    assert expected_totals(20) == {
        "aprovadas": 18,
        "barradas": 2,
        "total_nominal": "2000.20",
        "total_desconto": "36.00",
        "total_liquido": "1764.18",
    }
