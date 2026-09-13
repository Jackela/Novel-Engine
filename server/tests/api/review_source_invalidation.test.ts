import { describe, expect, it } from "vitest";

import { jobEvents, jobs } from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  deferredReviewFactory,
  expectNoReviewEvidence,
  firstDocument,
  studioDatabase,
} from "./job_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("review source invalidation closure", () => {
  it("records a failed job when a captured source is deleted before landing", async () => {
    const deferred = deferredReviewFactory();
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: deferred.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Concurrent review deletion");
      const document = firstDocument(project);
      const pendingReview = call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      await deferred.started;

      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
      deferred.succeed();

      const reviewed = await pendingReview;
      expect(reviewed.statusCode, reviewed.body).toBe(201);
      expect(reviewed.json<JobPayload>()).toMatchObject({
        status: "failed",
        provider: "mock",
        model: "deferred-review-model",
        result: { review_id: null, snapshot_id: null, summary: "", issues: [] },
        error: "Review source changed before the evaluated result could be recorded.",
      });
      expectNoReviewEvidence(app);
    } finally {
      deferred.succeed();
      await app.close();
    }
  });

  it("retains the evaluated model when a retry source is deleted before landing", async () => {
    const deferred = deferredReviewFactory(1);
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: deferred.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Concurrent review retry deletion");
      const document = firstDocument(project);
      const first = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      const firstJob = first.json<JobPayload>();
      expect(firstJob).toMatchObject({ status: "failed", model: "" });

      const pendingRetry = retryJobRequest(
        app,
        owner,
        `/api/projects/${project.id}/jobs/${firstJob.id}/retry`,
        "deleted-review-source-retry-0001",
      );
      await deferred.started;
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
      deferred.succeed();

      const retried = await pendingRetry;
      expect(retried.statusCode, retried.body).toBe(200);
      const retriedJob = retried.json<JobPayload>();
      expect(retriedJob).toMatchObject({
        status: "failed",
        model: "deferred-review-model",
        retry_of_job_id: firstJob.id,
        error: "Review source changed before the evaluated result could be recorded.",
      });
      // The failed outcome pins exactly this wire field set: a key may neither
      // appear nor vanish when the shared assembler changes shape.
      expect(Object.keys(retriedJob).sort()).toEqual([
        "created_at",
        "document_id",
        "error",
        "events",
        "id",
        "kind",
        "model",
        "operation",
        "project_id",
        "provider",
        "request",
        "result",
        "retry_of_job_id",
        "status",
        "updated_at",
      ]);
      expect(retriedJob.events.map((event) => event.status)).toEqual(["running", "failed"]);
      expectNoReviewEvidence(app);

      // The persisted outcome row carries the same field set, model included,
      // and its failed event mirrors the error message byte for byte.
      const database = studioDatabase(app);
      const retryRow = database
        .select()
        .from(jobs)
        .all()
        .find((row) => row.retry_of_job_id === firstJob.id);
      expect(retryRow).toMatchObject({
        status: "failed",
        model: "deferred-review-model",
        error: "Review source changed before the evaluated result could be recorded.",
        result_json: "{}",
      });
      const failedEvent = database
        .select()
        .from(jobEvents)
        .all()
        .find((event) => event.job_id === retryRow?.id && event.status === "failed");
      expect(failedEvent?.details_json).toBe(
        JSON.stringify({
          error: "Review source changed before the evaluated result could be recorded.",
        }),
      );
    } finally {
      deferred.succeed();
      await app.close();
    }
  });
});
