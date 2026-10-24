import { it, expect, vi, afterEach } from "vitest";
import { ruleMutationKey } from "../src/api/idempotency";
afterEach(() => vi.unstubAllGlobals());
it("retém chaves de edições distintas e recupera retries por 24h", () => {
  const values = new Map();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => values.get(k),
    setItem: (k: string, v: string) => values.set(k, v),
  });
  const first = ruleMutationKey("fund", { versao_base: "v1", taxa: "2.00" });
  const second = ruleMutationKey("fund", { versao_base: "v2", taxa: "3.00" });
  expect(second).not.toBe(first);
  expect(ruleMutationKey("fund", { versao_base: "v1", taxa: "2.00" })).toBe(
    first,
  );
  expect(JSON.parse([...values.values()][0])).toHaveLength(2);
});
