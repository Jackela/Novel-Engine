import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.NOVEL_ENGINE_ACP_E2E_URL;
if (!baseURL)
  throw new Error("NOVEL_ENGINE_ACP_E2E_URL must name the isolated coupled ACP test stack.");

/** Uses an explicitly provided fresh fake-ACP runtime, never an author's running store. */
export default defineConfig({
  testDir: "./tests/e2e-acp",
  workers: 1,
  fullyParallel: false,
  timeout: 120_000,
  use: { baseURL, locale: "en-US", trace: "retain-on-failure" },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
          ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } }
          : {}),
      },
    },
  ],
});
