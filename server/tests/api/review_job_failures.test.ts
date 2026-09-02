import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import {
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  deferredReviewFactory,
  firstDocument,
  flakyProviderFactory,
  studioDatabase,
} from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

function staticReviewFactory(content: Record<string, unknown>): TextGenerationProviderFactory {
  return (provider) => ({
    generateStructured: async () => ({
      step: "editorial_review",
      provider,
      model: "review-contract-model",
      rawText: JSON.stringify(content),
      content,
      promptTokens: null,
      completionTokens: null,
    }),
  });
}

function expectNoReviewEvidence(app: FastifyInstance): void {
  const database = studioDatabase(app);
  expect(database.select().from(projectSnapshots).all()).toEqual([]);
  expect(database.select().from(snapshotDocuments).all()).toEqual([]);
  expect(database.select().from(reviews).all()).toEqual([]);
  expect(database.select().from(reviewIssues).all()).toEqual([]);
}

describe("review job failure closure", () => {
  it("does not leave a deletion-blocking snapshot after a known provider failure", async () => {
    const failures = { count: 1 };
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: flakyProviderFactory(failures),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Failed review cleanup");
      const document = firstDocument(project);

      const reviewed = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(reviewed.statusCode, reviewed.body).toBe(201);
      expect(reviewed.json<JobPayload>()).toMatchObject({
        kind: "review",
        status: "failed",
        result: { review_id: null, snapshot_id: null },
      });
      expectNoReviewEvidence(app);

      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
    } finally {
      await app.close();
    }
  });

  it("fails a malformed top-level findings envelope without an empty assessment", async () => {
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: staticReviewFactory({ wrong_key: [] }),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Malformed review envelope");
      const document = firstDocument(project);

      const reviewed = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(reviewed.statusCode, reviewed.body).toBe(201);
      expect(reviewed.json<JobPayload>()).toMatchObject({
        kind: "review",
        status: "failed",
        error: "Review provider response must contain a findings array.",
      });
      expectNoReviewEvidence(app);
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
    } finally {
      await app.close();
    }
  });

  it("keeps unexpected provider bugs visible without persisting evidence or a job", async () => {
    const factory: TextGenerationProviderFactory = () => ({
      generateStructured: async () => {
        throw new Error("unexpected review provider bug");
      },
    });
    const { app } = await buildStudioApp(monotonicClock(), { textProviderFactory: factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Unexpected review failure");
      const document = firstDocument(project);

      const reviewed = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(reviewed.statusCode, reviewed.body).toBe(500);
      expect(reviewed.body).not.toContain("unexpected review provider bug");
      expectNoReviewEvidence(app);
      expect(
        (await call(app, owner, "GET", `/api/projects/${project.id}/jobs`)).json().jobs,
      ).toEqual([]);
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
    } finally {
      await app.close();
    }
  });

  it("fails a review retry without leaking evidence and records both events", async () => {
    const failures = { count: 2 };
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: flakyProviderFactory(failures),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Failed review retry");
      const document = firstDocument(project);
      const first = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      const firstJob = first.json<JobPayload>();
      expect(firstJob.status).toBe("failed");

      const retried = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${firstJob.id}/retry`,
      );
      expect(retried.statusCode, retried.body).toBe(200);
      expect(retried.json<JobPayload>()).toMatchObject({
        status: "failed",
        retry_of_job_id: firstJob.id,
      });
      expect(retried.json<JobPayload>().events.map((event) => event.status)).toEqual([
        "running",
        "failed",
      ]);
      expectNoReviewEvidence(app);
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
    } finally {
      await app.close();
    }
  });

  it("keeps a retry running when an unexpected provider bug escapes", async () => {
    let calls = 0;
    const factory: TextGenerationProviderFactory = () => ({
      generateStructured: async () => {
        calls += 1;
        if (calls === 1) throw new TextGenerationProviderError("known first failure");
        throw new Error("unexpected retry provider bug");
      },
    });
    const { app } = await buildStudioApp(monotonicClock(), { textProviderFactory: factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Unexpected review retry failure");
      const document = firstDocument(project);
      const first = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      const firstJob = first.json<JobPayload>();
      expect(firstJob.status).toBe("failed");

      const retried = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${firstJob.id}/retry`,
      );
      expect(retried.statusCode, retried.body).toBe(500);
      const listed = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      expect(listed.json().jobs).toMatchObject([
        { status: "running" },
        { id: firstJob.id, status: "failed" },
      ]);
      const runningDetail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs/${listed.json().jobs[0].id}`,
      );
      expect(runningDetail.json<JobPayload>().events).toMatchObject([{ status: "running" }]);
      expectNoReviewEvidence(app);
      const removed = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);
    } finally {
      await app.close();
    }
  });

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
        result: { review_id: null, snapshot_id: null },
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

      const pendingRetry = call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${firstJob.id}/retry`,
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
      expect(retried.json<JobPayload>()).toMatchObject({
        status: "failed",
        model: "deferred-review-model",
        retry_of_job_id: firstJob.id,
        error: "Review source changed before the evaluated result could be recorded.",
      });
      expect(retried.json<JobPayload>().events.map((event) => event.status)).toEqual([
        "running",
        "failed",
      ]);
      expectNoReviewEvidence(app);
    } finally {
      deferred.succeed();
      await app.close();
    }
  });
});
