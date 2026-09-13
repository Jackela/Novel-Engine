import { existsSync } from "node:fs";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { DatabaseExportPublicationCleanupJournal } from "../../src/contexts/studio/infrastructure/export_publication_cleanup_journal.js";
import { TEST_SESSION_SECRET } from "./auth_helpers.js";
import { studioDatabase } from "./job_test_helpers.js";
import { ownerJar, seedProject } from "./studio_helpers.js";

async function appAt(directory: string) {
  return buildApp({
    logger: false,
    databasePath: join(directory, "novel-engine.sqlite3"),
    sessionSecret: TEST_SESSION_SECRET,
  });
}

describe("data-directory ownership", () => {
  it("releases ownership when app composition fails after opening persistence", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-data-ownership-build-"));

    await expect(
      buildApp({
        logger: false,
        databasePath: join(directory, "novel-engine.sqlite3"),
        sessionSecret: TEST_SESSION_SECRET,
        exportStoreFactory: () => {
          throw new Error("simulated service composition failure");
        },
      }),
    ).rejects.toThrow("simulated service composition failure");

    const restarted = await appAt(directory);
    await restarted.close();
  });

  it("blocks a second production opener before it reconciles an active writer", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-data-ownership-"));
    const first = await appAt(directory);
    const owner = await ownerJar(first);
    const project = await seedProject(first, owner, "Active writer ownership");
    const evidence = await new FilesystemExportArtifactGateway(directory, {
      cleanupJournal: new DatabaseExportPublicationCleanupJournal(studioDatabase(first)),
    }).writeSnapshotArtifact({
      projectId: project.id,
      artifactId: "active-uncommitted",
      format: "markdown",
      projectTitle: "Active writer ownership",
      chapters: [{ title: "Chapter 1", contentMarkdown: "# Chapter 1\n\nDraft" }],
    });
    const finalPath = join(directory, evidence.relativePath);
    const stagingPath = join(directory, "exports", project.id, ".staging");
    try {
      await expect(appAt(directory)).rejects.toThrow(
        /already owned by another Novel Engine process/i,
      );
      expect(existsSync(finalPath)).toBe(true);
      expect(existsSync(stagingPath)).toBe(true);
    } finally {
      await first.close();
    }

    const restarted = await appAt(directory);
    try {
      expect(existsSync(finalPath)).toBe(false);
      expect(existsSync(stagingPath)).toBe(false);
    } finally {
      await restarted.close();
    }
  });
});
