import { readFileSync } from "node:fs";
import { mkdir, mkdtemp, readdir } from "node:fs/promises";
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
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-migrate-cli-"));
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

async function seedMigratedDatabase(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.databasePath);
  studio.close();
}

async function backupNames(dataDirectory: string): Promise<string[]> {
  return readdir(join(dataDirectory, "backups")).catch(() => []);
}

describe("migrate CLI (DR-032)", () => {
  it("applies pending migrations, backs up once, and reports the migration state", async () => {
    const harness = await cliHarness();
    seedPreMigrationDatabase(harness);

    const code = await runCli(["migrate"], harness.context);

    expect(code).toBe(0);
    expect(JSON.parse(harness.lines[0] ?? "")).toEqual({
      database: harness.databasePath,
      migrations: { applied: bundledMigrations, pending: false },
    });
    // The DR-031 conditional pre-migration backup fired exactly once.
    expect(await backupNames(harness.dataDirectory)).toHaveLength(1);

    // The migration really ran and preserved the pre-existing rows.
    const migrated = new Database(harness.databasePath, { readonly: true });
    try {
      expect(migrated.prepare("SELECT id FROM pre_rewrite_marker").all()).toEqual([
        { id: "kept-content" },
      ]);
      expect(migrated.prepare('SELECT COUNT(*) AS n FROM "__drizzle_migrations"').get()).toEqual({
        n: bundledMigrations,
      });
    } finally {
      migrated.close();
    }
  });

  it("reports a fully migrated database as pending false without a new backup", async () => {
    const harness = await cliHarness();
    await seedMigratedDatabase(harness);

    const code = await runCli(["migrate"], harness.context);

    expect(code).toBe(0);
    expect(JSON.parse(harness.lines[0] ?? "")).toEqual({
      database: harness.databasePath,
      migrations: { applied: bundledMigrations, pending: false },
    });
    expect(await backupNames(harness.dataDirectory)).toEqual([]);
  });

  it("refuses migrate while a server owns the data directory", async () => {
    const harness = await cliHarness();
    await seedMigratedDatabase(harness);
    const server = await openStudioDatabase(harness.databasePath);
    try {
      const code = await runCli(["migrate"], harness.context);

      expect(code).toBe(1);
      expect(harness.lines.join("\n")).toMatch(/already owned by another Novel Engine process/i);
      expect(harness.lines[0]?.trimStart().startsWith("{")).toBe(false);
    } finally {
      server.close();
    }
  });
});
