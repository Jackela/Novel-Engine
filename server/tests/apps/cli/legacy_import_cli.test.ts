import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import { AuthService } from "../../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";
import { makeLegacyWorkspace } from "../../legacy_workspace_fixtures.js";

async function importHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-import-cli-"));
  const dataDirectory = join(directory, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  const context = {
    envFile: null,
    workingDirectory: directory,
    env: { DB_URL: `sqlite:///${databasePath}`, APP_ENVIRONMENT: "testing" },
    writeLine: (line: string) => lines.push(line),
  };
  const database = await openStudioDatabase(databasePath);
  try {
    await new AuthService({
      store: new DrizzleAuthStore(database.db),
      sessionSecret: "cli-test-session-secret",
    }).configureOwner("owner", "correct horse battery");
  } finally {
    database.close();
  }
  return { directory, lines, context };
}

async function runImport(
  harness: Awaited<ReturnType<typeof importHarness>>,
  source: string,
): Promise<{ code: number; output: string; summary: Record<string, unknown> }> {
  harness.lines.length = 0;
  const code = await runCli(["import", "--source", source, "--owner", "owner"], harness.context);
  expect(harness.lines).toHaveLength(1);
  const output = harness.lines[0] ?? "";
  return { code, output, summary: JSON.parse(output) as Record<string, unknown> };
}

describe("legacy import CLI", () => {
  it("prints a bounded summary independent of chapter Markdown", async () => {
    const harness = await importHarness();
    const smallSource = makeLegacyWorkspace(join(harness.directory, "legacy-small"), {
      title: "CLI Import Story",
      chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
    });
    const chapterMarker = "chapter-markdown-must-not-reach-stdout";
    const largeSource = makeLegacyWorkspace(join(harness.directory, "legacy-large"), {
      title: "CLI Import Story",
      chapters: [{ filename: "chapter-001.md", content: chapterMarker.repeat(4_096) }],
    });

    const small = await runImport(harness, smallSource);
    const large = await runImport(harness, largeSource);

    expect(small.code).toBe(0);
    expect(large.code).toBe(0);
    expect(Object.keys(large.summary).sort()).toEqual([
      "chapter_count",
      "created",
      "description",
      "import_hash",
      "project_id",
      "title",
    ]);
    expect(large.summary).toMatchObject({
      project_id: expect.any(String),
      title: "CLI Import Story",
      description: "",
      import_hash: expect.stringMatching(/^[0-9a-f]{64}$/),
      chapter_count: 1,
      created: true,
    });
    expect(large.output).not.toContain(chapterMarker);
    expect(large.output.length).toBe(small.output.length);

    const repeated = await runImport(harness, largeSource);
    expect(repeated.code).toBe(0);
    expect(repeated.summary.project_id).toBe(large.summary.project_id);
    expect(repeated.summary.created).toBe(false);
    expect(repeated.output).not.toContain(chapterMarker);
  });

  it("reports a capacity failure as exit 1", async () => {
    const harness = await importHarness();
    const source = makeLegacyWorkspace(join(harness.directory, "oversized-legacy"), {
      title: "Oversized CLI Import",
      chapters: [{ filename: "chapter-001.md", content: "x".repeat(4 * 1024 * 1024 + 1) }],
    });

    const code = await runCli(["import", "--source", source, "--owner", "owner"], harness.context);

    expect(code).toBe(1);
    expect(harness.lines).toEqual(["Legacy import capacity exceeded."]);
  });

  it("reports a missing source as usage error exit 2", async () => {
    const harness = await importHarness();

    const code = await runCli(["import"], harness.context);

    expect(code).toBe(2);
    expect(harness.lines).toEqual(["Import requires --source DIR."]);
  });
});
