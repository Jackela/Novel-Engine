import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import process from 'node:process';

const args = process.argv.slice(2);
const env = { ...process.env };
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const playwrightCli = path.resolve(frontendDir, 'node_modules', '@playwright', 'test', 'cli.js');

delete env.NO_COLOR;

if (!existsSync(playwrightCli)) {
  console.error(
    `Playwright CLI not found at ${playwrightCli}. Run npm --prefix frontend install first.`,
  );
  process.exit(1);
}

const child = spawn(
  process.execPath,
  [playwrightCli, ...args],
  {
    cwd: frontendDir,
    env,
    stdio: 'inherit',
  },
);

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
