import { rm } from "node:fs/promises";
import type { FastifyInstance } from "fastify";
import { describe, expect, it, vi } from "vitest";

import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import { exports as exportRecords } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { jobs } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  type CookieJar,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

type CleanupPhase = "acknowledge" | "rollback";

interface DeferredCleanupGateway {
  readonly gateway: ExportArtifactGateway;
  readonly started: Promise<void>;
  release(): void;
  readonly writes: () => number;
  readonly acknowledgements: () => number;
  readonly rollbacks: () => number;
}

function deferredFirstCleanup(phase: CleanupPhase, cleanupFailure?: Error): DeferredCleanupGateway {
  let writes = 0;
  let acknowledgements = 0;
  let rollbacks = 0;
  let announceStarted: (() => void) | undefined;
  let releaseCleanup: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    announceStarted = resolve;
  });
  const blocked = new Promise<void>((resolve) => {
    releaseCleanup = resolve;
  });

  async function runFirstCleanup(index: number, currentPhase: CleanupPhase): Promise<void> {
    if (index !== 0 || currentPhase !== phase) return;
    announceStarted?.();
    await blocked;
    if (cleanupFailure !== undefined) throw cleanupFailure;
  }

  return {
    gateway: {
      async writeSnapshotArtifact(request) {
        const index = writes++;
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => {
            acknowledgements += 1;
            await runFirstCleanup(index, "acknowledge");
          },
          rollback: async () => {
            rollbacks += 1;
            await runFirstCleanup(index, "rollback");
          },
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    },
    started,
    release: () => releaseCleanup?.(),
    writes: () => writes,
    acknowledgements: () => acknowledgements,
    rollbacks: () => rollbacks,
  };
}

function cleanupReporter(app: FastifyInstance): {
  readonly reports: unknown[];
  restore(): void;
} {
  const reports: unknown[] = [];
  const spy = vi.spyOn(app.log, "error").mockImplementation((details, message) => {
    if (message === "artifact cleanup failed") reports.push(details);
  });
  return { reports, restore: () => spy.mockRestore() };
}

async function expectApplicationCapacity(
  app: FastifyInstance,
  owner: CookieJar,
  projectId: string,
): Promise<void> {
  const refused = await call(app, owner, "POST", `/api/projects/${projectId}/exports`, {
    format: "markdown",
  });
  expect(refused.statusCode, refused.body).toBe(503);
  expect(refused.headers["retry-after"]).toBe("5");
  expect(refused.json().error).toMatchObject({
    code: "OPERATION_CAPACITY_EXCEEDED",
    details: { scope: "application", limit: 1, in_flight: 1, project_id: projectId },
  });
}

class FailFirstFreshExportStore extends ExportStorePart {
  private shouldFail = true;

  protected override beforeFreshJobEventInsert(): void {
    if (!this.shouldFail) return;
    this.shouldFail = false;
    throw new Error("simulated fresh export persistence failure");
  }
}

function seedInterruptedExport(app: FastifyInstance, projectId: string, now: Date): void {
  studioDatabase(app)
    .insert(jobs)
    .values({
      id: "capacity-interrupted-export",
      project_id: projectId,
      document_id: null,
      kind: "export",
      operation: "export",
      status: "interrupted",
      provider: "studio",
      model: "",
      request_json: JSON.stringify({ format: "markdown" }),
      result_json: "{}",
      error: "restart interrupted the export",
      created_at: now,
      updated_at: now,
    })
    .run();
}

describe("export capacity cleanup lifetime", () => {
  it.each([
    { label: "successful acknowledgement", cleanupFailure: undefined, expectedReports: 0 },
    {
      label: "failed acknowledgement",
      cleanupFailure: new Error("simulated acknowledgement cleanup failure"),
      expectedReports: 1,
    },
  ])("holds a fresh-export permit through $label", async ({ cleanupFailure, expectedReports }) => {
    const deferred = deferredFirstCleanup("acknowledge", cleanupFailure);
    const { app, directory } = await buildStudioApp(monotonicClock(), {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      exportArtifactGateway: deferred.gateway,
    });
    const reporter = cleanupReporter(app);
    try {
      const owner = await ownerJar(app);
      const firstProject = await seedProject(app, owner, "Acknowledgement owner");
      const secondProject = await seedProject(app, owner, "Acknowledgement contender");
      const pending = call(app, owner, "POST", `/api/projects/${firstProject.id}/exports`, {
        format: "markdown",
      });
      await deferred.started;

      expect(studioDatabase(app).select().from(jobs).all()).toMatchObject([
        { project_id: firstProject.id, status: "completed" },
      ]);
      await expectApplicationCapacity(app, owner, secondProject.id);
      expect(deferred.writes()).toBe(1);

      deferred.release();
      const completed = await pending;
      expect(completed.statusCode, completed.body).toBe(201);
      expect(completed.json<JobPayload>()).toMatchObject({ kind: "export", status: "completed" });
      expect(reporter.reports).toHaveLength(expectedReports);
      expect(deferred.rollbacks()).toBe(0);

      const admitted = await call(app, owner, "POST", `/api/projects/${secondProject.id}/exports`, {
        format: "markdown",
      });
      expect(admitted.statusCode, admitted.body).toBe(201);
      expect(admitted.json<JobPayload>().status).toBe("completed");
      expect(deferred.acknowledgements()).toBe(2);
    } finally {
      deferred.release();
      reporter.restore();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it.each([
    { label: "successful rollback", cleanupFailure: undefined, expectedReports: 0 },
    {
      label: "failed rollback",
      cleanupFailure: new Error("simulated rollback cleanup failure"),
      expectedReports: 1,
    },
  ])("holds a fresh-export permit through $label", async ({ cleanupFailure, expectedReports }) => {
    const deferred = deferredFirstCleanup("rollback", cleanupFailure);
    const { app, directory } = await buildStudioApp(monotonicClock(), {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      exportArtifactGateway: deferred.gateway,
      exportStoreFactory: (database) => new FailFirstFreshExportStore(database),
    });
    const reporter = cleanupReporter(app);
    try {
      const owner = await ownerJar(app);
      const firstProject = await seedProject(app, owner, "Rollback owner");
      const secondProject = await seedProject(app, owner, "Rollback contender");
      const pending = call(app, owner, "POST", `/api/projects/${firstProject.id}/exports`, {
        format: "markdown",
      });
      await deferred.started;

      expect(studioDatabase(app).select().from(jobs).all()).toEqual([]);
      expect(studioDatabase(app).select().from(exportRecords).all()).toEqual([]);
      await expectApplicationCapacity(app, owner, secondProject.id);
      expect(deferred.writes()).toBe(1);

      deferred.release();
      const failed = await pending;
      expect(failed.statusCode, failed.body).toBe(500);
      expect(failed.json().error.code).toBe("INTERNAL_ERROR");
      expect(failed.body).not.toContain("simulated fresh export persistence failure");
      expect(failed.body).not.toContain(cleanupFailure?.message ?? "no cleanup failure");
      expect(reporter.reports).toHaveLength(expectedReports);
      expect(deferred.rollbacks()).toBe(1);

      const admitted = await call(app, owner, "POST", `/api/projects/${secondProject.id}/exports`, {
        format: "markdown",
      });
      expect(admitted.statusCode, admitted.body).toBe(201);
      expect(admitted.json<JobPayload>().status).toBe("completed");
    } finally {
      deferred.release();
      reporter.restore();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("holds an export-retry permit through acknowledgement", async () => {
    const clock = monotonicClock();
    const deferred = deferredFirstCleanup("acknowledge");
    const { app, directory } = await buildStudioApp(clock, {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      exportArtifactGateway: deferred.gateway,
    });
    const reporter = cleanupReporter(app);
    try {
      const owner = await ownerJar(app);
      const firstProject = await seedProject(app, owner, "Retry acknowledgement owner");
      const secondProject = await seedProject(app, owner, "Retry acknowledgement contender");
      seedInterruptedExport(app, firstProject.id, clock());
      const pending = call(
        app,
        owner,
        "POST",
        `/api/projects/${firstProject.id}/jobs/capacity-interrupted-export/retry`,
        undefined,
        { "idempotency-key": "capacity-export-cleanup-retry-0001" },
      );
      await deferred.started;

      expect(studioDatabase(app).select().from(jobs).all()).toMatchObject([
        { id: "capacity-interrupted-export", status: "interrupted" },
        { status: "completed", retry_of_job_id: "capacity-interrupted-export" },
      ]);
      await expectApplicationCapacity(app, owner, secondProject.id);

      deferred.release();
      const completed = await pending;
      expect(completed.statusCode, completed.body).toBe(200);
      expect(completed.json<JobPayload>()).toMatchObject({
        kind: "export",
        status: "completed",
        retry_of_job_id: "capacity-interrupted-export",
      });
      expect(completed.json<JobPayload>().events.map((event) => event.status)).toEqual([
        "running",
        "completed",
      ]);
      expect(reporter.reports).toHaveLength(0);

      const admitted = await call(app, owner, "POST", `/api/projects/${secondProject.id}/exports`, {
        format: "markdown",
      });
      expect(admitted.statusCode, admitted.body).toBe(201);
      expect(deferred.acknowledgements()).toBe(2);
      expect(deferred.rollbacks()).toBe(0);
    } finally {
      deferred.release();
      reporter.restore();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
