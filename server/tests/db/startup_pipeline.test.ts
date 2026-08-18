import { mkdtemp, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const DATABASE_FILENAME = "novel-engine.sqlite3";

async function makeDataDirectory(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-persistence-"));
}

function tableNames(database: Database.Database): string[] {
  const rows = database
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table'")
    .all() as Array<{ name: string }>;
  return rows.map((row) => row.name);
}

describe("startup pipeline", () => {
  it("bootstraps a missing database cleanly without writing a backup", async () => {
    const directory = await makeDataDirectory();

    const studio = await openStudioDatabase(directory);
    try {
      const tables = tableNames(studio.raw);
      expect(tables).toContain("sessions");
      expect(tables).toContain("jobs");
      expect(tables).toContain("job_events");
      expect(tables).toContain("__drizzle_migrations");
    } finally {
      studio.close();
    }

    await expect(readdir(join(directory, "backups"))).rejects.toThrow();
  });

  it("enforces the adjudicated connection PRAGMAs", async () => {
    const directory = await makeDataDirectory();

    const studio = await openStudioDatabase(directory);
    try {
      expect(studio.raw.pragma("journal_mode", { simple: true })).toBe("wal");
      expect(studio.raw.pragma("foreign_keys", { simple: true })).toBe(1);
      expect(studio.raw.pragma("synchronous", { simple: true })).toBe(1);
    } finally {
      studio.close();
    }
  });

  it("backs up the pre-migration state before migrating an earlier-release database", async () => {
    const directory = await makeDataDirectory();
    const databasePath = join(directory, DATABASE_FILENAME);

    const preRelease = new Database(databasePath);
    preRelease.exec("CREATE TABLE pre_rewrite_marker (id TEXT PRIMARY KEY)");
    preRelease.prepare("INSERT INTO pre_rewrite_marker (id) VALUES (?)").run("kept-content");
    preRelease.close();

    const studio = await openStudioDatabase(directory);
    try {
      expect(tableNames(studio.raw)).toContain("sessions");
    } finally {
      studio.close();
    }

    const backups = await readdir(join(directory, "backups"));
    expect(backups).toHaveLength(1);
    expect(backups[0]).toMatch(/^novel-engine-\d{8}T\d{6,9}Z\.sqlite3\.bak$/);

    const backup = new Database(join(directory, "backups", backups[0] ?? ""));
    try {
      expect(tableNames(backup)).toContain("pre_rewrite_marker");
      expect(tableNames(backup)).not.toContain("sessions");
      const marker = backup.prepare("SELECT id FROM pre_rewrite_marker").get();
      expect(marker).toEqual({ id: "kept-content" });
    } finally {
      backup.close();
    }
  });

  it("fails loudly and keeps the pre-migration state when migrations cannot apply", async () => {
    const directory = await makeDataDirectory();
    const databasePath = join(directory, DATABASE_FILENAME);

    const existing = new Database(databasePath);
    existing.exec("CREATE TABLE sessions (incompatible_shape INTEGER)");
    existing.exec("INSERT INTO sessions VALUES (7)");
    existing.close();

    await expect(openStudioDatabase(directory)).rejects.toThrow();

    const after = new Database(databasePath);
    try {
      const rows = after.prepare("SELECT incompatible_shape FROM sessions").all();
      expect(rows).toEqual([{ incompatible_shape: 7 }]);
    } finally {
      after.close();
    }
  });

  it("skips the backup for an empty database file", async () => {
    const directory = await makeDataDirectory();
    await writeFile(join(directory, DATABASE_FILENAME), "");

    const studio = await openStudioDatabase(directory);
    try {
      expect(tableNames(studio.raw)).toContain("sessions");
    } finally {
      studio.close();
    }

    await expect(readdir(join(directory, "backups"))).rejects.toThrow();
  });

  it("creates the hand-written FTS5 placeholder virtual table", async () => {
    const directory = await makeDataDirectory();

    const studio = await openStudioDatabase(directory);
    try {
      const ddl = studio.raw
        .prepare("SELECT sql FROM sqlite_master WHERE name = 'document_search'")
        .get() as { sql: string } | undefined;
      expect(ddl?.sql).toContain("USING fts5");
      expect(ddl?.sql).toContain("document_id UNINDEXED");
      expect(ddl?.sql).toContain("project_id UNINDEXED");

      studio.raw
        .prepare(
          "INSERT INTO document_search (document_id, project_id, title, content) VALUES (?, ?, ?, ?)",
        )
        .run("doc-1", "project-1", "The Lighthouse", "The keeper trimmed the lamp at dusk.");
      const hits = studio.raw
        .prepare("SELECT document_id FROM document_search WHERE document_search MATCH ?")
        .all("keeper") as Array<{ document_id: string }>;
      expect(hits).toEqual([{ document_id: "doc-1" }]);
    } finally {
      studio.close();
    }
  });
});
