import { expect, it } from "vitest";
import examples from "../contracts/examples.json";
import contract from "../contracts/openapi.json";
import type { DTO } from "../src/api/client";
import {
  isTerminal,
  lotMessage,
  resultMessage,
  statusLabel,
  statusTone,
} from "../src/analysisStatus";

it("distingue envio concluído de análise concluída", () => {
  const lot = structuredClone(examples.LoteDTO) as DTO<"LoteDTO">;
  lot.status = "RECEBENDO";
  lot.acoes.pode_iniciar = true;
  expect(lotMessage(lot)).toContain("Clique em Iniciar análise");
  lot.acoes.pode_iniciar = false;
  expect(lotMessage(lot)).toContain("envio ainda não terminou");
  expect(isTerminal("RECEBIDO")).toBe(false);
  expect(isTerminal("CONCLUIDO_COM_ERROS")).toBe(true);
  expect(statusTone("CONCLUIDO_COM_ERROS")).toBe("pending");
});

it("não apresenta recusa ou erro de dados como aprovação quando falta diagnóstico", () => {
  const row = structuredClone(examples.ResultadoDTO) as DTO<"ResultadoDTO">;
  row.motivos = [];
  row.erros_dados = [];
  row.tipo = "ANALISE";
  row.status = "BARRADO";
  expect(resultMessage(row)).toContain("recusado");
  row.tipo = "ERRO_DADOS";
  row.status = null;
  expect(resultMessage(row)).toContain("Não foi possível analisar");
});

it("todos os status do contrato têm textos de apresentação", () => {
  for (const status of [
    ...contract.components.schemas.StatusLote.enum,
    ...contract.components.schemas.StatusArquivo.enum,
    ...contract.components.schemas.StatusNota.enum,
  ]) {
    expect(statusLabel(status)).not.toContain("_");
    expect(statusLabel(status)).not.toBe(status);
  }
});
