import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import {
  type AddJobInput,
  type JobPageLimit,
  jobPageLimit,
} from "../../src/contexts/studio/application/ports/job_records.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import {
  buildJobEventsQuery,
  buildProjectJobsPageQuery,
} from "../../src/contexts/studio/infrastructure/job_page_queries.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { jobs as jobsTable } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

function completedJob(projectId: string, id: string, createdAtMs: number): AddJobInput {
  return {
    projectId,
    documentId: null,
    kind: "proposal",
    operation: id,
    status: "completed",
    provider: "mock",
    model: "deterministic-story-v1",
    requestJson: "{}",
    resultJson: "{}",
    error: null,
    eventDetailsJson: `{"job":"${id}"}`,
    now: new Date(createdAtMs),
  };
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-job-page-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3")).catch(
    async (error: unknown) => {
      await rm(directory, { recursive: true, force: true });
      throw error;
    },
  );
  const cleanup = async (): Promise<void> => {
    try {
      studio.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  };
  try {
    const store = new DrizzleStudioStore({ database: studio.db });
    const now = new Date("2026-09-02T00:00:00.000Z");
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "job-page-test-secret",
      now: () => now,
    });
    await auth.configureOwner("page-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("page-owner", "long-test-password")).principal;
    const scope = scopeForPrincipal(principal);
    const { project } = store.addProject(scope, {
      title: "Job page",
      description: "",
      settingsJson: "{}",
      seed: null,
      now,
    });
    return { cleanup, jobs: new JobStorePart(studio.db), projectId: project.id, scope, studio };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

describe("project job keyset pages", () => {
  it("returns only the requested newest jobs and a cursor from the last returned row", async () => {
    const { cleanup, jobs, projectId, scope } = await openHarness();
    try {
      const oldest = jobs.addJob(scope, completedJob(projectId, "oldest", 1_000));
      const middle = jobs.addJob(scope, completedJob(projectId, "middle", 2_000));
      const newest = jobs.addJob(scope, completedJob(projectId, "newest", 3_000));

      const page = jobs.collectProjectJobs(scope, projectId, { limit: jobPageLimit(2) });

      expect(page.jobs.map((job) => job.id)).toEqual([newest.id, middle.id]);
      expect(page.nextCursor).toEqual({ createdAtMs: 2_000, id: middle.id });
      expect(page.jobs.map((job) => job.id)).not.toContain(oldest.id);
    } finally {
      await cleanup();
    }
  });

  it("rejects invalid direct-store limits before reading a page", async () => {
    const { cleanup, jobs, projectId, scope } = await openHarness();
    try {
      for (const invalid of [0, 101, 1.5, Number.NaN]) {
        expect(() =>
          jobs.collectProjectJobs(scope, projectId, { limit: invalid as JobPageLimit }),
        ).toThrow(RangeError);
      }
    } finally {
      await cleanup();
    }
  });

  it("traverses equal timestamps after a deleted boundary without injecting a newer job", async () => {
    const { cleanup, jobs, projectId, scope, studio } = await openHarness();
    try {
      const tied = 5_000;
      const tiedJobs = ["one", "two", "three", "four"].map((label) =>
        jobs.addJob(scope, completedJob(projectId, label, tied)),
      );
      const expected = [...tiedJobs].sort((left, right) => (left.id < right.id ? 1 : -1));
      const first = jobs.collectProjectJobs(scope, projectId, { limit: jobPageLimit(2) });
      expect(first.jobs.map((job) => job.id)).toEqual(expected.slice(0, 2).map((job) => job.id));
      expect(first.nextCursor).not.toBeNull();
      const boundary = expected[1];
      if (boundary === undefined || first.nextCursor === null) {
        throw new Error("Expected a two-job first page with a continuation cursor.");
      }

      const newer = jobs.addJob(scope, completedJob(projectId, "newer", tied + 1));
      studio.db.delete(jobsTable).where(eq(jobsTable.id, boundary.id)).run();
      const second = jobs.collectProjectJobs(scope, projectId, {
        limit: jobPageLimit(2),
        cursor: first.nextCursor,
      });

      expect(second.jobs.map((job) => job.id)).toEqual(expected.slice(2).map((job) => job.id));
      expect(second.nextCursor).toBeNull();
      expect(second.jobs.map((job) => job.id)).not.toContain(newer.id);
      expect(
        jobs.collectProjectJobs(scope, projectId, { limit: jobPageLimit(1) }).jobs[0]?.id,
      ).toBe(newer.id);
    } finally {
      await cleanup();
    }
  });

  it("keeps a 32,767-job project within the page event-binding budget", async () => {
    const { cleanup, jobs, projectId, scope, studio } = await openHarness();
    try {
      const insert = studio.raw.prepare(
        "INSERT INTO jobs (id, project_id, kind, operation, status, created_at, updated_at) " +
          "VALUES (?, ?, 'proposal', 'continue', 'completed', ?, ?)",
      );
      studio.raw.transaction(() => {
        for (let index = 0; index < 32_767; index += 1) {
          const id = `job-${String(index).padStart(5, "0")}`;
          insert.run(id, projectId, index, index);
        }
      })();

      const page = jobs.collectProjectJobs(scope, projectId, { limit: jobPageLimit(100) });

      expect(page.jobs).toHaveLength(100);
      expect(page.jobs[0]?.id).toBe("job-32766");
      expect(page.jobs[99]?.id).toBe("job-32667");
      expect(page.jobs.every((job) => job.events.length === 0)).toBe(true);
      expect(page.nextCursor).toEqual({ createdAtMs: 32_667, id: "job-32667" });
    } finally {
      await cleanup();
    }
  });

  it("uses tuple-range and event indexes without temporary ordering", async () => {
    const { cleanup, projectId, studio } = await openHarness();
    try {
      const queries = studio.db.transaction((tx) => ({
        jobs: buildProjectJobsPageQuery(tx, projectId, {
          limit: jobPageLimit(100),
          cursor: { createdAtMs: 5_000, id: "boundary" },
        }).toSQL(),
        events: buildJobEventsQuery(tx, ["job-a", "job-b"]).toSQL(),
      }));
      const jobPlan = studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${queries.jobs.sql}`)
        .all(...queries.jobs.params) as Array<{ detail: string }>;
      const eventPlan = studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${queries.events.sql}`)
        .all(...queries.events.params) as Array<{ detail: string }>;
      const jobDetails = jobPlan.map((row) => row.detail).join("\n");
      const eventDetails = eventPlan.map((row) => row.detail).join("\n");

      expect(jobDetails).toContain("idx_jobs_project_created_id");
      expect(jobDetails).toContain("(created_at,id)<(?,?)");
      expect(jobDetails).not.toContain("USE TEMP B-TREE");
      expect(eventDetails).toContain("uq_job_events_job_sequence");
      expect(eventDetails).not.toContain("USE TEMP B-TREE");
    } finally {
      await cleanup();
    }
  });
});
