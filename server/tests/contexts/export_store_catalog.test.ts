import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { exportArtifactNames } from "../../src/contexts/studio/application/export_artifact_identity.js";
import type {
  ExportArtifactFormat,
  ExportSource,
  PreparedExportArtifact,
} from "../../src/contexts/studio/application/ports/export_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

interface ProjectPayload {
  id: string;
}

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-08-24T00:00:00.000Z");
  return () => new Date(++milliseconds);
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-catalog-"));
  const studio = await openStudioDatabase(directory);
  const clock = monotonicClock();
  const store = new DrizzleStudioStore({ database: studio.db });
  const projects = new ProjectService(store, clock);
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "export-catalog-test-secret",
    now: clock,
  });
  await auth.configureOwner("exporter", "long-test-password");
  const principal = (await auth.createOwnerSession("exporter", "long-test-password")).principal;
  return {
    clock,
    studio,
    projects,
    principal,
    scope: scopeForPrincipal(principal),
    exportStore: new ExportStorePart(studio.db),
  };
}

function newProject(
  projects: ProjectService,
  principal: Awaited<ReturnType<typeof openHarness>>["principal"],
  title: string,
): string {
  return (projects.newProject(principal, { title }) as unknown as ProjectPayload).id;
}

function prepared(
  source: ExportSource,
  id: string,
  format: ExportArtifactFormat,
  createdAt: Date,
): PreparedExportArtifact {
  const { relativePath } = exportArtifactNames(source.projectId, id, format);
  return {
    source,
    id,
    format,
    relativePath,
    sizeBytes: id.length,
    checksumSha256: "a".repeat(64),
    createdAt,
  };
}

describe("ExportStorePart artifact catalog", () => {
  it("persists project-scoped artifacts newest first and rejects cross-project evidence", async () => {
    const harness = await openHarness();
    try {
      const firstProjectId = newProject(harness.projects, harness.principal, "First project");
      const secondProjectId = newProject(harness.projects, harness.principal, "Second project");
      const firstSource = harness.exportStore.readExportSource(
        harness.scope,
        firstProjectId,
        harness.clock(),
      );
      const secondSource = harness.exportStore.readExportSource(
        harness.scope,
        secondProjectId,
        harness.clock(),
      );
      const early = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(firstSource, "artifact-early", "markdown", harness.clock()),
      ).artifact;
      const latest = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(
          harness.exportStore.readExportSource(harness.scope, firstProjectId, harness.clock()),
          "artifact-latest",
          "epub",
          harness.clock(),
        ),
      ).artifact;
      const other = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(secondSource, "artifact-other", "docx", harness.clock()),
      ).artifact;

      expect(harness.exportStore.listProjectArtifacts(harness.scope, firstProjectId)).toEqual([
        latest,
        early,
      ]);
      expect(
        harness.exportStore.findProjectArtifact(harness.scope, firstProjectId, latest.id),
      ).toMatchObject({
        relativePath: latest.relativePath,
        sizeBytes: latest.sizeBytes,
        checksumSha256: latest.checksumSha256,
      });
      expect(() =>
        harness.exportStore.findProjectArtifact(harness.scope, firstProjectId, other.id),
      ).toThrow(NotFoundError);
      expect(() =>
        harness.exportStore.recordCompletedExportJob(
          harness.scope,
          prepared(
            { ...secondSource, projectId: firstProjectId },
            "artifact-cross-project",
            "markdown",
            harness.clock(),
          ),
        ),
      ).toThrow();
    } finally {
      harness.studio.close();
    }
  });
});
