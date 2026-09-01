import { describe, expect, it } from "vitest";

import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import { jobs } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

function deferredArtifactGateway(): {
  gateway: ExportArtifactGateway;
  started: Promise<void>;
  release: () => void;
} {
  let announce: (() => void) | undefined;
  let release: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    announce = resolve;
  });
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  return {
    gateway: {
      async writeSnapshotArtifact(request) {
        announce?.();
        await blocked;
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => undefined,
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    },
    started,
    release: () => release?.(),
  };
}

describe("project deletion versus export retry", () => {
  it("rejects deletion while a retry is in flight, then releases ownership", async () => {
    const deferred = deferredArtifactGateway();
    const { app } = await buildStudioApp(undefined, {
      exportArtifactGateway: deferred.gateway,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Delete versus export retry");
      const interruptedAt = new Date();
      studioDatabase(app)
        .insert(jobs)
        .values({
          id: "interrupted-export-for-deletion",
          project_id: project.id,
          document_id: null,
          kind: "export",
          operation: "export",
          status: "interrupted",
          provider: "studio",
          model: "",
          request_json: JSON.stringify({ format: "markdown" }),
          result_json: "{}",
          error: "restart interrupted the export",
          created_at: interruptedAt,
          updated_at: interruptedAt,
        })
        .run();
      const pendingRetry = call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/interrupted-export-for-deletion/retry`,
      );
      await deferred.started;

      const rejected = await call(app, owner, "DELETE", `/api/projects/${project.id}`);
      expect(rejected.statusCode, rejected.body).toBe(409);
      expect(rejected.json().error).toMatchObject({
        code: "OPERATION_IN_FLIGHT",
        details: {
          project_id: project.id,
          operation: "retry (interrupted-export-for-deletion)",
        },
      });
      expect((await call(app, owner, "GET", `/api/projects/${project.id}`)).statusCode).toBe(200);

      deferred.release();
      const retry = await pendingRetry;
      expect(retry.statusCode, retry.body).toBe(200);
      expect((await call(app, owner, "DELETE", `/api/projects/${project.id}`)).statusCode).toBe(
        204,
      );
    } finally {
      deferred.release();
      await app.close();
    }
  });
});
