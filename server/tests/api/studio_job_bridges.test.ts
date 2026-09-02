import { existsSync } from "node:fs";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { jobs as jobsTable, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import {
  firstDocument,
  flakyProviderFactory,
  seedProjectWithChapter,
  studioDatabase,
} from "./job_test_helpers.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("terminal job bridges", () => {
  it("returns a terminal export job wrapping the materialized artifact", async () => {
    const clock = monotonicClock();
    const { app, directory } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Export job bridge");

      const created = await call(app, owner, "POST", `/api/projects/${projectId}/exports`, {
        format: "markdown",
      });
      expect(created.statusCode, created.body).toBe(201);
      const job = created.json() as JobPayload;
      expect(job).toMatchObject({
        project_id: projectId,
        document_id: null,
        kind: "export",
        operation: "export",
        status: "completed",
        retry_of_job_id: null,
        request: { format: "markdown" },
      });
      expect(job.result.export_id).toEqual(expect.any(String));
      expect(job.result.snapshot_id).toEqual(expect.any(String));
      expect(job.result.format).toBe("markdown");
      expect(job.result.download_url).toContain(
        `/api/projects/${projectId}/exports/${job.result.export_id}/download`,
      );
      expect(job.events[0]?.details).toEqual({ export_id: job.result.export_id });

      expect(existsSync(join(directory, "exports", projectId, `${job.result.export_id}.md`))).toBe(
        true,
      );

      const catalog = await call(app, owner, "GET", `/api/projects/${projectId}/exports`);
      expect(catalog.statusCode, catalog.body).toBe(200);
      expect(catalog.json().exports.map((item: { id: string }) => item.id)).toContain(
        job.result.export_id,
      );

      const anonymous = await anonymousCall(app, "POST", `/api/projects/${projectId}/exports`, {
        format: "markdown",
      });
      expect(anonymous.statusCode, anonymous.body).toBe(401);
    } finally {
      await app.close();
    }
  });

  it("rejects export requests for a chapter-less project without a job", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Empty export");
      const document = firstDocument(project);
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);

      const created = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "docx",
      });
      expect(created.statusCode, created.body).toBe(422);
      expect(created.json().error.code).toBe("INVALID_OPERATION");

      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      expect((listed.json().jobs as JobPayload[]).map((job) => job.kind)).not.toContain("export");
    } finally {
      await app.close();
    }
  });

  it("returns a terminal review job while the review listing keeps assessments", async () => {
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Review job bridge");
      const document = firstDocument(project);
      const projectId = project.id;

      const created = await call(app, owner, "POST", `/api/projects/${projectId}/reviews`);
      expect(created.statusCode, created.body).toBe(201);
      const job = created.json() as JobPayload;
      expect(job).toMatchObject({
        project_id: projectId,
        kind: "review",
        operation: "review",
        status: "completed",
        provider: "mock",
        model: "deterministic-story-v1",
        retry_of_job_id: null,
      });
      expect(job.result.review_id).toEqual(expect.any(String));
      expect(job.result.snapshot_id).toEqual(expect.any(String));
      expect(typeof job.result.summary).toBe("string");
      expect(job.events[0]?.details).toEqual({ review_id: job.result.review_id });

      const listed = await call(app, owner, "GET", `/api/projects/${projectId}/reviews`);
      expect(listed.statusCode, listed.body).toBe(200);
      expect(listed.json().reviews).toHaveLength(1);
      expect(listed.json().reviews[0].id).toBe(job.result.review_id);

      const protectedSource = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${projectId}/documents/${document.id}`,
      );
      expect(protectedSource.statusCode, protectedSource.body).toBe(409);
      expect(protectedSource.json().error.code).toBe("SNAPSHOT_CONFLICT");
    } finally {
      await app.close();
    }
  });
});

describe("job retry chains", () => {
  it("chains a completed retry onto a failed proposal and records usage", async () => {
    const clock = monotonicClock();
    const failures = { count: 1 };
    const { app } = await buildStudioApp(clock, {
      textProviderFactory: flakyProviderFactory(failures),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Retry chain");
      const document = firstDocument(project);

      const failed = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", instruction: "will fail once" },
      );
      expect(failed.statusCode, failed.body).toBe(200);
      const failedJob = failed.json() as JobPayload;
      expect(failedJob.status).toBe("failed");

      const retry = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${failedJob.id}/retry`,
      );
      expect(retry.statusCode, retry.body).toBe(200);
      const retryJob = retry.json() as JobPayload;
      expect(retryJob.status).toBe("completed");
      expect(retryJob.kind).toBe("proposal");
      expect(retryJob.retry_of_job_id).toBe(failedJob.id);
      expect(retryJob.model).toBe("recovered-model");
      expect(retryJob.result.proposal_markdown).toEqual(expect.any(String));
      expect(retryJob.events.map((event) => event.status)).toEqual(["running", "completed"]);
      expect(retryJob.events[0]?.details).toEqual({ retry_of: failedJob.id });

      const database = studioDatabase(app);
      const usage = database
        .select()
        .from(usageEvents)
        .where(eq(usageEvents.job_id, retryJob.id))
        .all();
      expect(usage).toHaveLength(1);
      expect(usage[0]?.model).toBe("recovered-model");
      expect(usage[0]?.prompt_tokens).toBe(3);
      expect(usage[0]?.completion_tokens).toBe(5);

      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      const original = (listed.json().jobs as Array<Pick<JobPayload, "id" | "status">>).find(
        (job) => job.id === failedJob.id,
      );
      expect(original?.status).toBe("failed");
      const originalDetail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs/${failedJob.id}`,
      );
      expect(originalDetail.json<JobPayload>().events.map((event) => event.status)).toEqual([
        "failed",
      ]);
    } finally {
      await app.close();
    }
  });

  it("fails an interrupted export retry when the project lost its chapters", async () => {
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Interrupted export retry");
      const document = firstDocument(project);
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);

      // Seed the interrupted export job the way restart recovery would leave it.
      const database = studioDatabase(app);
      const interruptedAt = clock();
      database
        .insert(jobsTable)
        .values({
          id: "export-job-interrupted",
          project_id: project.id,
          document_id: null,
          kind: "export",
          operation: "export",
          status: "interrupted",
          provider: "studio",
          model: "",
          request_json: JSON.stringify({ format: "markdown" }),
          result_json: JSON.stringify({}),
          error: "Job lost its execution lease during process restart.",
          created_at: interruptedAt,
          updated_at: interruptedAt,
        })
        .run();

      const retry = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/export-job-interrupted/retry`,
      );
      expect(retry.statusCode, retry.body).toBe(200);
      const retryJob = retry.json() as JobPayload;
      expect(retryJob.status).toBe("failed");
      expect(retryJob.kind).toBe("export");
      expect(retryJob.retry_of_job_id).toBe("export-job-interrupted");
      expect(retryJob.error).toContain("at least one chapter");
      expect(retryJob.events.map((event) => event.status)).toEqual(["running", "failed"]);

      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      const jobs = listed.json().jobs as Array<Pick<JobPayload, "id" | "status">>;
      expect(jobs.find((job) => job.id === "export-job-interrupted")?.status).toBe("interrupted");
      expect(jobs[0]?.id).toBe(retryJob.id);
    } finally {
      await app.close();
    }
  });

  it("retries a failed review job into a fresh assessment", async () => {
    const clock = monotonicClock();
    const failures = { count: 1 };
    const { app } = await buildStudioApp(clock, {
      textProviderFactory: flakyProviderFactory(failures),
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Review retry");

      const created = await call(app, owner, "POST", `/api/projects/${projectId}/reviews`);
      const reviewJob = created.json() as JobPayload;
      expect(reviewJob.status).toBe("failed");
      expect(reviewJob.model).toBe("");

      const retry = await call(
        app,
        owner,
        "POST",
        `/api/projects/${projectId}/jobs/${reviewJob.id}/retry`,
      );
      expect(retry.statusCode, retry.body).toBe(200);
      const retryJob = retry.json() as JobPayload;
      expect(retryJob.status).toBe("completed");
      expect(retryJob.kind).toBe("review");
      expect(retryJob.retry_of_job_id).toBe(reviewJob.id);
      expect(retryJob.model).toBe("recovered-model");
      expect(retryJob.result.review_id).toEqual(expect.any(String));
      expect(retryJob.result.review_id).not.toBe(reviewJob.result.review_id);
    } finally {
      await app.close();
    }
  });
});
