import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { JobRetryExecutor } from "../../src/contexts/studio/application/job_retry_executor.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { createStudioServices } from "../../src/contexts/studio/application/studio_services.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { jobs } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

class CapacityExportStore extends ExportStorePart {
  reads = 0;

  override readExportSource(): never {
    this.reads += 1;
    const limit = EXPORT_CAPACITY_LIMITS.source_bytes;
    throw new ExportCapacityExceededError("source_bytes", limit, limit + 99);
  }
}

describe("keyed export retry capacity outcome", () => {
  it("atomically settles once, replays 422 through both entry points, and lets a new key retry", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-retry-capacity-"));
    directories.push(directory);
    const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    const store = new DrizzleStudioStore({ database: database.db });
    const exportStore = new CapacityExportStore(database.db);
    const now = () => new Date("2026-09-03T08:00:00.000Z");
    const auth = new AuthService({
      store: new DrizzleAuthStore(database.db),
      sessionSecret: "export-retry-capacity-secret",
      now,
    });
    await auth.configureOwner("capacity-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("capacity-owner", "long-test-password"))
      .principal;
    const providerFactory = () => {
      throw new Error("Unexpected provider construction.");
    };
    const services = createStudioServices(store, {
      now,
      providerFactory,
      artifactStore: exportStore,
      artifactFiles: {
        async writeSnapshotArtifact() {
          throw new Error("Capacity refusal must precede artifact rendering.");
        },
        async readArtifactBytes() {
          throw new Error("Unexpected artifact read.");
        },
      },
      projectArtifactCleaner: { removeProjectArtifacts: async () => undefined },
      legacyWorkspaceReader: {
        read: async () => Promise.reject(new Error("Unexpected legacy read.")),
        readConfinedLegacyWorkspace: async () =>
          Promise.reject(new Error("Unexpected confined legacy read.")),
      },
    });

    try {
      const project = services.projects.newProject(principal, { title: "Capacity retry" }) as {
        id: string;
      };
      const scope = scopeForPrincipal(principal);
      const source = store.addJob(scope, {
        projectId: project.id,
        documentId: null,
        kind: "export",
        operation: "export",
        status: "interrupted",
        provider: "studio",
        model: "",
        requestJson: '{"format":"markdown"}',
        resultJson: "{}",
        error: "fixture interruption",
        eventDetailsJson: '{"error":"fixture interruption"}',
        now: now(),
      });
      const firstKey = "export-capacity-retry-key-0001";

      await expect(
        services.jobHistory.reexecuteProjectJob(
          principal,
          project.id,
          source.id,
          firstKey,
          () => undefined,
        ),
      ).rejects.toMatchObject(capacityError());
      expect(exportStore.reads).toBe(1);

      const retry = store.findJobRetry(scope, project.id, source.id, firstKey);
      expect(retry).toMatchObject({
        kind: "export",
        status: "failed",
        error: "Export capacity exceeded.",
        retryOfJobId: source.id,
      });
      expect(retry?.events.map((event) => event.status)).toEqual(["running", "failed"]);
      expect(JSON.parse(retry?.resultJson ?? "null")).toEqual({
        export_id: null,
        snapshot_id: null,
        format: "markdown",
        download_url: null,
        capacity_error: {
          code: "EXPORT_CAPACITY_EXCEEDED",
          resource: "source_bytes",
          limit: EXPORT_CAPACITY_LIMITS.source_bytes,
          observed: EXPORT_CAPACITY_LIMITS.source_bytes + 1,
        },
      });
      const rowsAfterFirst = database.db.select().from(jobs).all();

      await expect(
        services.jobHistory.reexecuteProjectJob(
          principal,
          project.id,
          source.id,
          firstKey,
          () => undefined,
        ),
      ).rejects.toMatchObject(capacityError());

      const executor = new JobRetryExecutor(store, services.reviewAssessments, services.artifacts, {
        now,
        providerFactory,
      });
      await expect(
        executor.reexecuteProjectJob(principal, project.id, source.id, firstKey, () => undefined),
      ).rejects.toMatchObject(capacityError());
      expect(exportStore.reads).toBe(1);
      expect(database.db.select().from(jobs).all()).toEqual(rowsAfterFirst);

      await expect(
        services.jobHistory.reexecuteProjectJob(
          principal,
          project.id,
          source.id,
          "export-capacity-retry-key-0002",
          () => undefined,
        ),
      ).rejects.toMatchObject(capacityError());
      expect(exportStore.reads).toBe(2);
      expect(database.db.select().from(jobs).all()).toHaveLength(3);
    } finally {
      database.close();
    }
  });
});

function capacityError() {
  return {
    name: "ExportCapacityExceededError",
    resource: "source_bytes",
    limit: EXPORT_CAPACITY_LIMITS.source_bytes,
    observed: EXPORT_CAPACITY_LIMITS.source_bytes + 1,
  };
}
