from antecipe.domain.entities import Title, Decision, document_root, normalize_document
from antecipe.domain.pricing import money


def title_dto(t: Title) -> dict:
    return {
        "fundo_id": t.fund.id,
        "nome_fundo": t.fund.name,
        "doc_fundo": t.fund.document,
        "nome_cedente": t.seller_name,
        "doc_cedente": normalize_document(t.seller_document),
        "raiz_cedente": document_root(t.seller_document),
        "nome_sacado": t.debtor_name,
        "doc_sacado": normalize_document(t.debtor_document),
        "raiz_sacado": document_root(t.debtor_document),
        "nu_documento": t.number,
        "tipo_recebivel": t.receivable_type,
        "valor_nominal": money(t.nominal),
        "data_aquisicao": t.acquisition_date.isoformat(),
        "data_vencimento_original": t.due_date.isoformat(),
        "prazo_dias": t.days,
    }


def decision_dto(result: Decision, rid: str) -> dict:
    t = result.title
    return {
        "id": rid,
        "lote_id": t.origin.lot_id,
        "arquivo_id": t.origin.file_id,
        "sequencia": t.origin.sequence,
        "linha": t.origin.line,
        "dados_originais": dict(t.original),
        "tipo": "ANALISE",
        "status": "APROVADO" if result.approved else "BARRADO",
        "titulo": title_dto(t),
        "motivos": [
            {
                "codigo": r.code,
                "mensagem": r.message,
                "valor_observado": r.observed,
                "limite_aplicado": r.limit,
            }
            for r in result.reasons
        ],
        "erros_dados": [],
        "desconto": money(result.discount),
        "valor_liquido": money(result.net),
    }
