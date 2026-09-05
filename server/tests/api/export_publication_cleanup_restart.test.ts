import { existsSync } from "node:fs";
import { mkdtemp, readdir, readFile, rename } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "../../src/apps/api/app.js";
import { exportPublicationCleanupIntents } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { DATABASE_FILENAME } from "../../src/shared/infrastructure/db/backup.js";
import { openConnection } from "../../src/shared/infrastructure/db/connection.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { TEST_SESSION_SECRET } from "./auth_helpers.js";
import { studioDatabase } from "./job_test_helpers.js";
import { ownerJar, seedProject } from "./studio_helpers.js";

const openApps: Array<Awaited<ReturnType<typeof buildApp>>> = [];

afterEach(async () => {
  while (openApps.length > 0) await openApps.pop()?.close();
});

describe("export cleanup authority restart ordering", () => {
  it("fails before job recovery and preserves an unowned cleanup quarantine", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-cleanup-restart-"));
    const first = await buildApp({
      logger: false,
      databasePath: join(directory, "novel-engine.sqlite3"),
      sessionSecret: TEST_SESSION_SECRET,
    });
    openApps.push(first);
    const owner = await ownerJar(first);
    const project = await seedProject(first, owner, "Unowned cleanup quarantine");
    const now = new Date("2026-09-01T00:00:00.000Z");
    studioDatabase(first)
      .insert(jobs)
      .values({
        id: "cleanup-blocked-running",
        project_id: project.id,
        document_id: null,
        kind: "export",
        operation: "export",
        status: "running",
        provider: "studio",
        model: "",
        request_json: '{"format":"markdown"}',
        result_json: "{}",
        error: null,
        retry_of_job_id: null,
        created_at: now,
        updated_at: now,
        started_at: now,
        finished_at: null,
      })
      .run();
    studioDatabase(first)
      .insert(jobEvents)
      .values({
        id: "cleanup-blocked-running-event",
        job_id: "cleanup-blocked-running",
        status: "running",
        details_json: "{}",
        created_at: now,
      })
      .run();
    openApps.pop();
    await first.close();

    const evidence = await new FilesystemExportArtifactGateway(directory).writeSnapshotArtifact({
      projectId: project.id,
      artifactId: "unowned-cleanup",
      format: "markdown",
      projectTitle: "Unowned cleanup quarantine",
      chapters: [{ title: "Chapter 1", contentMarkdown: "# Chapter 1\n\nDraft" }],
    });
    const staging = join(directory, "exports", project.id, ".staging");
    const manifestName = (await readdir(staging)).find((name) => name.endsWith(".manifest.json"));
    if (manifestName === undefined) throw new Error("Expected a recovery manifest.");
    const manifest = join(staging, manifestName);
    const quarantine = `${manifest}.cleanup-interrupted`;
    await rename(manifest, quarantine);

    await expect(
      buildApp({
        logger: false,
        databasePath: join(directory, "novel-engine.sqlite3"),
        sessionSecret: TEST_SESSION_SECRET,
      }),
    ).rejects.toThrow(/cleanup intent is missing/i);

    expect(existsSync(join(directory, evidence.relativePath))).toBe(true);
    await expect(readFile(quarantine, "utf8")).resolves.toContain(
      '"artifact_id":"unowned-cleanup"',
    );
    const connection = openConnection(join(directory, DATABASE_FILENAME));
    try {
      expect(connection.db.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
      expect(
        connection.db.select().from(jobs).where(eq(jobs.id, "cleanup-blocked-running")).get(),
      ).toMatchObject({ status: "running", error: null });
      expect(
        connection.db
          .select({ status: jobEvents.status })
          .from(jobEvents)
          .where(eq(jobEvents.job_id, "cleanup-blocked-running"))
          .all(),
      ).toEqual([{ status: "running" }]);
    } finally {
      connection.raw.close();
    }
  });
});
