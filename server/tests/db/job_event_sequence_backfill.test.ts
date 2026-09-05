import { cpSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { describe, expect, it } from "vitest";

import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const DATABASE_FILENAME = "novel-engine.sqlite3";

interface Journal {
  entries: Array<{ idx: number; when: number; tag: string }>;
}

async function migrationsFolderUpto(lastIndex: number): Promise<string> {
  const source = join(process.cwd(), "drizzle");
  const destination = await mkdtemp(join(tmpdir(), `novel-engine-drizzle-upto${lastIndex}-`));
  cpSync(source, destination, { recursive: true });
  const journalPath = join(destination, "meta", "_journal.json");
  const journal = JSON.parse(readFileSync(journalPath, "utf8")) as Journal;
  writeFileSync(
    journalPath,
    JSON.stringify({ entries: journal.entries.filter((entry) => entry.idx <= lastIndex) }, null, 2),
    "utf8",
  );
  return destination;
}

function migrateTo(directory: string, migrationsFolder: string): Database.Database {
  const raw = new Database(join(directory, DATABASE_FILENAME));
  raw.pragma("foreign_keys = ON");
  migrate(drizzle(raw), { migrationsFolder });
  return raw;
}

describe("job event sequence migration", () => {
  it("backfills causal order and continues it during restart recovery", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-job-event-sequence-"));
    const beforeSequence = await migrationsFolderUpto(14);
    const legacy = migrateTo(directory, beforeSequence);
    try {
      const now = 1_791_000_000_000;
      legacy.exec(`
        BEGIN;
        INSERT INTO jobs
          (id, project_id, kind, operation, status, provider, model,
           request_json, result_json, created_at, updated_at)
        VALUES
          ('completed-job', 'project-a', 'proposal', 'continue', 'completed',
           'mock', 'deterministic-story-v1', '{}', '{}', ${now}, ${now}),
          ('running-job', 'project-a', 'export', 'markdown', 'running',
           'mock', '', '{}', '{}', ${now}, ${now});
        INSERT INTO job_events (id, job_id, status, details_json, created_at)
        VALUES
          ('z-running', 'completed-job', 'running', '{}', ${now + 1}),
          ('a-completed', 'completed-job', 'completed', '{}', ${now}),
          ('running-only', 'running-job', 'running', '{}', ${now});
        COMMIT;
      `);
    } finally {
      legacy.close();
    }

    const advanced = migrateTo(directory, join(process.cwd(), "drizzle"));
    try {
      expect(
        advanced
          .prepare("SELECT id, sequence FROM job_events WHERE job_id = ? ORDER BY sequence ASC")
          .all("completed-job"),
      ).toEqual([
        { id: "z-running", sequence: 1 },
        { id: "a-completed", sequence: 2 },
      ]);
    } finally {
      advanced.close();
    }

    const restarted = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      expect(
        restarted.raw
          .prepare("SELECT status, sequence FROM job_events WHERE job_id = ? ORDER BY sequence ASC")
          .all("running-job"),
      ).toEqual([
        { status: "running", sequence: 1 },
        { status: "interrupted", sequence: 2 },
      ]);
    } finally {
      restarted.close();
    }
  });
});
