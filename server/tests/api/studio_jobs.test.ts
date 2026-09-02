import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import {
  jobEvents as jobEventsTable,
  jobs as jobsTable,
} from "../../src/shared/infrastructure/db/schema.js";
import { firstDocument, studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  draftProposal,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("jobs surface", () => {
  it("lists jobs newest first with each event stream newest first", async () => {
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Jobs ordering");
      const document = firstDocument(project);

      const older = await draftProposal(app, owner, project.id, document.id, {
        operation: "continue",
        instruction: "first attempt",
      });
      expect(older.status).toBe("completed");
      const newer = await draftProposal(app, owner, project.id, document.id, {
        operation: "rewrite",
        instruction: "second attempt",
      });
      expect(newer.status).toBe("completed");

      const database = studioDatabase(app);
      database
        .update(jobsTable)
        .set({ status: "interrupted" })
        .where(eq(jobsTable.id, older.id))
        .run();
      const retried = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${older.id}/retry`,
      );
      expect(retried.statusCode, retried.body).toBe(200);
      expect(retried.json().status).toBe("completed");

      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      expect(listed.statusCode, listed.body).toBe(200);
      const jobs = listed.json().jobs as JobPayload[];
      expect(jobs.map((job) => job.id)).toEqual([retried.json().id, newer.id, older.id]);
      const retryJob = jobs[0];
      expect(retryJob?.retry_of_job_id).toBe(older.id);
      expect(retryJob?.events.map((event) => event.status)).toEqual(["completed", "running"]);
      expect(retryJob?.events[1]?.details).toEqual({ retry_of: older.id });
      expect(jobs[2]?.events).toHaveLength(1);
    } finally {
      await app.close();
    }
  });

  it("uses a job id tie-breaker and causal event sequence for equal timestamps", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Tied job ordering");
      const database = studioDatabase(app);
      const tiedAt = new Date("2026-01-01T00:00:00.000Z");
      const lowerJobId = "00000000-0000-4000-8000-000000000001";
      const higherJobId = "00000000-0000-4000-8000-000000000002";
      database
        .insert(jobsTable)
        .values([
          {
            id: lowerJobId,
            project_id: project.id,
            document_id: null,
            kind: "proposal",
            operation: "continue",
            status: "completed",
            provider: "mock",
            model: "deterministic-story-v1",
            request_json: "{}",
            result_json: "{}",
            error: null,
            retry_of_job_id: null,
            created_at: tiedAt,
            updated_at: tiedAt,
          },
          {
            id: higherJobId,
            project_id: project.id,
            document_id: null,
            kind: "proposal",
            operation: "rewrite",
            status: "completed",
            provider: "mock",
            model: "deterministic-story-v1",
            request_json: "{}",
            result_json: "{}",
            error: null,
            retry_of_job_id: null,
            created_at: tiedAt,
            updated_at: tiedAt,
          },
        ])
        .run();
      database
        .insert(jobEventsTable)
        .values([
          {
            id: "00000000-0000-4000-8000-000000000012",
            job_id: higherJobId,
            status: "running",
            details_json: "{}",
            sequence: 1,
            created_at: tiedAt,
          },
          {
            id: "00000000-0000-4000-8000-000000000011",
            job_id: higherJobId,
            status: "completed",
            details_json: "{}",
            sequence: 2,
            created_at: tiedAt,
          },
        ])
        .run();

      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      expect(listed.statusCode, listed.body).toBe(200);
      const listedJobs = listed.json().jobs as JobPayload[];
      expect(listedJobs.map((job) => job.id)).toEqual([higherJobId, lowerJobId]);
      expect(listedJobs[0]?.events.map((event) => event.id)).toEqual([
        "00000000-0000-4000-8000-000000000011",
        "00000000-0000-4000-8000-000000000012",
      ]);
    } finally {
      await app.close();
    }
  });

  it("rejects retry of completed jobs and of import-kind jobs", async () => {
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Retry gating");
      const document = firstDocument(project);

      const completed = await draftProposal(app, owner, project.id, document.id, {
        operation: "continue",
        instruction: "healthy",
      });
      const rejected = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${completed.id}/retry`,
      );
      expect(rejected.statusCode, rejected.body).toBe(422);
      expect(rejected.json().error.code).toBe("INVALID_OPERATION");
      expect(rejected.json().error.message).toBe("Only failed or interrupted jobs may be retried.");

      const database = studioDatabase(app);
      const imported = await draftProposal(app, owner, project.id, document.id, {
        operation: "continue",
        instruction: "kind holder",
      });
      database
        .update(jobsTable)
        .set({ kind: "import", status: "failed" })
        .where(eq(jobsTable.id, imported.id))
        .run();
      const importRejected = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${imported.id}/retry`,
      );
      expect(importRejected.statusCode, importRejected.body).toBe(422);
      expect(importRejected.json().error.code).toBe("INVALID_OPERATION");
      expect(importRejected.json().error.message).toContain("Import");

      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      expect((listed.json().jobs as JobPayload[]).map((job) => job.retry_of_job_id)).toEqual([
        null,
        null,
      ]);
    } finally {
      await app.close();
    }
  });

  it("keeps the jobs surface session-scoped", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Scoped jobs");
      const document = firstDocument(project);
      await draftProposal(app, owner, project.id, document.id, {
        operation: "continue",
        instruction: "scoped",
      });

      const anonymous = await app.inject({
        method: "GET",
        url: `/api/projects/${project.id}/jobs`,
      });
      expect(anonymous.statusCode).toBe(401);

      const unknown = await call(
        app,
        owner,
        "GET",
        "/api/projects/00000000-0000-0000-0000-000000000000/jobs",
      );
      expect(unknown.statusCode, unknown.body).toBe(404);
    } finally {
      await app.close();
    }
  });
});
