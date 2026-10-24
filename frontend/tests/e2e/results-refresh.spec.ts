import { test, expect } from "@playwright/test";
import examples from "../../contracts/examples.json" with { type: "json" };
import fixtures from "../../contracts/fixtures.json" with { type: "json" };

const origin = `http://127.0.0.1:${process.env.E2E_API_PORT || "5184"}`;
const fixture = (name: string) =>
  structuredClone(fixtures.exemplos.find((x) => x.nome === name)!.valor) as any;

test("envio carrega a tabela e a análise atualiza os resultados até concluir", async ({
  page,
}) => {
  const created = fixture("lote_criado");
  const results = fixture("resultados");
  let uploaded = false,
    started = false,
    finished = false,
    reads = 0;
  await page.route("**/api/v1/**", (r) => {
    const req = r.request(),
      path = new URL(req.url()).pathname;
    if (path.endsWith("/capacidades"))
      return r.fulfill({
        json: { ...examples.CapacidadesResponse, polling_intervalo_ms: 200 },
      });
    if (path.endsWith("/cadastro/status"))
      return r.fulfill({ json: examples.BaseCadastralStatusResponse });
    if (path.endsWith("/lotes") && req.method() === "POST") {
      const body = req.postDataJSON();
      created.lote.nome = body.nome;
      created.arquivos[0] = { ...created.arquivos[0], ...body.arquivos[0] };
      return r.fulfill({ status: 201, json: created });
    }
    if (path.endsWith("/batches")) {
      uploaded = true;
      return r.fulfill({ status: 201, json: fixture("batch_recebido") });
    }
    if (path.endsWith("/processamento")) {
      started = true;
      return r.fulfill({ status: 202, json: examples.ProcessarLoteResponse });
    }
    if (path.endsWith("/arquivos"))
      return r.fulfill({
        json: {
          itens: [
            {
              ...created.arquivos[0],
              status: finished
                ? "CONCLUIDO_COM_ERROS"
                : started
                  ? "ANALISANDO"
                  : uploaded
                    ? "RECEBIDO"
                    : "AGUARDANDO_UPLOAD",
              bytes_recebidos: uploaded ? created.arquivos[0].tamanho_bytes : 0,
            },
          ],
          proximo_cursor: null,
          limit: 100,
        },
      });
    if (path.endsWith("/resultados")) {
      reads++;
      return r.fulfill({
        json: {
          ...results,
          itens: finished
            ? results.itens
            : started
              ? results.itens.slice(0, 1)
              : [],
          arquivo_finalizado: finished,
          snapshot_ate_sequencia: finished ? 3 : started ? 1 : 0,
          proximo_cursor: null,
        },
      });
    }
    if (path.endsWith("/pendencias") || path.endsWith("/resumos-fundos"))
      return r.fulfill({
        json: { itens: [], proximo_cursor: null, limit: 100 },
      });
    return r.fulfill({
      json: {
        ...created.lote,
        status: finished
          ? "CONCLUIDO_COM_ERROS"
          : started
            ? "ANALISANDO"
            : "RECEBENDO",
        acoes: {
          ...created.lote.acoes,
          pode_iniciar: uploaded && !started,
          pode_retomar: false,
        },
        resumo: { ...created.lote.resumo, definitivo: finished },
      },
    });
  });
  await page.goto(origin + "/novo");
  await page.getByLabel("Nome do lote").fill("Atualização automática");
  await page
    .locator("input[type=file]")
    .setInputFiles({
      name: "recebiveis.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("A,B\n1,2"),
    });
  await page
    .getByRole("button", { name: "Enviar recebíveis", exact: true })
    .click();
  await expect(page).toHaveURL(/\/lotes\//);
  await expect(
    page.getByText("Envio concluído. Clique em Iniciar análise", {
      exact: false,
    }),
  ).toBeVisible();
  await expect.poll(() => reads).toBeGreaterThan(0);
  expect(started).toBe(false);
  await page
    .getByRole("button", { name: "Iniciar análise", exact: true })
    .click();
  await expect(page.locator(".q-table tbody tr")).toHaveCount(1);
  finished = true;
  await expect(page.locator(".q-table tbody tr")).toHaveCount(3);
  await expect(
    page.getByText("Arquivo processado com erros nos dados.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.locator(".q-table").getByText("Dados inválidos", { exact: true }),
  ).toBeVisible();
});

test("paginação mantém snapshot durante análise e consulta final preserva filtros", async ({
  page,
}) => {
  const created = fixture("lote_criado"),
    results = fixture("resultados");
  let finished = false,
    lotReads = 0;
  const queries: URLSearchParams[] = [];
  await page.route("**/api/v1/**", (r) => {
    const url = new URL(r.request().url()),
      path = url.pathname;
    if (path.endsWith("/capacidades"))
      return r.fulfill({
        json: { ...examples.CapacidadesResponse, polling_intervalo_ms: 200 },
      });
    if (path.endsWith("/arquivos"))
      return r.fulfill({
        json: {
          itens: [
            {
              ...created.arquivos[0],
              status: finished ? "CONCLUIDO" : "ANALISANDO",
            },
          ],
          proximo_cursor: null,
          limit: 100,
        },
      });
    if (path.endsWith("/resultados")) {
      queries.push(url.searchParams);
      const row = {
        ...results.itens[0],
        id: url.searchParams.has("cursor") ? "second" : "first",
        status: "APROVADO",
      };
      return r.fulfill({
        json: {
          ...results,
          itens: [row],
          proximo_cursor: url.searchParams.has("cursor")
            ? null
            : "fixed-snapshot",
          arquivo_finalizado: finished,
        },
      });
    }
    if (path.endsWith("/pendencias") || path.endsWith("/resumos-fundos"))
      return r.fulfill({
        json: { itens: [], proximo_cursor: null, limit: 100 },
      });
    lotReads++;
    return r.fulfill({
      json: { ...created.lote, status: finished ? "CONCLUIDO" : "ANALISANDO" },
    });
  });
  await page.goto(origin + "/lotes/" + created.lote.id);
  await page.getByLabel("Resultado", { exact: true }).click();
  await page.getByRole("option", { name: "Aprovados", exact: true }).click();
  await page.getByRole("button", { name: "Próxima página" }).click();
  await expect(page.getByText("Página 2", { exact: true })).toBeVisible();
  const before = lotReads;
  await expect.poll(() => lotReads).toBeGreaterThan(before + 1);
  await expect(page.getByText("Página 2", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Carregar resultados recentes" }),
  ).toBeVisible();
  finished = true;
  await expect(page.getByText("Página 1", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Processamento encerrado. A tabela voltou", {
      exact: false,
    }),
  ).toBeVisible();
  await expect.poll(() => queries.at(-1)?.get("status")).toBe("APROVADO");
  expect(queries.at(-1)?.has("cursor")).toBe(false);
});
