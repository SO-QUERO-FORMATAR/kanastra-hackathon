import { it, expect, vi } from "vitest";
import { useCursor } from "../src/composables/useCursor";
it("mantém pilha de cursores e reinicia ao trocar filtros", async () => {
  const loader = vi.fn(async (cursor?: string) => ({
    itens: [cursor || "first"],
    proximo_cursor: cursor ? null : "opaque-token",
  }));
  const p = useCursor(loader);
  await p.load();
  await p.forward();
  expect(loader).toHaveBeenLastCalledWith("opaque-token");
  expect(p.rows.value).toEqual(["opaque-token"]);
  await p.back();
  expect(p.rows.value).toEqual(["first"]);
  await p.forward();
  await p.load(true);
  expect(p.history.value).toEqual([undefined]);
});
it("descarta resposta atrasada de consulta anterior", async () => {
  let resolve: (value: {
    itens: string[];
    proximo_cursor: null;
  }) => void = () => {};
  const loader = vi
    .fn()
    .mockImplementationOnce(() => new Promise((r) => (resolve = r)))
    .mockResolvedValue({ itens: ["new"], proximo_cursor: null });
  const p = useCursor<string>(loader);
  const first = p.load();
  await p.load(true);
  resolve({ itens: ["old"], proximo_cursor: null });
  await first;
  expect(p.rows.value).toEqual(["new"]);
});
it("falha não mantém linhas de uma consulta obsoleta", async () => {
  const p = useCursor(
    vi
      .fn()
      .mockResolvedValueOnce({ itens: ["first"], proximo_cursor: "next" })
      .mockRejectedValueOnce(Error("Cursor expirado")),
  );
  await p.load();
  await p.forward();
  expect(p.error.value).toBeInstanceOf(Error);
  expect(p.rows.value).toEqual([]);
  expect(p.next.value).toBeNull();
});
