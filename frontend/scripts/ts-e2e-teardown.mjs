import { rmSync } from "node:fs";

/**
 * #276 global teardown for the TS-stack suite: a passing run leaves nothing
 * behind. The Playwright config marks ownership via TS_E2E_OWN_DATA_DIR (set
 * only when the config itself created the fresh data directory); failures
 * keep the directory for debugging, matching retain-on-failure traces.
 */
export default async function teardown(options) {
  const passed = options?.status === "passed";
  const owns = process.env.TS_E2E_OWN_DATA_DIR === "1";
  const directory = process.env.TS_E2E_DATA_DIR;
  if (passed && owns && directory) {
    rmSync(directory, { recursive: true, force: true });
  }
}
