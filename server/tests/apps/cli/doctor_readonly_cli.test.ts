import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";

interface CliHarness {
  directory: string;
  dataDirectory: string;
  databasePath: string;
  lines: string[];
  context: Parameters<typeof runCli>[1];
}

async function cliHarness(): Promise<CliHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-doctor-readonly-"));
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

const bundledMigrations = (
  JSON.parse(
    readFileSync(new URL("../../../drizzle/meta/_journal.json", import.meta.url), "utf8"),
  ) as { entries: unknown[] }
).entries.length;

/** Leave a non-empty pre-migration marker database behind, so migrations are pending. */
function seedPreMigrationDatabase(harness: CliHarness): void {
  const preRelease = new Database(harness.databasePath);
  try {
    preRelease.exec("CREATE TABLE pre_rewrite_marker (id TEXT PRIMARY KEY)");
    preRelease.prepare("INSERT INTO pre_rewrite_marker (id) VALUES (?)").run("kept-content");
  } finally {
    preRelease.close();
  }
}

/** Leave a migrated, cleanly closed database behind. */
async function seedMigratedDatabase(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.databasePath);
  studio.close();
}

interface DataDirectoryFingerprint {
  readonly files: string[];
  readonly databaseSha256: string;
  readonly databaseMtimeMs: number;
}

/** The full directory listing plus the database's exact bytes and mtime. */
function dataDirectoryFingerprint(harness: CliHarness): DataDirectoryFingerprint {
  return {
    files: readdirSync(harness.dataDirectory).sort(),
    databaseSha256: createHash("sha256").update(readFileSync(harness.databasePath)).digest("hex"),
    databaseMtimeMs: statSync(harness.databasePath).mtimeMs,
  };
}

describe("doctor read-only contract (DR-032)", () => {
  it("leaves a pre-migration copy byte-identical: no backup, no migration, no sidecars", async () => {
    const harness = await cliHarness();
    seedPreMigrationDatabase(harness);
    const before = dataDirectoryFingerprint(harness);

    const code = await runCli(["doctor"], harness.context);

    // The un-migrated schema is readable but incomplete: the integrity family
    // is healthy, the migration reading says pending, and the probe failure
    // is carried by `error`, never by `quick_check`.
    expect(code).toBe(1);
    const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(payload.quick_check).toBe("ok");
    expect(payload.migrations).toEqual({ applied: 0, pending: true });
    expect(payload.error).toMatch(/no such table/i);
    expect(dataDirectoryFingerprint(harness)).toEqual(before);
    expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);

    // No migration row may have appeared either: the journal table is absent.
    const probe = new Database(harness.databasePath, { readonly: true });
    try {
      expect(
        probe
          .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?")
          .get("__drizzle_migrations"),
      ).toBeUndefined();
      expect(probe.prepare("SELECT id FROM pre_rewrite_marker").all()).toEqual([
        { id: "kept-content" },
      ]);
    } finally {
      probe.close();
    }
  });

  it("reports a fully migrated copy without adding backups or sidecars", async () => {
    const harness = await cliHarness();
    await seedMigratedDatabase(harness);
    const before = dataDirectoryFingerprint(harness);

    const code = await runCli(["doctor"], harness.context);

    expect(code).toBe(0);
    const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(payload.quick_check).toBe("ok");
    expect(payload.journal_mode).toBe("wal");
    expect(payload.foreign_keys).toBe(true);
    expect(payload.owner_configured).toBe(false);
    expect(payload.document_index).toEqual({ documents: 0, indexed: 0, drifted: false });
    expect(payload.migrations).toEqual({ applied: bundledMigrations, pending: false });
    expect(payload.error).toBeNull();
    expect(dataDirectoryFingerprint(harness)).toEqual(before);
    expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
  });

  it("runs read-only while a server owns the data directory", async () => {
    const harness = await cliHarness();
    await seedMigratedDatabase(harness);
    const server = await openStudioDatabase(harness.databasePath);
    const before = dataDirectoryFingerprint(harness);
    try {
      const code = await runCli(["doctor"], harness.context);

      expect(code).toBe(0);
      const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
      expect(payload.quick_check).toBe("ok");
      expect(payload.error).toBeNull();
      expect(harness.lines.join("\n")).not.toMatch(/already owned/i);
      expect(dataDirectoryFingerprint(harness)).toEqual(before);
      expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
    } finally {
      server.close();
    }
  });

  it("reports a locked database as an error, never as a quick_check corruption reading", async () => {
    const harness = await cliHarness();
    const plain = new Database(harness.databasePath);
    try {
      plain.exec("CREATE TABLE marker (id INTEGER PRIMARY KEY)");
    } finally {
      plain.close();
    }
    const writer = new Database(harness.databasePath, { timeout: 0 });
    writer.exec("BEGIN EXCLUSIVE");
    try {
      const code = await runCli(["doctor"], harness.context);

      expect(code).toBe(1);
      const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
      expect(payload.error).toMatch(/database is locked/i);
      expect(payload.quick_check).toBe("unknown");
      expect(payload.quick_check).not.toMatch(/lock/i);
    } finally {
      writer.exec("ROLLBACK");
      writer.close();
    }
  });

  it("reports a missing database file without creating one", async () => {
    const harness = await cliHarness();

    const code = await runCli(["doctor"], harness.context);

    expect(code).toBe(1);
    const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(payload.error).toMatch(/No database file exists/i);
    expect(payload.quick_check).toBe("unknown");
    expect(existsSync(harness.databasePath)).toBe(false);
    expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
  });

  it("documents doctor as read-only and migrate as the write path in the usage text", async () => {
    const harness = await cliHarness();

    expect(await runCli(["teleport"], harness.context)).toBe(2);

    const usage = harness.lines.join("\n");
    expect(usage).toContain(
      "Read-only: never migrates, backs up, reconciles, or takes the write lock.",
    );
    expect(usage).toContain("Apply pending migrations and data reconciliation");
  });
});
