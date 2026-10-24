import type { components } from "./schema";
export type DTO<K extends keyof components["schemas"]> =
  components["schemas"][K];
export const demo = import.meta.env.VITE_DEMO_MODE === "true";
const base = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
  /\/$/,
  "",
);
export const storagePrefix = `antecipe.${demo ? "demo" : base}.`;
export class ApiError extends Error {
  constructor(
    public status: number,
    public payload: DTO<"ErroResponse"> | null,
    public retryAfter = 0,
  ) {
    super(
      payload?.erro?.mensagem ||
        `Não foi possível concluir a solicitação (${status}).`,
    );
    if (!payload?.erro || !Array.isArray(payload.erro.detalhes))
      this.payload = null;
  }
}
export function query(values: object = {}) {
  const p = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  return p.size ? `?${p}` : "";
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (demo)
    return (await import("./mock")).mockRequest(path, options) as Promise<T>;
  let response: Response;
  try {
    response = await fetch(base + path, options);
  } catch (e) {
    if (options.signal?.aborted) throw e;
    throw new ApiError(0, null);
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const h = response.headers.get("Retry-After");
    throw new ApiError(
      response.status,
      payload,
      h
        ? /^\d+$/.test(h)
          ? Number(h) * 1000
          : Math.max(0, Date.parse(h) - Date.now())
        : 0,
    );
  }
  if (!payload) throw new ApiError(502, null);
  return payload as T;
}
export function mutate<T>(
  path: string,
  method: string,
  key: string,
  body?: unknown,
) {
  return request<T>(path, {
    method,
    headers: {
      "Idempotency-Key": key,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}
export const api = {
  live: () => request<DTO<"SaudeResponse">>("/health/live"),
  ready: () => request<DTO<"SaudeResponse">>("/health/ready"),
  capacidades: () => request<DTO<"CapacidadesResponse">>("/capacidades"),
  cadastro: () =>
    request<DTO<"BaseCadastralStatusResponse">>("/cadastro/status"),
  fundos: (q: DTO<"ListarFundosQuery"> = {}) =>
    request<DTO<"FundosPageResponse">>("/fundos" + query(q)),
  regras: (id: string, versao?: string) =>
    request<DTO<"RegrasFundoResponse">>(
      `/fundos/${id}/regras` + query({ versao }),
    ),
  salvarRegras: (id: string, b: DTO<"AtualizarRegrasRequest">, key: string) =>
    mutate<DTO<"RegrasFundoResponse">>(`/fundos/${id}/regras`, "PUT", key, b),
  lotes: (q: DTO<"ListarLotesQuery"> = {}) =>
    request<DTO<"LotesPageResponse">>("/lotes" + query(q)),
  lote: (id: string, signal?: AbortSignal) =>
    request<DTO<"LoteDTO">>(`/lotes/${id}`, { signal }),
  criar: (b: DTO<"CriarLoteRequest">, key: string) =>
    mutate<DTO<"CriarLoteResponse">>("/lotes", "POST", key, b),
  processar: (id: string, key: string) =>
    mutate<DTO<"ProcessarLoteResponse">>(
      `/lotes/${id}/processamento`,
      "POST",
      key,
    ),
  arquivos: (id: string, cursor?: string) =>
    request<DTO<"ArquivosPageResponse">>(
      `/lotes/${id}/arquivos` + query({ limit: 100, cursor }),
    ),
  arquivo: (id: string) => request<DTO<"ArquivoDTO">>(`/arquivos/${id}`),
  pendencias: (id: string, cursor?: string) =>
    request<DTO<"PendenciasPageResponse">>(
      `/lotes/${id}/pendencias` + query({ limit: 100, cursor }),
    ),
  resumos: (id: string, cursor?: string) =>
    request<DTO<"ResumosFundosPageResponse">>(
      `/lotes/${id}/resumos-fundos` + query({ limit: 100, cursor }),
    ),
  resultados: (id: string, q: DTO<"ListarResultadosQuery">) =>
    request<DTO<"ResultadosPageResponse">>(
      `/arquivos/${id}/resultados` + query(q),
    ),
};
export function multipart(items: { id: string; file: File }[]) {
  const form = new FormData();
  form.append(
    "metadados",
    JSON.stringify({ arquivo_ids: items.map((x) => x.id) }),
  );
  items.forEach((x) => form.append("arquivos", x.file, x.file.name));
  return form;
}
export async function upload(
  id: string,
  items: { id: string; file: File }[],
  key: string,
  onProgress: (n: number) => void,
): Promise<DTO<"EnviarBatchResponse">> {
  const body = multipart(items);
  if (demo) {
    onProgress(1);
    return request(`/lotes/${id}/batches`, {
      method: "POST",
      body,
      headers: { "Idempotency-Key": key },
    });
  }
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${base}/lotes/${id}/batches`);
    xhr.timeout = 120000;
    xhr.setRequestHeader("Idempotency-Key", key);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onerror = xhr.ontimeout = () => reject(new ApiError(0, null));
    xhr.onload = () => {
      let p;
      try {
        p = JSON.parse(xhr.responseText);
      } catch {
        reject(new ApiError(xhr.status, null));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(p);
      else
        reject(
          new ApiError(
            xhr.status,
            p,
            Number(xhr.getResponseHeader("Retry-After") || 0) * 1000,
          ),
        );
    };
    xhr.send(body);
  });
}
