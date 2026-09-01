import { mkdtemp, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { acquireDataDirectoryLock } from "../../src/shared/infrastructure/db/data_directory_lock.js";
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
  it("closes a data-directory ownership handle idempotently", async () => {
    const directory = await makeDataDirectory();
    const ownership = acquireDataDirectoryLock(directory);

    ownership.close();
    expect(() => ownership.close()).not.toThrow();

    const reacquired = acquireDataDirectoryLock(directory);
    reacquired.close();
  });

  it("owns one data directory before backup or recovery work begins", async () => {
    const directory = await makeDataDirectory();
    const first = await openStudioDatabase(directory);
    let blockedHookRan = false;
    try {
      await expect(
        openStudioDatabase(directory, {
          beforeJobRecovery: () => {
            blockedHookRan = true;
          },
        }),
      ).rejects.toThrow(/already owned by another Novel Engine process/i);
      expect(blockedHookRan).toBe(false);
      await expect(readdir(join(directory, "backups"))).rejects.toThrow();
    } finally {
      first.close();
    }

    let reopenedHookRan = false;
    const reopened = await openStudioDatabase(directory, {
      beforeJobRecovery: () => {
        reopenedHookRan = true;
      },
    });
    try {
      expect(reopenedHookRan).toBe(true);
    } finally {
      reopened.close();
    }
  });

  it("releases data-directory ownership when startup recovery fails", async () => {
    const directory = await makeDataDirectory();

    await expect(
      openStudioDatabase(directory, {
        beforeJobRecovery: () => {
          throw new Error("simulated recovery failure");
        },
      }),
    ).rejects.toThrow("simulated recovery failure");

    const reopened = await openStudioDatabase(directory);
    reopened.close();
  });

  it("retries partial connection cleanup before releasing directory ownership", async () => {
    const directory = await makeDataDirectory();
    const databasePath = join(directory, DATABASE_FILENAME);
    const originalPragma = Database.prototype.pragma;
    const originalClose = Database.prototype.close;
    let contentCloseAttempts = 0;
    Database.prototype.pragma = function pragmaWithInitializationFailure(source, options) {
      if (this.name === databasePath && source === "foreign_keys = ON") {
        throw new Error("simulated pragma initialization failure");
      }
      return originalPragma.call(this, source, options);
    };
    Database.prototype.close = function closeWithOneInitializationFailure() {
      if (this.name === databasePath) {
        contentCloseAttempts += 1;
        if (contentCloseAttempts === 1) {
          throw new Error("simulated partial connection close failure");
        }
      }
      return originalClose.call(this);
    };

    let failure: unknown;
    try {
      failure = await openStudioDatabase(directory).catch((error: unknown) => error);
    } finally {
      Database.prototype.pragma = originalPragma;
      Database.prototype.close = originalClose;
    }

    expect(failure).toBeInstanceOf(AggregateError);
    expect((failure as AggregateError).errors).toEqual([
      expect.objectContaining({ message: "simulated pragma initialization failure" }),
      expect.objectContaining({ message: "simulated partial connection close failure" }),
    ]);
    expect(contentCloseAttempts).toBe(2);
    const reacquired = acquireDataDirectoryLock(directory);
    reacquired.close();
  });

  it("keeps ownership when the content database cannot close and retries in order", async () => {
    const directory = await makeDataDirectory();
    const studio = await openStudioDatabase(directory);
    const closeContentDatabase = studio.raw.close.bind(studio.raw);
    let closeAttempts = 0;
    studio.raw.close = () => {
      closeAttempts += 1;
      if (closeAttempts === 1) throw new Error("simulated content close failure");
      return closeContentDatabase();
    };

    try {
      expect(() => studio.close()).toThrow("simulated content close failure");
      expect(() => acquireDataDirectoryLock(directory)).toThrow(
        /already owned by another Novel Engine process/i,
      );

      expect(() => studio.close()).not.toThrow();
      expect(closeAttempts).toBe(2);
      const reacquired = acquireDataDirectoryLock(directory);
      reacquired.close();
    } finally {
      studio.close();
    }
  });

  it("retries ownership release without closing the content database twice", async () => {
    const directory = await makeDataDirectory();
    const studio = await openStudioDatabase(directory);
    const closeContentDatabase = studio.raw.close.bind(studio.raw);
    let contentCloseAttempts = 0;
    studio.raw.close = () => {
      contentCloseAttempts += 1;
      return closeContentDatabase();
    };

    const originalClose = Database.prototype.close;
    let failOwnershipClose = true;
    Database.prototype.close = function closeWithOneOwnershipFailure() {
      if (failOwnershipClose && this.name.endsWith(".novel-engine-ownership.sqlite3")) {
        failOwnershipClose = false;
        throw new Error("simulated ownership close failure");
      }
      return originalClose.call(this);
    };
    try {
      expect(() => studio.close()).toThrow("simulated ownership close failure");
      expect(contentCloseAttempts).toBe(1);
      expect(() => acquireDataDirectoryLock(directory)).toThrow(
        /already owned by another Novel Engine process/i,
      );

      expect(() => studio.close()).not.toThrow();
      expect(contentCloseAttempts).toBe(1);
      const reacquired = acquireDataDirectoryLock(directory);
      reacquired.close();
    } finally {
      Database.prototype.close = originalClose;
      studio.close();
    }
  });

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
      expect(studio.raw.pragma("synchronous", { simple: true })).toBe(2);
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
