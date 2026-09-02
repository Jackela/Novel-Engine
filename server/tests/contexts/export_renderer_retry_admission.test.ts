import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { createStudioServices } from "../../src/contexts/studio/application/studio_services.js";
import { OperationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
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

describe("export retry renderer admission", () => {
  it("refuses before reserving a retry Job while another render owns the app", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-renderer-retry-"));
    directories.push(directory);
    const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    const store = new DrizzleStudioStore({ database: database.db });
    const now = () => new Date("2026-09-03T00:00:00.000Z");
    const auth = new AuthService({
      store: new DrizzleAuthStore(database.db),
      sessionSecret: "renderer-retry-secret",
      now,
    });
    await auth.configureOwner("renderer-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("renderer-owner", "long-test-password"))
      .principal;
    const acknowledgement = deferred<void>();
    let acknowledgementStarted = false;
    const services = createStudioServices(store, {
      now,
      providerFactory: () => {
        throw new Error("Unexpected provider construction.");
      },
      artifactStore: new ExportStorePart(database.db),
      artifactFiles: {
        async writeSnapshotArtifact(request) {
          return {
            relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
            sizeBytes: 1,
            checksumSha256: "a".repeat(64),
            acknowledge: async () => {
              acknowledgementStarted = true;
              await acknowledgement.promise;
            },
            rollback: async () => undefined,
          };
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
      const project = services.projects.newProject(principal, { title: "Renderer owner" }) as {
        id: string;
      };
      const scope = scopeForPrincipal(principal);
      const retrySource = store.addJob(scope, {
        projectId: project.id,
        documentId: null,
        kind: "export",
        operation: "export",
        status: "failed",
        provider: "studio",
        model: "",
        requestJson: '{"format":"markdown"}',
        resultJson: "{}",
        error: "fixture failure",
        eventDetailsJson: '{"error":"fixture failure"}',
        now: now(),
      });
      const active = services.jobHistory.recordExportJob(principal, project.id, "markdown");
      await waitUntil(() => acknowledgementStarted);
      const jobsBeforeRetry = database.db.select().from(jobs).all().length;

      await expect(
        services.jobHistory.reexecuteProjectJob(
          principal,
          project.id,
          retrySource.id,
          "renderer-retry-key",
          () => undefined,
        ),
      ).rejects.toBeInstanceOf(OperationCapacityExceededError);
      expect(database.db.select().from(jobs).all()).toHaveLength(jobsBeforeRetry);

      acknowledgement.resolve();
      await expect(active).resolves.toMatchObject({ status: "completed" });
    } finally {
      database.close();
    }
  });
});

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

async function waitUntil(predicate: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  throw new Error("Timed out waiting for acknowledgement ownership.");
}
