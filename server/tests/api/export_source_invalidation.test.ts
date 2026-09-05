import { describe, expect, it } from "vitest";
import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import {
  exports as exportRecords,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { firstDocument, studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

function deferredGateway(): {
  gateway: ExportArtifactGateway;
  started: Promise<void>;
  release: () => void;
  rollbackCount: () => number;
} {
  let announceStarted: (() => void) | undefined;
  let releaseWrite: (() => void) | undefined;
  let rollbacks = 0;
  const started = new Promise<void>((resolve) => {
    announceStarted = resolve;
  });
  const waitForRelease = new Promise<void>((resolve) => {
    releaseWrite = resolve;
  });
  return {
    gateway: {
      async writeSnapshotArtifact(request) {
        announceStarted?.();
        await waitForRelease;
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => {
            rollbacks += 1;
          },
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    },
    started,
    release: () => releaseWrite?.(),
    rollbackCount: () => rollbacks,
  };
}

describe("export source invalidation", () => {
  it("records a failed job and no evidence when a captured document is deleted", async () => {
    const deferred = deferredGateway();
    const { app } = await buildStudioApp(monotonicClock(), {
      exportArtifactGateway: deferred.gateway,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Concurrent export deletion");
      const document = firstDocument(project);
      const pending = call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });
      await deferred.started;

      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
      deferred.release();

      const response = await pending;
      expect(response.statusCode, response.body).toBe(201);
      expect(response.json<JobPayload>()).toMatchObject({
        status: "failed",
        error: "Export source changed before the artifact outcome could be recorded.",
        result: { export_id: null, snapshot_id: null, format: "markdown", download_url: null },
      });
      expect(deferred.rollbackCount()).toBe(1);
      const database = studioDatabase(app);
      expect(database.select().from(projectSnapshots).all()).toEqual([]);
      expect(database.select().from(snapshotDocuments).all()).toEqual([]);
      expect(database.select().from(exportRecords).all()).toEqual([]);
      expect(database.select().from(jobs).all()).toHaveLength(1);
      expect(database.select().from(jobEvents).all()).toHaveLength(1);
    } finally {
      deferred.release();
      await app.close();
    }
  });
});
