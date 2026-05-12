import { spawnSync } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(frontendDir, '..');
const defaultOutputPath = path.resolve(
  repoRoot,
  'artifacts',
  'qa',
  'frontend-dependency-audit.json',
);

function parseArgs() {
  let outputPath = defaultOutputPath;
  for (let index = 2; index < process.argv.length; index += 1) {
    const argument = process.argv[index];
    if (argument === '--output') {
      const next = process.argv[index + 1];
      if (!next) {
        throw new Error('Missing value for --output');
      }
      outputPath = path.resolve(process.cwd(), next);
      index += 1;
    }
  }
  return { outputPath };
}

function summarizeIssues(issues) {
  const summary = {
    issue_files: 0,
    unused_dependencies: 0,
    unused_dev_dependencies: 0,
    unlisted_dependencies: 0,
    unresolved_imports: 0,
  };

  if (!Array.isArray(issues)) {
    return summary;
  }

  summary.issue_files = issues.length;
  for (const issue of issues) {
    summary.unused_dependencies += issue.dependencies?.length ?? 0;
    summary.unused_dev_dependencies += issue.devDependencies?.length ?? 0;
    summary.unlisted_dependencies += issue.unlisted?.length ?? 0;
    summary.unresolved_imports += issue.unresolved?.length ?? 0;
  }
  return summary;
}

async function runAudit() {
  const { outputPath } = parseArgs();
  const knipCli = path.resolve(frontendDir, 'node_modules', 'knip', 'bin', 'knip.js');
  const command = [
    knipCli,
    '--dependencies',
    '--reporter',
    'json',
    '--no-progress',
  ];

  const result = spawnSync(process.execPath, command, {
    cwd: frontendDir,
    env: process.env,
    encoding: 'utf8',
  });

  if (result.error) {
    throw result.error;
  }

  const stdout = (result.stdout ?? '').trim();
  const stderr = (result.stderr ?? '').trim();

  let raw = null;
  if (stdout) {
    try {
      raw = JSON.parse(stdout);
    } catch (error) {
      raw = {
        parse_error: error instanceof Error ? error.message : String(error),
        stdout,
      };
    }
  } else {
    raw = { issues: [] };
  }

  const issueSummary = summarizeIssues(raw?.issues);
  const report = {
    generated_at: new Date().toISOString(),
    tool: 'knip',
    command: ['node', ...command],
    summary: {
      ...issueSummary,
      exit_code: result.status ?? 2,
      passed: (result.status ?? 2) === 0,
    },
    stderr: stderr || null,
    raw,
  };

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

  console.log(
    `[frontend-dependency-audit] issue files=${issueSummary.issue_files}, ` +
      `unused deps=${issueSummary.unused_dependencies}, ` +
      `unused devDeps=${issueSummary.unused_dev_dependencies}, ` +
      `unlisted=${issueSummary.unlisted_dependencies}, ` +
      `unresolved=${issueSummary.unresolved_imports}`,
  );
  console.log(`[frontend-dependency-audit] report: ${outputPath}`);

  if (result.status !== 0 && stderr) {
    console.error(stderr);
  }

  process.exit(result.status ?? 2);
}

await runAudit();
