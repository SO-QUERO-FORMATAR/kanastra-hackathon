import { test, expect } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };
import fixtures from "../../contracts/fixtures.json" with { type: "json" };
const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;
const fixture = (name: string) =>
  structuredClone(fixtures.exemplos.find((x) => x.nome === name)!.valor) as any;

test("API indisponível mostra erro e correlação, sem inventar dados", async ({
  page,
}) => {
  await page.route("**/api/v1/lotes**", (r) =>
    r.fulfill({
      status: 503,
      json: {
        ...examples.ErroResponse,
        erro: { ...examples.ErroDTO, mensagem: "Banco indisponível" },
      },
    }),
  );
  await page.goto(origin);
  await expect(page.getByRole("alert")).toContainText("Banco indisponível");
  await expect(page.getByRole("alert")).toContainText(
    examples.ErroResponse.request_id,
  );
  await expect(page.locator(".q-table tbody tr")).toHaveCount(0);
});
test("409 de versão exige recarga e preserva edição até revisar", async ({
  page,
}) => {
  await page.route("**/api/v1/fundos**", (r) => {
    if (r.request().method() === "PUT")
      return r.fulfill({ status: 409, json: examples.ErroResponse });
    if (r.request().url().includes("/regras"))
      return r.fulfill({ json: examples.RegrasFundoResponse });
    return r.fulfill({
      json: { itens: [examples.FundoDTO], limit: 20, proximo_cursor: null },
    });
  });
  await page.goto(origin + "/fundos");
  await page.getByText("ANTECIPE FIDC", { exact: true }).click();
  await page.getByLabel("Taxa mensal (%)").fill("3.125");
  await page
    .getByText("Revisei os nove validadores e a precificação deste fundo.")
    .click();
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "As regras foram alteradas",
  );
  await page.getByRole("button", { name: "Manter minha edição" }).click();
  await expect(
    page.getByRole("button", { name: "Recarregar configuração" }),
  ).toBeVisible();
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("3.125");
  await expect(
    page.getByRole("button", { name: "Salvar configuração" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Recarregar configuração" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "substituirá os valores locais",
  );
  await page.getByRole("button", { name: "Carregar versão atual" }).click();
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("2.0");
});
test("retry de criação mantém manifesto e Idempotency-Key", async ({
  page,
}) => {
  const attempts: { key: string | undefined; body: unknown }[] = [];
  let created: any;
  await page.route("**/api/v1/**", async (r) => {
    const req = r.request(),
      path = new URL(req.url()).pathname;
    if (path.endsWith("/capacidades"))
      return r.fulfill({ json: examples.CapacidadesResponse });
    if (path.endsWith("/cadastro/status"))
      return r.fulfill({ json: examples.BaseCadastralStatusResponse });
    if (path.endsWith("/lotes") && req.method() === "POST") {
      const b = req.postDataJSON();
      attempts.push({ key: req.headers()["idempotency-key"], body: b });
      if (attempts.length === 1) return r.abort("connectionfailed");
      created = fixture("lote_criado");
      created.arquivos[0] = { ...created.arquivos[0], ...b.arquivos[0] };
      return r.fulfill({ status: 201, json: created });
    }
    if (path.endsWith("/arquivos"))
      return r.fulfill({
        json: { itens: created.arquivos, limit: 100, proximo_cursor: null },
      });
    if (path.endsWith("/batches")) {
      expect(req.headers()["content-type"]).toContain(
        "multipart/form-data; boundary=",
      );
      expect(req.postData()).toContain('name="metadados"');
      return r.fulfill({ status: 201, json: fixture("batch_recebido") });
    }
    if (path.endsWith("/pendencias") || path.endsWith("/resumos-fundos"))
      return r.fulfill({
        json: { itens: [], limit: 100, proximo_cursor: null },
      });
    if (path.includes("/resultados"))
      return r.fulfill({ json: fixture("resultados") });
    return r.fulfill({ json: created?.lote ?? examples.LoteDTO });
  });
  await page.goto(origin + "/novo");
  await page.getByLabel("Nome do lote").fill("Retry seguro");
  await page.locator("input[type=file]").setInputFiles({
    name: "arquivo.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("A,B\n1,2"),
  });
  await page
    .getByRole("button", { name: "Enviar recebíveis", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Não foi possível concluir o envio",
  );
  await page.getByRole("button", { name: "Voltar ao envio" }).click();
  await page
    .getByRole("button", { name: "Retomar envio", exact: true })
    .click();
  await expect(page).toHaveURL(/\/lotes\//);
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);
});
test("resultados enviam cursor opaco e reiniciam após mudar filtro", async ({
  page,
}) => {
  const queries: URLSearchParams[] = [];
  const initial = fixture("lote_criado");
  initial.lote.status = "CONCLUIDO";
  await page.route("**/api/v1/**", (r) => {
    const url = new URL(r.request().url()),
      path = url.pathname;
    if (path.endsWith("/capacidades"))
      return r.fulfill({ json: examples.CapacidadesResponse });
    if (path.endsWith("/arquivos"))
      return r.fulfill({
        json: { itens: initial.arquivos, limit: 100, proximo_cursor: null },
      });
    if (path.endsWith("/pendencias") || path.endsWith("/resumos-fundos"))
      return r.fulfill({
        json: { itens: [], limit: 100, proximo_cursor: null },
      });
    if (path.endsWith("/resultados")) {
      queries.push(url.searchParams);
      const v = fixture("resultados");
      v.itens = v.itens.slice(
        url.searchParams.has("cursor") ? 1 : 0,
        url.searchParams.has("cursor") ? 2 : 1,
      );
      v.proximo_cursor = url.searchParams.has("cursor")
        ? null
        : "opaque-snapshot";
      return r.fulfill({ json: v });
    }
    return r.fulfill({ json: initial.lote });
  });
  await page.goto(origin + "/lotes/" + initial.lote.id);
  await page.getByRole("button", { name: "Próxima página" }).click();
  await expect
    .poll(() => queries.at(-1)?.get("cursor"))
    .toBe("opaque-snapshot");
  await page.getByLabel("Resultado", { exact: true }).click();
  await page.getByRole("option", { name: "Aprovados", exact: true }).click();
  await expect.poll(() => queries.at(-1)?.get("status")).toBe("APROVADO");
  expect(queries.at(-1)?.has("cursor")).toBe(false);
  expect(queries.at(-1)?.has("motivo")).toBe(false);
});

test("histórico vazio apresenta orientação de importação", async ({ page }) => {
  await page.route("**/api/v1/lotes**", (r) =>
    r.fulfill({ json: { itens: [], proximo_cursor: null, limit: 10 } }),
  );
  await page.goto(origin);
  await expect(
    page.getByText("Nenhuma importação encontrada.", { exact: false }),
  ).toBeVisible();
});
