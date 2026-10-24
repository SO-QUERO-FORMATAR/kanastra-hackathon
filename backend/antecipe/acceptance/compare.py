from collections import Counter


def compare(expected: list[dict], actual: list[dict]) -> dict:
    def normalized(item):
        if "dados_originais" in item:
            return {
                "linha": item["linha"],
                "id": item["dados_originais"]["NU_DOCUMENTO"],
                "status": item["status"],
                "barrado_por": [r["codigo"] for r in item["motivos"]],
            }
        return item

    expected, actual = [normalized(x) for x in expected], [normalized(x) for x in actual]
    target = {x["linha"]: x for x in expected}
    observed = {x["linha"]: x for x in actual}
    differences = []
    for line in sorted(target.keys() & observed.keys()):
        a, b = target[line], observed[line]
        fields = []
        if a["id"] != b["id"]:
            fields.append("id")
        if a["status"] != b["status"]:
            fields.append("status")
        if set(a.get("barrado_por", [])) != set(b.get("barrado_por", [])):
            fields.append("motivos")
        if fields:
            differences.append({"linha": line, "fields": fields, "expected": a, "actual": b})
    return {
        "missing": sorted(target.keys() - observed.keys()),
        "extra": sorted(observed.keys() - target.keys()),
        "divergences": differences,
        "duplicate_expected_lines": sorted(
            k for k, v in Counter(x["linha"] for x in expected).items() if v > 1
        ),
        "duplicate_actual_lines": sorted(k for k, v in Counter(x["linha"] for x in actual).items() if v > 1),
    }
