import { readFileSync } from "node:fs";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
const base = (
  process.env.API_CHECK_BASE_URL || "http://127.0.0.1:5173/api/v1"
).replace(/\/$/, "");
const contract = JSON.parse(
  readFileSync(new URL("../contracts/openapi.json", import.meta.url), "utf8"),
);
const ajv = new Ajv({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(contract, "contract");
let failed = false;
for (const [path, schema] of [
  ["/health/live", "SaudeResponse"],
  ["/health/ready", "SaudeResponse"],
  ["/capacidades", "CapacidadesResponse"],
  ["/cadastro/status", "BaseCadastralStatusResponse"],
]) {
  try {
    const response = await fetch(base + path, {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw Error(`HTTP ${response.status}`);
    const data = await response.json();
    const validate = ajv.compile({
      $ref: `contract#/components/schemas/${schema}`,
    });
    if (!validate(data))
      throw Error(
        `Resposta incompatível com ${schema}: ${ajv.errorsText(validate.errors)}`,
      );
    console.log(`OK ${path} (${schema})`);
    if (path === "/cadastro/status" && !data.disponivel) {
      failed = true;
      console.error(
        "Base cadastral ausente: solicite a carga administrativa antes da análise.",
      );
    }
  } catch (error) {
    failed = true;
    console.error(
      `FALHOU ${path}: ${error.message}${error.cause?.code ? " (" + error.cause.code + ")" : ""}`,
    );
  }
}
if (failed) process.exitCode = 1;
else
  console.log(
    "API e cadastro disponíveis através da URL configurada. Isso não certifica o processamento de um lote completo.",
  );
