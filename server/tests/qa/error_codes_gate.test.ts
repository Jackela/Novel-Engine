import { spawnSync } from "node:child_process";
import { copyFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const QA_SOURCE_DIRECTORY = resolve(dirname(fileURLToPath(import.meta.url)), "../../scripts/qa");

async function createQaRepository(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "novel-engine-error-codes-gate-"));
  const destination = join(root, "server/scripts/qa");
  await mkdir(destination, { recursive: true });
  await copyFile(join(QA_SOURCE_DIRECTORY, "common.mjs"), join(destination, "common.mjs"));
  await copyFile(
    join(QA_SOURCE_DIRECTORY, "check_error_codes.mjs"),
    join(destination, "check_error_codes.mjs"),
  );
  return root;
}

function initializeGitRepository(root: string): void {
  const result = spawnSync("git", ["init", "--quiet"], { cwd: root, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`git init failed: ${result.stderr}`);
  }
}

async function writeCandidate(root: string, relativePath: string, contents: string): Promise<void> {
  const absolutePath = join(root, relativePath);
  await mkdir(dirname(absolutePath), { recursive: true });
  await writeFile(absolutePath, contents, "utf8");
}

function runGate(root: string) {
  return spawnSync(process.execPath, [join(root, "server/scripts/qa/check_error_codes.mjs")], {
    cwd: root,
    encoding: "utf8",
  });
}

const ERROR_CODES_FIXTURE = `export const ERROR_CODES = {\n  ALPHA: "ALPHA",\n  BETA: "BETA",\n} as const;\n`;
const ERROR_STATUS_FIXTURE = `export const ERROR_HTTP_STATUS = {\n  ALPHA: 401,\n  BETA: 422,\n} as const satisfies Record<ErrorCode, number>;\n`;
const CATALOG_FIXTURE = `# Error codes\n\n| Code | HTTP | Meaning | Action |\n| --- | --- | --- | --- |\n| \`ALPHA\` | 401 | Meaning. | Act. |\n| \`BETA\` | 422 | Meaning. | Act. |\n`;

async function writeCandidateFiles(
  root: string,
  catalog: string,
  statuses: string,
  codes: string,
): Promise<void> {
  await writeCandidate(root, "docs/agents/error-codes.md", catalog);
  await writeCandidate(root, "server/src/shared/domain/error_codes.ts", codes);
  await writeCandidate(root, "server/src/shared/interface/http/error_envelope.ts", statuses);
}

describe("error codes lockstep gate", () => {
  it("accepts a catalog in lockstep with both TS sources", async () => {
    const root = await createQaRepository();

    try {
      initializeGitRepository(root);
      await writeCandidateFiles(root, CATALOG_FIXTURE, ERROR_STATUS_FIXTURE, ERROR_CODES_FIXTURE);

      const result = runGate(root);

      expect(result.status, result.stderr).toBe(0);
      expect(result.stdout).toContain("2 codes verified in lockstep");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it.each([
    {
      drift: "lists a code absent from both TS sources",
      catalog: `${CATALOG_FIXTURE}| \`PHANTOM\` | 404 | Meaning. | Act. |\n`,
      expected: "lists code `PHANTOM`, which is absent from both ERROR_CODES and ERROR_HTTP_STATUS",
    },
    {
      drift: "omits a code declared by ERROR_CODES",
      catalog: CATALOG_FIXTURE.replace("| `BETA` | 422 | Meaning. | Act. |\n", ""),
      expected: "is missing code `BETA` declared by ERROR_CODES",
    },
    {
      drift: "maps a code to the wrong HTTP status",
      catalog: CATALOG_FIXTURE.replace("| `BETA` | 422", "| `BETA` | 500"),
      expected: "maps `BETA` to HTTP 500, but ERROR_HTTP_STATUS declares 422",
    },
    {
      drift: "duplicates a catalog row",
      catalog: `${CATALOG_FIXTURE}| \`ALPHA\` | 500 | Meaning. | Act. |\n`,
      expected: "duplicate catalog row for `ALPHA`",
    },
    {
      drift: "declares an HTTP status outside ERROR_CODES",
      statuses: ERROR_STATUS_FIXTURE.replace("  BETA: 422,", "  BETA: 422,\n  PHANTOM: 404,"),
      expected: "ERROR_HTTP_STATUS declares `PHANTOM`, which ERROR_CODES",
    },
    {
      drift: "has an unparsable entry in ERROR_CODES",
      codes: ERROR_CODES_FIXTURE.replace('  BETA: "BETA",', '  BETA: "BETA", // legacy alias'),
      expected: "contains an entry inside ERROR_CODES that the lockstep gate cannot parse",
    },
    {
      drift: "omits an HTTP status for a declared code",
      statuses: ERROR_STATUS_FIXTURE.replace("  BETA: 422,\n", ""),
      expected: "no HTTP status for code `BETA`",
    },
    {
      drift: "has an unparsable entry in ERROR_HTTP_STATUS",
      statuses: ERROR_STATUS_FIXTURE.replace("  BETA: 422,", "  BETA: 422, // legacy alias"),
      expected: "contains an entry inside ERROR_HTTP_STATUS that the lockstep gate cannot parse",
    },
    {
      drift: "deletes the ERROR_HTTP_STATUS declaration line",
      statuses: ERROR_STATUS_FIXTURE.replace("export const ERROR_HTTP_STATUS = {\n", ""),
      expected: "must declare `export const ERROR_HTTP_STATUS = {`",
    },
    {
      drift: "leaves the ERROR_HTTP_STATUS block unclosed",
      statuses: ERROR_STATUS_FIXTURE.replace("} as const satisfies", " as const satisfies"),
      expected: "must close the `export const ERROR_HTTP_STATUS = {` block before end of file",
    },
    {
      drift: "empties the ERROR_HTTP_STATUS declaration body",
      statuses: ERROR_STATUS_FIXTURE.replace("  ALPHA: 401,\n  BETA: 422,\n", ""),
      expected: "declares no HTTP statuses; the drift gate found nothing to check",
    },
  ])("rejects a catalog that $drift", async ({ catalog, statuses, codes, expected }) => {
    const root = await createQaRepository();

    try {
      initializeGitRepository(root);
      await writeCandidateFiles(
        root,
        catalog ?? CATALOG_FIXTURE,
        statuses ?? ERROR_STATUS_FIXTURE,
        codes ?? ERROR_CODES_FIXTURE,
      );

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain(expected);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
