import { test, expect } from "@playwright/test";
test("histórico, resumo, resultados e dados originais", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("Demonstração · dados de exemplo")).toBeVisible();
  await expect(page.getByText("R$ 9.800,00").first()).toBeVisible();
  await page
    .getByRole("link", {
      name: "Recebíveis · demonstração do contrato",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Resultados da análise" }),
  ).toBeVisible();
  await expect(page.getByText("000351153").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Detalhar resultado" })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Detalhe do recebível" }),
  ).toBeVisible();
  await expect(page.getByText("R$ 200,00").last()).toBeVisible();
  await page.getByRole("button", { name: "Fechar detalhe" }).click();
  expect(errors).toEqual([]);
});
test("upload com nomes repetidos e bloqueio por fundo sem regras", async ({
  page,
}) => {
  await page.goto("/novo");
  await page.getByLabel("Nome do lote").fill("Teste de upload");
  await page.locator("input[type=file]").setInputFiles([
    {
      name: "recebiveis.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("header\nA"),
    },
    {
      name: "recebiveis.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("header\nB"),
    },
  ]);
  await page
    .getByRole("button", { name: "Enviar recebíveis", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Iniciar análise" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Iniciar análise" }).click();
  await expect(
    page.getByRole("heading", { name: "Pendências para continuar" }),
  ).toBeVisible({ timeout: 10000 });
  await page
    .getByRole("link", { name: "Configurar fundo", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: /SAFIRA/ })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Salvar configuração" }),
  ).toBeDisabled();
});
test("edição exige revisão explícita e preserva versão", async ({ page }) => {
  await page.goto("/fundos");
  await page.getByText("ANTECIPE FIDC", { exact: true }).click();
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("2.0");
  await page.getByLabel("Taxa mensal (%)").fill("2.5");
  await page
    .getByText("Revisei os nove validadores e a precificação deste fundo.")
    .click();
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByText("Configuração salva com sucesso.")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Salvar configuração" }),
  ).toBeDisabled();
  await expect(page.getByLabel("Taxa mensal (%)")).toHaveValue("2.5");
});
test("layout em dispositivo móvel sem overflow da página", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Recebíveis, sob controle." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Abrir navegação" }).click();
  await expect(
    page.getByRole("link", { name: "Fundos e regras" }),
  ).toBeVisible();
});
