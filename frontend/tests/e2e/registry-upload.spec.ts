import { test, expect } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };
const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;
const csv = "DOC;SITUACAO_CADASTRAL\n22144961000102;ATIVA\n";

test("carrega cadastro no lote bloqueado e retoma sem solicitar o backend", async ({
  page,
}) => {
  let loaded = false,
    resumed = false,
    uploads = 0;
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/cadastro/importacao")) {
      expect(route.request().postDataJSON()).toEqual({ csv });
      expect(route.request().headers()["idempotency-key"]).toBeTruthy();
      uploads++;
      loaded = true;
      return route.fulfill({ json: examples.BaseCadastralStatusResponse });
    }
    if (path.endsWith("/cadastro/status"))
      return route.fulfill({
        json: { ...examples.BaseCadastralStatusResponse, disponivel: loaded },
      });
    if (path.endsWith("/capacidades"))
      return route.fulfill({ json: examples.CapacidadesResponse });
    if (path.endsWith("/processamento")) {
      expect(loaded).toBe(true);
      resumed = true;
      return route.fulfill({
        status: 202,
        json: examples.ProcessarLoteResponse,
      });
    }
    if (path.endsWith("/pendencias"))
      return route.fulfill({
        json: {
          itens: resumed
            ? []
            : [
                {
                  codigo: "BASE_CADASTRAL_AUSENTE",
                  mensagem: "Importe a base cadastral",
                  fundo: null,
                  arquivo_id: null,
                  linha: null,
                  campo: null,
                  acao: "IMPORTAR_BASE_CADASTRAL",
                },
              ],
          proximo_cursor: null,
          limit: 100,
        },
      });
    if (path.endsWith("/arquivos") || path.endsWith("/resumos-fundos"))
      return route.fulfill({
        json: { itens: [], proximo_cursor: null, limit: 100 },
      });
    return route.fulfill({
      json: {
        ...examples.LoteDTO,
        status: resumed ? "CONCLUIDO" : "BLOQUEADO",
        quantidade_pendencias: resumed ? 0 : 1,
        acoes: {
          ...examples.LoteDTO.acoes,
          pode_iniciar: false,
          pode_retomar: !resumed,
        },
      },
    });
  });
  await page.goto(origin + "/lotes/" + examples.LoteDTO.id);
  await expect(
    page.getByText("Solicite a carga cadastral ao responsável pelo backend.", {
      exact: false,
    }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Importar base cadastral", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Importar base cadastral" });
  await expect(dialog).toContainText("O JSON define as regras dos fundos");
  await dialog
    .locator("input[type=file]")
    .setInputFiles({
      name: "cadastro.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
  await dialog.getByRole("button", { name: "Carregar cadastro" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByText("Base cadastral carregada. Clique em Retomar análise.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Retomar análise", exact: true })
    .click();
  await expect(
    page.getByText("Pendências para continuar", { exact: true }),
  ).toHaveCount(0);
  expect(uploads).toBe(1);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Retomar análise", exact: true }),
  ).toHaveCount(0);
});

test("falha na carga cadastral preserva arquivo e chave para tentar novamente", async ({
  page,
}) => {
  const keys: string[] = [];
  let loaded = false;
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/cadastro/importacao")) {
      keys.push(route.request().headers()["idempotency-key"]!);
      if (keys.length === 1) return route.abort();
      loaded = true;
      return route.fulfill({ json: examples.BaseCadastralStatusResponse });
    }
    if (path.endsWith("/cadastro/status"))
      return route.fulfill({
        json: { ...examples.BaseCadastralStatusResponse, disponivel: loaded },
      });
    return route.fulfill({
      json: { itens: [], proximo_cursor: null, limit: 20 },
    });
  });
  await page.goto(origin + "/fundos");
  await page
    .getByRole("button", { name: "Importar base cadastral", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Importar base cadastral" });
  await dialog
    .locator("input[type=file]")
    .setInputFiles({
      name: "cadastro.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
  await dialog.getByRole("button", { name: "Carregar cadastro" }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Carregar cadastro" }),
  ).toBeEnabled();
  await dialog.getByRole("button", { name: "Carregar cadastro" }).click();
  await expect(dialog).toHaveCount(0);
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
});
