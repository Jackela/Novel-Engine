import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { exportArtifactNames } from "../../src/contexts/studio/application/export_artifact_identity.js";
import { sameExportSourceProjection } from "../../src/contexts/studio/application/export_source_identity.js";
import type {
  ExportSource,
  PreparedExportArtifact,
} from "../../src/contexts/studio/application/ports/export_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ExportSourceInvalidatedError } from "../../src/contexts/studio/domain/exceptions.js";
import { readExportSnapshotDocuments } from "../../src/contexts/studio/infrastructure/db/export_records.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

describe("export source revalidation capacity", () => {
  it("lands complete sources across SQLite's former variable boundary", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-revalidation-"));
    directories.push(directory);
    const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    try {
      const now = new Date("2026-09-02T09:00:00.000Z");
      const store = new DrizzleStudioStore({ database: studio.db });
      const auth = new AuthService({
        store: new DrizzleAuthStore(studio.db),
        sessionSecret: "export-revalidation-test-secret",
        now: () => now,
      });
      await auth.configureOwner("export-revalidation-owner", "long-test-password");
      const principal = (
        await auth.createOwnerSession("export-revalidation-owner", "long-test-password")
      ).principal;
      const scope = scopeForPrincipal(principal);
      const seeded = store.addProject(scope, {
        title: "High-cardinality export",
        description: "",
        settingsJson: "{}",
        seed: {
          kind: "chapter",
          title: "Chapter 1",
          contentMarkdown: "Chapter content.",
          metadataJson: "{}",
        },
        now,
      });

      seedAdditionalDocuments(studio.raw, seeded.project.id, 32_765, now.getTime());

      const exportStore = new ExportStorePart(studio.db);
      const firstSource = exportStore.readExportSource(scope, seeded.project.id, now);
      expect(firstSource.documents).toHaveLength(32_765);
      assertInvalidCollectionsFailClosed(exportStore, scope, firstSource, studio.raw, now);

      for (const count of [32_765, 32_766, 32_767]) {
        if (count > 32_765) {
          seedOneDocument(studio.raw, seeded.project.id, count, now.getTime());
        }
        const source = exportStore.readExportSource(scope, seeded.project.id, now);
        expect(source.documents, `captured source at ${count}`).toHaveLength(count);
        const completed = exportStore.recordCompletedExportJob(
          scope,
          prepared(source, `capacity-export-${count}`, now),
        );
        const persistedCount = studio.raw
          .prepare("SELECT count(*) AS value FROM snapshot_documents WHERE snapshot_id = ?")
          .get(completed.artifact.snapshotId) as { value: number };
        expect(persistedCount.value, `snapshot cardinality at ${count}`).toBe(count);
        const persisted = studio.db.transaction((tx) =>
          readExportSnapshotDocuments(tx, completed.artifact.snapshotId),
        );
        expect(sameExportSourceProjection(persisted, source.documents)).toBe(true);
      }
    } finally {
      studio.close();
    }
  }, 60_000);
});

function prepared(source: ExportSource, id: string, createdAt: Date): PreparedExportArtifact {
  const { relativePath } = exportArtifactNames(source.projectId, id, "markdown");
  return {
    source,
    id,
    format: "markdown",
    relativePath,
    sizeBytes: 17,
    checksumSha256: "a".repeat(64),
    createdAt,
  };
}

function assertInvalidCollectionsFailClosed(
  store: ExportStorePart,
  scope: Parameters<ExportStorePart["recordCompletedExportJob"]>[0],
  source: ExportSource,
  database: import("better-sqlite3").Database,
  now: Date,
): void {
  const first = source.documents[0];
  const last = source.documents.at(-1);
  if (first === undefined || last === undefined) throw new Error("Expected captured documents.");
  const replaceLast = (replacement: typeof last): ExportSource => ({
    ...source,
    documents: [...source.documents.slice(0, -1), replacement],
  });

  expect(() =>
    store.recordCompletedExportJob(
      scope,
      prepared(replaceLast({ ...last, documentId: first.documentId }), "duplicate-document", now),
    ),
  ).toThrow("duplicate document identity");
  expect(() =>
    store.recordCompletedExportJob(
      scope,
      prepared(replaceLast({ ...last, revisionId: first.revisionId }), "duplicate-revision", now),
    ),
  ).toThrow("duplicate revision identity");
  expect(() =>
    store.recordCompletedExportJob(
      scope,
      prepared(
        replaceLast({ ...last, revisionId: "missing-later-revision" }),
        "missing-source",
        now,
      ),
    ),
  ).toThrow(ExportSourceInvalidatedError);

  database
    .prepare("UPDATE document_revisions SET content_markdown = ? WHERE id = ?")
    .run("tampered immutable content", last.revisionId);
  expect(() =>
    store.recordCompletedExportJob(scope, prepared(source, "tampered-source", now)),
  ).toThrow("Persisted immutable export source changed after capture.");
  database
    .prepare("UPDATE document_revisions SET content_markdown = ? WHERE id = ?")
    .run(last.contentMarkdown, last.revisionId);

  const evidence = database
    .prepare(
      `SELECT
         (SELECT count(*) FROM project_snapshots) AS snapshots,
         (SELECT count(*) FROM snapshot_documents) AS snapshot_documents,
         (SELECT count(*) FROM exports) AS artifacts,
         (SELECT count(*) FROM jobs) AS jobs,
         (SELECT count(*) FROM job_events) AS events`,
    )
    .get();
  expect(evidence).toEqual({
    snapshots: 0,
    snapshot_documents: 0,
    artifacts: 0,
    jobs: 0,
    events: 0,
  });
}

function seedAdditionalDocuments(
  database: import("better-sqlite3").Database,
  projectId: string,
  totalDocuments: number,
  now: number,
): void {
  database.transaction(() => {
    database
      .prepare(
        `WITH RECURSIVE sequence(value) AS (
           SELECT 2 UNION ALL SELECT value + 1 FROM sequence WHERE value < ?
         )
         INSERT INTO documents
           (id, project_id, kind, title, position, volume_id, beat_ref, lore_aliases_json,
            lore_status, current_revision_id, created_at, updated_at)
         SELECT printf('capacity-document-%05d', value), ?, 'note', printf('Note %05d', value),
                value, NULL, NULL, '[]', 'draft', printf('capacity-revision-%05d', value), ?, ?
         FROM sequence`,
      )
      .run(totalDocuments, projectId, now, now);
    database
      .prepare(
        `WITH RECURSIVE sequence(value) AS (
           SELECT 2 UNION ALL SELECT value + 1 FROM sequence WHERE value < ?
         )
         INSERT INTO document_revisions
           (id, document_id, parent_revision_id, revision_number, content_markdown,
            metadata_json, source, created_at)
         SELECT printf('capacity-revision-%05d', value), printf('capacity-document-%05d', value),
                NULL, 1, printf('Note content %05d.', value), '{}', 'author', ?
         FROM sequence`,
      )
      .run(totalDocuments, now);
  })();
}

function seedOneDocument(
  database: import("better-sqlite3").Database,
  projectId: string,
  position: number,
  now: number,
): void {
  const suffix = String(position).padStart(5, "0");
  database.transaction(() => {
    database
      .prepare(
        `INSERT INTO documents
           (id, project_id, kind, title, position, volume_id, beat_ref, lore_aliases_json,
            lore_status, current_revision_id, created_at, updated_at)
         VALUES (?, ?, 'note', ?, ?, NULL, NULL, '[]', 'draft', ?, ?, ?)`,
      )
      .run(
        `capacity-document-${suffix}`,
        projectId,
        `Note ${suffix}`,
        position,
        `capacity-revision-${suffix}`,
        now,
        now,
      );
    database
      .prepare(
        `INSERT INTO document_revisions
           (id, document_id, parent_revision_id, revision_number, content_markdown,
            metadata_json, source, created_at)
         VALUES (?, ?, NULL, 1, ?, '{}', 'author', ?)`,
      )
      .run(
        `capacity-revision-${suffix}`,
        `capacity-document-${suffix}`,
        `Note content ${suffix}.`,
        now,
      );
  })();
}
