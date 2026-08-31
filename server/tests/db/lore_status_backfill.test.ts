import { cpSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { describe, expect, it } from "vitest";

import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";

const DATABASE_FILENAME = "novel-engine.sqlite3";

interface Journal {
  entries: Array<{ idx: number; when: number; tag: string }>;
}

/**
 * Copy of the real migrations folder whose journal stops before the given
 * index, so a database can be migrated to that historical version and then
 * advanced — replaying exactly what a pre-upgrade installation lives through.
 * (Same harness shape as `volume_backfill.test.ts`.)
 */
async function migrationsFolderUpto(lastIndex: number): Promise<string> {
  const source = join(process.cwd(), "drizzle");
  const destination = await mkdtemp(join(tmpdir(), `novel-engine-drizzle-upto${lastIndex}-`));
  cpSync(source, destination, { recursive: true });
  const journalPath = join(destination, "meta", "_journal.json");
  const journal = JSON.parse(readFileSync(journalPath, "utf8")) as Journal;
  const truncated: Journal = {
    entries: journal.entries.filter((entry) => entry.idx <= lastIndex),
  };
  writeFileSync(journalPath, JSON.stringify(truncated, null, 2), "utf8");
  return destination;
}

/** Migrate a raw file to the pre-status schema and seed the legacy rows. */
function migrateTo(targetDirectory: string, folder: string): Database.Database {
  const raw = new Database(join(targetDirectory, DATABASE_FILENAME));
  raw.pragma("foreign_keys = ON");
  migrate(drizzle(raw), { migrationsFolder: folder });
  return raw;
}

describe("lore lifecycle status migration (#444)", () => {
  it("adds the column and promotes existing lore entries to stable", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-lore-status-"));
    // Journal index 9 == migration folder 0010: the exact pre-status schema
    // (journal entries lag folder numbering by one because folder 0000_init
    // pairs with journal idx 0).
    const preStatus = await migrationsFolderUpto(9);

    // Phase one — arrive at the post-0010 schema and carry rows like a real
    // pre-upgrade installation would: lore entries (character/world) plus
    // non-lore kinds whose semantics must not change.
    const legacy = migrateTo(directory, preStatus);
    try {
      const now = 1_791_000_000_000;
      legacy.exec(`
        BEGIN;
        INSERT INTO owners (id, username, password_hash, created_at)
          VALUES ('owner-1', 'legacy-owner', 'hash', ${now});
        INSERT INTO projects (id, owner_id, title, description, settings_json, import_hash, created_at, updated_at)
          VALUES ('project-a', 'owner-1', 'Legacy A', '', '{}', NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-character', 'project-a', 'character', 'Mara', 1, NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-world', 'project-a', 'world', 'Sable Reaches', 1, NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-chapter', 'project-a', 'chapter', 'Chapter 1', 1, NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-note', 'project-a', 'note', 'Scratch', 1, NULL, ${now}, ${now});
        COMMIT;
      `);
    } finally {
      legacy.close();
    }

    // Phase two — advance with the full journal: migration 0011 applies and
    // its backfill pins the adjudication (#444, ADR-0006) that pre-existing
    // lore entries are the author's approved canon: character/world rows
    // read `stable` (injectable as before the gate existed), while every
    // other kind stays at the `draft` default and ignores the column.
    const advanced = migrateTo(directory, join(process.cwd(), "drizzle"));
    try {
      const statuses = advanced
        .prepare("SELECT id, kind, lore_status FROM documents ORDER BY id")
        .all() as Array<{ id: string; kind: string; lore_status: string }>;
      expect(statuses).toEqual([
        { id: "doc-chapter", kind: "chapter", lore_status: "draft" },
        { id: "doc-character", kind: "character", lore_status: "stable" },
        { id: "doc-note", kind: "note", lore_status: "draft" },
        { id: "doc-world", kind: "world", lore_status: "stable" },
      ]);
    } finally {
      advanced.close();
    }

    // Phase three — the restart pipeline accepts the upgraded store unchanged.
    const restarted: StudioDatabase = await openStudioDatabase(directory);
    try {
      expect(
        restarted.raw
          .prepare("SELECT COUNT(*) AS count FROM documents WHERE lore_status = 'stable'")
          .get(),
      ).toEqual({ count: 2 });
    } finally {
      restarted.close();
    }
  });
});
