import { mkdir, mkdtemp, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import {
  backupDatabaseFile,
  DEFAULT_BACKUP_RETENTION,
} from "../../src/shared/infrastructure/db/backup.js";

async function makeSourceDatabase(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-backup-policy-"));
  const databasePath = join(directory, "novel-engine.sqlite3");
  const database = new Database(databasePath);
  try {
    database.exec("CREATE TABLE marker (id TEXT PRIMARY KEY)");
    database.prepare("INSERT INTO marker (id) VALUES (?)").run("kept-content");
  } finally {
    database.close();
  }
  return databasePath;
}

async function listBackups(databasePath: string): Promise<string[]> {
  return readdir(join(dirname(databasePath), "backups")).catch(() => []);
}

describe("backup policy", () => {
  it("writes a verified backup, prunes older generations, and leaves no sidecars", async () => {
    const databasePath = await makeSourceDatabase();
    const backupsDirectory = join(dirname(databasePath), "backups");
    await mkdir(backupsDirectory, { recursive: true });
    const planted = [
      "novel-engine-20200101T000000000Z.sqlite3.bak",
      "novel-engine-20200102T000000000Z.sqlite3.bak",
      "novel-engine-20200103T000000000Z.sqlite3.bak",
      "novel-engine-20200104T000000000Z.sqlite3.bak",
    ];
    for (const name of planted) {
      await writeFile(join(backupsDirectory, name), "superseded generation");
    }

    const target = await backupDatabaseFile(databasePath);
    if (target === null) throw new Error("expected a backup target");

    const names = await readdir(backupsDirectory);
    expect(names).toHaveLength(DEFAULT_BACKUP_RETENTION);
    expect(names.some((name) => /-(wal|shm|journal)$/.test(name))).toBe(false);
    expect(names).not.toContain(planted[0]);
    expect(names).not.toContain(planted[1]);
    expect(names).toContain(planted[2]);
    expect(names).toContain(planted[3]);
    expect(names).toContain(target.split("/").pop());

    const check = new Database(target, { readonly: true, fileMustExist: true });
    try {
      expect(String(check.pragma("quick_check", { simple: true }))).toBe("ok");
    } finally {
      check.close();
    }
  });

  it("fails with the required and available byte counts without writing a file", async () => {
    const databasePath = await makeSourceDatabase();

    const failure = await backupDatabaseFile(databasePath, { spaceProbe: () => 1 }).catch(
      (error: unknown) => error,
    );

    expect(failure).toBeInstanceOf(Error);
    const message = (failure as Error).message;
    expect(message).toMatch(/Not enough free space to back up/);
    expect(message).toMatch(/need \d+ bytes, only 1 bytes are available/);
    expect(message).toMatch(/Free disk space or move old backups/);
    expect(await listBackups(databasePath)).toEqual([]);
  });

  it("removes an artifact that fails its integrity self-check", async () => {
    const databasePath = await makeSourceDatabase();
    const originalPragma = Database.prototype.pragma;
    Database.prototype.pragma = function pragmaWithFailingQuickCheck(source, options) {
      if (this.name.endsWith(".sqlite3.bak") && source === "quick_check") {
        throw new Error("simulated malformed backup");
      }
      return originalPragma.call(this, source, options);
    };
    try {
      await expect(backupDatabaseFile(databasePath)).rejects.toThrow(
        /failed its integrity self-check \(simulated malformed backup\): .*The file was removed/,
      );
    } finally {
      Database.prototype.pragma = originalPragma;
    }

    expect(await listBackups(databasePath)).toEqual([]);
  });
});
