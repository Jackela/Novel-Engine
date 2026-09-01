import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readdir, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import {
  exportPublicationCleanupIntents,
  exports as exportRecords,
  projectSnapshots,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DATABASE_FILENAME } from "../../src/shared/infrastructure/db/backup.js";
import { openConnection } from "../../src/shared/infrastructure/db/connection.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import {
  appAt,
  auditEvidence,
  closeTracked,
  committedWithoutAcknowledgement,
  seedRunningExportRetry,
  storedAuditEvidence,
  writeUncommittedPublication,
} from "./export_publication_restart_fixture.js";
import { studioDatabase } from "./job_test_helpers.js";
import { call, ownerJar, seedProject } from "./studio_helpers.js";

describe("export publication restart recovery", () => {
  it("removes an uncommitted final and recovery sidecars before serving", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-restart-"));
    const first = await appAt(directory);
    const owner = await ownerJar(first);
    const project = await seedProject(first, owner, "Uncommitted artifact");
    await closeTracked(first);

    const evidence = await writeUncommittedPublication(directory, {
      projectId: project.id,
      artifactId: "crashed-before-database",
      format: "markdown",
      projectTitle: "Uncommitted artifact",
      chapters: [{ title: "Chapter 1", contentMarkdown: "# Chapter 1\n\nDraft" }],
    });
    const finalPath = join(directory, evidence.relativePath);
    const stagingPath = join(directory, "exports", project.id, ".staging");
    expect(existsSync(finalPath)).toBe(true);
    expect(existsSync(stagingPath)).toBe(true);

    await appAt(directory);

    expect(existsSync(finalPath)).toBe(false);
    expect(existsSync(stagingPath)).toBe(false);
  });

  it("reconciles an uncommitted retry publication before interrupting its running job", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-restart-"));
    const first = await appAt(directory);
    const owner = await ownerJar(first);
    const project = await seedProject(first, owner, "Crashed retry publication");
    const retryId = seedRunningExportRetry(first, project.id, "crashed-publication");
    await closeTracked(first);

    const evidence = await writeUncommittedPublication(directory, {
      projectId: project.id,
      artifactId: "crashed-retry-artifact",
      format: "markdown",
      projectTitle: "Crashed retry publication",
      chapters: [{ title: "Chapter 1", contentMarkdown: "# Chapter 1\n\nDraft" }],
    });
    const finalPath = join(directory, evidence.relativePath);
    const stagingPath = join(directory, "exports", project.id, ".staging");

    const restarted = await appAt(directory);

    expect(existsSync(finalPath)).toBe(false);
    expect(existsSync(stagingPath)).toBe(false);
    const database = studioDatabase(restarted);
    expect(database.select().from(projectSnapshots).all()).toEqual([]);
    expect(database.select().from(exportRecords).all()).toEqual([]);
    expect(database.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
    expect(database.select().from(jobs).all()).toHaveLength(2);
    expect(database.select().from(jobs).where(eq(jobs.id, retryId)).get()).toMatchObject({
      status: "interrupted",
      retry_of_job_id: "crashed-publication-original",
      error: "Job lost its execution lease during process restart.",
    });
    const retryEvents = database
      .select()
      .from(jobEvents)
      .where(eq(jobEvents.job_id, retryId))
      .all();
    expect(retryEvents.map((event) => event.status).sort()).toEqual(["interrupted", "running"]);
  });

  it("keeps committed bytes and removes sidecars left before acknowledgement", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-restart-"));
    const committed = await committedWithoutAcknowledgement(directory);
    const finalPath = join(directory, committed.evidence.relativePath);
    const stagingPath = join(directory, "exports", committed.projectId, ".staging");
    expect(existsSync(stagingPath)).toBe(true);
    await closeTracked(committed.app);

    const restarted = await appAt(directory);

    expect(existsSync(finalPath)).toBe(true);
    expect(existsSync(stagingPath)).toBe(false);
    expect(studioDatabase(restarted).select().from(exportPublicationCleanupIntents).all()).toEqual(
      [],
    );
    expect((await call(restarted, committed.owner, "GET", committed.downloadUrl)).statusCode).toBe(
      200,
    );
  });

  it("restores a missing committed final from its durable stage", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-restart-"));
    const committed = await committedWithoutAcknowledgement(directory);
    const finalPath = join(directory, committed.evidence.relativePath);
    await unlink(finalPath);
    await closeTracked(committed.app);

    await appAt(directory);

    expect(existsSync(finalPath)).toBe(true);
    expect(existsSync(join(directory, "exports", committed.projectId, ".staging"))).toBe(false);
  });

  it("fails closed before job recovery and preserves committed audit rows", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-restart-"));
    const committed = await committedWithoutAcknowledgement(directory);
    const retryId = seedRunningExportRetry(committed.app, committed.projectId, "blocked-recovery");
    const before = auditEvidence(studioDatabase(committed.app));
    const finalPath = join(directory, committed.evidence.relativePath);
    const staging = join(directory, "exports", committed.projectId, ".staging");
    await unlink(finalPath);
    for (const name of await readdir(staging)) {
      if (name.endsWith(".stage")) await unlink(join(staging, name));
    }
    await closeTracked(committed.app);

    await expect(appAt(directory)).rejects.toThrow(/missing|Unsafe/i);
    expect(storedAuditEvidence(directory)).toEqual(before);

    const connection = openConnection(join(directory, DATABASE_FILENAME));
    try {
      expect(connection.db.select().from(jobs).where(eq(jobs.id, retryId)).get()).toMatchObject({
        status: "running",
        error: null,
      });
      expect(
        connection.db
          .select({ status: jobEvents.status })
          .from(jobEvents)
          .where(eq(jobEvents.job_id, retryId))
          .all(),
      ).toEqual([{ status: "running" }]);
    } finally {
      connection.raw.close();
    }
  });

  it("removes a deleted project's directory left by failed post-commit cleanup", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-restart-"));
    const first = await appAt(directory, {
      projectArtifactCleaner: {
        async removeProjectArtifacts() {
          throw new Error("simulated cleanup crash");
        },
      },
    });
    const owner = await ownerJar(first);
    const project = await seedProject(first, owner, "Deleted directory recovery");
    const projectDirectory = join(directory, "exports", project.id);
    await mkdir(projectDirectory, { recursive: true });
    await writeFile(join(projectDirectory, "orphan.md"), "orphan", { flag: "wx" });
    expect((await call(first, owner, "DELETE", `/api/projects/${project.id}`)).statusCode).toBe(
      204,
    );
    expect(existsSync(projectDirectory)).toBe(true);
    await closeTracked(first);

    await appAt(directory);

    expect(existsSync(projectDirectory)).toBe(false);
  });
});
