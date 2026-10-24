import { describe, expect, it } from "vitest";
import examples from "../contracts/examples.json";
import type { DTO } from "../src/api/client";
import { ruleFieldErrors, validateRules } from "../src/ruleValidation";

describe("validação de campos por regra", () => {
  it.each([
    [
      "SITUACAO_CADASTRAL_SACADO",
      "situacoes_aceitas",
      ["ATIVA", "SUSPENSA", "INAPTA", "BAIXADA"],
    ],
    [
      "TIPO_RECEBIVEL",
      "tipos_aceitos",
      ["Duplicata", "Duplicata de Serviço", "Cheque", "CCB", "Nota Comercial"],
    ],
  ])("restringe as opções de %s", (code, key, choices) => {
    const form = structuredClone(
      examples.AtualizarRegrasRequest,
    ) as DTO<"AtualizarRegrasRequest">;
    const index = form.configuracao.validadores.findIndex(
      (v) => v.codigo === code,
    );
    const rule = form.configuracao.validadores[index]!;
    rule.ativo = true;
    rule.parametros[String(key)] = choices;
    expect(validateRules(form)).toBe(true);
    rule.parametros[String(key)] = ["OPÇÃO INVENTADA"];
    expect(validateRules(form)).toBe(false);
    expect(
      ruleFieldErrors(form)[`/validadores/${index}/parametros/${key}/0`],
    ).toContain("Use uma das opções permitidas");
    rule.ativo = false;
    expect(validateRules(form)).toBe(true);
    expect(ruleFieldErrors(form)).toEqual({});
  });
  it("ignora parâmetros inativos e volta a validar quando a regra é ativada", () => {
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
    expect(validateRules(form)).toBe(true);
    expect(ruleFieldErrors(form)).toEqual({});
    form.configuracao.validadores[i]!.ativo = true;
    const errors = ruleFieldErrors(form);
    expect(validateRules(form)).toBe(false);
    expect(errors[`/validadores/${i}/parametros/valor_minimo`]).toBeDefined();
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
