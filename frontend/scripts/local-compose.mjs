import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const args = [
  "compose",
  "-f",
  "compose.yaml",
  "-f",
  "compose.frontend.yaml",
  "--profile",
  "app",
];
const action = process.argv[2] || "up";
const commands = {
  up: ["up", "--build", "-d"],
  down: ["down"],
  logs: ["logs", "--follow", "--tail", "100"],
  status: ["ps"],
};
if (!(action in commands)) {
  console.error("Use up, down, logs ou status.");
  process.exit(1);
}
// Resolve interpolation exactly as Docker Compose does (including a local .env).
if (action === "up") {
  const config = spawnSync("docker", [...args, "config", "--format", "json"], {
    cwd: root,
    encoding: "utf8",
  });
  if (config.status !== 0) {
    console.error(
      config.stderr ||
        config.error?.message ||
        "Não foi possível ler o Compose.",
    );
    process.exit(config.status || 1);
  }
  const services = JSON.parse(config.stdout).services;
  const backend = services.api.build.context;
  const required = [
    resolve(backend, "backend/Dockerfile"),
    resolve(backend, "backend/init-test.sql"),
    resolve(backend, "files"),
  ];
  const missing = required.filter((path) => !existsSync(path));
  if (missing.length) {
    console.error(
      "O Compose precisa do código e dos insumos do backend. Ausentes:\n" +
        missing.map((path) => "  " + path).join("\n") +
        "\nColoque-os na raiz do projeto ou configure BACKEND_ROOT no arquivo .env (veja frontend/docs/local-development.md).",
    );
    process.exit(1);
  }
}
const result = spawnSync("docker", [...args, ...commands[action]], {
  cwd: root,
  stdio: "inherit",
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
