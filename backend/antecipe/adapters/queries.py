from decimal import Decimal, localcontext
from sqlalchemy import select, func, tuple_, cast, Text, or_, ColumnElement
from antecipe.adapters.schema import funds, rules, lots, files, pending, contexts, results
from antecipe.adapters.views import require, fund_dto, file_dto, lot_dto, instant, financial
from antecipe.adapters.cursor import Cursor
from antecipe.domain.entities import normalize_document
from antecipe.domain.config import Configuration
from antecipe.domain.pricing import money
from antecipe.application.errors import AppError


class Queries:
    def __init__(self, engine, secret):
        self.engine, self.cursor = engine, Cursor(secret)

    def page(self, c, query, columns, q, scope, render, descending=False, revision=None):
        limit = q.get("limit", 50)
        binding = {
            "scope": scope,
            "query": {k: v for k, v in q.items() if k != "cursor"},
            "limit": limit,
            "revision": revision,
        }
        cols = [cast(col, Text) for col in columns]
        order = [col.desc() if descending else col for col in cols]
        data = self.cursor.decode(q["cursor"], binding) if "cursor" in q else None
        ceiling = data.get("ceiling") if data else None
        if descending and not data:
            top = c.execute(query.with_only_columns(*cols).order_by(*order).limit(1)).first()
            ceiling = list(top) if top else None
        if ceiling:
            query = query.where(tuple_(*cols) <= tuple(ceiling))
        if data:
            query = query.where(
                tuple_(*cols) < tuple(data["last"]) if descending else tuple_(*cols) > tuple(data["last"])
            )
        rows = (
            c.execute(
                query.add_columns(*[col.label("_key" + str(i)) for i, col in enumerate(cols)])
                .order_by(*order)
                .limit(limit + 1)
            )
            .mappings()
            .all()
        )
        selected = rows[:limit]
        token = None
        if len(rows) > limit:
            token = self.cursor.encode(
                {
                    "binding": binding,
                    "last": [selected[-1]["_key" + str(i)] for i in range(len(cols))],
                    "ceiling": ceiling,
                }
            )
        return {"itens": [render(r) for r in selected], "proximo_cursor": token, "limit": limit}

    def get(self, operation, paths, q):
        with self.engine.connect() as c:
            if operation == "listarResultados":
                return self.result_page(c, paths["arquivo_id"], q)
            if operation == "consultarLote":
                return lot_dto(c, require(c, lots, paths["lote_id"]))
            if operation == "consultarArquivo":
                return file_dto(c, require(c, files, paths["arquivo_id"]))
            if operation == "consultarRegrasFundo":
                fund = require(c, funds, paths["fundo_id"])
                version = q.get("versao") or fund["active_rule"]
                rule = (
                    c.execute(select(rules).where(rules.c.id == version, rules.c.fund_id == fund["id"]))
                    .mappings()
                    .first()
                )
                if not rule:
                    raise AppError("RECURSO_NAO_ENCONTRADO", "Configuração não encontrada", 404)
                return {
                    "fundo": fund_dto(fund),
                    "versao": rule["id"],
                    "criada_em": instant(rule["created_at"]),
                    "configuracao": rule["configuration"],
                }
            if operation == "listarFundos":
                query = select(funds)
                if "configurado" in q:
                    query = query.where(
                        funds.c.active_rule.is_not(None)
                        if q["configurado"]
                        else funds.c.active_rule.is_(None)
                    )
                if "busca" in q:
                    search = q["busca"]
                    doc = normalize_document(search)
                    condition: ColumnElement[bool] = funds.c.name.ilike(
                        "%" + search.replace("%", "\\%").replace("_", "\\_") + "%"
                    )
                    if doc.isascii() and doc.isdigit():
                        condition = or_(condition, funds.c.cnpj.startswith(doc))
                    query = query.where(condition)
                return self.page(c, query, [funds.c.cnpj, funds.c.id], q, operation, fund_dto)
            if operation == "listarLotes":
                query = select(lots)
                if "status" in q:
                    query = query.where(lots.c.status == q["status"])

                def render(row):
                    dto = lot_dto(c, row)
                    return {
                        **{k: dto[k] for k in ["id", "nome", "status", "criado_em", "atualizado_em"]},
                        "arquivos_total": dto["progresso"]["arquivos_total"],
                        "linhas_processadas": row["processed"],
                        "total_liquido": dto["resumo"]["total_liquido"],
                    }

                return self.page(
                    c, query, [lots.c.created_at, lots.c.id], q, operation, render, descending=True
                )
            lid = paths.get("lote_id")
            if lid:
                lot = require(c, lots, lid)
                if operation == "listarArquivosLote":
                    return self.page(
                        c,
                        select(files).where(files.c.lot_id == lid),
                        [func.lpad(cast(files.c.position, Text), 3, "0"), files.c.id],
                        q,
                        operation + lid,
                        lambda r: file_dto(c, r),
                    )
                if operation == "listarPendenciasLote":

                    def render_pending(r):
                        return {
                            "codigo": r["code"],
                            "mensagem": r["message"],
                            "fundo": fund_dto(require(c, funds, r["fund_id"])) if r["fund_id"] else None,
                            "arquivo_id": r["file_id"],
                            "linha": r["line"],
                            "campo": r["field"],
                            "acao": r["action"],
                        }

                    return self.page(
                        c,
                        select(pending).where(pending.c.lot_id == lid),
                        [
                            pending.c.code,
                            func.coalesce(cast(pending.c.fund_id, Text), ""),
                            func.coalesce(cast(pending.c.file_id, Text), ""),
                            func.coalesce(func.lpad(cast(pending.c.line, Text), 10, "0"), ""),
                            pending.c.id,
                        ],
                        q,
                        operation + lid,
                        render_pending,
                        revision=lot["pending_revision"],
                    )
                if operation == "listarResumosFundos":
                    query = (
                        select(contexts, funds.c.cnpj, funds.c.name, funds.c.active_rule)
                        .join(funds)
                        .where(contexts.c.lot_id == lid)
                    )

                    def render_context(r):
                        limits: dict[str, str | None] = {"SACADO": None, "CEDENTE": None}
                        if r["rule_id"]:
                            cfg = Configuration.from_dict(
                                c.scalar(select(rules.c.configuration).where(rules.c.id == r["rule_id"]))
                            )
                            for side in limits:
                                rule = cfg.rule("CONCENTRACAO_MAXIMA_" + side)
                                if rule.active:
                                    with localcontext() as ctx:
                                        ctx.prec = 38
                                        limits[side] = money(
                                            r["pl"] * Decimal(rule.parameters["percentual_maximo"]) / 100
                                        )
                        return {
                            "fundo": fund_dto({**r, "id": r["fund_id"]}),
                            "versao_regras_utilizada": r["rule_id"],
                            "pl": money(r["pl"]),
                            "limite_sacado": limits["SACADO"],
                            "limite_cedente": limits["CEDENTE"],
                            "resumo": financial(
                                c,
                                (results.c.lot_id == lid) & (results.c.fund_id == r["fund_id"]),
                                r["pl"],
                                lot["status"] in ["CONCLUIDO", "CONCLUIDO_COM_ERROS"],
                            ),
                        }

                    return self.page(
                        c, query, [funds.c.cnpj, contexts.c.fund_id], q, operation + lid, render_context
                    )
            raise AppError("RECURSO_NAO_ENCONTRADO", "Operação não encontrada", 404)

    def result_page(self, c, aid, q):
        from antecipe.adapters.schema import reasons

        file = require(c, files, aid)
        if (q.get("tipo") == "ERRO_DADOS" and ("status" in q or "motivo" in q)) or (
            q.get("status") == "APROVADO" and "motivo" in q
        ):
            raise AppError("VALIDACAO_REQUISICAO", "Filtros incompatíveis")
        limit = q.get("limit", 50)
        binding = {
            "arquivo": aid,
            "limit": limit,
            "filtros": {k: q[k] for k in ["status", "motivo", "tipo"] if k in q},
        }
        cursor = self.cursor.decode(q["cursor"], binding) if "cursor" in q else None
        ceiling = (
            cursor["ceiling"]
            if cursor
            else c.scalar(
                select(func.coalesce(func.max(results.c.sequence), 0)).where(results.c.file_id == aid)
            )
        )
        last = cursor["last"] if cursor else 0
        query = select(results.c.payload, results.c.sequence).where(
            results.c.file_id == aid, results.c.sequence > last, results.c.sequence <= ceiling
        )
        if "status" in q:
            query = query.where(results.c.status == q["status"])
        if "tipo" in q:
            query = query.where(results.c.type == q["tipo"])
        order: ColumnElement = results.c.sequence
        if "motivo" in q:
            # A reason always belongs to an ANALISE/BARRADO result. Bound the
            # indexed reason page before fetching JSON payloads, even when table
            # statistics lag behind the concurrently committing worker.
            page = (
                select(reasons.c.result_id, reasons.c.sequence)
                .where(
                    reasons.c.file_id == aid,
                    reasons.c.code == q["motivo"],
                    reasons.c.sequence > last,
                    reasons.c.sequence <= ceiling,
                )
                .order_by(reasons.c.sequence)
                .limit(limit + 1)
                .subquery()
            )
            query = select(results.c.payload, results.c.sequence).join(page, page.c.result_id == results.c.id)
            order = page.c.sequence
        rows = c.execute(query.order_by(order).limit(limit + 1)).all()
        token = (
            self.cursor.encode({"binding": binding, "last": rows[limit - 1].sequence, "ceiling": ceiling})
            if len(rows) > limit
            else None
        )
        return {
            "itens": [r.payload for r in rows[:limit]],
            "limit": limit,
            "proximo_cursor": token,
            "snapshot_ate_sequencia": ceiling,
            "arquivo_finalizado": file["status"] in ["CONCLUIDO", "CONCLUIDO_COM_ERROS", "FALHOU"],
        }
