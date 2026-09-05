import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import {
  buildBoundedCurrentDocumentCountQuery,
  buildBoundedSnapshotDocumentCountQuery,
} from "../../src/contexts/studio/infrastructure/db/export_source_capacity.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];
const now = new Date("2026-09-02T12:00:00.000Z");

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

describe("export source capacity", () => {
  it("accepts 65,536 documents and rejects the next before source rows materialize", async () => {
    const harness = await openHarness("Document boundary");
    try {
      seedDocuments(
        harness.database.raw,
        harness.projectId,
        EXPORT_CAPACITY_LIMITS.source_documents,
      );

      const exact = harness.exports.readExportSource(harness.scope, harness.projectId, now);
      expect(exact.documents).toHaveLength(EXPORT_CAPACITY_LIMITS.source_documents);
      expect(exact.documents.at(-1)?.documentId).toBe("d65536");

      insertInvalidNextDocument(harness.database.raw, harness.projectId);
      const queryEvidence = harness.database.db.transaction((tx) => {
        const boundedQuery = buildBoundedCurrentDocumentCountQuery(tx, harness.projectId);
        return { compiled: boundedQuery.toSQL(), result: boundedQuery.get() };
      });
      const { compiled } = queryEvidence;
      expect(compiled.sql).toContain("limit ?");
      expect(compiled.params).toContain(EXPORT_CAPACITY_LIMITS.source_documents + 1);
      expect(compiled.sql).not.toContain("content_markdown");
      expect(queryEvidence.result).toEqual({
        value: EXPORT_CAPACITY_LIMITS.source_documents + 1,
      });
      expectCapacityFailure(
        () => harness.exports.readExportSource(harness.scope, harness.projectId, now),
        "source_documents",
        EXPORT_CAPACITY_LIMITS.source_documents,
      );

      seedOversizedSnapshot(harness.database.raw, harness.projectId, harness.seeded.documents[0]);
      const snapshotEvidence = harness.database.db.transaction((tx) => {
        const query = buildBoundedSnapshotDocumentCountQuery(
          tx,
          harness.projectId,
          "bounded-snapshot",
        );
        return { compiled: query.toSQL(), result: query.get() };
      });
      expect(snapshotEvidence.compiled.sql).toContain("limit ?");
      expect(snapshotEvidence.compiled.params).toContain(
        EXPORT_CAPACITY_LIMITS.source_documents + 1,
      );
      expect(snapshotEvidence.result).toEqual({
        value: EXPORT_CAPACITY_LIMITS.source_documents + 1,
      });
    } finally {
      harness.database.close();
    }
  }, 60_000);

  it("counts exact UTF-8 bytes across project title and all six document fields", async () => {
    const harness = await openHarness("界");
    try {
      const document = harness.seeded.documents[0];
      if (document?.currentRevision === null || document === undefined) {
        throw new Error("Expected one current source revision.");
      }
      const kind = "chapter";
      const title = "第一章";
      const metadataJson = '{"标签":"值"}';
      const fixedBytes = [
        "界",
        document.id,
        document.currentRevision.id,
        kind,
        title,
        metadataJson,
      ].reduce((total, value) => total + Buffer.byteLength(value, "utf8"), 0);
      const exactContent = "a".repeat(EXPORT_CAPACITY_LIMITS.source_bytes - fixedBytes);
      harness.database.raw
        .prepare("UPDATE documents SET kind = ?, title = ? WHERE id = ?")
        .run(kind, title, document.id);
      harness.database.raw
        .prepare(
          "UPDATE document_revisions SET content_markdown = ?, metadata_json = ? WHERE id = ?",
        )
        .run(exactContent, metadataJson, document.currentRevision.id);

      const exact = harness.exports.readExportSource(harness.scope, harness.projectId, now);
      expect(exact.documents[0]?.contentMarkdown).toHaveLength(exactContent.length);

      harness.database.raw
        .prepare(
          "UPDATE document_revisions SET content_markdown = content_markdown || 'a' WHERE id = ?",
        )
        .run(document.currentRevision.id);
      expectCapacityFailure(
        () => harness.exports.readExportSource(harness.scope, harness.projectId, now),
        "source_bytes",
        EXPORT_CAPACITY_LIMITS.source_bytes,
      );
    } finally {
      harness.database.close();
    }
  }, 30_000);
});

async function openHarness(title: string) {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-source-capacity-"));
  directories.push(directory);
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const store = new DrizzleStudioStore({ database: database.db });
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "export-source-capacity-secret",
    now: () => now,
  });
  await auth.configureOwner("export-capacity-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("export-capacity-owner", "long-test-password"))
    .principal;
  const scope = scopeForPrincipal(principal);
  const seeded = store.addProject(scope, {
    title,
    description: "",
    settingsJson: "{}",
    seed: {
      kind: "chapter",
      title: "Seed",
      contentMarkdown: "seed",
      metadataJson: "{}",
    },
    now,
  });
  return {
    database,
    exports: new ExportStorePart(database.db),
    projectId: seeded.project.id,
    scope,
    seeded,
  };
}

function seedDocuments(
  database: import("better-sqlite3").Database,
  projectId: string,
  total: number,
): void {
  database.transaction(() => {
    database
      .prepare(
        `WITH RECURSIVE sequence(value) AS (
           SELECT 2 UNION ALL SELECT value + 1 FROM sequence WHERE value < ?
         )
         INSERT INTO documents
           (id, project_id, kind, title, position, lore_aliases_json, lore_status,
            current_revision_id, created_at, updated_at)
         SELECT printf('d%05d', value), ?, 'note', printf('N%05d', value), value,
                '[]', 'draft', printf('r%05d', value), ?, ?
         FROM sequence`,
      )
      .run(total, projectId, now.getTime(), now.getTime());
    database
      .prepare(
        `WITH RECURSIVE sequence(value) AS (
           SELECT 2 UNION ALL SELECT value + 1 FROM sequence WHERE value < ?
         )
         INSERT INTO document_revisions
           (id, document_id, revision_number, content_markdown, metadata_json, source, created_at)
         SELECT printf('r%05d', value), printf('d%05d', value), 1, '', '{}', 'author', ?
         FROM sequence`,
      )
      .run(total, now.getTime());
  })();
}

function insertInvalidNextDocument(
  database: import("better-sqlite3").Database,
  projectId: string,
): void {
  database
    .prepare(
      `INSERT INTO documents
         (id, project_id, kind, title, position, lore_aliases_json, lore_status,
          current_revision_id, created_at, updated_at)
       VALUES ('d65537', ?, 'note', 'N65537', 65537, '[]', 'draft', NULL, ?, ?)`,
    )
    .run(projectId, now.getTime(), now.getTime());
}

function seedOversizedSnapshot(
  database: import("better-sqlite3").Database,
  projectId: string,
  seed: { id: string; currentRevision: { id: string } | null } | undefined,
): void {
  if (seed?.currentRevision === null || seed === undefined) {
    throw new Error("Expected the seed revision for snapshot capacity.");
  }
  const seedRevision = seed.currentRevision;
  database.transaction(() => {
    database
      .prepare(
        `INSERT INTO document_revisions
           (id, document_id, revision_number, content_markdown, metadata_json, source, created_at)
         VALUES ('r65537', 'd65537', 1, '', '{}', 'author', ?)`,
      )
      .run(now.getTime());
    database
      .prepare("UPDATE documents SET current_revision_id = 'r65537' WHERE id = 'd65537'")
      .run();
    database
      .prepare(
        "INSERT INTO project_snapshots (id, project_id, reason, created_at) VALUES ('bounded-snapshot', ?, 'export', ?)",
      )
      .run(projectId, now.getTime());
    database
      .prepare(
        `INSERT INTO snapshot_documents
           (id, snapshot_id, document_id, revision_id, document_kind, document_title,
            revision_metadata_json, position)
         VALUES ('snapshot-seed', 'bounded-snapshot', ?, ?, 'chapter', 'Seed', '{}', 1)`,
      )
      .run(seed.id, seedRevision.id);
    database
      .prepare(
        `WITH RECURSIVE sequence(value) AS (
           SELECT 2 UNION ALL SELECT value + 1 FROM sequence WHERE value < 65537
         )
         INSERT INTO snapshot_documents
           (id, snapshot_id, document_id, revision_id, document_kind, document_title,
            revision_metadata_json, position)
         SELECT printf('s%05d', value), 'bounded-snapshot', printf('d%05d', value),
                printf('r%05d', value), 'note', printf('N%05d', value), '{}', value
         FROM sequence`,
      )
      .run();
  })();
}

function expectCapacityFailure(
  action: () => unknown,
  resource: "source_documents" | "source_bytes",
  limit: number,
): void {
  try {
    action();
    throw new Error("Expected export source capacity to reject the request.");
  } catch (error) {
    expect(error).toBeInstanceOf(ExportCapacityExceededError);
    expect(error).toMatchObject({ resource, limit, observed: limit + 1 });
  }
}
