import { test, expect, type Page } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };

const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;
const csv = {
  name: "recebiveis.csv",
  mimeType: "text/csv",
  buffer: Buffer.from("A,B\n1,2"),
};

async function uploadSetup(page: Page) {
  await page.route("**/api/v1/capacidades", (r) =>
    r.fulfill({
      json: {
        ...examples.CapacidadesResponse,
        max_arquivos_lote: 2,
        max_bytes_arquivo: 32,
      },
    }),
  );
  await page.route("**/api/v1/cadastro/status", (r) =>
    r.fulfill({ json: examples.BaseCadastralStatusResponse }),
  );
  await page.goto(origin + "/novo");
}

test("nome obrigatório recebe foco e erros dos arquivos ficam na seleção", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/v1/lotes", (r) => {
    posts++;
    return r.abort();
  });
  await uploadSetup(page);
  await page.locator("input[type=file]").setInputFiles(csv);
  await page
    .getByRole("button", { name: "Enviar recebíveis", exact: true })
    .click();
  await expect(
    page.getByText("Informe o nome do lote.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Nome do lote")).toBeFocused();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Nome do lote").fill("Meu lote");
  await page.getByRole("button", { name: "Remover recebiveis.csv" }).click();
  await page.locator("input[type=file]").setInputFiles([
    { ...csv, name: "vazio.csv", buffer: Buffer.from("") },
    { ...csv, name: "grande.csv", buffer: Buffer.alloc(33) },
    { ...csv, name: "arquivo.zip" },
  ]);
  await expect(
    page.getByText("Este arquivo está vazio.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("O arquivo excede o limite", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Formato não permitido.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Selecione no máximo 2 arquivos.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Enviar recebíveis", exact: true })
    .click();
  await expect(
    page.getByRole("group", { name: "Seleção de arquivos" }),
  ).toBeFocused();
  expect(posts).toBe(0);
});

test("recuperação exige os originais e nova seleção pede confirmação", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/v1/lotes", (r) => {
    posts++;
    return r.abort();
  });
  await uploadSetup(page);
  await page.getByLabel("Nome do lote").fill("Envio preservado");
  await page.locator("input[type=file]").setInputFiles(csv);
  await page
    .getByRole("button", { name: "Enviar recebíveis", exact: true })
    .click();
  await page.getByRole("button", { name: "Voltar ao envio" }).click();
  await page.reload();
  await expect(page.getByLabel("Nome do lote")).toHaveValue("Envio preservado");
  await page
    .locator("input[type=file]")
    .setInputFiles({ ...csv, buffer: Buffer.from("A,B\n3,4") });
  await page
    .getByRole("button", { name: "Retomar envio", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Os arquivos são diferentes",
  );
  await page.getByRole("button", { name: "Voltar à seleção" }).click();
  await expect(
    page.getByRole("group", { name: "Seleção de arquivos" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Nova seleção", exact: true }).click();
  await page.getByRole("button", { name: "Manter envio" }).click();
  await expect(
    page.getByRole("button", { name: "Retomar envio", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Nova seleção", exact: true }).click();
  await page
    .getByRole("button", { name: "Iniciar nova seleção", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Enviar recebíveis", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("0 arquivo(s) selecionado(s)")).toBeVisible();
  expect(posts).toBe(1);
});

test("regras inválidas exibem mensagens locais e falha ao salvar preserva edição", async ({
  page,
}) => {
  let saves = 0;
  await page.route("**/api/v1/fundos**", (r) => {
    if (r.request().method() === "PUT") {
      saves++;
      return r.abort();
    }
    return r.fulfill({
      json: r.request().url().includes("/regras")
        ? examples.RegrasFundoResponse
        : { itens: [examples.FundoDTO], limit: 20, proximo_cursor: null },
    });
  });
  await page.goto(origin + "/fundos");
  await page.getByText("ANTECIPE FIDC", { exact: true }).click();
  await page.getByLabel("Taxa mensal (%)").fill("-1");
  await page.getByLabel("Base de dias (1–366)").fill("367");
  await page
    .getByText("Revisei os nove validadores e a precificação deste fundo.")
    .click();
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByLabel("Taxa mensal (%)")).toBeFocused();
  await expect(
    page.getByText("Informe um número não negativo", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Informe um valor menor ou igual a 366."),
  ).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(saves).toBe(0);
  await page.getByLabel("Taxa mensal (%)").fill("3.125");
  await page.getByLabel("Base de dias (1–366)").fill("30");
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Não foi possível salvar a configuração",
  );
  await page.getByRole("button", { name: "Voltar à edição" }).click();
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("3.125");
  expect(saves).toBe(1);
});

test("falha da análise abre modal acessível no celular e polling não reabre", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let reads = 0;
  await page.route("**/api/v1/**", (r) => {
    const path = new URL(r.request().url()).pathname;
    if (path.endsWith("/capacidades"))
      return r.fulfill({
        json: { ...examples.CapacidadesResponse, polling_intervalo_ms: 100 },
      });
    if (path.endsWith("/processamento"))
      return r.fulfill({
        status: 503,
        json: {
          ...examples.ErroResponse,
          erro: {
            ...examples.ErroDTO,
            codigo: "INFRAESTRUTURA_INDISPONIVEL",
            mensagem: "Serviço temporariamente indisponível.",
          },
        },
      });
    if (
      path.endsWith("/arquivos") ||
      path.endsWith("/pendencias") ||
      path.endsWith("/resumos-fundos")
    )
      return r.fulfill({
        json: { itens: [], proximo_cursor: null, limit: 100 },
      });
    reads++;
    if (reads > 1) return r.abort();
    return r.fulfill({
      json: {
        ...examples.LoteDTO,
        status: "NA_FILA",
        acoes: {
          ...examples.LoteDTO.acoes,
          pode_iniciar: true,
          pode_retomar: false,
        },
      },
    });
  });
  await page.goto(origin + "/lotes/" + examples.LoteDTO.id);
  await page
    .getByRole("button", { name: "Iniciar análise", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Não foi possível confirmar o início da análise",
  });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Detalhes para suporte")).toBeVisible();
  await expect(
    dialog.getByText("Referência:", { exact: false }),
  ).not.toBeVisible();
  await dialog.getByText("Detalhes para suporte").click();
  await expect(
    dialog.getByText(examples.ErroResponse.request_id, { exact: false }),
  ).toBeVisible();
  const card = page.locator(".feedback-dialog");
  expect(await card.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await page.screenshot({ path: testInfo.outputPath("modal-mobile.png") });
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Iniciar análise", exact: true }),
  ).toBeFocused();
  await expect.poll(() => reads).toBeGreaterThan(2);
  await expect(page.getByRole("alert")).toContainText("Verifique sua conexão");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("conflito mantém edição quando a recarga falha", async ({ page }) => {
  let reads = 0;
  await page.route("**/api/v1/fundos**", (r) => {
    if (r.request().method() === "PUT")
      return r.fulfill({ status: 409, json: examples.ErroResponse });
    if (r.request().url().includes("/regras")) {
      reads++;
      if (reads === 2) return r.abort();
      return r.fulfill({ json: examples.RegrasFundoResponse });
    }
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
  await page.getByRole("button", { name: "Carregar versão atual" }).click();
  await expect(page.getByRole("dialog")).toContainText("Verifique sua conexão");
  await page.getByRole("button", { name: "Manter minha edição" }).click();
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("3.125");
  await expect(
    page.getByRole("button", { name: "Salvar configuração" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Recarregar configuração" }).click();
  await page.getByRole("button", { name: "Carregar versão atual" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("2.0");
  await expect(
    page.getByRole("button", { name: "Salvar configuração" }),
  ).toBeDisabled();
});
