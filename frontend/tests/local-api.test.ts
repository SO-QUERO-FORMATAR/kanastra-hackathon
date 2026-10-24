import { afterEach, beforeEach, it, expect } from "vitest";
import { createServer, type Server } from "node:http";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import examples from "../contracts/examples.json";
const exec = promisify(execFile);
let server: Server, base: string;
let unavailable = false,
  invalid = false;
beforeEach(async () => {
  unavailable = false;
  invalid = false;
  server = createServer((req, res) => {
    const path = req.url!;
    res.setHeader("Content-Type", "application/json");
    const value = path.endsWith("/capacidades")
      ? invalid
        ? {}
        : examples.CapacidadesResponse
      : path.endsWith("/cadastro/status")
        ? { ...examples.BaseCadastralStatusResponse, disponivel: !unavailable }
        : examples.SaudeResponse;
    res.end(JSON.stringify(value));
  });
  await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
  const address = server.address() as { port: number };
  base = `http://127.0.0.1:${address.port}/api/v1`;
});
afterEach(() => new Promise<void>((r) => server.close(() => r())));
it("diagnóstico consulta os quatro endpoints e valida o contrato", async () => {
  const { stdout } = await exec(
    process.execPath,
    ["scripts/check-local-api.mjs"],
    { env: { ...process.env, API_CHECK_BASE_URL: base } },
  );
  expect(stdout).toContain("OK /health/ready");
  expect(stdout).toContain("OK /capacidades");
  expect(stdout).toContain("OK /cadastro/status");
});
it("diagnóstico falha se o contrato da API diverge", async () => {
  invalid = true;
  await expect(
    exec(process.execPath, ["scripts/check-local-api.mjs"], {
      env: { ...process.env, API_CHECK_BASE_URL: base },
    }),
  ).rejects.toMatchObject({
    code: 1,
    stderr: expect.stringContaining("Resposta incompatível"),
  });
});
it("diagnóstico separa disponibilidade da API e carga cadastral", async () => {
  unavailable = true;
  await expect(
    exec(process.execPath, ["scripts/check-local-api.mjs"], {
      env: { ...process.env, API_CHECK_BASE_URL: base },
    }),
  ).rejects.toMatchObject({
    code: 1,
    stderr: expect.stringContaining("Base cadastral ausente"),
  });
});
