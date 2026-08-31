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
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
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

function seedLegacyReviewSnapshots(raw: Database.Database): void {
  const now = Date.parse("2026-08-31T00:00:00.000Z");
  raw.exec(`
    BEGIN;
    INSERT INTO owners (id, username, password_hash, created_at)
      VALUES ('owner-1', 'legacy-review-owner', 'hash', ${now});
    INSERT INTO projects
      (id, owner_id, title, description, settings_json, import_hash, created_at, updated_at)
      VALUES ('project-1', 'owner-1', 'Legacy reviews', '', '{}', NULL, ${now}, ${now});

    INSERT INTO documents
      (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
      VALUES ('doc-orphan', 'project-1', 'chapter', 'Orphan source', 1, NULL, ${now}, ${now});
    INSERT INTO documents
      (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
      VALUES ('doc-kept', 'project-1', 'chapter', 'Kept source', 2, NULL, ${now}, ${now});
    INSERT INTO document_revisions
      (id, document_id, parent_revision_id, revision_number, content_markdown, metadata_json, source, created_at)
      VALUES ('rev-orphan', 'doc-orphan', NULL, 1, 'orphan content', '{}', 'author', ${now});
    INSERT INTO document_revisions
      (id, document_id, parent_revision_id, revision_number, content_markdown, metadata_json, source, created_at)
      VALUES ('rev-kept', 'doc-kept', NULL, 1, 'kept content', '{}', 'author', ${now});
    UPDATE documents SET current_revision_id = 'rev-orphan' WHERE id = 'doc-orphan';
    UPDATE documents SET current_revision_id = 'rev-kept' WHERE id = 'doc-kept';

    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-orphan', 'project-1', 'review', ${now});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-review', 'project-1', 'review', ${now + 1});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-export-used', 'project-1', 'export', ${now + 2});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-export-empty', 'project-1', 'export', ${now + 3});
    INSERT INTO project_snapshots (id, project_id, reason, created_at)
      VALUES ('snapshot-review-export-guard', 'project-1', 'review', ${now + 4});

    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-orphan', 'snapshot-orphan', 'doc-orphan', 'rev-orphan', 'chapter', 'Orphan source', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-review', 'snapshot-review', 'doc-kept', 'rev-kept', 'chapter', 'Kept source', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-export-used', 'snapshot-export-used', 'doc-kept', 'rev-kept', 'chapter', 'Kept source', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-export-empty', 'snapshot-export-empty', 'doc-kept', 'rev-kept', 'chapter', 'Kept source', '{}', 1);
    INSERT INTO snapshot_documents
      (id, snapshot_id, document_id, revision_id, document_kind, document_title, revision_metadata_json, position)
      VALUES ('sd-review-export-guard', 'snapshot-review-export-guard', 'doc-kept', 'rev-kept', 'chapter', 'Kept source', '{}', 1);

    INSERT INTO reviews (id, project_id, snapshot_id, provider, model, summary, created_at)
      VALUES ('review-1', 'project-1', 'snapshot-review', 'mock', 'legacy-model', 'kept', ${now + 4});
    INSERT INTO review_issues
      (id, review_id, snapshot_document_id, document_id, severity, code, message, suggestion, evidence_json)
      VALUES ('issue-1', 'review-1', 'sd-review', 'doc-kept', 'warning', 'pacing', 'kept issue', '', '{}');
    INSERT INTO exports
      (id, project_id, snapshot_id, format, relative_path, size_bytes, checksum_sha256, created_at)
      VALUES ('export-1', 'project-1', 'snapshot-export-used', 'markdown', 'exports/file.md', 4, 'hash', ${now + 5});
    INSERT INTO exports
      (id, project_id, snapshot_id, format, relative_path, size_bytes, checksum_sha256, created_at)
      VALUES ('export-guard', 'project-1', 'snapshot-review-export-guard', 'markdown', 'exports/guard.md', 5, 'hash-guard', ${now + 6});
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

describe("orphan review snapshot migration", () => {
  it("removes only review snapshots without durable assessments", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-review-cleanup-"));
    directories.push(directory);
    const preCleanup = await migrationsFolderUpto(11);
    const legacy = migrateTo(directory, preCleanup);
    try {
      seedLegacyReviewSnapshots(legacy);
    } finally {
      legacy.close();
    }

    const upgraded = await openStudioDatabase(directory);
    try {
      expect(ids(upgraded.raw, "project_snapshots")).toEqual([
        "snapshot-export-empty",
        "snapshot-export-used",
        "snapshot-review",
        "snapshot-review-export-guard",
      ]);
      expect(ids(upgraded.raw, "snapshot_documents")).toEqual([
        "sd-export-empty",
        "sd-export-used",
        "sd-review",
        "sd-review-export-guard",
      ]);
      expect(ids(upgraded.raw, "reviews")).toEqual(["review-1"]);
      expect(ids(upgraded.raw, "review_issues")).toEqual(["issue-1"]);
      expect(ids(upgraded.raw, "exports")).toEqual(["export-1", "export-guard"]);
      expect(upgraded.raw.pragma("foreign_key_check")).toEqual([]);
      expect(() =>
        upgraded.raw.prepare("DELETE FROM documents WHERE id = ?").run("doc-orphan"),
      ).not.toThrow();
    } finally {
      upgraded.close();
    }

    const restarted = await openStudioDatabase(directory);
    try {
      expect(ids(restarted.raw, "project_snapshots")).toEqual([
        "snapshot-export-empty",
        "snapshot-export-used",
        "snapshot-review",
        "snapshot-review-export-guard",
      ]);
      expect(restarted.raw.pragma("foreign_key_check")).toEqual([]);
    } finally {
      restarted.close();
    }
  });
});
