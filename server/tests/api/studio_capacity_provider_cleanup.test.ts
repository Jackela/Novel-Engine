import { describe, expect, it } from "vitest";

import {
  type ApiResponse,
  cleanupGatedProvider,
  expectApplicationCapacity,
  proposalRequest,
  proveExactlyOnePermitRecovered,
  seedFailedProposalRetry,
} from "./studio_capacity_provider_cleanup_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("Studio Provider cleanup capacity", () => {
  it("holds a synchronous proposal permit through successful disposal and releases it once", async () => {
    const provider = cleanupGatedProvider();
    const { app } = await buildStudioApp(undefined, {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      textProviderFactory: provider.factory,
    });
    let primary: Promise<ApiResponse> | undefined;
    try {
      const owner = await ownerJar(app);
      const activeProject = await seedProject(app, owner, "Proposal cleanup owner");
      const waitingProject = await seedProject(app, owner, "Proposal cleanup waiter");

      primary = proposalRequest(app, owner, activeProject);
      await provider.firstDisposeStarted;

      const landed = await call(app, owner, "GET", `/api/projects/${activeProject.id}/jobs`);
      expect(landed.statusCode, landed.body).toBe(200);
      expect(landed.json().jobs).toMatchObject([{ kind: "proposal", status: "completed" }]);
      const landedDetail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${activeProject.id}/jobs/${landed.json().jobs[0].id}`,
      );
      expect(landedDetail.json().events).toMatchObject([{ status: "completed" }]);
      await expectApplicationCapacity(
        await proposalRequest(app, owner, waitingProject),
        waitingProject.id,
      );
      expect(provider.factoryCalls()).toBe(1);

      provider.releaseFirstDispose();
      const completed = await primary;
      primary = undefined;
      expect(completed.statusCode, completed.body).toBe(200);

      await proveExactlyOnePermitRecovered(app, owner, activeProject.id, waitingProject, provider);
    } finally {
      provider.releaseFirstDispose();
      provider.releaseSecondWork();
      await primary?.catch(() => undefined);
      await app.close();
    }
  });

  it("holds a review permit through failed disposal and lands its outcome afterward", async () => {
    const provider = cleanupGatedProvider({ failFirstDispose: true });
    const { app } = await buildStudioApp(undefined, {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      textProviderFactory: provider.factory,
    });
    let primary: Promise<ApiResponse> | undefined;
    try {
      const owner = await ownerJar(app);
      const activeProject = await seedProject(app, owner, "Review cleanup owner");
      const waitingProject = await seedProject(app, owner, "Review cleanup waiter");

      primary = call(app, owner, "POST", `/api/projects/${activeProject.id}/reviews`, {});
      await provider.firstDisposeStarted;

      // Review evaluation owns Provider disposal, so its generated outcome is
      // ready here but the atomic review/snapshot/job evidence lands afterward.
      const jobsWhileDisposing = await call(
        app,
        owner,
        "GET",
        `/api/projects/${activeProject.id}/jobs`,
      );
      const reviewsWhileDisposing = await call(
        app,
        owner,
        "GET",
        `/api/projects/${activeProject.id}/reviews`,
      );
      expect(jobsWhileDisposing.json().jobs).toEqual([]);
      expect(reviewsWhileDisposing.json().reviews).toEqual([]);
      await expectApplicationCapacity(
        await proposalRequest(app, owner, waitingProject),
        waitingProject.id,
      );
      expect(provider.factoryCalls()).toBe(1);

      provider.releaseFirstDispose();
      const completed = await primary;
      primary = undefined;
      expect(completed.statusCode, completed.body).toBe(201);
      expect(completed.body).not.toContain(provider.cleanupFailureMessage);

      const landedJobs = await call(app, owner, "GET", `/api/projects/${activeProject.id}/jobs`);
      const landedReviews = await call(
        app,
        owner,
        "GET",
        `/api/projects/${activeProject.id}/reviews`,
      );
      expect(landedJobs.json().jobs).toMatchObject([{ kind: "review", status: "completed" }]);
      const landedDetail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${activeProject.id}/jobs/${landedJobs.json().jobs[0].id}`,
      );
      expect(landedDetail.json().events).toMatchObject([{ status: "completed" }]);
      expect(landedReviews.json().reviews).toHaveLength(1);

      await proveExactlyOnePermitRecovered(app, owner, activeProject.id, waitingProject, provider);
    } finally {
      provider.releaseFirstDispose();
      provider.releaseSecondWork();
      await primary?.catch(() => undefined);
      await app.close();
    }
  });

  it("holds a proposal retry permit after terminal landing until disposal finishes", async () => {
    const clock = monotonicClock();
    const provider = cleanupGatedProvider();
    const { app } = await buildStudioApp(clock, {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      textProviderFactory: provider.factory,
    });
    let primary: Promise<ApiResponse> | undefined;
    try {
      const owner = await ownerJar(app);
      const activeProject = await seedProject(app, owner, "Retry cleanup owner");
      const waitingProject = await seedProject(app, owner, "Retry cleanup waiter");
      const activeDetail = await getProject(app, owner, activeProject.id);
      const document = activeDetail.documents[0];
      if (document === undefined) throw new Error("Expected the seeded chapter.");
      const sourceJobId = seedFailedProposalRetry(
        app,
        activeProject.id,
        document.id,
        document.current_revision_id,
        clock(),
      );

      primary = call(
        app,
        owner,
        "POST",
        `/api/projects/${activeProject.id}/jobs/${sourceJobId}/retry`,
      );
      await provider.firstDisposeStarted;

      const landed = await call(app, owner, "GET", `/api/projects/${activeProject.id}/jobs`);
      expect(landed.statusCode, landed.body).toBe(200);
      expect(landed.json().jobs).toMatchObject([
        {
          kind: "proposal",
          status: "completed",
          retry_of_job_id: sourceJobId,
        },
        { id: sourceJobId, status: "failed" },
      ]);
      const landedDetail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${activeProject.id}/jobs/${landed.json().jobs[0].id}`,
      );
      expect(landedDetail.json().events).toMatchObject([
        { status: "running" },
        { status: "completed" },
      ]);
      await expectApplicationCapacity(
        await proposalRequest(app, owner, waitingProject),
        waitingProject.id,
      );
      expect(provider.factoryCalls()).toBe(1);

      provider.releaseFirstDispose();
      const completed = await primary;
      primary = undefined;
      expect(completed.statusCode, completed.body).toBe(200);
      expect(completed.json()).toMatchObject({
        status: "completed",
        retry_of_job_id: sourceJobId,
      });
      expect(completed.json().events.map((event: { status: string }) => event.status)).toEqual([
        "running",
        "completed",
      ]);

      await proveExactlyOnePermitRecovered(app, owner, activeProject.id, waitingProject, provider);
    } finally {
      provider.releaseFirstDispose();
      provider.releaseSecondWork();
      await primary?.catch(() => undefined);
      await app.close();
    }
  });
});
