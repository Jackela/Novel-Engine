// CI gate: regenerate the frontend API types from the TS server OpenAPI
// baseline into a temp file and fail when the committed artifact is not
// byte-identical — catches hand edits to generated output and snapshot
// changes that were not followed by `pnpm gen:api-types`.

import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = dirname(fileURLToPath(new URL(".", import.meta.url)));
const projectRoot = join(frontendRoot, "..");
const snapshotPath = join(projectRoot, "server", "qa-baselines", "openapi.current.json");
const committedPath = join(frontendRoot, "generated", "api-types.ts");
// openapi-typescript runs from the tools/api-types container: it crashes on
// typescript@7 (ts.factory undefined — no JS API yet, upstream issue
// openapi-ts/openapi-typescript#2841), so the container pins typescript@6.
const cliPath = join(
  projectRoot,
  "tools",
  "api-types",
  "node_modules",
  "openapi-typescript",
  "bin",
  "cli.js",
);

function fail(message) {
  console.error(`[api-types-drift] ${message}`);
  return 1;
}

function firstDiffLine(committed, regenerated) {
  const committedLines = committed.split("\n");
  const regeneratedLines = regenerated.split("\n");
  const limit = Math.max(committedLines.length, regeneratedLines.length);
  for (let index = 0; index < limit; index += 1) {
    if (committedLines[index] !== regeneratedLines[index]) {
      return {
        line: index + 1,
        committed: committedLines[index] ?? "<missing>",
        regenerated: regeneratedLines[index] ?? "<missing>",
      };
    }
  }
  return null;
}

function main() {
  if (!existsSync(snapshotPath)) {
    return fail(`OpenAPI snapshot not found: ${snapshotPath}`);
  }
  if (!existsSync(committedPath)) {
    return fail(
      `generated types not found: ${committedPath} — run \`pnpm gen:api-types\` and commit the output.`,
    );
  }
  if (!existsSync(cliPath)) {
    return fail(`openapi-typescript CLI not found: ${cliPath} — run \`pnpm install\` first.`);
  }

  const tempDir = mkdtempSync(join(tmpdir(), "api-types-drift-"));
  try {
    const regeneratedPath = join(tempDir, "api-types.ts.tmp");
    execFileSync(process.execPath, [cliPath, snapshotPath, "-o", regeneratedPath], {
      cwd: frontendRoot,
      stdio: "pipe",
    });
    const committed = readFileSync(committedPath);
    const regenerated = readFileSync(regeneratedPath);
    if (committed.equals(regenerated)) {
      console.log(`[api-types-drift] clean: ${committedPath} matches the snapshot.`);
      return 0;
    }
    const diff = firstDiffLine(committed.toString("utf8"), regenerated.toString("utf8"));
    return fail(
      diff
        ? `generated types differ from the snapshot at line ${diff.line}:\n` +
            `  committed:    ${diff.committed}\n` +
            `  regenerated:  ${diff.regenerated}\n` +
            "run `pnpm gen:api-types` and commit the result."
        : "generated types differ from the snapshot — run `pnpm gen:api-types` and commit the result.",
    );
  } catch (error) {
    return fail(
      `openapi-typescript failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

process.exitCode = main();
