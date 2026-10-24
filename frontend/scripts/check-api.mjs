import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isDeepStrictEqual } from "node:util";
const canonical = JSON.parse(
  readFileSync("../docs/contratos/openapi.json", "utf8"),
);
const frontend = JSON.parse(readFileSync("contracts/openapi.json", "utf8"));
if (!isDeepStrictEqual(canonical, frontend)) {
  throw Error(
    "Contrato do frontend diverge de docs/contratos/openapi.json. Sincronize a cópia após coordenar a alteração com o backend.",
  );
}

const dir = mkdtempSync(join(tmpdir(), "antecipe-schema-"));
try {
  const dest = join(dir, "schema.d.ts");
  execFileSync(
    process.execPath,
    [
      "node_modules/openapi-typescript/bin/cli.js",
      "contracts/openapi.json",
      "-o",
      dest,
      "--default-non-nullable",
      "false",
    ],
    { stdio: "inherit" },
  );
  // Git may check out CRLF on Windows; generated files always use LF.
  const readTypes = (path) =>
    readFileSync(path, "utf8").replaceAll("\r\n", "\n");
  if (readTypes(dest) !== readTypes("src/api/schema.d.ts"))
    throw Error("Tipos desatualizados: execute npm run generate:api.");
} finally {
  rmSync(dir, { recursive: true, force: true });
}
