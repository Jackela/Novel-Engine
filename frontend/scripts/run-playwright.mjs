import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import process from 'node:process';

const args = process.argv.slice(2);
const env = { ...process.env };
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const npmBin = process.platform === 'win32' ? 'npm.cmd' : 'npm';

delete env.NO_COLOR;

const child = spawn(
  npmBin,
  ['exec', '--', 'playwright', ...args],
  {
    cwd: frontendDir,
    env,
    shell: process.platform === 'win32',
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
