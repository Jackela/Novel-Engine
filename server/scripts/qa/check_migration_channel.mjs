import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { listRepoFiles, readTextLines, repoRoot, reportFailures } from "./common.mjs";

/**
 * Migration-channel gate (#264): generated migration files are the single
 * schema evolution channel. The ad-hoc schema-{{push}} tool of the ORM
 * kit must never appear anywhere in the tracked tree (scripts, workflows,
 * docs-as-instructions), and the migrations channel itself must be real —
 * a journal plus every migration file it references. The banned literal is
 * assembled from fragments so this gate never matches its own source.
 */

const MIGRATIONS_DIRECTORY = "server/drizzle";
const JOURNAL_PATH = `${MIGRATIONS_DIRECTORY}/meta/_journal.json`;

// Fragments join into: /drizzle-kit(?:@[^\s]+)?\s+push/i — also catches
// versioned invocations such as `npx drizzle-kit@latest push`.
const BANNED_SCHEMA_PUSH = new RegExp(
  ["driz", "zle-kit(?:@[^\\s]+)?\\s+", "pu", "sh"].join(""),
  "i",
);

const SKIP_PATHS = new Set([
  JOURNAL_PATH,
  "pnpm-lock.yaml",
  "uv.lock",
  "server/scripts/qa/check_migration_channel.mjs",
]);
const SKIP_PARTS = new Set([
  ".git",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  ".venv",
  "coverage",
  "dist",
  "htmlcov",
  "node_modules",
  "playwright-report",
  "test-results",
]);

function shouldSkip(relativePath) {
  if (SKIP_PATHS.has(relativePath)) {
    return true;
  }
  return relativePath.split("/").some((part) => SKIP_PARTS.has(part));
}

function bannedCommandFailures(root) {
  const failures = [];
  for (const relativePath of listRepoFiles(root)) {
    if (shouldSkip(relativePath)) {
      continue;
    }
    const lines = readTextLines(join(root, relativePath));
    for (let index = 0; index < lines.length; index += 1) {
      if (BANNED_SCHEMA_PUSH.test(lines[index])) {
        failures.push(
          `${relativePath}:${index + 1}: direct schema-{{push}} invocation is banned; ship a generated migration instead (${lines[index].trim()})`,
        );
      }
    }
  }
  return failures;
}

function migrationChannelFailures(root) {
  const failures = [];
  const journalPath = join(root, JOURNAL_PATH);
  if (!existsSync(journalPath)) {
    failures.push(`${JOURNAL_PATH}: the migrations journal is missing — run db:generate first`);
    return failures;
  }
  let entries;
  try {
    entries = JSON.parse(readFileSync(journalPath, "utf8")).entries;
  } catch (error) {
    failures.push(`${JOURNAL_PATH}: unreadable journal (${error.message})`);
    return failures;
  }
  if (!Array.isArray(entries) || entries.length === 0) {
    failures.push(`${JOURNAL_PATH}: journal lists no migrations — the channel is empty`);
    return failures;
  }
  for (const entry of entries) {
    const migrationPath = join(MIGRATIONS_DIRECTORY, `${entry.tag}.sql`);
    if (typeof entry.tag !== "string" || !existsSync(join(root, migrationPath))) {
      failures.push(`${JOURNAL_PATH}: journal entry ${JSON.stringify(entry.tag)} has no .sql file`);
    }
  }
  return failures;
}

const root = repoRoot();
const failures = [...bannedCommandFailures(root), ...migrationChannelFailures(root)];
if (failures.length === 0) {
  console.log("[migration-channel] clean: generated migrations are the sole schema channel");
} else {
  reportFailures("migration-channel", failures);
}
