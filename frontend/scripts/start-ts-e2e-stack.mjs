import { spawn } from 'node:child_process';
import { mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import process from 'node:process';

/**
 * Boots the TypeScript backend for the #274 SPA Playwright suite: the emitted
 * CLI (`server/dist/apps/cli/main.js serve`) serves the built frontend from
 * `frontend/dist` at the site root — the same origin, no Vite dev server.
 * Unlike the Python stack harness (start-e2e-stack.mjs), the guest UI talks
 * to the API over the exact same origin the SPA is served from.
 *
 * Prerequisites (CI builds these in earlier steps; locally run them first):
 *   pnpm --dir frontend build && pnpm --dir server build
 */

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(frontendDir, '..');
const serverDistCli = path.join(repoRoot, 'server', 'dist', 'apps', 'cli', 'main.js');
const frontendDist = path.join(frontendDir, 'dist');

const PORT = Number(process.env.TS_E2E_PORT ?? 4274);
const baseURL = `http://127.0.0.1:${PORT}`;

function fail(message) {
  console.error(message);
  process.exit(1);
}

if (!existsSync(serverDistCli)) {
  fail(`Emitted TS CLI not found at ${serverDistCli}. Run pnpm --dir server build first.`);
}
if (!existsSync(path.join(frontendDist, 'index.html'))) {
  fail(`Built SPA not found at ${frontendDist}. Run pnpm --dir frontend build first.`);
}

// Fresh per-boot SQLite store outside the repository: the TS pipeline backs
// up and migrates this directory, and each run must start from a clean slate.
const dataDir = process.env.TS_E2E_DATA_DIR ?? mkdtempSync(join(tmpdir(), 'ne-ts-e2e-'));
const databasePath = path.join(dataDir, 'novel-engine.sqlite3').replaceAll('\\', '/');

const serverEnv = {
  ...process.env,
  APP_ENVIRONMENT: 'testing',
  DB_URL: `sqlite:///${databasePath}`,
  SECURITY_SECRET_KEY:
    process.env.SECURITY_SECRET_KEY ?? 'test-secret-key-for-ts-playwright-1234567890',
  SECURITY_CORS_ORIGINS: process.env.SECURITY_CORS_ORIGINS ?? `${baseURL},http://localhost:${PORT}`,
};

const server = spawn(
  process.execPath,
  [serverDistCli, 'serve', '--host', '127.0.0.1', '--port', String(PORT)],
  { cwd: repoRoot, env: serverEnv, stdio: 'inherit' },
);

let shuttingDown = false;

const shutdown = (exitCode = 0) => {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  server.kill('SIGTERM');
  setTimeout(() => process.exit(exitCode), 1000).unref();
};

const isControlledExit = (code, signal) =>
  shuttingDown || code === 0 || signal === 'SIGTERM' || signal === 'SIGINT';

server.on('exit', (code, signal) => {
  if (!isControlledExit(code, signal)) {
    console.error(`TS server exited with code ${code ?? 'unknown'}`);
    shutdown(code ?? 1);
  }
});

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

async function waitForReady(url) {
  const deadline = Date.now() + 90_000;
  let lastError;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
      lastError = new Error(`${url} responded with ${response.status}`);
    } catch (error) {
      lastError = error;
    }

    await sleep(1000);
  }

  throw lastError ?? new Error(`${url} did not become ready`);
}

try {
  await waitForReady(`${baseURL}/health/ready`);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  shutdown(1);
}

await new Promise(() => {});
