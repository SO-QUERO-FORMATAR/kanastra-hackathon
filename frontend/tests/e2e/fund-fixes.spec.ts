import { test, expect } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };
import fixtures from "../../contracts/fixtures.json" with { type: "json" };

const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;

test("modal de fundo permite salvar regras desativadas e cabe no celular", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const fund = {
    ...examples.FundoDTO,
    configurado: false,
    versao_regras_atual: null,
  };
  let saved: any;
  await page.route("**/api/v1/fundos**", (r) => {
    if (r.request().method() === "PUT") {
      saved = r.request().postDataJSON();
      return r.fulfill({
        json: {
          ...examples.RegrasFundoResponse,
          configuracao: saved.configuracao,
        },
      });
    }
    return r.fulfill({
      json: { itens: [fund], limit: 20, proximo_cursor: null },
    });
  });
  await page.goto(origin + "/fundos");
  await page.getByText(fund.nome, { exact: true }).click();
  const dialog = page.getByRole("dialog", { name: fund.nome, exact: true });
  await expect(dialog).toBeVisible();
  const card = page.locator(".fund-rules-dialog");
  expect(await card.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await expect(
    dialog.getByRole("textbox", { name: "Valor minimo", exact: true }),
  ).toBeDisabled();
  await dialog.getByLabel("Taxa mensal (%)").fill("2");
  await dialog
    .getByText("Revisei os nove validadores e a precificação deste fundo.")
    .click();
  await dialog.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByText("Configuração salva com sucesso.")).toBeVisible();
  expect(saved.configuracao.validadores.every((v: any) => !v.ativo)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("fund-modal-mobile.png") });
  await dialog.getByRole("button", { name: "Fechar regras" }).click();
  await expect(dialog).toHaveCount(0);
});

test("JSON de inputs é enviado pela tela e erros preservam o arquivo", async ({
  page,
}) => {
  const body = {
    fundo: { nome: "Fundo importado", cnpj: "92.234.400/0001-80" },
    ...examples.ConfiguracaoRegrasDTO,
  };
  let uploaded: unknown;
  let attempts = 0;
  await page.route("**/api/v1/fundos**", (r) => {
    if (r.request().method() === "POST") {
      uploaded = r.request().postDataJSON();
      attempts++;
      if (attempts === 1)
        return r.fulfill({
          status: 422,
          json: {
            ...examples.ErroResponse,
            erro: {
              ...examples.ErroDTO,
              codigo: "CONFIGURACAO_INVALIDA",
              mensagem: "Revise as regras do fundo.",
            },
          },
        });
      return r.fulfill({ json: { fundos: [examples.FundoDTO] } });
    }
    return r.fulfill({ json: { itens: [], limit: 20, proximo_cursor: null } });
  });
  await page.goto(origin + "/fundos");
  const file = page.locator("input[type=file]");
  await file.setInputFiles({
    name: "regras.json",
    mimeType: "application/json",
    buffer: Buffer.from("{inválido"),
  });
  await page
    .getByRole("button", { name: "Importar regras", exact: true })
    .click();
  await expect(
    page.getByText("O arquivo não contém um JSON válido."),
  ).toBeVisible();
  expect(attempts).toBe(0);
  await file.setInputFiles({
    name: "regras.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify([body])),
  });
  await page
    .getByRole("button", { name: "Importar regras", exact: true })
    .click();
  await expect(page.getByText("Revise as regras do fundo.")).toBeVisible();
  expect(uploaded).toEqual([body]);
  await page
    .getByRole("button", { name: "Importar regras", exact: true })
    .click();
  await expect(
    page.getByText("Regras importadas para 1 fundo(s)."),
  ).toBeVisible();
});

test("notas sem regras exibem diagnóstico vermelho junto dos resultados processados", async ({
  page,
}) => {
  const results: any = structuredClone(
    fixtures.exemplos.find((x) => x.nome === "resultados")!.valor,
  );
  results.itens[2].erros_dados = [
    {
      campo: "DOC_FUNDO",
      codigo: "FUNDO_SEM_REGRAS",
      mensagem: "Regras de fundo não configuradas",
    },
  ];
  await page.route("**/api/v1/**", (r) => {
    const path = new URL(r.request().url()).pathname;
    if (path.endsWith("/capacidades"))
      return r.fulfill({ json: examples.CapacidadesResponse });
    if (path.endsWith("/arquivos"))
      return r.fulfill({
        json: {
          itens: [{ ...examples.ArquivoDTO, status: "CONCLUIDO_COM_ERROS" }],
          proximo_cursor: null,
          limit: 100,
        },
      });
    if (path.endsWith("/resultados")) return r.fulfill({ json: results });
    if (path.endsWith("/pendencias") || path.endsWith("/resumos-fundos"))
      return r.fulfill({
        json: { itens: [], proximo_cursor: null, limit: 100 },
      });
    return r.fulfill({ json: { ...examples.LoteDTO, status: "BLOQUEADO" } });
  });
  await page.goto(origin + "/lotes/" + examples.LoteDTO.id);
  await expect(
    page.getByText("Regras de fundo não configuradas", { exact: true }),
  ).toHaveClass("text-negative");
  await expect(
    page.getByText("Recebível aprovado pelas regras do fundo."),
  ).toBeVisible();
});
