from decimal import Decimal
from datetime import timezone
from sqlalchemy import select, func
from antecipe.adapters.schema import files, results, pending, loads
from antecipe.application.errors import AppError
from antecipe.domain.pricing import money


def instant(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def require(c, table, rid):
    row = c.execute(select(table).where(table.c.id == rid)).mappings().first()
    if not row:
        raise AppError("RECURSO_NAO_ENCONTRADO", "Recurso não encontrado", 404)
    return row


def fund_dto(row):
    return {
        "id": row["id"],
        "nome": row["name"],
        "cnpj": row["cnpj"],
        "configurado": bool(row["active_rule"]),
        "versao_regras_atual": row["active_rule"],
    }


def financial(c, condition, total=Decimal(0), definitive=False):
    summary = dict(
        definitivo=definitive,
        total_nominal=money(total),
        total_nominal_aprovado="0.00",
        total_nominal_barrado="0.00",
        total_nominal_erro_dados="0.00",
        total_desconto="0.00",
        total_liquido="0.00",
        aprovadas=0,
        barradas=0,
        erros_dados=0,
    )
    for row in c.execute(
        select(
            results.c.status,
            func.count(),
            func.sum(results.c.nominal),
            func.sum(results.c.discount),
            func.sum(results.c.net),
        )
        .where(condition)
        .group_by(results.c.status)
    ):
        suffix, count_key = {
            "APROVADO": ("aprovado", "aprovadas"),
            "BARRADO": ("barrado", "barradas"),
            None: ("erro_dados", "erros_dados"),
        }[row[0]]
        summary["total_nominal_" + suffix] = money(row[2])
        summary[count_key] = row[1]
        if row[0] == "APROVADO":
            summary["total_desconto"], summary["total_liquido"] = money(row[3]), money(row[4])
    return summary


def file_dto(c, row):
    counts = dict(
        c.execute(
            select(results.c.status, func.count())
            .where(results.c.file_id == row["id"])
            .group_by(results.c.status)
        ).all()
    )
    return {
        "id": row["id"],
        "lote_id": row["lot_id"],
        "client_id": row["client_id"],
        "nome": row["name"],
        "formato": row["format"],
        "ordem": row["position"],
        "aba": row["sheet"],
        "tamanho_bytes": row["size"],
        "sha256": row["sha256"],
        "bytes_recebidos": row["size"] if row["received_at"] else 0,
        "status": row["status"],
        "linhas_total": row["total_lines"],
        "linhas_processadas": row["processed"],
        "aprovadas": counts.get("APROVADO", 0),
        "barradas": counts.get("BARRADO", 0),
        "erros_dados": counts.get(None, 0),
        "recebido_em": instant(row["received_at"]),
        "concluido_em": instant(row["completed_at"]),
        "erro": row["error"],
    }


def lot_dto(c, row):
    from antecipe.adapters.schema import contexts

    fs = c.execute(select(files).where(files.c.lot_id == row["id"])).mappings().all()
    pend = c.execute(select(pending.c.action).where(pending.c.lot_id == row["id"])).scalars().all()
    status = row["status"]
    terminal = status in ["CONCLUIDO", "CONCLUIDO_COM_ERROS"]
    received = sum(bool(f["received_at"]) for f in fs)
    total = c.scalar(select(func.coalesce(func.sum(contexts.c.pl), 0)).where(contexts.c.lot_id == row["id"]))
    return {
        "id": row["id"],
        "nome": row["name"],
        "status": status,
        "criado_em": instant(row["created_at"]),
        "iniciado_em": instant(row["started_at"]),
        "concluido_em": instant(row["completed_at"]),
        "atualizado_em": instant(row["updated_at"]),
        "versao_cadastral": row["load_id"],
        "progresso": {
            "fase": "FINALIZADO"
            if terminal
            else "ANALISE"
            if row["load_id"]
            else "INDEXACAO"
            if status in ["INDEXANDO", "BLOQUEADO"]
            else "AGUARDANDO",
            "arquivos_total": len(fs),
            "arquivos_recebidos": received,
            "arquivos_falhos": sum(f["status"] == "FALHOU" for f in fs),
            "bytes_esperados": sum(f["size"] for f in fs),
            "bytes_recebidos": sum(f["size"] for f in fs if f["received_at"]),
            "linhas_lidas_primeira_passagem": row["lines_read"],
            "linhas_total": row["total_lines"],
            "linhas_processadas": row["processed"],
        },
        "resumo": financial(c, results.c.lot_id == row["id"], total, terminal),
        "quantidade_pendencias": len(pend),
        "acoes": {
            "pode_enviar_arquivos": status == "RECEBENDO",
            "pode_iniciar": status == "RECEBENDO" and received == len(fs),
            "pode_retomar": (status == "BLOQUEADO" and "RECRIAR_LOTE" not in pend)
            or (status == "FALHOU" and bool(row["error"] and row["error"]["retry_permitido"])),
            "precisa_corrigir_configuracao": "CONFIGURAR_FUNDO" in pend or "IMPORTAR_BASE_CADASTRAL" in pend,
            "precisa_recriar_lote": "RECRIAR_LOTE" in pend
            or bool(row["error"] and row["error"]["codigo"] == "LIMITE_LOTE_EXCEDIDO"),
        },
        "erro": row["error"],
    }


def registry_dto(c):
    row = c.execute(select(loads).where(loads.c.active)).mappings().first()
    return {
        "disponivel": bool(row),
        "versao": row["id"] if row else None,
        "sha256": row["sha256"] if row else None,
        "quantidade_cnpjs": row["count"] if row else 0,
        "importado_em": instant(row["created_at"]) if row else None,
    }
