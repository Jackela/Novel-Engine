import { cpSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { describe, expect, it } from "vitest";

interface Journal {
  entries: Array<{ idx: number }>;
}

async function migrationsBeforeSafeUsage(): Promise<string> {
  const destination = await mkdtemp(join(tmpdir(), "novel-engine-before-safe-usage-"));
  cpSync(join(process.cwd(), "drizzle"), destination, { recursive: true });
  const journalPath = join(destination, "meta", "_journal.json");
  const journal = JSON.parse(readFileSync(journalPath, "utf8")) as Journal;
  writeFileSync(
    journalPath,
    JSON.stringify({ entries: journal.entries.filter((entry) => entry.idx <= 17) }, null, 2),
    "utf8",
  );
  return destination;
}

function openMigrated(databasePath: string, migrationsFolder: string): Database.Database {
  const raw = new Database(databasePath);
  migrate(drizzle(raw), { migrationsFolder });
  return raw;
}

function insertUsage(raw: Database.Database, promptTokens: number, completionTokens: number): void {
  raw
    .prepare(
      `INSERT INTO usage_events
        (id, project_id, provider, model, prompt_tokens, completion_tokens,
         request_evidence_json, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .run("usage-1", "project-1", "mock", "model", promptTokens, completionTokens, "{}", 1);
}

describe("safe usage-token migration", () => {
  it("preserves the exact maximum safe integer", async () => {
    const databasePath = join(
      await mkdtemp(join(tmpdir(), "novel-engine-safe-usage-")),
      "db.sqlite3",
    );
    const legacy = openMigrated(databasePath, await migrationsBeforeSafeUsage());
    insertUsage(legacy, Number.MAX_SAFE_INTEGER, 0);
    legacy.close();

    const advanced = openMigrated(databasePath, join(process.cwd(), "drizzle"));
    try {
      expect(
        advanced.prepare("SELECT prompt_tokens, completion_tokens FROM usage_events").get(),
      ).toEqual({ prompt_tokens: Number.MAX_SAFE_INTEGER, completion_tokens: 0 });
    } finally {
      advanced.close();
    }
  });

  it.each([
    ["negative INTEGER", -1],
    ["unsafe INTEGER", Number.MAX_SAFE_INTEGER + 1],
    ["fractional REAL", 1.5],
    ["oversized REAL", 1e308],
  ])("rejects an invalid historical %s", async (_label, promptTokens) => {
    const databasePath = join(
      await mkdtemp(join(tmpdir(), "novel-engine-bad-usage-")),
      "db.sqlite3",
    );
    const legacy = openMigrated(databasePath, await migrationsBeforeSafeUsage());
    insertUsage(legacy, promptTokens, 0);
    legacy.close();

    const advanced = new Database(databasePath);
    try {
      expect(() =>
        migrate(drizzle(advanced), { migrationsFolder: join(process.cwd(), "drizzle") }),
      ).toThrow();
    } finally {
      advanced.close();
    }
  });
});
