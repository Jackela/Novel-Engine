import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
  projects,
} from "../../../src/contexts/studio/infrastructure/db/schema.js";
import { owners } from "../../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";
import { makeLegacyWorkspace } from "../../legacy_workspace_fixtures.js";

interface CliHarness {
  directory: string;
  dataDirectory: string;
  databasePath: string;
  lines: string[];
  context: Parameters<typeof runCli>[1];
}

async function cliHarness(): Promise<CliHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-cli-"));
  const dataDirectory = join(directory, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  return {
    directory,
    dataDirectory,
    databasePath,
    lines,
    context: {
      envFile: null,
      workingDirectory: directory,
      env: { DB_URL: `sqlite:///${databasePath}`, APP_ENVIRONMENT: "testing" },
      writeLine: (line: string) => {
        lines.push(line);
      },
    },
  };
}

async function seedMissingCommittedExport(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.databasePath);
  const now = new Date("2026-08-31T18:00:00.000Z");
  try {
    studio.db
      .insert(owners)
      .values({
        id: "owner-recovery",
        username: "owner",
        password_hash: "test-only",
        created_at: now,
      })
      .run();
    studio.db
      .insert(projects)
      .values({
        id: "project-recovery",
        ownerId: "owner-recovery",
        title: "Recovery evidence",
        description: "",
        settingsJson: "{}",
        importHash: null,
        createdAt: now,
        updatedAt: now,
      })
      .run();
    studio.db
      .insert(projectSnapshots)
      .values({
        id: "snapshot-recovery",
        projectId: "project-recovery",
        reason: "export",
        createdAt: now,
      })
      .run();
    studio.db
      .insert(exportArtifacts)
      .values({
        id: "artifact-recovery",
        projectId: "project-recovery",
        snapshotId: "snapshot-recovery",
        format: "markdown",
        relativePath: "exports/project-recovery/artifact-recovery.md",
        sizeBytes: 7,
        checksumSha256: "a".repeat(64),
        createdAt: now,
      })
      .run();
  } finally {
    studio.close();
  }
}

/**
 * Relocated from cli.test.ts to keep that file inside the 300-code-line
 * budget; the assertions are unchanged. The recovery gate and the index
 * reconciliation are different command families, so they keep separate
 * suites.
 */
describe("operational CLI export recovery", () => {
  it("keeps doctor read-only while import and migrate fail before mutation when committed export bytes are missing", async () => {
    const harness = await cliHarness();
    await seedMissingCommittedExport(harness);

    // doctor is read-only by DR-032: it reports the healthy database family and
    // never reconciles; the write paths below carry the recovery gate.
    const doctorCode = await runCli(["doctor"], harness.context);
    expect(doctorCode).toBe(0);
    const doctor = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(doctor.quick_check).toBe("ok");
    expect(doctor.error).toBeNull();
    expect(doctor.document_index).toEqual({ documents: 0, indexed: 0, drifted: false });

    harness.lines.length = 0;
    const migrateCode = await runCli(["migrate"], harness.context);
    expect(migrateCode).toBe(1);
    expect(harness.lines.join("\n")).toMatch(/missing/i);

    harness.lines.length = 0;
    const source = makeLegacyWorkspace(join(harness.directory, "blocked-import"), {
      title: "Must not import",
      chapters: [{ filename: "chapter-001.md", content: "# Blocked\n" }],
    });
    const importCode = await runCli(
      ["import", "--source", source, "--owner", "owner"],
      harness.context,
    );
    expect(importCode).toBe(1);
    expect(harness.lines.join("\n")).toMatch(/missing/i);

    const unchanged = await openStudioDatabase(harness.databasePath);
    try {
      expect(unchanged.db.select().from(projects).all()).toHaveLength(1);
      expect(unchanged.db.select().from(exportArtifacts).all()).toHaveLength(1);
    } finally {
      unchanged.close();
    }
  });
});
