import { mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import { JobHistoryService } from "../../src/contexts/studio/application/job_history_service.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ReviewService } from "../../src/contexts/studio/application/review_service.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

function clock(): () => Date {
  let milliseconds = Date.parse("2026-08-31T13:00:00.000Z");
  return () => new Date(++milliseconds);
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-outcome-"));
  directories.push(directory);
  const database = await openStudioDatabase(directory);
  const now = clock();
  const store = new DrizzleStudioStore({ database: database.db, dataDirectory: directory });
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "export-outcome-test-secret",
    now,
  });
  await auth.configureOwner("export-outcome-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("export-outcome-owner", "long-test-password"))
    .principal;
  const scope = scopeForPrincipal(principal);
  const seeded = store.addProject(scope, {
    title: "Atomic export",
    description: "",
    settingsJson: "{}",
    seed: {
      kind: "chapter",
      title: "Chapter 1",
      contentMarkdown: "The first export source.",
      metadataJson: "{}",
    },
    now: now(),
  });
  return { database, directory, now, principal, project: seeded.project, scope, store };
}

function evidenceCounts(database: Awaited<ReturnType<typeof openHarness>>["database"]) {
  return {
    snapshots: database.db.select().from(projectSnapshots).all().length,
    snapshotDocuments: database.db.select().from(snapshotDocuments).all().length,
    artifacts: database.db.select().from(exportArtifacts).all().length,
    jobs: database.db.select().from(jobs).all().length,
    events: database.db.select().from(jobEvents).all().length,
  };
}

function exportHistory(
  harness: Awaited<ReturnType<typeof openHarness>>,
  exportStore: ExportStorePart,
  artifactId: string,
): JobHistoryService {
  const artifacts = new SnapshotArtifactService(
    exportStore,
    new FilesystemExportArtifactGateway(harness.directory),
    { now: harness.now, newId: () => artifactId },
  );
  const reviews = new ReviewService(harness.store, {
    now: harness.now,
    providerFactory: () => {
      throw new Error("unexpected provider request");
    },
  });
  return new JobHistoryService(harness.store, reviews, artifacts, {
    now: harness.now,
    providerFactory: () => {
      throw new Error("unexpected provider request");
    },
    inFlight: new InFlightOperationGuard(),
  });
}

describe("export outcome transactions", () => {
  it("does not persist a snapshot when artifact publication fails", async () => {
    const harness = await openHarness();
    try {
      const artifacts = new SnapshotArtifactService(
        new ExportStorePart(harness.database.db),
        {
          async writeSnapshotArtifact() {
            throw new Error("simulated artifact write failure");
          },
          async readArtifactBytes() {
            throw new Error("unexpected artifact read");
          },
        },
        { now: harness.now },
      );

      await expect(
        artifacts.recordCompletedExportJob(harness.principal, harness.project.id, "markdown"),
      ).rejects.toThrow("simulated artifact write failure");
      expect(evidenceCounts(harness.database)).toEqual({
        snapshots: 0,
        snapshotDocuments: 0,
        artifacts: 0,
        jobs: 0,
        events: 0,
      });
    } finally {
      harness.database.close();
    }
  });

  it("does not publish an artifact when the fresh completed job cannot persist", async () => {
    const harness = await openHarness();
    try {
      class ExplodingExportStore extends ExportStorePart {
        protected override beforeFreshJobEventInsert(): never {
          throw new Error("simulated fresh export job failure");
        }
      }
      const history = exportHistory(
        harness,
        new ExplodingExportStore(harness.database.db),
        "orphan-artifact",
      );

      await expect(
        history.recordExportJob(harness.principal, harness.project.id, "markdown"),
      ).rejects.toThrow("simulated fresh export job failure");
      expect(evidenceCounts(harness.database)).toEqual({
        snapshots: 0,
        snapshotDocuments: 0,
        artifacts: 0,
        jobs: 0,
        events: 0,
      });
      await expect(
        readdir(join(harness.directory, "exports", harness.project.id)),
      ).resolves.toEqual([]);
    } finally {
      harness.database.close();
    }
  });

  it("rolls the snapshot and file back when artifact insertion fails", async () => {
    const harness = await openHarness();
    try {
      class ExplodingArtifactInsertStore extends ExportStorePart {
        protected override beforeArtifactInsert(): never {
          throw new Error("simulated export artifact insert failure");
        }
      }
      const history = exportHistory(
        harness,
        new ExplodingArtifactInsertStore(harness.database.db),
        "failed-artifact-insert",
      );

      await expect(
        history.recordExportJob(harness.principal, harness.project.id, "markdown"),
      ).rejects.toThrow("simulated export artifact insert failure");
      expect(evidenceCounts(harness.database)).toEqual({
        snapshots: 0,
        snapshotDocuments: 0,
        artifacts: 0,
        jobs: 0,
        events: 0,
      });
      await expect(
        readdir(join(harness.directory, "exports", harness.project.id)),
      ).resolves.toEqual([]);
    } finally {
      harness.database.close();
    }
  });
});
