import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";
import { exportArtifactNames } from "../../src/contexts/studio/application/export_artifact_identity.js";
import type {
  ExportSource,
  PreparedExportArtifact,
} from "../../src/contexts/studio/application/ports/export_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ExportSourceInvalidatedError } from "../../src/contexts/studio/domain/exceptions.js";
import {
  documentRevisions,
  exports as exportArtifacts,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import type { StudioSqliteDatabase } from "../../src/shared/infrastructure/db/connection.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];
const NO_EXPORT_ROWS = {
  snapshots: 0,
  snapshotDocuments: 0,
  artifacts: 0,
  jobs: 0,
  events: 0,
};

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

function clock(): () => Date {
  let milliseconds = Date.parse("2026-08-31T14:00:00.000Z");
  return () => new Date(++milliseconds);
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-store-"));
  directories.push(directory);
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const now = clock();
  const store = new DrizzleStudioStore({ database: database.db });
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "export-store-test-secret",
    now,
  });
  await auth.configureOwner("export-store-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("export-store-owner", "long-test-password"))
    .principal;
  const scope = scopeForPrincipal(principal);
  const seeded = store.addProject(scope, {
    title: "Atomic export",
    description: "",
    settingsJson: "{}",
    seed: {
      kind: "chapter",
      title: "Chapter 1",
      contentMarkdown: "The immutable export source.",
      metadataJson: "{}",
    },
    now: now(),
  });
  const document = seeded.documents[0];
  if (document === undefined) throw new Error("Expected a seeded export document.");
  return { database, document, now, project: seeded.project, scope, store };
}

function prepared(
  source: ExportSource,
  id: string,
  format: PreparedExportArtifact["format"],
  createdAt: Date,
): PreparedExportArtifact {
  const { relativePath } = exportArtifactNames(source.projectId, id, format);
  return {
    source,
    id,
    format,
    relativePath,
    sizeBytes: 17,
    checksumSha256: "a".repeat(64),
    createdAt,
  };
}

function evidenceCounts(db: StudioSqliteDatabase) {
  return {
    snapshots: db.select().from(projectSnapshots).all().length,
    snapshotDocuments: db.select().from(snapshotDocuments).all().length,
    artifacts: db.select().from(exportArtifacts).all().length,
    jobs: db.select().from(jobs).all().length,
    events: db.select().from(jobEvents).all().length,
  };
}

describe("export store transactions", () => {
  it("lands the captured revision after a concurrent author edit", async () => {
    const harness = await openHarness();
    try {
      const store = new ExportStorePart(harness.database.db);
      const source = store.readExportSource(harness.scope, harness.project.id, harness.now());
      const captured = source.documents[0];
      if (captured === undefined) throw new Error("Expected a captured source document.");
      const advanced = harness.store.advanceDocument(
        harness.scope,
        harness.project.id,
        harness.document.id,
        {
          contentMarkdown: "A later author edit.",
          baseRevisionId: harness.document.currentRevisionId,
          title: null,
          metadataJson: "{}",
          source: "author",
          now: harness.now(),
        },
      );

      const completed = store.recordCompletedExportJob(
        harness.scope,
        prepared(source, "captured-export", "markdown", harness.now()),
      );
      const snapshot = harness.database.db
        .select()
        .from(snapshotDocuments)
        .where(eq(snapshotDocuments.snapshotId, completed.artifact.snapshotId))
        .get();
      expect(snapshot?.revisionId).toBe(captured.revisionId);
      expect(snapshot?.revisionId).not.toBe(advanced.currentRevisionId);
      expect(completed.job.status).toBe("completed");
    } finally {
      harness.database.close();
    }
  });

  it("rolls all fresh evidence back when the completed event insert fails", async () => {
    const harness = await openHarness();
    try {
      class ExplodingFreshEventStore extends ExportStorePart {
        protected override beforeFreshJobEventInsert(): never {
          throw new Error("simulated completed export event failure");
        }
      }
      const store = new ExplodingFreshEventStore(harness.database.db);
      const source = store.readExportSource(harness.scope, harness.project.id, harness.now());
      expect(() =>
        store.recordCompletedExportJob(
          harness.scope,
          prepared(source, "failed-fresh", "markdown", harness.now()),
        ),
      ).toThrow("simulated completed export event failure");
      expect(evidenceCounts(harness.database.db)).toEqual(NO_EXPORT_ROWS);
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
    } finally {
      harness.database.close();
    }
  });

  it("rolls artifact evidence and retry transition back when its event fails", async () => {
    const harness = await openHarness();
    try {
      const original = harness.store.addJob(harness.scope, {
        projectId: harness.project.id,
        documentId: null,
        kind: "export",
        operation: "export",
        status: "failed",
        provider: "studio",
        model: "",
        requestJson: JSON.stringify({ format: "markdown" }),
        resultJson: "{}",
        error: "write failed",
        eventDetailsJson: "{}",
        now: harness.now(),
      });
      const retry = harness.store.addJob(harness.scope, {
        projectId: harness.project.id,
        documentId: null,
        kind: "export",
        operation: "export",
        status: "running",
        provider: "studio",
        model: "",
        requestJson: JSON.stringify({ format: "markdown" }),
        resultJson: "{}",
        error: null,
        retryOfJobId: original.id,
        eventDetailsJson: JSON.stringify({ retry_of: original.id }),
        now: harness.now(),
      });
      const retryBefore = harness.store.findJob(harness.scope, harness.project.id, retry.id);
      class ExplodingRetryEventStore extends ExportStorePart {
        protected override beforeRetryEventInsert(): never {
          throw new Error("simulated export retry event failure");
        }
      }
      const store = new ExplodingRetryEventStore(harness.database.db);
      const source = store.readExportSource(harness.scope, harness.project.id, harness.now());
      expect(() =>
        store.completeExportRetryJob(
          harness.scope,
          harness.project.id,
          retry.id,
          prepared(source, "failed-retry", "markdown", harness.now()),
        ),
      ).toThrow("simulated export retry event failure");
      expect(evidenceCounts(harness.database.db)).toEqual({
        ...NO_EXPORT_ROWS,
        jobs: 2,
        events: 2,
      });
      const retryAfter = harness.store.findJob(harness.scope, harness.project.id, retry.id);
      expect(retryAfter).toMatchObject({ status: "running", resultJson: "{}", error: null });
      expect(retryAfter.updatedAt).toEqual(retryBefore.updatedAt);
      expect(retryAfter.events).toEqual(retryBefore.events);
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
    } finally {
      harness.database.close();
    }
  });

  it("rejects tampered or deleted captured sources without partial evidence", async () => {
    const harness = await openHarness();
    try {
      const store = new ExportStorePart(harness.database.db);
      const source = store.readExportSource(harness.scope, harness.project.id, harness.now());
      const captured = source.documents[0];
      if (captured === undefined) throw new Error("Expected a captured source document.");
      const input = prepared(source, "invalid-source", "markdown", harness.now());
      harness.database.db
        .update(documentRevisions)
        .set({ contentMarkdown: "tampered immutable content" })
        .where(eq(documentRevisions.id, captured.revisionId))
        .run();
      expect(() => store.recordCompletedExportJob(harness.scope, input)).toThrow(
        "Persisted immutable export source changed after capture.",
      );
      expect(evidenceCounts(harness.database.db)).toEqual(NO_EXPORT_ROWS);
      harness.database.db
        .update(documentRevisions)
        .set({ contentMarkdown: captured.contentMarkdown })
        .where(eq(documentRevisions.id, captured.revisionId))
        .run();
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
      expect(() => store.recordCompletedExportJob(harness.scope, input)).toThrow(
        ExportSourceInvalidatedError,
      );
      expect(evidenceCounts(harness.database.db)).toEqual(NO_EXPORT_ROWS);
    } finally {
      harness.database.close();
    }
  });

  it("reuses only an exact captured projection across concurrent format landings", async () => {
    const harness = await openHarness();
    try {
      const store = new ExportStorePart(harness.database.db);
      const firstSource = store.readExportSource(harness.scope, harness.project.id, harness.now());
      const secondSource = store.readExportSource(harness.scope, harness.project.id, harness.now());
      const markdown = store.recordCompletedExportJob(
        harness.scope,
        prepared(firstSource, "same-markdown", "markdown", harness.now()),
      ).artifact;
      const docx = store.recordCompletedExportJob(
        harness.scope,
        prepared(secondSource, "same-docx", "docx", harness.now()),
      ).artifact;
      expect(docx.snapshotId).toBe(markdown.snapshotId);
      expect(evidenceCounts(harness.database.db)).toMatchObject({
        snapshots: 1,
        artifacts: 2,
        jobs: 2,
        events: 2,
      });

      const changedProjection: ExportSource = {
        ...secondSource,
        capturedAt: harness.now(),
        documents: secondSource.documents.map((document) => ({
          ...document,
          title: `${document.title} (captured earlier)`,
        })),
      };
      const epub = store.recordCompletedExportJob(
        harness.scope,
        prepared(changedProjection, "different-epub", "epub", harness.now()),
      ).artifact;
      expect(epub.snapshotId).not.toBe(markdown.snapshotId);
      expect(evidenceCounts(harness.database.db).snapshots).toBe(2);
      expect(evidenceCounts(harness.database.db).artifacts).toBe(3);
    } finally {
      harness.database.close();
    }
  });
});
