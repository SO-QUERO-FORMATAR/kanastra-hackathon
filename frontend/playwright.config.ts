import { defineConfig } from "@playwright/test";
const demoPort = process.env.E2E_DEMO_PORT || "5173";
const apiPort = process.env.E2E_API_PORT || "5174";
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
      command: `VITE_DEMO_MODE=true npm run dev -- --port ${demoPort} --strictPort`,
      url: `http://127.0.0.1:${demoPort}`,
      reuseExistingServer: false,
    },
    {
      command: `VITE_DEMO_MODE=false npm run dev -- --port ${apiPort} --strictPort`,
      url: `http://127.0.0.1:${apiPort}`,
      reuseExistingServer: false,
    },
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
