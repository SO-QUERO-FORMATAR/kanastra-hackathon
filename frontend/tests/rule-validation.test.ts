import { describe, expect, it } from "vitest";
import examples from "../contracts/examples.json";
import type { DTO } from "../src/api/client";
import { ruleFieldErrors, validateRules } from "../src/ruleValidation";

describe("validação de campos por regra", () => {
  it("associa erros à regra correta, inclusive inativa, sem mensagens de outras variantes", () => {
    const form = structuredClone(
      examples.AtualizarRegrasRequest,
    ) as DTO<"AtualizarRegrasRequest">;
    const i = form.configuracao.validadores.findIndex(
      (v) => v.codigo === "VALOR_MINIMO",
    );
    form.configuracao.validadores[i] = {
      codigo: "VALOR_MINIMO",
      ativo: false,
      parametros: { valor_minimo: "-1" },
    };
    const errors = ruleFieldErrors(form);
    expect(validateRules(form)).toBe(false);
    expect(Object.keys(errors)).toEqual([
      `/validadores/${i}/parametros/valor_minimo`,
    ]);
    expect(Object.values(errors)[0]).toContain("número não negativo");
  });

  it("mantém a validação estrutural de códigos duplicados", () => {
    const form = structuredClone(
      examples.AtualizarRegrasRequest,
    ) as DTO<"AtualizarRegrasRequest">;
    expect(validateRules(form)).toBe(true);
    form.configuracao.validadores[1] = structuredClone(
      form.configuracao.validadores[0]!,
    );
    expect(ruleFieldErrors(form)).toEqual({});
    expect(validateRules(form)).toBe(false);
  });
});
