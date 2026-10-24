import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import insert, select, update, func

from antecipe.adapters.schema import lots, files, executions
from antecipe.adapters.contract import validate
from antecipe.adapters.idempotency import execute
from antecipe.adapters.views import lot_dto, file_dto, require
from antecipe.application.errors import AppError

MAX_BYTES = 67108864


class LotStore:
    def __init__(self, engine, storage: Path):
        self.engine, self.storage = engine, storage

    def create(self, body, key):
        validate("CriarLoteRequest", body)
        items = body["arquivos"]
        if sorted(a["ordem"] for a in items) != list(range(len(items))) or len(
            {a["client_id"] for a in items}
        ) != len(items):
            raise AppError("VALIDACAO_REQUISICAO", "Ordem deve ser contígua e client_id único")
        for a in items:
            if not a["nome"].lower().endswith("." + a["formato"].lower()) or (
                a["formato"] == "CSV" and a["aba"] is not None
            ):
                raise AppError("VALIDACAO_REQUISICAO", "Formato, nome ou aba incompatível")
        with self.engine.begin() as c:

            def action():
                lid = str(uuid4())
                c.execute(insert(lots).values(id=lid, name=body["nome"]))
                c.execute(
                    insert(files),
                    [
                        dict(
                            id=str(uuid4()),
                            lot_id=lid,
                            client_id=a["client_id"],
                            position=a["ordem"],
                            name=a["nome"],
                            format=a["formato"],
                            sheet=a["aba"],
                            size=a["tamanho_bytes"],
                            sha256=a["sha256"],
                        )
                        for a in items
                    ],
                )
                return {
                    "lote": lot_dto(c, require(c, lots, lid)),
                    "arquivos": [
                        file_dto(c, r)
                        for r in c.execute(
                            select(files).where(files.c.lot_id == lid).order_by(files.c.position)
                        ).mappings()
                    ],
                }

            return execute(c, "POST /lotes", key, body, 201, action)

    def upload(self, lid, ids, contents, key):
        if (
            len(ids) > 3
            or len(contents) > 3
            or sum(map(len, contents)) > MAX_BYTES
            or any(len(b) > MAX_BYTES for b in contents)
        ):
            raise AppError("LIMITE_UPLOAD_EXCEDIDO", "Máximo três arquivos e 64 MiB por batch", 413)
        validate("BatchMetadadosDTO", {"arquivo_ids": ids})
        if len(ids) != len(contents):
            raise AppError("UPLOAD_INCOMPLETO", "Partes e IDs não correspondem", 422)
        hashes = [hashlib.sha256(data).hexdigest() for data in contents]
        with self.engine.begin() as c:

            def action():
                lot = c.execute(select(lots).where(lots.c.id == lid).with_for_update()).mappings().first()
                if not lot:
                    raise AppError("RECURSO_NAO_ENCONTRADO", "Lote não encontrado", 404)
                if lot["status"] != "RECEBENDO":
                    raise AppError("ESTADO_INVALIDO", "Manifesto selado", 409)
                selected = []
                for aid, data, digest in zip(ids, contents, hashes):
                    row = (
                        c.execute(select(files).where(files.c.id == aid, files.c.lot_id == lid))
                        .mappings()
                        .first()
                    )
                    if not row:
                        raise AppError("ARQUIVO_FORA_MANIFESTO", "Arquivo fora do manifesto", 409)
                    if row["received_at"]:
                        raise AppError("ARQUIVO_JA_RECEBIDO", "Arquivo já recebido", 409)
                    if len(data) != row["size"] or digest != row["sha256"]:
                        raise AppError("INTEGRIDADE_ARQUIVO", "Tamanho ou SHA-256 divergente", 422)
                    if row["format"] == "XLSX" and not data.startswith(b"PK"):
                        raise AppError("INTEGRIDADE_ARQUIVO", "Container XLSX inválido", 422)
                    selected.append(row)
                directory = self.storage / lid
                directory.mkdir(parents=True, exist_ok=True)
                now = datetime.now(timezone.utc)
                for row, data in zip(selected, contents):
                    target = directory / row["id"]
                    temporary = directory / (row["id"] + "." + str(uuid4()) + ".tmp")
                    try:
                        with temporary.open("xb") as stream:
                            stream.write(data)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, target)
                    finally:
                        temporary.unlink(missing_ok=True)
                    c.execute(
                        update(files)
                        .where(files.c.id == row["id"])
                        .values(path=str(target.resolve()), status="RECEBIDO", received_at=now)
                    )
                c.execute(update(lots).where(lots.c.id == lid).values(updated_at=func.now()))
                return {
                    "batch_id": str(uuid4()),
                    "lote_id": lid,
                    "recebido_em": now.isoformat().replace("+00:00", "Z"),
                    "arquivos": [
                        {
                            "arquivo_id": r["id"],
                            "client_id": r["client_id"],
                            "sha256": r["sha256"],
                            "bytes_recebidos": r["size"],
                            "status": "RECEBIDO",
                        }
                        for r in selected
                    ],
                }

            return execute(
                c, f"POST /lotes/{lid}/batches", key, {"arquivo_ids": ids, "hashes": hashes}, 201, action
            )

    def enqueue(self, lid, key):
        with self.engine.begin() as c:

            def action():
                row = c.execute(select(lots).where(lots.c.id == lid).with_for_update()).mappings().first()
                if not row:
                    raise AppError("RECURSO_NAO_ENCONTRADO", "Lote não encontrado", 404)
                dto = lot_dto(c, row)
                if row["status"] == "RECEBENDO" and not dto["acoes"]["pode_iniciar"]:
                    raise AppError("UPLOAD_INCOMPLETO", "Envie todos os arquivos", 409)
                if not (dto["acoes"]["pode_iniciar"] or dto["acoes"]["pode_retomar"]):
                    raise AppError("ESTADO_INVALIDO", "Lote não pode ser iniciado/retomado", 409)
                eid = str(uuid4())
                now = datetime.now(timezone.utc)
                c.execute(insert(executions).values(id=eid, lot_id=lid))
                c.execute(
                    update(lots).where(lots.c.id == lid).values(status="NA_FILA", error=None, updated_at=now)
                )
                return {
                    "lote_id": lid,
                    "execucao_id": eid,
                    "status": "NA_FILA",
                    "aceito_em": now.isoformat().replace("+00:00", "Z"),
                    "status_url": f"/api/v1/lotes/{lid}",
                }

            return execute(c, f"POST /lotes/{lid}/processamento", key, None, 202, action)
