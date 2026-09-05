import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { jobs, sessions } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

async function makeDataDirectory(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-lifecycle-"));
}

describe("database lifecycle at the app seam", () => {
  it("stays database-free by default (walking skeleton)", async () => {
    const app = await buildApp({ logger: false });
    try {
      expect(app.studioDb).toBeUndefined();
      const response = await app.inject({ method: "GET", url: "/health/live" });
      expect(response.statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });

  it("opens the database before serving and releases it on close", async () => {
    const directory = await makeDataDirectory();

    const databasePath = join(directory, "novel-engine.sqlite3");
    const app = await buildApp({ logger: false, databasePath });
    try {
      expect(app.studioDb).toBeDefined();
      const response = await app.inject({ method: "GET", url: "/health/live" });
      expect(response.statusCode).toBe(200);
    } finally {
      await app.close();
    }

    const reopened = await openStudioDatabase(databasePath);
    reopened.close();
  });

  it("runs the startup pipeline on every build over one data directory", async () => {
    const directory = await makeDataDirectory();
    const started = new Date("2026-08-18T10:00:00.000Z");

    const databasePath = join(directory, "novel-engine.sqlite3");
    const first = await buildApp({ logger: false, databasePath });
    try {
      const db = first.studioDb;
      expect(db).toBeDefined();
      await db?.db.insert(sessions).values({
        id: "session-1",
        kind: "owner",
        owner_id: null,
        token_hash: "b".repeat(64),
        csrf_token: null,
        created_at: started,
        expires_at: new Date("2026-08-19T10:00:00.000Z"),
        last_seen_at: started,
      });
      await db?.db.insert(jobs).values({
        id: "job-running",
        kind: "ai_proposal",
        operation: "draft_continuation",
        status: "running",
        error: null,
        created_at: started,
        updated_at: started,
        started_at: started,
        finished_at: null,
      });
    } finally {
      await first.close();
    }

    const second = await buildApp({ logger: false, databasePath });
    try {
      const db = second.studioDb;
      const restoredSessions = await db?.db
        .select()
        .from(sessions)
        .where(eq(sessions.id, "session-1"));
      expect(restoredSessions).toHaveLength(1);

      const recoveredJobs = await db?.db.select().from(jobs).where(eq(jobs.id, "job-running"));
      expect(recoveredJobs?.[0]?.status).toBe("interrupted");
    } finally {
      await second.close();
    }
  });
});
