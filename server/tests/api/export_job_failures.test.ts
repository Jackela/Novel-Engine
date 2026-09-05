import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";
import { describe, expect, it, vi } from "vitest";
import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import { ExportArtifactWriteError } from "../../src/contexts/studio/domain/exceptions.js";
import {
  exports as exportRecords,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { seedProjectWithChapter, studioDatabase } from "./job_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

function throwingGateway(error: Error): ExportArtifactGateway {
  return {
    async writeSnapshotArtifact() {
      throw error;
    },
    async readArtifactBytes() {
      throw new Error("Unexpected artifact read.");
    },
  };
}

function expectNoExportEvidence(app: FastifyInstance): void {
  const database = studioDatabase(app);
  expect(database.select().from(projectSnapshots).all()).toEqual([]);
  expect(database.select().from(snapshotDocuments).all()).toEqual([]);
  expect(database.select().from(exportRecords).all()).toEqual([]);
}

function seedInterruptedExport(
  app: FastifyInstance,
  projectId: string,
  createdAt: Date,
  id = "export-job-interrupted",
): void {
  studioDatabase(app)
    .insert(jobs)
    .values({
      id,
      project_id: projectId,
      document_id: null,
      kind: "export",
      operation: "export",
      status: "interrupted",
      provider: "studio",
      model: "",
      request_json: JSON.stringify({ format: "markdown" }),
      result_json: JSON.stringify({}),
      error: "Job lost its execution lease during process restart.",
      created_at: createdAt,
      updated_at: createdAt,
    })
    .run();
}

describe("export job failure closure", () => {
  it("records a terminal failed job for a known artifact-write failure", async () => {
    const { app } = await buildStudioApp(monotonicClock(), {
      exportArtifactGateway: throwingGateway(new ExportArtifactWriteError()),
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Known export failure");

      const response = await call(app, owner, "POST", `/api/projects/${projectId}/exports`, {
        format: "markdown",
      });

      expect(response.statusCode, response.body).toBe(201);
      expect(response.json<JobPayload>()).toMatchObject({
        kind: "export",
        status: "failed",
        error: "Export artifact could not be written.",
        result: {
          export_id: null,
          snapshot_id: null,
          format: "markdown",
          download_url: null,
        },
      });
      expect(response.json<JobPayload>().events.map((event) => event.status)).toEqual(["failed"]);
      expectNoExportEvidence(app);
      expect(studioDatabase(app).select().from(jobs).all()).toHaveLength(1);
      expect(studioDatabase(app).select().from(jobEvents).all()).toHaveLength(1);
    } finally {
      await app.close();
    }
  });

  it("keeps an unexpected renderer bug opaque without export or job evidence", async () => {
    const { app } = await buildStudioApp(monotonicClock(), {
      exportArtifactGateway: throwingGateway(new TypeError("unexpected renderer bug")),
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Unexpected export failure");

      const response = await call(app, owner, "POST", `/api/projects/${projectId}/exports`, {
        format: "epub",
      });

      expect(response.statusCode, response.body).toBe(500);
      expect(response.json().error.code).toBe("INTERNAL_ERROR");
      expect(response.body).not.toContain("unexpected renderer bug");
      expectNoExportEvidence(app);
      expect(studioDatabase(app).select().from(jobs).all()).toEqual([]);
      expect(studioDatabase(app).select().from(jobEvents).all()).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("reports compensation failure without masking a database publication defect", async () => {
    class ExplodingFreshOutcomeStore extends ExportStorePart {
      protected override beforeFreshJobEventInsert(): never {
        throw new Error("simulated database publication defect");
      }
    }
    const cleanupFailure = new Error("simulated artifact cleanup failure");
    const gateway: ExportArtifactGateway = {
      async writeSnapshotArtifact() {
        return {
          relativePath: "exports/project-1/orphan.md",
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => {
            throw cleanupFailure;
          },
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    };
    const { app } = await buildStudioApp(monotonicClock(), {
      exportStoreFactory: (database) => new ExplodingFreshOutcomeStore(database),
      exportArtifactGateway: gateway,
    });
    const logError = vi.spyOn(app.log, "error").mockImplementation(() => undefined);
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Failed compensation");

      const response = await call(app, owner, "POST", `/api/projects/${projectId}/exports`, {
        format: "markdown",
      });

      expect(response.statusCode, response.body).toBe(500);
      expect(response.body).not.toContain("simulated database publication defect");
      expect(response.body).not.toContain(cleanupFailure.message);
      expect(
        logError.mock.calls.filter(
          ([details, message]) =>
            message === "artifact cleanup failed" &&
            typeof details === "object" &&
            (details as Record<string, unknown>).artifact_cleanup_failed === true,
        ),
      ).toHaveLength(1);
      expectNoExportEvidence(app);
      expect(studioDatabase(app).select().from(jobs).all()).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("marks a retry failed for a known write failure and preserves its original", async () => {
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock, {
      exportArtifactGateway: throwingGateway(new ExportArtifactWriteError()),
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Known retry failure");
      seedInterruptedExport(app, projectId, clock());

      const response = await retryJobRequest(
        app,
        owner,
        `/api/projects/${projectId}/jobs/export-job-interrupted/retry`,
        "known-export-retry-failure-0001",
      );

      expect(response.statusCode, response.body).toBe(200);
      expect(response.json<JobPayload>()).toMatchObject({
        status: "failed",
        retry_of_job_id: "export-job-interrupted",
        error: "Export artifact could not be written.",
      });
      expect(response.json<JobPayload>().events.map((event) => event.status)).toEqual([
        "running",
        "failed",
      ]);
      const listed = await call(app, owner, "GET", `/api/projects/${projectId}/jobs`);
      expect(listed.json().jobs).toMatchObject([
        { status: "failed", retry_of_job_id: "export-job-interrupted" },
        { id: "export-job-interrupted", status: "interrupted" },
      ]);
      expectNoExportEvidence(app);
    } finally {
      await app.close();
    }
  });

  it("leaves a retry running when an unexpected renderer bug escapes", async () => {
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock, {
      exportArtifactGateway: throwingGateway(new TypeError("unexpected retry renderer bug")),
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Unexpected retry failure");
      seedInterruptedExport(app, projectId, clock());

      const response = await retryJobRequest(
        app,
        owner,
        `/api/projects/${projectId}/jobs/export-job-interrupted/retry`,
        "unexpected-export-retry-failure-0001",
      );

      expect(response.statusCode, response.body).toBe(500);
      expect(response.json().error.code).toBe("INTERNAL_ERROR");
      expect(response.body).not.toContain("unexpected retry renderer bug");
      const listed = await call(app, owner, "GET", `/api/projects/${projectId}/jobs`);
      expect(listed.json().jobs).toMatchObject([
        { status: "running" },
        { id: "export-job-interrupted", status: "interrupted" },
      ]);
      const detailUrl = `/api/projects/${projectId}/jobs/${listed.json().jobs[0].id}`;
      const runningDetail = await call(app, owner, "GET", detailUrl);
      expect(runningDetail.json<JobPayload>().events).toMatchObject([{ status: "running" }]);
      expectNoExportEvidence(app);
    } finally {
      await app.close();
    }
  });

  it("lands one coherent retry from the current source after the original was interrupted", async () => {
    const clock = monotonicClock();
    const { app, directory } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Successful export retry");
      const projectId = project.id;
      seedInterruptedExport(app, projectId, clock());
      const current = await getProject(app, owner, projectId);
      const document = current.documents.at(0);
      if (document === undefined) throw new Error("Expected the seeded chapter.");
      const sourceMarker = "Fresh source selected by retry.";
      const updated = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${projectId}/documents/${document.id}`,
        {
          content_markdown: `# Revised chapter\n\n${sourceMarker}`,
          base_revision_id: document.current_revision_id,
        },
      );
      expect(updated.statusCode, updated.body).toBe(200);
      const updatedRevisionId = updated.json().current_revision_id;

      const response = await retryJobRequest(
        app,
        owner,
        `/api/projects/${projectId}/jobs/export-job-interrupted/retry`,
        "updated-export-retry-source-0001",
      );

      expect(response.statusCode, response.body).toBe(200);
      const retry = response.json<JobPayload>();
      expect(retry).toMatchObject({
        status: "completed",
        retry_of_job_id: "export-job-interrupted",
        result: { format: "markdown" },
      });
      expect(retry.events.map((event) => event.status)).toEqual(["running", "completed"]);
      const exportId = retry.result.export_id;
      const snapshotId = retry.result.snapshot_id;
      if (typeof exportId !== "string" || typeof snapshotId !== "string") {
        throw new Error("Completed export retry must expose its evidence ids.");
      }
      const database = studioDatabase(app);
      expect(database.select().from(projectSnapshots).all()).toEqual([
        expect.objectContaining({ id: snapshotId, projectId }),
      ]);
      expect(database.select().from(snapshotDocuments).all()).toEqual([
        expect.objectContaining({ snapshotId, revisionId: updatedRevisionId }),
      ]);
      expect(database.select().from(exportRecords).all()).toEqual([
        expect.objectContaining({ id: exportId, snapshotId, projectId }),
      ]);
      expect(database.select().from(jobs).all()).toHaveLength(2);
      expect(database.select().from(jobEvents).all()).toHaveLength(2);
      expect(retry.events.at(-1)?.details).toEqual({ export_id: exportId });
      const artifactPath = join(directory, "exports", projectId, `${exportId}.md`);
      expect(existsSync(artifactPath)).toBe(true);
      await expect(readFile(artifactPath, "utf8")).resolves.toContain(sourceMarker);
    } finally {
      await app.close();
    }
  });
});
