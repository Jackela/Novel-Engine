import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { jobEvents, jobs, sessions } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const DATABASE_FILENAME = "novel-engine.sqlite3";

async function makeDataDirectory(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-restart-"));
}

function columnNames(studio: Awaited<ReturnType<typeof openStudioDatabase>>, table: string) {
  return (studio.raw.pragma(`table_info(${table})`) as Array<{ name: string }>).map(
    (column) => column.name,
  );
}

describe("restart persistence", () => {
  it("persists sessions across restart with the adjudicated columns", async () => {
    const directory = await makeDataDirectory();
    const created = new Date("2026-08-18T10:00:00.000Z");
    const expires = new Date("2026-09-17T10:00:00.000Z");
    const lastSeen = new Date("2026-08-18T11:30:00.000Z");

    const first = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      expect(columnNames(first, "sessions")).toEqual([
        "id",
        "kind",
        "owner_id",
        "token_hash",
        "csrf_token",
        "created_at",
        "expires_at",
        "last_seen_at",
      ]);
      await first.db.insert(sessions).values({
        id: "session-1",
        kind: "owner",
        owner_id: null,
        token_hash: "a".repeat(64),
        csrf_token: "c".repeat(64),
        created_at: created,
        expires_at: expires,
        last_seen_at: lastSeen,
      });
    } finally {
      first.close();
    }

    const second = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      const restored = await second.db.select().from(sessions).where(eq(sessions.id, "session-1"));
      expect(restored).toHaveLength(1);
      expect(restored[0]).toEqual({
        id: "session-1",
        kind: "owner",
        owner_id: null,
        token_hash: "a".repeat(64),
        csrf_token: "c".repeat(64),
        created_at: created,
        expires_at: expires,
        last_seen_at: lastSeen,
      });

      const duplicateHash = second.db.insert(sessions).values({
        id: "session-2",
        kind: "owner",
        owner_id: null,
        token_hash: "a".repeat(64),
        csrf_token: null,
        created_at: created,
        expires_at: null,
        last_seen_at: lastSeen,
      });
      await expect(duplicateHash).rejects.toThrow(/UNIQUE/i);
    } finally {
      second.close();
    }
  });

  it("marks a seeded running job interrupted at restart with its event", async () => {
    const directory = await makeDataDirectory();
    const beforeRestart = new Date("2026-08-18T10:00:00.000Z");

    const first = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      await first.db.insert(jobs).values([
        {
          id: "job-running",
          kind: "ai_proposal",
          operation: "draft_continuation",
          status: "running",
          error: null,
          created_at: beforeRestart,
          updated_at: beforeRestart,
          started_at: beforeRestart,
          finished_at: null,
        },
        {
          id: "job-done",
          kind: "export",
          operation: "export_markdown",
          status: "succeeded",
          error: null,
          created_at: beforeRestart,
          updated_at: beforeRestart,
          started_at: beforeRestart,
          finished_at: beforeRestart,
        },
      ]);
    } finally {
      first.close();
    }

    let statusBeforeJobRecovery: string | undefined;
    const second = await openStudioDatabase(join(directory, DATABASE_FILENAME), {
      beforeJobRecovery: (database) => {
        statusBeforeJobRecovery = database
          .select({ status: jobs.status })
          .from(jobs)
          .where(eq(jobs.id, "job-running"))
          .get()?.status;
      },
    });
    try {
      expect(statusBeforeJobRecovery).toBe("running");
      const interrupted = await second.db.select().from(jobs).where(eq(jobs.id, "job-running"));
      expect(interrupted).toHaveLength(1);
      expect(interrupted[0]?.status).toBe("interrupted");
      expect(interrupted[0]?.error).toBe("Job lost its execution lease during process restart.");
      expect(interrupted[0]?.finished_at).toBeInstanceOf(Date);

      const events = await second.db
        .select()
        .from(jobEvents)
        .where(eq(jobEvents.job_id, "job-running"));
      expect(events).toHaveLength(1);
      expect(events[0]?.status).toBe("interrupted");
      expect(events[0]?.details_json).toBe('{"reason":"execution_lease_lost_during_restart"}');

      const untouched = await second.db.select().from(jobs).where(eq(jobs.id, "job-done"));
      expect(untouched[0]?.status).toBe("succeeded");
      expect(untouched[0]?.error).toBeNull();
      expect(untouched[0]?.finished_at).toEqual(beforeRestart);
      const untouchedEvents = await second.db
        .select()
        .from(jobEvents)
        .where(eq(jobEvents.job_id, "job-done"));
      expect(untouchedEvents).toHaveLength(0);
    } finally {
      second.close();
    }
  });

  it("keeps the jobs schema free of invented lease machinery", async () => {
    const directory = await makeDataDirectory();

    const studio = await openStudioDatabase(join(directory, DATABASE_FILENAME));
    try {
      // The proposal workflow (#268) grew the persistence columns (project
      // scoping, provider/model, request/result, retry chain/identity) — everything
      // the adjudicated synchronous jobs model carries, and nothing more.
      expect(columnNames(studio, "jobs")).toEqual([
        "id",
        "kind",
        "operation",
        "status",
        "error",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "project_id",
        "document_id",
        "provider",
        "model",
        "request_json",
        "result_json",
        "retry_of_job_id",
        "retry_idempotency_key",
      ]);
      for (const name of columnNames(studio, "jobs")) {
        expect(name).not.toMatch(/lease|ttl|heartbeat|worker/i);
      }
    } finally {
      studio.close();
    }
  });
});
