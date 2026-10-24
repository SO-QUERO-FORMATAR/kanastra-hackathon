import { test, expect } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };
import type { DTO } from "../../src/api/client";

const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;

test("listas fechadas salvam as opções escolhidas e restauram a seleção ao reabrir", async ({
  page,
}) => {
  let stored = structuredClone(
    examples.RegrasFundoResponse,
  ) as DTO<"RegrasFundoResponse">;
  let saves = 0;
  await page.route("**/api/v1/fundos**", (r) => {
    if (r.request().method() === "PUT") {
      saves++;
      stored = {
        ...stored,
        configuracao: r.request().postDataJSON().configuracao,
      };
      return r.fulfill({ json: stored });
    }
    return r.fulfill({
      json: r.request().url().includes("/regras")
        ? stored
        : { itens: [stored.fundo], limit: 20, proximo_cursor: null },
    });
  });
  await page.goto(origin + "/fundos");
  await page.getByText("ANTECIPE FIDC", { exact: true }).click();
  const dialog = page.getByRole("dialog", {
    name: "ANTECIPE FIDC",
    exact: true,
  });
  const situations = dialog.getByRole("combobox", {
    name: "Situações aceitas",
    exact: true,
  });
  const types = dialog.getByRole("combobox", {
    name: "Tipos de recebível aceitos",
    exact: true,
  });
  await situations.click();
  await expect(page.getByRole("option")).toHaveText([
    "Ativa",
    "Suspensa",
    "Inapta",
    "Baixada",
  ]);
  await expect(
    page.getByRole("textbox", { name: "Situações aceitas", exact: true }),
  ).toHaveCount(0);
  await page.keyboard.type("INVENTADA");
  await expect(page.getByRole("option")).toHaveCount(4);
  await page.getByRole("option", { name: "Ativa", exact: true }).click();
  await page.getByRole("option", { name: "Suspensa", exact: true }).click();
  await page.getByRole("option", { name: "Baixada", exact: true }).click();
  await page.keyboard.press("Escape");
  await types.click();
  await expect(page.getByRole("option")).toHaveText([
    "Duplicata",
    "Duplicata de Serviço",
    "Cheque",
    "CCB",
    "Nota Comercial",
  ]);
  await page.getByRole("option", { name: "Duplicata", exact: true }).click();
  await page
    .getByRole("option", { name: "Duplicata de Serviço", exact: true })
    .click();
  await page.getByRole("option", { name: "CCB", exact: true }).click();
  await page
    .getByRole("option", { name: "Nota Comercial", exact: true })
    .click();
  await page.keyboard.press("Escape");
  await dialog
    .getByText("Revisei os nove validadores e a precificação deste fundo.")
    .click();
  await dialog.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByText("Configuração salva com sucesso.")).toBeVisible();
  expect(saves).toBe(1);
  expect(
    stored.configuracao.validadores.find(
      (v) => v.codigo === "SITUACAO_CADASTRAL_SACADO",
    )!.parametros.situacoes_aceitas,
  ).toEqual(["SUSPENSA", "BAIXADA"]);
  expect(
    stored.configuracao.validadores.find((v) => v.codigo === "TIPO_RECEBIVEL")!
      .parametros.tipos_aceitos,
  ).toEqual(["CCB", "Nota Comercial"]);
  await page.reload();
  await page.getByText("ANTECIPE FIDC", { exact: true }).click();
  await expect(dialog.getByText("Suspensa", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Baixada", { exact: true })).toBeVisible();
  await expect(dialog.getByText("CCB", { exact: true })).toBeVisible();
  await expect(
    dialog.getByText("Nota Comercial", { exact: true }),
  ).toBeVisible();
});
