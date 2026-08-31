import { spawnSync } from "node:child_process";
import { copyFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { describe, expect, it } from "vitest";

const QA_SOURCE_DIRECTORY = resolve(dirname(fileURLToPath(import.meta.url)), "../../scripts/qa");

async function createQaRepository(...scriptNames: readonly string[]): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "novel-engine-qa-gate-"));
  const destination = join(root, "server/scripts/qa");
  await mkdir(destination, { recursive: true });
  await copyFile(join(QA_SOURCE_DIRECTORY, "common.mjs"), join(destination, "common.mjs"));
  await Promise.all(
    scriptNames.map((scriptName) =>
      copyFile(join(QA_SOURCE_DIRECTORY, scriptName), join(destination, scriptName)),
    ),
  );
  return root;
}

function initializeGitRepository(root: string): void {
  const result = spawnSync("git", ["init", "--quiet"], { cwd: root, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`git init failed: ${result.stderr}`);
  }
}

function commitFiles(root: string, ...relativePaths: readonly string[]): void {
  const add = spawnSync("git", ["add", "--", ...relativePaths], { cwd: root, encoding: "utf8" });
  if (add.status !== 0) {
    throw new Error(`git add failed: ${add.stderr}`);
  }
  const commit = spawnSync(
    "git",
    [
      "-c",
      "user.name=QA Gate",
      "-c",
      "user.email=qa@example.invalid",
      "commit",
      "--quiet",
      "-m",
      "baseline",
    ],
    { cwd: root, encoding: "utf8" },
  );
  if (commit.status !== 0) {
    throw new Error(`git commit failed: ${commit.stderr}`);
  }
}

async function writeCandidate(root: string, relativePath: string, contents: string): Promise<void> {
  const absolutePath = join(root, relativePath);
  await mkdir(dirname(absolutePath), { recursive: true });
  await writeFile(absolutePath, contents, "utf8");
}

function runGate(root: string, scriptName: string) {
  return spawnSync(process.execPath, [join(root, "server/scripts/qa", scriptName)], {
    cwd: root,
    encoding: "utf8",
  });
}

interface MigrationEntry {
  readonly idx: number;
  readonly tag: string;
}

async function writeMigrationFixture(
  root: string,
  entries: readonly MigrationEntry[],
  sqlTags: readonly string[],
): Promise<void> {
  await writeCandidate(
    root,
    "server/drizzle/meta/_journal.json",
    `${JSON.stringify({ version: "7", dialect: "sqlite", entries }, null, 2)}\n`,
  );
  await Promise.all(
    sqlTags.map((tag) => writeCandidate(root, `server/drizzle/${tag}.sql`, "-- migration\n")),
  );
}

describe("QA gate regressions", () => {
  it("fails closed when a candidate file cannot be read", async () => {
    const root = await createQaRepository();

    try {
      const commonUrl = pathToFileURL(join(root, "server/scripts/qa/common.mjs")).href;
      const missingPath = join(root, "missing-candidate.ts");
      const result = spawnSync(
        process.execPath,
        [
          "--input-type=module",
          "--eval",
          `import { readTextLines } from ${JSON.stringify(commonUrl)}; readTextLines(${JSON.stringify(missingPath)});`,
        ],
        { encoding: "utf8" },
      );

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("ENOENT");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it.each([
    "server/src/contexts/studio/interface/http/private_payload.ts",
    "server/src/shared/interface/http/private_payload.ts",
  ])("rejects private API payload fields in %s", async (relativePath) => {
    const root = await createQaRepository("check_repo_hygiene.mjs");

    try {
      initializeGitRepository(root);
      await writeCandidate(root, relativePath, "export const raw_model_output = 'secret';\n");

      const result = runGate(root, "check_repo_hygiene.mjs");

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("api_private_payload_surface");
      expect(result.stderr).toContain(relativePath);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("rejects a migration SQL file missing from the journal", async () => {
    const root = await createQaRepository("check_migration_channel.mjs");

    try {
      initializeGitRepository(root);
      await writeMigrationFixture(
        root,
        [{ idx: 0, tag: "0000_init" }],
        ["0000_init", "0001_orphan"],
      );

      const result = runGate(root, "check_migration_channel.mjs");

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("0001_orphan.sql");
      expect(result.stderr).toContain("not referenced by the journal");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("rejects duplicate migration tags in the journal", async () => {
    const root = await createQaRepository("check_migration_channel.mjs");

    try {
      initializeGitRepository(root);
      await writeMigrationFixture(
        root,
        [
          { idx: 0, tag: "0000_init" },
          { idx: 1, tag: "0000_init" },
        ],
        ["0000_init"],
      );

      const result = runGate(root, "check_migration_channel.mjs");

      expect(result.status).toBe(1);
      expect(result.stderr).toContain('duplicate journal tag "0000_init"');
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it.each([
    {
      entry: { idx: 1, tag: "0001_first" },
      expected: "journal entry at position 0 must have idx 0, got 1",
    },
    {
      entry: { idx: 0, tag: "0001_wrong_sequence" },
      expected: 'journal tag "0001_wrong_sequence" must start with 0000_',
    },
  ])("rejects migration journal/file sequence drift: $expected", async ({ entry, expected }) => {
    const root = await createQaRepository("check_migration_channel.mjs");

    try {
      initializeGitRepository(root);
      await writeMigrationFixture(root, [entry], [entry.tag]);

      const result = runGate(root, "check_migration_channel.mjs");

      expect(result.status).toBe(1);
      expect(result.stderr).toContain(expected);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("accepts an llms.txt target present in the current candidate but not HEAD", async () => {
    const root = await createQaRepository("check_llms_txt.mjs");
    const target = "docs/current-candidate.md";

    try {
      initializeGitRepository(root);
      await writeCandidate(
        root,
        "llms.txt",
        `# Index\n\n- [Candidate](https://raw.githubusercontent.com/Jackela/Novel-Engine/main/${target})\n`,
      );
      commitFiles(root, "llms.txt");
      await writeCandidate(root, target, "# Current candidate\n");

      const result = runGate(root, "check_llms_txt.mjs");

      expect(result.status).toBe(0);
      expect(result.stdout).toContain("1 link targets verified against the current candidate");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("rejects an llms.txt target deleted from the current candidate but still present in HEAD", async () => {
    const root = await createQaRepository("check_llms_txt.mjs");
    const target = "docs/deleted-candidate.md";

    try {
      initializeGitRepository(root);
      await writeCandidate(
        root,
        "llms.txt",
        `# Index\n\n- [Deleted](https://raw.githubusercontent.com/Jackela/Novel-Engine/main/${target})\n`,
      );
      await writeCandidate(root, target, "# Baseline only\n");
      commitFiles(root, "llms.txt", target);
      await rm(join(root, target));

      const result = runGate(root, "check_llms_txt.mjs");

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("link target missing from the current candidate");
      expect(result.stderr).toContain(target);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
