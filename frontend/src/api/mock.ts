// Explicit local demonstration only. Never interprets uploaded receivables or calculates decisions.
import examples from "../../contracts/examples.json";
import fixtures from "../../contracts/fixtures.json";
import { ApiError, type DTO } from "./client";
const copy = <T>(v: T): T => JSON.parse(JSON.stringify(v));
function fixture<T>(name: string): T {
  return copy(fixtures.exemplos.find((f) => f.nome === name)!.valor) as T;
}
const pending = fixture<DTO<"PendenciasPageResponse">>("pendencias").itens;
const initial = fixture<DTO<"CriarLoteResponse">>("lote_criado");
const initialLot = copy(initial.lote);
initialLot.status = "CONCLUIDO_COM_ERROS";
initialLot.nome = "Recebíveis · demonstração do contrato";
initialLot.progresso = {
  ...initialLot.progresso,
  fase: "FINALIZADO",
  arquivos_recebidos: 1,
  bytes_recebidos: 1024,
  linhas_total: 3,
  linhas_lidas_primeira_passagem: 3,
  linhas_processadas: 3,
};
initialLot.acoes = {
  pode_enviar_arquivos: false,
  pode_iniciar: false,
  pode_retomar: false,
  precisa_corrigir_configuracao: false,
  precisa_recriar_lote: false,
};
initialLot.resumo = {
  definitivo: true,
  total_nominal: "30000.00",
  total_nominal_aprovado: "10000.00",
  total_nominal_barrado: "10000.00",
  total_nominal_erro_dados: "10000.00",
  total_desconto: "200.00",
  total_liquido: "9800.00",
  aprovadas: 1,
  barradas: 1,
  erros_dados: 1,
};
initial.arquivos[0] = {
  ...initial.arquivos[0]!,
  status: "CONCLUIDO_COM_ERROS",
  bytes_recebidos: 1024,
  linhas_total: 3,
  linhas_processadas: 3,
  aprovadas: 1,
  barradas: 1,
  erros_dados: 1,
};
const lots = new Map<string, DTO<"LoteDTO">>([[initialLot.id, initialLot]]),
  files = new Map<string, DTO<"ArquivoDTO">[]>([
    [initialLot.id, initial.arquivos],
  ]);
const funds: DTO<"FundoDTO">[] = [
  copy(examples.FundoDTO) as DTO<"FundoDTO">,
  pending[0]!.fundo!,
];
const rules = new Map<string, DTO<"RegrasFundoResponse">>([
  [
    funds[0]!.id,
    copy(examples.RegrasFundoResponse) as DTO<"RegrasFundoResponse">,
  ],
]);
const versions = new Map<string, DTO<"RegrasFundoResponse">>(
  [...rules.values()].map((r) => [r.versao, copy(r)]),
);
const replay = new Map<string, unknown>();
function fail(
  status: number,
  message: string,
  code: DTO<"CodigoErro"> = "RECURSO_NAO_ENCONTRADO",
): never {
  throw new ApiError(status, {
    request_id: crypto.randomUUID(),
    erro: {
      codigo: code,
      mensagem: message,
      retry_permitido: false,
      detalhes: [],
      versao_atual: null,
    },
  });
}
function page<T>(items: T[], url: URL) {
  const limit = Number(url.searchParams.get("limit") || 50);
  const start = url.searchParams.get("cursor")
    ? Number(atob(url.searchParams.get("cursor")!))
    : 0;
  return {
    itens: copy(items.slice(start, start + limit)),
    limit,
    proximo_cursor:
      start + limit < items.length ? btoa(String(start + limit)) : null,
  };
}
export async function mockRequest(
  path: string,
  options: RequestInit = {},
): Promise<unknown> {
  const url = new URL(path, "http://demo.local"),
    parts = url.pathname.split("/").filter(Boolean),
    method = options.method || "GET",
    key = `${method}:${url.pathname}:${new Headers(options.headers).get("Idempotency-Key")}`;
  if (method !== "GET" && replay.has(key)) return copy(replay.get(key));
  let result: unknown;
  if (parts[0] === "health") return copy(examples.SaudeResponse);
  if (parts[0] === "capacidades") return copy(examples.CapacidadesResponse);
  if (parts[0] === "cadastro")
    return copy(examples.BaseCadastralStatusResponse);
  if (parts[0] === "fundos") {
    if (parts.length === 1) {
      const busca = (url.searchParams.get("busca") || "").toLowerCase();
      return page(
        funds.filter(
          (f) =>
            (f.nome.toLowerCase().includes(busca) ||
              (f.cnpj.startsWith(busca.replace(/\D/g, "")) &&
                /\d/.test(busca))) &&
            (!url.searchParams.has("configurado") ||
              String(f.configurado) === url.searchParams.get("configurado")),
        ),
        url,
      );
    }
    const f = funds.find((f) => f.id === parts[1]);
    if (!f) fail(404, "Fundo não encontrado.");
    if (method === "PUT") {
      const body = JSON.parse(
        String(options.body),
      ) as DTO<"AtualizarRegrasRequest">;
      if (body.versao_base !== f.versao_regras_atual)
        fail(
          409,
          "As regras foram alteradas. Recarregue e revise.",
          "VERSAO_REGRAS_CONFLITANTE",
        );
      const v = crypto.randomUUID();
      f.configurado = true;
      f.versao_regras_atual = v;
      const r = {
        fundo: copy(f),
        versao: v,
        criada_em: new Date().toISOString(),
        configuracao: body.configuracao,
      };
      rules.set(f.id, r);
      versions.set(v, copy(r));
      result = r;
    } else {
      const r = url.searchParams.has("versao")
        ? versions.get(url.searchParams.get("versao")!)
        : rules.get(f.id);
      if (!r) fail(404, "Configuração não encontrada.");
      return copy(r);
    }
  } else if (parts[0] === "lotes") {
    if (parts.length === 1 && method === "GET")
      return page(
        [...lots.values()]
          .reverse()
          .filter(
            (l) =>
              !url.searchParams.has("status") ||
              l.status === url.searchParams.get("status"),
          )
          .map((l) => ({
            id: l.id,
            nome: l.nome,
            status: l.status,
            criado_em: l.criado_em,
            atualizado_em: l.atualizado_em,
            arquivos_total: l.progresso.arquivos_total,
            linhas_processadas: l.progresso.linhas_processadas,
            total_liquido: l.resumo.total_liquido,
          })),
        url,
      );
    if (parts.length === 1 && method === "POST") {
      const b = JSON.parse(String(options.body)) as DTO<"CriarLoteRequest">;
      const l = copy(initial.lote);
      l.id = crypto.randomUUID();
      l.nome = b.nome;
      l.criado_em = new Date().toISOString();
      l.progresso.arquivos_total = b.arquivos.length;
      l.progresso.bytes_esperados = b.arquivos.reduce(
        (s, f) => s + f.tamanho_bytes,
        0,
      );
      const fs = b.arquivos.map((a) => ({
        ...copy(initial.arquivos[0]!),
        ...a,
        id: crypto.randomUUID(),
        lote_id: l.id,
        status: "AGUARDANDO_UPLOAD" as DTO<"StatusArquivo">,
        bytes_recebidos: 0,
        linhas_total: null,
        linhas_processadas: 0,
        aprovadas: 0,
        barradas: 0,
        erros_dados: 0,
      }));
      lots.set(l.id, l);
      files.set(l.id, fs);
      result = { lote: l, arquivos: fs };
    } else {
      const l = lots.get(parts[1]!);
      if (!l)
        fail(
          404,
          "Lote não encontrado. A demonstração reinicia ao recarregar a página.",
        );
      const fs = files.get(l.id)!;
      if (parts.length === 2) return copy(l);
      if (parts[2] === "arquivos") return page(fs, url);
      if (parts[2] === "pendencias")
        return page(
          l.status === "BLOQUEADO"
            ? pending.filter(
                (p) => !funds.find((f) => f.id === p.fundo?.id)?.configurado,
              )
            : [],
          url,
        );
      if (parts[2] === "resumos-fundos")
        return page(
          l.resumo.definitivo
            ? [
                {
                  ...copy(examples.ResumoFundoDTO),
                  fundo: funds[0],
                  pl: l.resumo.total_nominal,
                  resumo: l.resumo,
                  versao_regras_utilizada: funds[0]!.versao_regras_atual,
                },
              ]
            : [],
          url,
        );
      if (parts[2] === "batches") {
        const b = options.body as FormData;
        const ids = JSON.parse(String(b.get("metadados")))
          .arquivo_ids as string[];
        ids.forEach((id) => {
          const f = fs.find((f) => f.id === id)!;
          f.bytes_recebidos = f.tamanho_bytes;
          f.status = "RECEBIDO";
        });
        l.progresso.arquivos_recebidos = fs.filter(
          (f) => f.status === "RECEBIDO",
        ).length;
        l.acoes.pode_iniciar = l.progresso.arquivos_recebidos === fs.length;
        result = {
          batch_id: crypto.randomUUID(),
          lote_id: l.id,
          recebido_em: new Date().toISOString(),
          arquivos: fs
            .filter((f) => ids.includes(f.id))
            .map((f) => ({
              arquivo_id: f.id,
              client_id: f.client_id,
              sha256: f.sha256,
              bytes_recebidos: f.bytes_recebidos,
              status: "RECEBIDO",
            })),
        };
      }
      if (parts[2] === "processamento") {
        l.status = "NA_FILA";
        l.acoes.pode_iniciar = false;
        l.acoes.pode_retomar = false;
        l.acoes.pode_enviar_arquivos = false;
        result = {
          lote_id: l.id,
          execucao_id: crypto.randomUUID(),
          status: "NA_FILA",
          aceito_em: new Date().toISOString(),
          status_url: `/api/v1/lotes/${l.id}`,
        };
        setTimeout(() => {
          if (funds.some((f) => !f.configurado)) {
            l.status = "BLOQUEADO";
            l.quantidade_pendencias = 1;
            l.acoes.pode_retomar = true;
            l.acoes.precisa_corrigir_configuracao = true;
          } else {
            l.status = "CONCLUIDO_COM_ERROS";
            l.resumo = copy(initialLot.resumo);
            l.progresso = {
              ...l.progresso,
              fase: "FINALIZADO",
              linhas_total: 3,
              linhas_processadas: 3,
            };
            l.quantidade_pendencias = 0;
            l.acoes.precisa_corrigir_configuracao = false;
            fs.forEach((f) => (f.status = "CONCLUIDO_COM_ERROS"));
          }
        }, 600);
      }
    }
  } else if (parts[0] === "arquivos") {
    const f = [...files.values()].flat().find((f) => f.id === parts[1]);
    if (!f) fail(404, "Arquivo não encontrado.");
    if (parts.length === 2) return copy(f);
    const l = lots.get(f.lote_id)!;
    const r = fixture<DTO<"ResultadosPageResponse">>("resultados");
    let items = l.resumo.definitivo
      ? r.itens.map((x) => ({ ...x, lote_id: l.id, arquivo_id: f.id }))
      : [];
    items = items.filter(
      (x) =>
        (!url.searchParams.has("status") ||
          x.status === url.searchParams.get("status")) &&
        (!url.searchParams.has("tipo") ||
          x.tipo === url.searchParams.get("tipo")) &&
        (!url.searchParams.has("motivo") ||
          x.motivos.some((m) => m.codigo === url.searchParams.get("motivo"))),
    );
    return {
      ...page(items, url),
      snapshot_ate_sequencia: l.resumo.definitivo ? 3 : 0,
      arquivo_finalizado: l.resumo.definitivo,
    };
  }
  if (result !== undefined) {
    replay.set(key, copy(result));
    return copy(result);
  }
  fail(404, "Operação indisponível na demonstração.");
}
