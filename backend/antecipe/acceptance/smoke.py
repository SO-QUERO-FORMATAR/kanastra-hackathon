"""Smoke HTTP/worker da instalação: cria um lote sintético identificado, sem apagar dados."""

import argparse
import hashlib
import json
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx

from antecipe.adapters.contract import validator
from antecipe.adapters.readers import COLUMNS


def run(base):
    name = "Verificação Docker sintética " + str(uuid4())
    rows = [
        [
            "ANTECIPE",
            "92234400000180",
            "Cedente",
            "10062050000157",
            "Sacado",
            "22144961000102",
            f"{name}-{i:03d}",
            "Duplicata de Serviço",
            "10000,00",
            "31/10/2026",
            "01/10/2026",
        ]
        for i in range(12)
    ]
    data = (";".join(COLUMNS) + "\n" + "\n".join(";".join(r) for r in rows) + "\n").encode("utf-8-sig")

    def headers():
        return {"Idempotency-Key": str(uuid4())}

    with httpx.Client(base_url=base, timeout=10) as client:
        for path in ["/health/live", "/health/ready"]:
            client.get(path).raise_for_status()
        manifest = {
            "nome": name,
            "arquivos": [
                {
                    "client_id": str(uuid4()),
                    "nome": "smoke.csv",
                    "formato": "CSV",
                    "tamanho_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "ordem": 0,
                    "aba": None,
                }
            ],
        }
        response = client.post("/lotes", headers=headers(), json=manifest)
        response.raise_for_status()
        created = response.json()
        validator("CriarLoteResponse").validate(created)
        lid, aid = created["lote"]["id"], created["arquivos"][0]["id"]
        response = client.post(
            f"/lotes/{lid}/batches",
            headers=headers(),
            data={"metadados": json.dumps({"arquivo_ids": [aid]})},
            files={"arquivos": ("smoke.csv", data)},
        )
        response.raise_for_status()
        key = headers()
        response = client.post(f"/lotes/{lid}/processamento", headers=key)
        response.raise_for_status()
        assert (
            client.post(f"/lotes/{lid}/processamento", headers=key).headers["Idempotency-Replayed"] == "true"
        )
        deadline = time.monotonic() + 60
        while True:
            response = client.get(f"/lotes/{lid}")
            response.raise_for_status()
            lot = response.json()
            if lot["status"] in ["CONCLUIDO", "CONCLUIDO_COM_ERROS", "BLOQUEADO", "FALHOU"]:
                break
            assert time.monotonic() < deadline, "Worker não concluiu em 60 segundos"
            time.sleep(0.5)
        assert lot["status"] == "CONCLUIDO", lot
        assert lot["progresso"]["linhas_processadas"] == 12
        result = client.get(f"/arquivos/{aid}/resultados", params={"limit": 100}).json()
        validator("ResultadosPageResponse").validate(result)
        assert len(result["itens"]) == 12
        summary = lot["resumo"]
        assert summary["aprovadas"] + summary["barradas"] == 12
        assert Decimal(summary["total_nominal"]) == Decimal("120000.00")
        assert Decimal(summary["total_nominal_aprovado"]) == Decimal(summary["total_desconto"]) + Decimal(
            summary["total_liquido"]
        )
        report = {
            "base_url": base,
            "lote": lot,
            "resultados": result,
            "observacao": "Configuração fornecida; exposição anterior é preservada. Sem gabarito.",
        }
        report_path = Path(__file__).resolve().parents[3] / "docs/execucao/docker-smoke.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
        print(json.dumps({"status": lot["status"], "lote_id": lid, "resumo": summary}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    run(parser.parse_args().base_url)
