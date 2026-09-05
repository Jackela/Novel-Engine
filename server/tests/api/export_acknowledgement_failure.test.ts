import { describe, expect, it, vi } from "vitest";

import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

describe("export acknowledgement failure", () => {
  it("keeps the committed outcome completed and reports cleanup once", async () => {
    const cleanupFailure = new Error("simulated acknowledgement failure");
    let acknowledgementCalls = 0;
    let rollbackCalls = 0;
    const gateway: ExportArtifactGateway = {
      async writeSnapshotArtifact(request) {
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => {
            acknowledgementCalls += 1;
            throw cleanupFailure;
          },
          rollback: async () => {
            rollbackCalls += 1;
          },
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    };
    const { app } = await buildStudioApp(undefined, { exportArtifactGateway: gateway });
    const logError = vi.spyOn(app.log, "error").mockImplementation(() => undefined);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Committed acknowledgement failure");

      const response = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });

      expect(response.statusCode, response.body).toBe(201);
      expect(response.json()).toMatchObject({ status: "completed" });
      expect(acknowledgementCalls).toBe(1);
      expect(rollbackCalls).toBe(0);
      expect(
        logError.mock.calls.filter(
          ([details, message]) =>
            message === "artifact cleanup failed" &&
            typeof details === "object" &&
            (details as Record<string, unknown>).artifact_cleanup_failed === true,
        ),
      ).toHaveLength(1);
      const catalog = await call(app, owner, "GET", `/api/projects/${project.id}/exports`);
      expect(catalog.json().exports).toHaveLength(1);
    } finally {
      await app.close();
    }
  });
});
