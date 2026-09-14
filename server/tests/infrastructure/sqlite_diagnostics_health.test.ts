import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { describe, expect, it } from "vitest";

import { sqliteDiagnosticsHealth } from "../../src/contexts/studio/infrastructure/sqlite_diagnostics_health.js";
import * as schema from "../../src/shared/infrastructure/db/schema.js";

/** A migrated file database with the app's connection pragmas applied. */
function migratedScratchDatabase(databasePath: string) {
  const raw = new Database(databasePath);
  raw.pragma("journal_mode = WAL");
  raw.pragma("foreign_keys = ON");
  migrate(drizzle(raw, { schema }), { migrationsFolder: join(process.cwd(), "drizzle") });
  return { raw, db: drizzle(raw, { schema }) };
}

describe("SQLite diagnostics health probe (#654)", () => {
  it("reports the doctor field family for a healthy database", () => {
    const directory = mkdtempSync(join(tmpdir(), "novel-engine-diagnostics-health-"));
    try {
      const { raw, db } = migratedScratchDatabase(join(directory, "healthy.sqlite3"));
      try {
        expect(sqliteDiagnosticsHealth(raw, db)()).toEqual({
          quickCheck: "ok",
          journalMode: "wal",
          foreignKeys: true,
          // A scratch database has no owner account configured.
          ownerConfigured: false,
        });
      } finally {
        raw.close();
      }
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  it("carries a corrupt database's read failure through the integrity field", () => {
    const directory = mkdtempSync(join(tmpdir(), "novel-engine-diagnostics-health-"));
    const databasePath = join(directory, "corrupt.sqlite3");
    try {
      writeFileSync(databasePath, "definitely not a sqlite database file");
      const raw = new Database(databasePath);
      try {
        const database = drizzle(raw, { schema });
        expect(sqliteDiagnosticsHealth(raw, database)()).toEqual({
          quickCheck: "file is not a database",
          journalMode: "unknown",
          foreignKeys: false,
          ownerConfigured: false,
        });
      } finally {
        raw.close();
      }
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });
});
