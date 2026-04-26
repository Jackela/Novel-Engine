import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import process from 'node:process';
import { setTimeout as sleep } from 'node:timers/promises';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(frontendDir, '..');

const pythonBin = process.env.PYTHON_BIN ?? (process.platform === 'win32' ? 'python' : 'python3');
const npmBin = process.platform === 'win32' ? 'npm.cmd' : 'npm';

function spawnProcess(command, args, cwd, env) {
  return spawn(command, args, {
    cwd,
    env,
    stdio: 'inherit',
  });
}

function spawnLocalBin(command, args, cwd, env) {
  return spawn(command, args, {
    cwd,
    env,
    shell: process.platform === 'win32',
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

const backendEnv = {
  ...process.env,
  APP_ENVIRONMENT: process.env.APP_ENVIRONMENT ?? 'testing',
  SECURITY_SECRET_KEY:
    process.env.SECURITY_SECRET_KEY ?? 'test-secret-key-for-playwright-1234567890',
  MONITORING_METRICS_ENABLED: process.env.MONITORING_METRICS_ENABLED ?? 'false',
  // Ordinary Playwright smoke should be deterministic. Use E2E_LLM_PROVIDER
  // when a live provider is explicitly desired.
  LLM_PROVIDER: e2eProvider,
  CORS_ALLOWED_ORIGINS:
    process.env.CORS_ALLOWED_ORIGINS ??
    'http://127.0.0.1:4273,http://localhost:4273',
};

const backendPort = await getFreePort();
const backendUrl = `http://127.0.0.1:${backendPort}`;
const backend = spawnProcess(
  pythonBin,
  ['-m', 'uvicorn', 'src.apps.api.main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
  repoRoot,
  backendEnv,
);

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

backend.on('exit', (code) => {
  if (!shuttingDown && code !== 0) {
    console.error(`Backend server exited with code ${code ?? 'unknown'}`);
    shutdown(code ?? 1);
  }
});

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

await waitForUrl(`${backendUrl}/health/live`, 'backend health');

frontend = spawnLocalBin(
  npmBin,
  ['exec', '--', 'vite', '--host', '127.0.0.1', '--port', '4273'],
  frontendDir,
  {
    ...process.env,
    VITE_API_BASE_URL: backendUrl,
    VITE_API_TIMEOUT: process.env.VITE_API_TIMEOUT ?? '300000',
    VITE_API_PROXY_TARGET: backendUrl,
  },
);

frontend.on('exit', (code) => {
  if (!shuttingDown && code !== 0) {
    console.error(`Frontend server exited with code ${code ?? 'unknown'}`);
    shutdown(code ?? 1);
  }
});

await waitForUrl('http://127.0.0.1:4273', 'frontend dev server');

await new Promise(() => {});
