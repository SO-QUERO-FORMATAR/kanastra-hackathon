import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from typing import Any
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import psutil
from openpyxl import Workbook

from antecipe.acceptance.official import reset_test_database
from antecipe.adapters.admin import PgAdmin
from antecipe.adapters.readers import COLUMNS


def generate(directory: Path, count: int, format: str, per_file=250000):
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for start in range(0, count, per_file):
        path = directory / f"notas-{start:06d}.{format.lower()}"
        if format == "XLSX":
            book = Workbook(write_only=True)
            sheet = book.create_sheet("Notas")
            sheet.append(COLUMNS)
        else:
            stream = path.open("w", encoding="utf-8-sig", newline="")
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(COLUMNS)
        for i in range(start, min(start + per_file, count)):
            row = [
                "Sintético",
                "92234400000180",
                "Cedente",
                "10062050000157",
                "Sacado",
                "22144961000102",
                f"{i:012d}",
                "Cheque" if i % 10 == 0 else "Duplicata",
                "100,01",
                "31/10/2026",
                "01/10/2026",
            ]
            if format == "XLSX":
                sheet.append(row)
            else:
                writer.writerow(row)
        if format == "XLSX":
            book.save(path)
        else:
            stream.close()
        paths.append(path)
    return paths


def expected_totals(count):
    barred = (count + 9) // 10
    approved = count - barred
    return {
        "aprovadas": approved,
        "barradas": barred,
        "total_nominal": f"{Decimal(count) * Decimal('100.01'):.2f}",
        "total_desconto": f"{Decimal(approved) * 2:.2f}",
        "total_liquido": f"{Decimal(approved) * Decimal('98.01'):.2f}",
    }


def run(count, format, reuse_input=False):
    root = Path(__file__).resolve().parents[3]
    directory = root / ".local" / f"benchmark-{count}-{format.lower()}"
    paths = (
        sorted(directory.glob("*." + format.lower())) if reuse_input else generate(directory, count, format)
    )
    if not paths:
        raise ValueError("Nenhum arquivo de benchmark existente")
    settings, engine = reset_test_database()
    admin = PgAdmin(engine)
    admin.import_registry(root / "files/cnpj_situacao_mock.csv")
    fid, version = admin.import_rules(root / "files/validadores_antecipe.json")
    # These parameters belong exclusively to this synthetic benchmark fixture.
    config = admin.get_rules(fid)["configuration"]
    for rule in config["validadores"]:
        if rule["codigo"].startswith("CONCENTRACAO_MAXIMA"):
            rule["ativo"] = True
            rule["parametros"]["percentual_maximo"] = "100"
    admin.publish_rules(fid, config, version)
    env = dict(
        os.environ,
        DATABASE_URL=settings.database_url,
        STORAGE_PATH=str(directory / "storage"),
        PYTHONUTF8="1",
    )
    log = (directory / "api.log").open("w", encoding="utf8")
    options: dict[str, Any] = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "antecipe.adapters.http:app",
            "--host",
            "127.0.0.1",
            "--port",
            "18080",
            "--no-access-log",
        ],
        env=env,
        stdout=log,
        stderr=log,
        **options,
    )
    worker = None
    measurements: list[dict[str, Any]] = []
    peak = 0
    try:
        with httpx.Client(base_url="http://127.0.0.1:18080/api/v1", timeout=30) as client:
            for _ in range(100):
                try:
                    client.get("/health/ready").raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.1)
            body: dict[str, Any] = {"nome": f"Benchmark sintético {count} {format}", "arquivos": []}
            for i, path in enumerate(paths):
                body["arquivos"].append(
                    {
                        "client_id": str(uuid4()),
                        "nome": path.name,
                        "formato": format,
                        "ordem": i,
                        "aba": None,
                        "tamanho_bytes": path.stat().st_size,
                        "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
                    }
                )
            response = client.post("/lotes", json=body, headers={"Idempotency-Key": str(uuid4())})
            response.raise_for_status()
            created = response.json()
            lid = created["lote"]["id"]
            ids = [f["id"] for f in created["arquivos"]]
            for path, aid in zip(paths, ids):
                with path.open("rb") as stream:
                    client.post(
                        f"/lotes/{lid}/batches",
                        headers={"Idempotency-Key": str(uuid4())},
                        data={"metadados": json.dumps({"arquivo_ids": [aid]})},
                        files={"arquivos": (path.name, stream)},
                    ).raise_for_status()
            client.post(
                f"/lotes/{lid}/processamento", headers={"Idempotency-Key": str(uuid4())}
            ).raise_for_status()
            start = time.perf_counter()
            worker = subprocess.Popen(
                [sys.executable, "-m", "antecipe.performance.worker_metrics", str(directory / "worker.json")],
                env=env,
                **options,
            )
            process = psutil.Process(worker.pid)
            filters = [
                {},
                {"status": "APROVADO"},
                {"status": "BARRADO"},
                {"motivo": "TIPO_RECEBIVEL"},
                {"tipo": "ERRO_DADOS"},
            ]
            index = 0
            while worker.poll() is None:
                try:
                    peak = max(
                        peak, sum(p.memory_info().rss for p in [process, *process.children(recursive=True)])
                    )
                except psutil.NoSuchProcess:
                    pass
                query = filters[index % len(filters)]
                index += 1
                tick = time.perf_counter()
                response = client.get(f"/arquivos/{ids[-1]}/resultados", params={"limit": 100, **query})
                elapsed = (time.perf_counter() - tick) * 1000
                response.raise_for_status()
                if response.json()["snapshot_ate_sequencia"] > 0:
                    measurements.append({"ms": elapsed, "filter": query, "during_processing": True})
                time.sleep(0.1)
            assert worker.returncode == 0
            seconds = time.perf_counter() - start
            # Warm each representative filter, then collect 100 completed-dataset samples.
            for query in filters:
                client.get(
                    f"/arquivos/{ids[-1]}/resultados", params={"limit": 100, **query}
                ).raise_for_status()
            for i in range(100):
                query = filters[i % len(filters)]
                tick = time.perf_counter()
                client.get(
                    f"/arquivos/{ids[-1]}/resultados", params={"limit": 100, **query}
                ).raise_for_status()
                measurements.append(
                    {"ms": (time.perf_counter() - tick) * 1000, "filter": query, "during_processing": False}
                )
            lot = client.get(f"/lotes/{lid}").json()
            assert lot["status"] == "CONCLUIDO", lot
            assert lot["progresso"]["linhas_processadas"] == count
            for key, value in expected_totals(count).items():
                assert lot["resumo"][key] == value, (key, lot["resumo"])
            ordered = sorted(x["ms"] for x in measurements)
            p95 = ordered[int(0.95 * (len(ordered) - 1))]
            per_filter = {}
            for query in filters:
                timings = sorted(x["ms"] for x in measurements if x["filter"] == query)
                per_filter[str(query)] = timings[int(0.95 * (len(timings) - 1))]
            report = {
                "count": count,
                "format": format,
                "seconds": seconds,
                "peak_worker_rss_bytes": peak,
                "p95_ms": p95,
                "samples": measurements,
                "workers": 1,
                "batch_size": 2000,
                "page_size": 100,
                "http": "uvicorn + httpx TCP localhost",
                "hardware": {
                    "os": platform.platform(),
                    "cpu": platform.processor(),
                    "logical_cpus": psutil.cpu_count(),
                    "ram_bytes": psutil.virtual_memory().total,
                },
                "worker_metrics": json.loads((directory / "worker.json").read_text()),
                "summary": lot["resumo"],
                "p95_by_filter_ms": per_filter,
                "target_passed": max(per_filter.values()) <= 300,
            }
            (root / f"docs/execucao/volume-{count}-{format.lower()}.json").write_text(
                json.dumps(report, indent=2), encoding="utf8"
            )
            print(
                json.dumps(
                    {
                        k: report[k]
                        for k in [
                            "count",
                            "format",
                            "seconds",
                            "peak_worker_rss_bytes",
                            "p95_ms",
                            "target_passed",
                        ]
                    }
                ),
                flush=True,
            )
            assert report["target_passed"], per_filter
    finally:
        if worker and worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=30)
        api.terminate()
        api.wait(timeout=30)
        log.close()
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--format", choices=["CSV", "XLSX"], required=True)
    parser.add_argument("--reuse-input", action="store_true")
    args = parser.parse_args()
    run(args.count, args.format, args.reuse_input)
