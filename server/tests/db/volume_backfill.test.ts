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
 * The runtime migrator reads only the journal plus the tag-named SQL files.
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

/** Migrate a raw file to the pre-volumes schema and seed the legacy rows. */
function migrateTo(targetDirectory: string, folder: string): Database.Database {
  const raw = new Database(join(targetDirectory, DATABASE_FILENAME));
  raw.pragma("foreign_keys = ON");
  migrate(drizzle(raw), { migrationsFolder: folder });
  return raw;
}

describe("volume backfill migration", () => {
  it("backfills one default volume per legacy project holding its chapters", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-backfill-"));
    // Journal index 7 == migration folder 0007_naive_morg: the exact
    // pre-volumes schema state (journal entries lag folder numbering by one
    // because folder 0000_init pairs with journal idx 0).
    const preVolumes = await migrationsFolderUpto(7);

    // Phase one — arrive at the exact post-0007 schema and carry rows like a
    // real pre-upgrade installation would (two projects, chapter documents,
    // and one non-chapter outline per project).
    const legacy = migrateTo(directory, preVolumes);
    try {
      const now = 1_791_000_000_000;
      legacy.exec(`
        BEGIN;
        INSERT INTO owners (id, username, password_hash, created_at)
          VALUES ('owner-1', 'legacy-owner', 'hash', ${now});
        INSERT INTO projects (id, owner_id, title, description, settings_json, import_hash, created_at, updated_at)
          VALUES ('project-a', 'owner-1', 'Legacy A', '', '{}', NULL, ${now}, ${now});
        INSERT INTO projects (id, owner_id, title, description, settings_json, import_hash, created_at, updated_at)
          VALUES ('project-b', 'owner-1', 'Legacy B', '', '{}', NULL, ${now + 1}, ${now + 1});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-a1', 'project-a', 'chapter', 'Chapter 1', 1, NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-a2', 'project-a', 'chapter', 'Chapter 2', 2, NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-outline', 'project-a', 'outline', 'Outline 1', 1, NULL, ${now}, ${now});
        INSERT INTO documents (id, project_id, kind, title, position, current_revision_id, created_at, updated_at)
          VALUES ('doc-b1', 'project-b', 'chapter', 'Chapter 1', 1, NULL, ${now}, ${now});
        COMMIT;
      `);
    } finally {
      legacy.close();
    }

    // Phase two — advance with the full journal: migration 0008 applies and
    // its hand-written backfill places every chapter into its project's new
    // default volume while non-chapter documents stay outside volumes.
    const advanced = migrateTo(directory, join(process.cwd(), "drizzle"));
    try {
      const volumes = advanced.prepare("SELECT id, project_id, title, position FROM volumes").all();
      expect(volumes).toEqual([
        { id: "dvol-project-a", project_id: "project-a", title: "Default Volume", position: 1 },
        { id: "dvol-project-b", project_id: "project-b", title: "Default Volume", position: 1 },
      ]);
      const links = advanced
        .prepare("SELECT id, volume_id FROM documents ORDER BY id")
        .all() as Array<{ id: string; volume_id: string | null }>;
      expect(links).toEqual([
        { id: "doc-a1", volume_id: "dvol-project-a" },
        { id: "doc-a2", volume_id: "dvol-project-a" },
        { id: "doc-b1", volume_id: "dvol-project-b" },
        { id: "doc-outline", volume_id: null },
      ]);
    } finally {
      advanced.close();
    }

    // Phase three — the restart pipeline accepts the upgraded store unchanged.
    const restarted: StudioDatabase = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      expect(restarted.raw.prepare("SELECT COUNT(*) AS count FROM volumes").get()).toEqual({
        count: 2,
      });
    } finally {
      restarted.close();
    }
  });
});
