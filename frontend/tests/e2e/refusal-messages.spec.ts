import { test, expect } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };
import fixtures from "../../contracts/fixtures.json" with { type: "json" };

const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;

test("exibe todos os requisitos reprovados na tabela e no detalhe após recarregar", async ({
  page,
}) => {
  const results: any = structuredClone(
    fixtures.exemplos.find((x) => x.nome === "resultados")!.valor,
  );
  const item = results.itens.find((x: any) => x.status === "BARRADO");
  item.motivos = [
    {
      codigo: "TIPO_RECEBIVEL",
      mensagem:
        "Tipo de recebível não aceito: esta nota é do tipo Cheque. Este fundo aceita apenas Duplicata, Duplicata de Serviço.",
      valor_observado: "Cheque",
      limite_aplicado: "Duplicata, Duplicata de Serviço",
    },
    {
      codigo: "VALOR_MINIMO",
      mensagem:
        "Valor abaixo do mínimo: esta nota tem valor de R$ 99,99; o mínimo é R$ 100,00.",
      valor_observado: "99.99",
      limite_aplicado: "100.00",
    },
    {
      codigo: "PRAZO_MAXIMO",
      mensagem:
        "Prazo acima do limite: esta nota vence em 181 dias; o limite configurado é 180.",
      valor_observado: "181",
      limite_aplicado: "180",
    },
  ];
  results.itens = [item];
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/capacidades"))
      return route.fulfill({ json: examples.CapacidadesResponse });
    if (path.endsWith("/arquivos"))
      return route.fulfill({
        json: {
          itens: [{ ...examples.ArquivoDTO, status: "CONCLUIDO" }],
          proximo_cursor: null,
          limit: 100,
        },
      });
    if (path.endsWith("/resultados")) return route.fulfill({ json: results });
    if (path.endsWith("/pendencias") || path.endsWith("/resumos-fundos"))
      return route.fulfill({
        json: { itens: [], proximo_cursor: null, limit: 100 },
      });
    return route.fulfill({
      json: { ...examples.LoteDTO, status: "CONCLUIDO" },
    });
  });
  await page.goto(origin + "/lotes/" + examples.LoteDTO.id);
  for (const reload of [false, true]) {
    if (reload) await page.reload();
    const list = page.getByRole("list", { name: "Requisitos não atendidos" });
    await expect(list.getByRole("listitem")).toHaveCount(3);
    for (const reason of item.motivos)
      await expect(
        list.getByText(reason.mensagem, { exact: true }),
      ).toBeVisible();
  }
  await page.getByRole("button", { name: "Detalhar resultado" }).click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText("Requisitos não atendidos (3)", { exact: true }),
  ).toBeVisible();
  for (const reason of item.motivos)
    await expect(
      dialog.getByText(reason.mensagem, { exact: true }),
    ).toBeVisible();
});
