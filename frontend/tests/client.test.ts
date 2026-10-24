import { describe, it, expect, vi, afterEach } from "vitest";
import { api, query, multipart, ApiError } from "../src/api/client";
import { money, batches, sha256 } from "../src/utils";
afterEach(() => vi.unstubAllGlobals());
describe("integração HTTP", () => {
  it("omite opcionais nulos sem perder false", () =>
    expect(query({ cursor: null, status: undefined, configurado: false })).toBe(
      "?configurado=false",
    ));
  it("envia processamento sem corpo e preserva chave no retry", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    await api.processar("id", "same-key");
    fetch.mockResolvedValue(new Response("{}"));
    await api.processar("id", "same-key");
    for (const call of fetch.mock.calls) {
      expect(call[1].body).toBeUndefined();
      expect(call[1].headers).toEqual({ "Idempotency-Key": "same-key" });
    }
  });
  it("multipart correlaciona IDs e permite nomes repetidos", () => {
    const a = new File(["a"], "igual.csv"),
      b = new File(["b"], "igual.csv");
    const form = multipart([
      { id: "1", file: a },
      { id: "2", file: b },
    ]);
    expect(form.get("metadados")).toBe('{"arquivo_ids":["1","2"]}');
    expect(form.getAll("arquivos").map((x) => (x as File).size)).toEqual([
      1, 1,
    ]);
  });
  it("separa batches por quantidade e bytes", () => {
    expect(
      batches(
        [{ tamanho_bytes: 40 }, { tamanho_bytes: 30 }, { tamanho_bytes: 20 }],
        3,
        64,
      ).map((x) => x.length),
    ).toEqual([1, 2]);
    expect(
      batches(
        Array.from({ length: 7 }, () => ({ tamanho_bytes: 1 })),
        3,
        64,
      ).map((x) => x.length),
    ).toEqual([3, 3, 1]);
    expect(() => batches([{ tamanho_bytes: 65 }], 3, 64)).toThrow();
  });
  it("mantém decimais além da precisão de Number e o sinal", () => {
    expect(money("9007199254740993.01")).toBe("R$ 9.007.199.254.740.993,01");
    expect(money("-12.34")).toBe("-R$ 12,34");
  });
  it("SHA-256 usa os bytes originais", async () =>
    expect(await sha256(new File(["abc"], "a.csv"))).toBe(
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    ));
  it("preserva correlação e Retry-After", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            request_id: "trace",
            erro: {
              mensagem: "Indisponível",
              retry_permitido: true,
              detalhes: [],
            },
          }),
          { status: 503, headers: { "Retry-After": "3" } },
        ),
      ),
    );
    try {
      await api.capacidades();
      throw Error("expected rejection");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).retryAfter).toBe(3000);
      expect((e as ApiError).payload?.request_id).toBe("trace");
    }
  });
});
