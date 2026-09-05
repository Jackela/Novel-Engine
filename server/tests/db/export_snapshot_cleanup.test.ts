import { cpSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { afterEach, describe, expect, it } from "vitest";

import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const DATABASE_FILENAME = "novel-engine.sqlite3";
const directories: string[] = [];

interface Journal {
  entries: Array<{ idx: number; when: number; tag: string }>;
}

afterEach(async () => {
  await Promise.all(
    directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })),
  );
});

async function migrationsFolderUpto(lastIndex: number): Promise<string> {
  const source = join(process.cwd(), "drizzle");
  const destination = await mkdtemp(join(tmpdir(), `novel-engine-drizzle-upto${lastIndex}-`));
  directories.push(destination);
  cpSync(source, destination, { recursive: true });
  const journalPath = join(destination, "meta", "_journal.json");
  const journal = JSON.parse(readFileSync(journalPath, "utf8")) as Journal;
  writeFileSync(
    journalPath,
    JSON.stringify({ entries: journal.entries.filter((entry) => entry.idx <= lastIndex) }, null, 2),
    "utf8",
  );
  return destination;
}

function migrateTo(directory: string, migrationsFolder: string): Database.Database {
  const raw = new Database(join(directory, DATABASE_FILENAME));
  raw.pragma("foreign_keys = ON");
  migrate(drizzle(raw), { migrationsFolder });
  return raw;
}

function seedLegacyExportSnapshots(raw: Database.Database): void {
  const now = Date.parse("2026-08-31T08:00:00.000Z");
  raw.exec(`
    BEGIN;
    INSERT INTO owners (id, username, password_hash, created_at)
      VALUES ('owner-1', 'legacy-export-owner', 'hash', ${now});
    INSERT INTO projects
      (id, owner_id, title, description, settings_json, import_hash, created_at, updated_at)
      VALUES ('project-1', 'owner-1', 'Legacy exports', '', '{}', NULL, ${now}, ${now});

    INSERT INTO documents
      (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
      VALUES ('doc-orphan', 'project-1', 'chapter', 'Orphan source', 1, NULL, ${now}, ${now});
    INSERT INTO documents
      (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
      VALUES ('doc-export', 'project-1', 'chapter', 'Exported source', 2, NULL, ${now}, ${now});
    INSERT INTO documents
      (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
      VALUES ('doc-export-review', 'project-1', 'chapter', 'Cross evidence', 3, NULL, ${now}, ${now});
    INSERT INTO documents
      (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
      VALUES ('doc-review', 'project-1', 'chapter', 'Review source', 4, NULL, ${now}, ${now});

    INSERT INTO document_revisions
      (id, document_id, parent_revision_id, revision_number, content_markdown, metadata_json, source, created_at)
      VALUES ('rev-orphan', 'doc-orphan', NULL, 1, 'orphan content', '{}', 'author', ${now});
    INSERT INTO document_revisions
      (id, document_id, parent_revision_id, revision_number, content_markdown, metadata_json, source, created_at)
      VALUES ('rev-export', 'doc-export', NULL, 1, 'export content', '{}', 'author', ${now});
    INSERT INTO document_revisions
      (id, document_id, parent_revision_id, revision_number, content_markdown, metadata_json, source, created_at)
      VALUES ('rev-export-review', 'doc-export-review', NULL, 1, 'cross content', '{}', 'author', ${now});
    INSERT INTO document_revisions
      (id, document_id, parent_revision_id, revision_number, content_markdown, metadata_json, source, created_at)
      VALUES ('rev-review', 'doc-review', NULL, 1, 'review content', '{}', 'author', ${now});
    UPDATE documents SET current_revision_id = 'rev-orphan' WHERE id = 'doc-orphan';
    UPDATE documents SET current_revision_id = 'rev-export' WHERE id = 'doc-export';
    UPDATE documents SET current_revision_id = 'rev-export-review' WHERE id = 'doc-export-review';
    UPDATE documents SET current_revision_id = 'rev-review' WHERE id = 'doc-review';

    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-export-orphan', 'project-1', 'export', ${now});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-export-completed', 'project-1', 'export', ${now + 1});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-export-review-guard', 'project-1', 'export', ${now + 2});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-review', 'project-1', 'review', ${now + 3});

    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-export-orphan', 'snapshot-export-orphan', 'doc-orphan', 'rev-orphan', 'chapter', 'Orphan source', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-export-completed', 'snapshot-export-completed', 'doc-export', 'rev-export', 'chapter', 'Exported source', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-export-review-guard', 'snapshot-export-review-guard', 'doc-export-review', 'rev-export-review', 'chapter', 'Cross evidence', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-review', 'snapshot-review', 'doc-review', 'rev-review', 'chapter', 'Review source', '{}', 1);

    INSERT INTO exports
      (id, project_id, snapshot_id, format, relative_path, size_bytes, checksum_sha256, created_at)
      VALUES ('export-completed', 'project-1', 'snapshot-export-completed', 'markdown', 'exports/project-1/export-completed.md', 14, 'hash-export', ${now + 4});
    INSERT INTO reviews (id, project_id, snapshot_id, provider, model, summary, created_at)
      VALUES ('review-completed', 'project-1', 'snapshot-review', 'mock', 'legacy-model', 'review evidence', ${now + 6});
    INSERT INTO review_issues
      (id, review_id, snapshot_document_id, document_id, severity, code, message, suggestion, evidence_json)
      VALUES ('issue-export-guard', 'review-completed', 'sd-export-review-guard', 'doc-export-review', 'warning', 'pacing', 'cross issue', '', '{}');
    INSERT INTO review_issues
      (id, review_id, snapshot_document_id, document_id, severity, code, message, suggestion, evidence_json)
      VALUES ('issue-review', 'review-completed', 'sd-review', 'doc-review', 'warning', 'continuity', 'review issue', '', '{}');
    COMMIT;
  `);
}

const ID_QUERIES = {
  exports: "SELECT id FROM exports ORDER BY id",
  project_snapshots: "SELECT id FROM project_snapshots ORDER BY id",
  review_issues: "SELECT id FROM review_issues ORDER BY id",
  reviews: "SELECT id FROM reviews ORDER BY id",
  snapshot_documents: "SELECT id FROM snapshot_documents ORDER BY id",
} as const;

function ids(raw: Database.Database, table: keyof typeof ID_QUERIES): string[] {
  return (raw.prepare(ID_QUERIES[table]).all() as Array<{ id: string }>).map((row) => row.id);
}

describe("orphan export snapshot migration", () => {
  it("removes only export snapshots without artifact or review evidence", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-cleanup-"));
    directories.push(directory);
    const preCleanup = await migrationsFolderUpto(12);
    const legacy = migrateTo(directory, preCleanup);
    try {
      seedLegacyExportSnapshots(legacy);
    } finally {
      legacy.close();
    }

    const upgraded = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      expect(ids(upgraded.raw, "project_snapshots")).toEqual([
        "snapshot-export-completed",
        "snapshot-export-review-guard",
        "snapshot-review",
      ]);
      expect(ids(upgraded.raw, "snapshot_documents")).toEqual([
        "sd-export-completed",
        "sd-export-review-guard",
        "sd-review",
      ]);
      expect(ids(upgraded.raw, "exports")).toEqual(["export-completed"]);
      expect(ids(upgraded.raw, "reviews")).toEqual(["review-completed"]);
      expect(ids(upgraded.raw, "review_issues")).toEqual(["issue-export-guard", "issue-review"]);
      expect(upgraded.raw.pragma("foreign_key_check")).toEqual([]);
      expect(
        upgraded.raw.prepare("DELETE FROM documents WHERE id = ?").run("doc-orphan").changes,
      ).toBe(1);
    } finally {
      upgraded.close();
    }

    const restarted = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      expect(ids(restarted.raw, "project_snapshots")).toEqual([
        "snapshot-export-completed",
        "snapshot-export-review-guard",
        "snapshot-review",
      ]);
      expect(ids(restarted.raw, "snapshot_documents")).toEqual([
        "sd-export-completed",
        "sd-export-review-guard",
        "sd-review",
      ]);
      expect(ids(restarted.raw, "exports")).toEqual(["export-completed"]);
      expect(ids(restarted.raw, "reviews")).toEqual(["review-completed"]);
      expect(ids(restarted.raw, "review_issues")).toEqual(["issue-export-guard", "issue-review"]);
      expect(restarted.raw.pragma("foreign_key_check")).toEqual([]);
    } finally {
      restarted.close();
    }
  });
});
