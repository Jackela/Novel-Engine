import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  fullyParallel: true,
  use: {
    baseURL: 'http://127.0.0.1:4273',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node ./scripts/start-e2e-stack.mjs',
    url: 'http://127.0.0.1:4273',
    // Always boot a fresh backend/frontend pair so local manual stacks do not
    // leak stale code or session state into the deterministic smoke suite.
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
