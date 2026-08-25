import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { defineConfig, devices } from '@playwright/test';

/**
 * #274: the TS-stack SPA suite. The emitted TS backend serves the built
 * frontend itself (scripts/start-ts-e2e-stack.mjs), so this project exercises
 * the same-origin contract — deep-link fallback, novel_engine_* cookies, the
 * unified error envelope — against the rewrite target rather than the Python
 * stack that playwright.config.ts (tests/e2e) still drives until cutover.
 * Keep the two configs' test directories disjoint.
 */

// #276: pin one fresh data directory per run and export it through the
// environment. The webServer (start-ts-e2e-stack.mjs honors TS_E2E_DATA_DIR)
// and the test workers both resolve the same directory, so the
// content-acceptance specs can assert on-disk export artifacts and database
// rows of the exact stack under test.
const ownsDataDirectory = process.env.TS_E2E_DATA_DIR === undefined;
process.env.TS_E2E_DATA_DIR ??= mkdtempSync(join(tmpdir(), 'ne-ts-e2e-'));
// The teardown module reads the ownership marker from the environment.
process.env.TS_E2E_OWN_DATA_DIR = ownsDataDirectory ? '1' : '';

const chromiumExecutablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

export default defineConfig({
  testDir: './tests/e2e-ts',
  timeout: 60_000,
  // The second test relies on the owner the first test creates, so the two
  // flows must run in file order against the shared fresh store.
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:4274',
    trace: 'retain-on-failure',
  },
  // A passing run leaves nothing behind (scripts/ts-e2e-teardown.mjs);
  // failures keep the data directory for debugging, matching the trace
  // retain-on-failure policy.
  globalTeardown: './scripts/ts-e2e-teardown.mjs',
  webServer: {
    command: 'node ./scripts/start-ts-e2e-stack.mjs',
    url: 'http://127.0.0.1:4274/health/ready',
    // Always boot a fresh TS server and SQLite store so no leaked session or
    // data state can affect the deterministic suite.
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        ...(chromiumExecutablePath
          ? { launchOptions: { executablePath: chromiumExecutablePath } }
          : {}),
      },
    },
  ],
});
