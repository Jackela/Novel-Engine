import { mkdtemp, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const DATABASE_FILENAME = "novel-engine.sqlite3";

async function makeDataDirectory(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-schema-guard-"));
}

/**
 * The misconfiguration hazard from the #264 review: a live Python data
 * directory whose alembic-managed schema is incompatible with the drizzle
 * migrations (same filename, different physical schema).
 */
function createPythonSchemaDatabase(databasePath: string): void {
  const python = new Database(databasePath);
  try {
    python.exec(`
      CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
      CREATE TABLE sessions (
        session_id VARCHAR(64) PRIMARY KEY,
        created_at DATETIME,
        expires_at DATETIME,
        csrf_token VARCHAR(64)
      );
    `);
  } finally {
    python.close();
  }
}

describe("non-drizzle schema guard", () => {
  it("refuses a Python-schema database with an operator-facing error and no backup", async () => {
    const directory = await makeDataDirectory();
    const databasePath = join(directory, DATABASE_FILENAME);
    createPythonSchemaDatabase(databasePath);

    await expect(openStudioDatabase(databasePath)).rejects.toThrow(/non-drizzle schema/);
    await expect(readdir(join(directory, "backups"))).rejects.toThrow();
  });

  it("keeps refusing on repeated attempts without accumulating backups", async () => {
    const directory = await makeDataDirectory();
    createPythonSchemaDatabase(join(directory, DATABASE_FILENAME));

    await expect(openStudioDatabase(join(directory, DATABASE_FILENAME))).rejects.toThrow(
      /non-drizzle schema/,
    );
    await expect(openStudioDatabase(join(directory, DATABASE_FILENAME))).rejects.toThrow(
      /non-drizzle schema/,
    );
    await expect(readdir(join(directory, "backups"))).rejects.toThrow();
  });

  it("preserves backup-first for databases without the Python marker", async () => {
    const directory = await makeDataDirectory();
    const databasePath = join(directory, DATABASE_FILENAME);
    const foreign = new Database(databasePath);
    try {
      foreign.exec("CREATE TABLE pre_rewrite_marker (id TEXT PRIMARY KEY)");
    } finally {
      foreign.close();
    }

    // Journal-less foreign tables are not the Python schema: the pipeline
    // still writes its pre-migration backup before migrations run.
    await expect(openStudioDatabase(databasePath)).resolves.toBeTruthy();
    const backups = await readdir(join(directory, "backups"));
    expect(backups.length).toBe(1);
  });
});
