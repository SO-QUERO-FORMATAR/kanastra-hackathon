import { describe, it, expect } from "vitest";
import Ajv from "ajv/dist/2020";
import addFormats from "ajv-formats";
import contract from "../contracts/openapi.json";
import examples from "../contracts/examples.json";
import fixtures from "../contracts/fixtures.json";
const ajv = new Ajv({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(contract, "contract");
describe("contrato fornecido", () => {
  it("declara as 17 operações com IDs únicos", () => {
    const ops = Object.values(contract.paths)
      .flatMap((x) => Object.values(x))
      .map((x) => x.operationId);
    expect(ops).toHaveLength(17);
    expect(new Set(ops).size).toBe(17);
  });
  for (const [schema, value] of Object.entries(examples))
    it(`exemplo ${schema}`, () => {
      const validate = ajv.compile({
        $ref: `contract#/components/schemas/${schema}`,
      });
      expect(validate(value), JSON.stringify(validate.errors)).toBe(true);
    });
  for (const f of fixtures.exemplos)
    it(`fixture ${f.nome}`, () => {
      const validate = ajv.compile({
        $ref: `contract#/components/schemas/${f.schema}`,
      });
      expect(validate(f.valor), JSON.stringify(validate.errors)).toBe(true);
    });
  it("rejeita códigos duplicados e propriedades desconhecidas", () => {
    const validate = ajv.compile({
      $ref: "contract#/components/schemas/AtualizarRegrasRequest",
    });
    const b = structuredClone(examples.AtualizarRegrasRequest);
    b.configuracao.validadores[1] = b.configuracao.validadores[0]!;
    expect(validate(b)).toBe(false);
    expect(validate({ ...examples.AtualizarRegrasRequest, extra: true })).toBe(
      false,
    );
  });
});
