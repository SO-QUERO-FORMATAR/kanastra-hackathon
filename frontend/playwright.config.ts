import { defineConfig } from "@playwright/test";
const demoPort = process.env.E2E_DEMO_PORT || "5183";
const apiPort = process.env.E2E_API_PORT || "5184";
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  use: {
    baseURL: `http://127.0.0.1:${demoPort}`,
    headless: true,
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined,
    },
  },
  webServer: [
    {
      command: `npm run dev -- --port ${demoPort} --strictPort`,
      env: { VITE_DEMO_MODE: "true" },
      url: `http://127.0.0.1:${demoPort}`,
      reuseExistingServer: false,
    },
    {
      command: `npm run dev -- --port ${apiPort} --strictPort`,
      env: { VITE_DEMO_MODE: "false" },
      url: `http://127.0.0.1:${apiPort}`,
      reuseExistingServer: false,
    },
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
