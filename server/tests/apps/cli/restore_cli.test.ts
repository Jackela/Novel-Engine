import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import { backupDatabaseFile } from "../../../src/shared/infrastructure/db/backup.js";
import { owners } from "../../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";

interface RestoreHarness {
  directory: string;
  dataDirectory: string;
  databasePath: string;
  lines: string[];
  context: Parameters<typeof runCli>[1];
}

async function restoreHarness(): Promise<RestoreHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-restore-cli-"));
  const dataDirectory = join(directory, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  return {
    directory,
    dataDirectory,
    databasePath,
    lines,
    context: {
      envFile: null,
      workingDirectory: directory,
      env: { DB_URL: `sqlite:///${databasePath}`, APP_ENVIRONMENT: "testing" },
      writeLine: (line: string) => {
        lines.push(line);
      },
    },
  };
}

/** Leave a migrated database with one distinguishing owner row behind. */
async function seedOwner(databasePath: string, username: string): Promise<void> {
  const studio = await openStudioDatabase(databasePath);
  try {
    studio.db
      .insert(owners)
      .values({
        id: `owner-${username}`,
        username,
        password_hash: "test-only",
        created_at: new Date("2026-09-01T00:00:00.000Z"),
      })
      .run();
  } finally {
    studio.close();
  }
}

/** Produce a real `backup`-style artifact from a database holding `username`. */
async function backupFromSeededSource(directory: string, username: string): Promise<string> {
  const sourcePath = join(directory, "restore-source", "novel-engine.sqlite3");
  await seedOwner(sourcePath, username);
  const backupPath = await backupDatabaseFile(sourcePath);
  expect(backupPath).not.toBeNull();
  return backupPath as string;
}

function ownerUsernames(databasePath: string): string[] {
  const raw = new Database(databasePath, { readonly: true, fileMustExist: true });
  try {
    return (
      raw.prepare("SELECT username FROM owners ORDER BY username").all() as Array<{
        username: string;
      }>
    ).map((row) => row.username);
  } finally {
    raw.close();
  }
}

describe("restore CLI", () => {
  it("restores a verified backup over the current database after a safety backup", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    const input = await backupFromSeededSource(harness.directory, "rescued");

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(0);
    expect(ownerUsernames(harness.databasePath)).toEqual(["rescued"]);

    const backupsDirectory = join(harness.dataDirectory, "backups");
    const safetyBackups = await readdir(backupsDirectory);
    expect(safetyBackups).toHaveLength(1);
    expect(ownerUsernames(join(backupsDirectory, safetyBackups[0] ?? ""))).toEqual(["current"]);

    expect(harness.lines.join("\n")).toContain(`Verifying restore input: ${input}`);
    expect(harness.lines.join("\n")).toContain("Backed up the replaced database:");
    expect(harness.lines.join("\n")).toContain(`Restored the database: ${harness.databasePath}`);
  });

  it("removes stale WAL sidecars of the replaced database generation", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    // Planted after seeding so the sidecar exists when restore replaces the
    // database file, mirroring a database left behind by an abrupt exit.
    await writeFile(`${harness.databasePath}-wal`, "stale write-ahead log bytes");
    await writeFile(`${harness.databasePath}-shm`, "stale shared-memory bytes");
    const input = await backupFromSeededSource(harness.directory, "rescued");

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(0);
    // Assert sidecar removal before any database open: a read-only open of a
    // WAL-mode database itself creates lingering -wal/-shm files.
    expect(existsSync(`${harness.databasePath}-wal`)).toBe(false);
    expect(existsSync(`${harness.databasePath}-shm`)).toBe(false);
    expect(ownerUsernames(harness.databasePath)).toEqual(["rescued"]);
  });

  it("refuses a corrupt backup input without touching the current database", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    const input = join(harness.directory, "corrupt.sqlite3");
    await writeFile(input, "this is definitely not a sqlite database");

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toMatch(/Restore input failed the integrity check/i);
    expect(ownerUsernames(harness.databasePath)).toEqual(["current"]);
    expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
  });

  it("refuses a missing backup input without touching the current database", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    const input = join(harness.directory, "absent.sqlite3");

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toContain(`Restore input is missing or unreadable: ${input}`);
    expect(ownerUsernames(harness.databasePath)).toEqual(["current"]);
  });

  it("refuses an empty backup input", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    const input = join(harness.directory, "empty.sqlite3");
    await writeFile(input, "");

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toMatch(/Restore input is empty/i);
    expect(ownerUsernames(harness.databasePath)).toEqual(["current"]);
  });

  it("refuses a structurally valid unrelated SQLite database", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    const input = join(harness.directory, "foreign.sqlite3");
    const foreign = new Database(input);
    try {
      foreign.exec("CREATE TABLE address_book (id text PRIMARY KEY, name text NOT NULL)");
    } finally {
      foreign.close();
    }

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toMatch(
      /Restore input is not a Novel Engine database: missing "__drizzle_migrations" table/i,
    );
    expect(ownerUsernames(harness.databasePath)).toEqual(["current"]);
    expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
  });

  it("refuses a retired Python-stack database that shares the jobs table", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    // The 0.3.x Python authority also named its workflow table `jobs`
    // (python-final: src/contexts/studio/infrastructure/workflow_models.py),
    // so table-name presence alone cannot discriminate. Only the drizzle
    // migration journal, created by the first TS-stack startup, proves the
    // input belongs to this stack.
    const input = join(harness.directory, "python-era.sqlite3");
    const pythonEra = new Database(input);
    try {
      pythonEra.exec(
        "CREATE TABLE jobs (id text PRIMARY KEY, kind text NOT NULL, status text NOT NULL, created_at integer NOT NULL)",
      );
    } finally {
      pythonEra.close();
    }

    const code = await runCli(["restore", "--input", input], harness.context);

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toMatch(
      /Restore input is not a Novel Engine database: missing "__drizzle_migrations" table/i,
    );
    expect(ownerUsernames(harness.databasePath)).toEqual(["current"]);
    expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
  });

  it("reports a missing --input flag as usage error exit 2", async () => {
    const harness = await restoreHarness();

    const code = await runCli(["restore"], harness.context);

    expect(code).toBe(2);
    expect(harness.lines).toEqual(["Restore requires --input BACKUP."]);
  });

  it("refuses restore while another process owns the data directory", async () => {
    const harness = await restoreHarness();
    await seedOwner(harness.databasePath, "current");
    const input = await backupFromSeededSource(harness.directory, "rescued");
    const active = await openStudioDatabase(harness.databasePath);
    try {
      const code = await runCli(["restore", "--input", input], harness.context);

      expect(code).toBe(1);
      expect(harness.lines.join("\n")).toMatch(/already owned by another Novel Engine process/i);
      expect(ownerUsernames(harness.databasePath)).toEqual(["current"]);
    } finally {
      active.close();
    }

    harness.lines.length = 0;
    const completedCode = await runCli(["restore", "--input", input], harness.context);
    expect(completedCode).toBe(0);
    expect(ownerUsernames(harness.databasePath)).toEqual(["rescued"]);
  });
});
