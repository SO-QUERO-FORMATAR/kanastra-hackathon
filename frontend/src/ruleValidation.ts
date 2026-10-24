import Ajv, { type ErrorObject } from "ajv/dist/2020";
import addFormats from "ajv-formats";
import contract from "../contracts/openapi.json";
import type { DTO } from "./api/client";

const ajv = new Ajv({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(contract, "contract");
export const validateRules = ajv.compile({
  $ref: "contract#/components/schemas/AtualizarRegrasRequest",
});
// Validate only the matching union branch to avoid errors from unrelated rules.
const validators = Object.fromEntries(
  Object.entries(
    contract.components.schemas.ValidadorDTO.discriminator.mapping,
  ).map(([code, path]) => [code, ajv.compile({ $ref: `contract${path}` })]),
);
const pricing = ajv.compile({
  $ref: "contract#/components/schemas/PrecificacaoDTO",
});

function message(e: ErrorObject) {
  switch (e.keyword) {
    case "required":
      return "Preencha este campo.";
    case "pattern":
      return "Informe um número não negativo, com ponto decimal e até 8 casas (ex.: 2.5).";
    case "minimum":
      return `Informe um valor maior ou igual a ${e.params.limit}.`;
    case "maximum":
      return `Informe um valor menor ou igual a ${e.params.limit}.`;
    case "type":
      return e.params.type === "integer"
        ? "Informe um número inteiro."
        : "Preencha este campo com um valor válido.";
    case "minItems":
      return `Adicione pelo menos ${e.params.limit} opção(ões).`;
    case "uniqueItems":
      return "Remova as opções repetidas.";
    case "minLength":
      return "Preencha este valor.";
    case "enum":
      return `Use uma das opções permitidas: ${e.params.allowedValues.join(", ")}.`;
    default:
      return "Revise o valor informado.";
  }
}

export function ruleFieldErrors(form: DTO<"AtualizarRegrasRequest">) {
  const errors: Record<string, string> = {};
  function collect(prefix: string, items: ErrorObject[] | null | undefined) {
    for (const e of items || []) {
      const path =
        prefix +
        e.instancePath +
        (e.keyword === "required" ? `/${e.params.missingProperty}` : "");
      errors[path] ??= message(e);
    }
  }
  form.configuracao.validadores.forEach((v, i) => {
    const validate = validators[v.codigo];
    if (validate && !validate(v)) collect(`/validadores/${i}`, validate.errors);
  });
  if (!pricing(form.configuracao.precificacao))
    collect("/precificacao", pricing.errors);
  return errors;
}
