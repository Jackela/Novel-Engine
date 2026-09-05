import { describe, expect, it, vi } from "vitest";

import type {
  ArtifactFileEvidence,
  ArtifactReadRequest,
  ArtifactWriteRequest,
  ExportArtifactGateway,
} from "../../src/contexts/studio/application/export_artifact_service.js";
import { EXPORT_CAPACITY_LIMITS } from "../../src/contexts/studio/domain/exceptions.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

function downloadUrl(projectId: string, artifactId: string): string {
  return `/api/projects/${projectId}/exports/${artifactId}/download`;
}

describe("artifact download capacity API", () => {
  it("keeps permanent, transient, and unexpected failures distinct", async () => {
    const pending: Array<(bytes: Buffer) => void> = [];
    const readArtifactBytes = vi.fn((request: ArtifactReadRequest): Promise<Buffer> => {
      if (request.artifactId === "first" || request.artifactId === "second") {
        return new Promise((resolve) => pending.push(resolve));
      }
      if (request.artifactId === "io-failure") {
        throw Object.assign(new Error("simulated filesystem failure"), { code: "EIO" });
      }
      if (request.artifactId === "reader-defect") {
        throw new TypeError("simulated artifact reader defect");
      }
      return Promise.resolve(Buffer.from("delivered"));
    });
    const gateway: ExportArtifactGateway = {
      writeSnapshotArtifact: async (
        _request: ArtifactWriteRequest,
      ): Promise<ArtifactFileEvidence> => Promise.reject(new Error("Unexpected artifact write.")),
      readArtifactBytes,
    };
    const { app } = await buildStudioApp(undefined, { exportArtifactGateway: gateway });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Download capacity");
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("Expected database.");
      const now = new Date();
      database
        .insert(projectSnapshots)
        .values({
          id: "snapshot-download",
          projectId: project.id,
          reason: "export",
          createdAt: now,
        })
        .run();
      for (const [id, sizeBytes] of [
        ["oversized", EXPORT_CAPACITY_LIMITS.artifact_bytes + 1],
        ["first", EXPORT_CAPACITY_LIMITS.artifact_bytes],
        ["second", EXPORT_CAPACITY_LIMITS.artifact_bytes],
        ["third", 1],
        ["io-failure", 1],
        ["reader-defect", 1],
      ] as const) {
        database
          .insert(exportArtifacts)
          .values({
            id,
            projectId: project.id,
            snapshotId: "snapshot-download",
            format: "markdown",
            relativePath: `exports/${project.id}/${id}.md`,
            sizeBytes,
            checksumSha256: "a".repeat(64),
            createdAt: now,
          })
          .run();
      }

      const oversized = await call(app, owner, "GET", downloadUrl(project.id, "oversized"));
      expect(oversized.statusCode, oversized.body).toBe(422);
      expect(oversized.json().error).toMatchObject({
        code: "EXPORT_CAPACITY_EXCEEDED",
        details: {
          resource: "artifact_bytes",
          limit: EXPORT_CAPACITY_LIMITS.artifact_bytes,
          observed: EXPORT_CAPACITY_LIMITS.artifact_bytes + 1,
        },
      });
      expect(readArtifactBytes).not.toHaveBeenCalledWith(
        expect.objectContaining({ artifactId: "oversized" }),
      );

      const first = call(app, owner, "GET", downloadUrl(project.id, "first"));
      const second = call(app, owner, "GET", downloadUrl(project.id, "second"));
      await expect.poll(() => pending.length).toBe(2);
      const refused = await call(app, owner, "GET", downloadUrl(project.id, "third"));
      expect(refused.statusCode, refused.body).toBe(503);
      expect(refused.headers["retry-after"]).toBe("5");
      expect(refused.json().error).toMatchObject({
        code: "OPERATION_CAPACITY_EXCEEDED",
        details: {
          scope: "application",
          limit: 134_217_728,
          in_flight: 134_217_728,
        },
      });
      for (const resolve of pending.splice(0)) resolve(Buffer.from("delivered"));
      expect((await first).statusCode).toBe(200);
      expect((await second).statusCode).toBe(200);
      expect((await call(app, owner, "GET", downloadUrl(project.id, "third"))).statusCode).toBe(
        200,
      );

      const ioFailure = await call(app, owner, "GET", downloadUrl(project.id, "io-failure"));
      expect(ioFailure.statusCode, ioFailure.body).toBe(500);
      expect(ioFailure.json().error.code).toBe("INTERNAL_ERROR");
      expect(ioFailure.body).not.toContain("simulated filesystem failure");

      const defect = await call(app, owner, "GET", downloadUrl(project.id, "reader-defect"));
      expect(defect.statusCode, defect.body).toBe(500);
      expect(defect.json().error.code).toBe("INTERNAL_ERROR");
      expect(defect.body).not.toContain("simulated artifact reader defect");
    } finally {
      await app.close();
    }
  });
});
