import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import type { AddJobInput } from "../../src/contexts/studio/application/ports/job_records.js";
import { jobPageLimit } from "../../src/contexts/studio/application/ports/job_records.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  NotFoundError,
  OperationInFlightError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

function failedJob(projectId: string, now: Date): AddJobInput {
  return {
    projectId,
    documentId: null,
    kind: "proposal",
    operation: "continue",
    status: "failed",
    provider: "mock",
    model: "deterministic-story-v1",
    requestJson: '{"instruction":"continue"}',
    resultJson: "{}",
    error: "provider unavailable",
    eventDetailsJson: '{"error":"provider unavailable"}',
    now,
  };
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-job-retry-key-"));
  const databasePath = join(directory, "novel-engine.sqlite3");
  const studio = await openStudioDatabase(databasePath).catch(async (error: unknown) => {
    await rm(directory, { recursive: true, force: true });
    throw error;
  });
  const cleanup = async (): Promise<void> => {
    try {
      studio.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  };
  try {
    const now = new Date("2026-09-02T00:00:00.000Z");
    const store = {
      projects: new ProjectStorePart(studio.db),
      jobs: new JobStorePart(studio.db),
    };
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "job-retry-key-test-secret",
      now: () => now,
    });
    await auth.configureOwner("retry-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("retry-owner", "long-test-password"))
      .principal;
    const scope = scopeForPrincipal(principal);
    const { project } = store.projects.addProject(scope, {
      title: "Retry idempotency",
      description: "",
      settingsJson: "{}",
      seed: null,
      now,
    });
    return { cleanup, databasePath, now, projectId: project.id, scope, store, studio };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

describe("durable job retry identity", () => {
  it("claims one running job and first event for one source and request key", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      const input = {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000001",
        now,
      };

      const claimed = store.jobs.claimJobRetry(scope, input);

      expect(claimed.created).toBe(true);
      expect(claimed.job).toMatchObject({
        projectId,
        retryOfJobId: source.id,
        status: "running",
      });
      expect(claimed.job.events.map((event) => event.status)).toEqual(["running"]);
      expect(
        store.jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) }).jobs,
      ).toHaveLength(2);
    } finally {
      await cleanup();
    }
  });

  it("reports a running claim in flight without adding another job or event", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      const input = {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000002",
        now,
      };
      const first = store.jobs.claimJobRetry(scope, input);

      expect(() => store.jobs.claimJobRetry(scope, input)).toThrow(OperationInFlightError);
      expect(store.jobs.findJob(scope, projectId, first.job.id).events).toHaveLength(1);
      expect(
        store.jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) }).jobs,
      ).toHaveLength(2);
    } finally {
      await cleanup();
    }
  });

  it("replays the exact terminal retry without adding evidence", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      const input = {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000003",
        now,
      };
      const first = store.jobs.claimJobRetry(scope, input);
      const completed = store.jobs.markJobOutcome(scope, projectId, first.job.id, {
        status: "completed",
        resultJson: '{"proposal_markdown":"done"}',
        error: null,
        eventDetailsJson: '{"proposal":true}',
        now: new Date(now.getTime() + 1),
      });

      const replay = store.jobs.claimJobRetry(scope, input);

      expect(replay).toEqual({ job: completed, created: false });
      expect(
        store.jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) }).jobs,
      ).toHaveLength(2);
    } finally {
      await cleanup();
    }
  });

  it("creates a distinct retry for a different request key", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      const first = store.jobs.claimJobRetry(scope, {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000004",
        now,
      });
      store.jobs.markJobOutcome(scope, projectId, first.job.id, {
        status: "failed",
        error: "retry failed",
        eventDetailsJson: '{"error":"retry failed"}',
        now: new Date(now.getTime() + 1),
      });

      const second = store.jobs.claimJobRetry(scope, {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000005",
        now: new Date(now.getTime() + 2),
      });

      expect(second.created).toBe(true);
      expect(second.job.id).not.toBe(first.job.id);
      expect(second.job.retryOfJobId).toBe(source.id);
    } finally {
      await cleanup();
    }
  });

  it("does not disclose or collide with a retry outside the scoped project", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      store.jobs.claimJobRetry(scope, {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000006",
        now,
      });
      const { project: otherProject } = store.projects.addProject(scope, {
        title: "Other retry scope",
        description: "",
        settingsJson: "{}",
        seed: null,
        now,
      });
      const otherSource = store.jobs.addJob(scope, failedJob(otherProject.id, now));

      expect(() =>
        store.jobs.claimJobRetry(
          { ownerId: "another-owner" },
          {
            projectId,
            sourceJobId: source.id,
            requestKey: "retry-key-00000006",
            now,
          },
        ),
      ).toThrow(NotFoundError);
      expect(() =>
        store.jobs.claimJobRetry(scope, {
          projectId: otherProject.id,
          sourceJobId: source.id,
          requestKey: "retry-key-00000006",
          now,
        }),
      ).toThrow(NotFoundError);
      expect(
        store.jobs.claimJobRetry(scope, {
          projectId: otherProject.id,
          sourceJobId: otherSource.id,
          requestKey: "retry-key-00000006",
          now,
        }).created,
      ).toBe(true);
    } finally {
      await cleanup();
    }
  });

  it("rolls the retry row back when its first event cannot be inserted", async () => {
    const { cleanup, now, projectId, scope, store, studio } = await openHarness();
    class ExplodingRetryClaimStore extends JobStorePart {
      protected override beforeRetryClaimEventInsert(): void {
        throw new Error("simulated retry first-event failure");
      }
    }
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      const input = {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000007",
        now,
      };

      expect(() => new ExplodingRetryClaimStore(studio.db).claimJobRetry(scope, input)).toThrow(
        "simulated retry first-event failure",
      );
      expect(
        store.jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) }).jobs,
      ).toHaveLength(1);
      expect(store.jobs.claimJobRetry(scope, input).created).toBe(true);
    } finally {
      await cleanup();
    }
  });

  it("replays a keyed running retry after startup recovery marks it interrupted", async () => {
    const { cleanup, databasePath, now, projectId, scope, store, studio } = await openHarness();
    let reopened: Awaited<ReturnType<typeof openStudioDatabase>> | undefined;
    try {
      const source = store.jobs.addJob(scope, failedJob(projectId, now));
      const input = {
        projectId,
        sourceJobId: source.id,
        requestKey: "retry-key-00000008",
        now,
      };
      const running = store.jobs.claimJobRetry(scope, input);
      studio.close();

      reopened = await openStudioDatabase(databasePath);
      const restartedStore = new JobStorePart(reopened.db);
      const replay = restartedStore.claimJobRetry(scope, input);

      expect(replay.created).toBe(false);
      expect(replay.job).toMatchObject({ id: running.job.id, status: "interrupted" });
      expect(replay.job.events.map((event) => event.status)).toEqual(["running", "interrupted"]);
    } finally {
      reopened?.close();
      await cleanup();
    }
  });
});
