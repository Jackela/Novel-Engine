import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import process from 'node:process';
import { setTimeout as sleep } from 'node:timers/promises';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(frontendDir, '..');

const viteCli = path.resolve(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js');

function spawnProcess(command, args, cwd, env) {
  return spawn(command, args, {
    cwd,
    env,
    stdio: 'inherit',
  });
}

async function getFreePort() {
  const server = createServer();

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });

  const address = server.address();

  await new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }

      resolve();
    });
  });

  if (address == null || typeof address === 'string') {
    throw new Error('Unable to reserve an ephemeral backend port.');
  }

  return address.port;
}

async function waitForUrl(url, label) {
  const deadline = Date.now() + 90_000;
  let lastError;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
      lastError = new Error(`${label} responded with ${response.status}`);
    } catch (error) {
      lastError = error;
    }

    await sleep(1000);
  }

  throw lastError ?? new Error(`${label} did not become ready`);
}

const e2eProvider = process.env.E2E_LLM_PROVIDER ?? 'mock';
const dataDir = path.resolve(process.env.APP_DATA_DIR ?? path.join(repoRoot, 'data', 'playwright'));
const databasePath = path.join(dataDir, 'novel-engine.sqlite3').replaceAll('\\', '/');

const backendEnv = {
  ...process.env,
  APP_ENVIRONMENT: process.env.APP_ENVIRONMENT ?? 'testing',
  APP_DATA_DIR: dataDir,
  DB_URL: process.env.DB_URL ?? `sqlite:///${databasePath}`,
  SECURITY_SECRET_KEY:
    process.env.SECURITY_SECRET_KEY ?? 'test-secret-key-for-playwright-1234567890',
  MONITORING_METRICS_ENABLED: process.env.MONITORING_METRICS_ENABLED ?? 'false',
  // Ordinary Playwright smoke should be deterministic. Use E2E_LLM_PROVIDER
  // when a live provider is explicitly desired.
  LLM_PROVIDER: e2eProvider,
  CORS_ALLOWED_ORIGINS:
    process.env.CORS_ALLOWED_ORIGINS ?? 'http://127.0.0.1:4273,http://localhost:4273',
};

const backendPort = await getFreePort();
const backendUrl = `http://127.0.0.1:${backendPort}`;
const backendCommand = process.env.PYTHON_BIN ?? 'uv';
const backendArgs = process.env.PYTHON_BIN
  ? [
      '-m',
      'src.apps.cli.novel_engine',
      'serve',
      '--host',
      '127.0.0.1',
      '--port',
      String(backendPort),
    ]
  : [
      'run',
      'python',
      '-m',
      'src.apps.cli.novel_engine',
      'serve',
      '--host',
      '127.0.0.1',
      '--port',
      String(backendPort),
    ];
const backend = spawnProcess(backendCommand, backendArgs, repoRoot, backendEnv);

let frontend = null;
let shuttingDown = false;

const shutdown = (exitCode = 0) => {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  backend.kill('SIGTERM');
  frontend?.kill('SIGTERM');
  setTimeout(() => process.exit(exitCode), 1000).unref();
};

function isControlledExit(code, signal) {
  return shuttingDown || code === 0 || signal === 'SIGTERM' || signal === 'SIGINT';
}

backend.on('exit', (code, signal) => {
  if (!isControlledExit(code, signal)) {
    console.error(`Backend server exited with code ${code ?? 'unknown'}`);
    shutdown(code ?? 1);
  }
});

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

await waitForUrl(`${backendUrl}/health/live`, 'backend health');

if (!existsSync(viteCli)) {
  console.error(`Vite CLI not found at ${viteCli}. Run npm --prefix frontend install first.`);
  shutdown(1);
}

frontend = spawnProcess(
  process.execPath,
  [viteCli, '--host', '127.0.0.1', '--port', '4273'],
  frontendDir,
  {
    ...process.env,
    VITE_API_BASE_URL: backendUrl,
    VITE_API_TIMEOUT: process.env.VITE_API_TIMEOUT ?? '300000',
    VITE_API_PROXY_TARGET: backendUrl,
  },
);

frontend.on('exit', (code, signal) => {
  if (!isControlledExit(code, signal)) {
    console.error(`Frontend server exited with code ${code ?? 'unknown'}`);
    shutdown(code ?? 1);
  }
});

await waitForUrl('http://127.0.0.1:4273', 'frontend dev server');

await new Promise(() => {});
