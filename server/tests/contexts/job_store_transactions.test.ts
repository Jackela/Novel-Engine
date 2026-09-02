import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  type AddJobInput,
  jobPageLimit,
} from "../../src/contexts/studio/application/ports/job_records.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { InvalidJobTransitionError } from "../../src/contexts/studio/domain/exceptions.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

/**
 * #392: the combined job/usage writes commit atomically and the job state
 * machine refuses terminal outcomes on jobs that are no longer open.
 */

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-08-29T00:00:00.000Z");
  return () => {
    milliseconds += 1;
    return new Date(milliseconds);
  };
}

function completedJobInput(projectId: string, now: Date): AddJobInput {
  return {
    projectId,
    documentId: null,
    kind: "proposal",
    operation: "continue",
    status: "completed",
    provider: "mock",
    model: "deterministic-story-v1",
    requestJson: "{}",
    resultJson: "{}",
    error: null,
    eventDetailsJson: "{}",
    now,
  };
}

function usageInput() {
  return {
    provider: "mock",
    model: "deterministic-story-v1",
    promptTokens: 3,
    completionTokens: 5,
    requestEvidenceJson: "{}",
  };
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-job-store-tx-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const clock = monotonicClock();
  const store = new DrizzleStudioStore({ database: studio.db });
  // Projects reference the owners table, so the harness registers a real owner.
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "job-store-tx-test-secret",
    now: clock,
  });
  await auth.configureOwner("ledger-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("ledger-owner", "long-test-password")).principal;
  const scope = scopeForPrincipal(principal);
  const { project } = store.addProject(scope, {
    title: "Ledger",
    description: "",
    settingsJson: "{}",
    seed: null,
    now: clock(),
  });
  return {
    clock,
    store,
    scope,
    jobs: new JobStorePart(studio.db),
    db: studio.db,
    projectId: project.id,
  };
}

describe("atomic completed-proposal landing (#392)", () => {
  it("commits the job row and its usage event together", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const job = store.recordCompletedProposalJob(scope, {
      job: completedJobInput(projectId, clock()),
      usage: usageInput(),
    });
    expect(job.status).toBe("completed");
    const usage = store.aggregateProjectUsage(scope, projectId, new Date());
    expect(usage.requestCount).toBe(1);
    expect(usage.promptTokens).toBe(3);
    expect(usage.completionTokens).toBe(5);
  });

  it("rolls back both writes when the usage insert fails, leaving no orphan job", async () => {
    const { scope, clock, store, db, projectId } = await openHarness();
    class ExplodingUsageStore extends JobStorePart {
      protected override writeUsageEvent(): void {
        throw new Error("simulated ledger failure between the two writes");
      }
    }
    // The same underlying database handle; only the usage write differs.
    const exploding = new ExplodingUsageStore(db);
    expect(() =>
      exploding.recordCompletedProposalJob(scope, {
        job: completedJobInput(projectId, clock()),
        usage: usageInput(),
      }),
    ).toThrow("simulated ledger failure between the two writes");

    // The whole transaction rolled back: no job row, no usage event.
    expect(store.collectProjectJobs(scope, projectId, { limit: jobPageLimit(50) }).jobs).toEqual(
      [],
    );
    const usage = store.aggregateProjectUsage(scope, projectId, new Date());
    expect(usage.requestCount).toBe(0);
  });
});

describe("atomic retry completion with usage (#392)", () => {
  it("commits the outcome transition and its usage event together", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const tiedAt = clock();
    const running = store.addJob(scope, {
      ...completedJobInput(projectId, tiedAt),
      status: "running",
    });
    const done = store.markJobOutcomeWithUsage(scope, projectId, running.id, {
      outcome: {
        status: "completed",
        model: "retry-model",
        resultJson: "{}",
        error: null,
        eventDetailsJson: "{}",
        now: tiedAt,
      },
      usage: usageInput(),
    });
    expect(done.status).toBe("completed");
    expect(done.model).toBe("retry-model");
    expect(done.events.map((event) => event.status)).toEqual(["running", "completed"]);
    expect(
      store
        .collectProjectJobs(scope, projectId, { limit: jobPageLimit(50) })
        .jobs[0]?.events.map((event) => event.status),
    ).toEqual(["completed", "running"]);
    const usage = store.aggregateProjectUsage(scope, projectId, new Date());
    expect(usage.requestCount).toBe(1);
  });

  it("rolls back both writes when the usage insert fails after the transition", async () => {
    const { scope, clock, store, jobs, db, projectId } = await openHarness();
    const running = store.addJob(scope, {
      ...completedJobInput(projectId, clock()),
      status: "running",
    });
    class ExplodingUsageStore extends JobStorePart {
      protected override writeUsageEvent(): void {
        throw new Error("simulated ledger failure after the outcome transition");
      }
    }
    const exploding = new ExplodingUsageStore(db);
    expect(() =>
      exploding.markJobOutcomeWithUsage(scope, projectId, running.id, {
        outcome: {
          status: "completed",
          model: "retry-model",
          resultJson: "{}",
          error: null,
          eventDetailsJson: "{}",
          now: clock(),
        },
        usage: usageInput(),
      }),
    ).toThrow("simulated ledger failure after the outcome transition");

    // The transition rolled back with the usage write: the job stays running.
    expect(store.findJob(scope, projectId, running.id).status).toBe("running");
    expect(jobs.aggregateProjectUsage(scope, projectId, new Date()).requestCount).toBe(0);
  });
});

describe("job transition guard (#392)", () => {
  it("allows a terminal outcome on a running job", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const running = store.addJob(scope, {
      ...completedJobInput(projectId, clock()),
      status: "running",
    });
    const done = store.markJobOutcome(scope, projectId, running.id, {
      status: "completed",
      error: null,
      eventDetailsJson: "{}",
      now: clock(),
    });
    expect(done.status).toBe("completed");
  });

  it("refuses a second terminal outcome on an already-completed job", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const completed = store.addJob(scope, completedJobInput(projectId, clock()));
    expect(() =>
      store.markJobOutcome(scope, projectId, completed.id, {
        status: "failed",
        error: "late failure",
        eventDetailsJson: "{}",
        now: clock(),
      }),
    ).toThrow(InvalidJobTransitionError);
    // The refused transition left the original outcome untouched.
    expect(store.findJob(scope, projectId, completed.id).status).toBe("completed");
  });

  it("refuses an outcome on a failed job outside the retry chain", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const failed = store.addJob(scope, {
      ...completedJobInput(projectId, clock()),
      status: "failed",
      error: "first failure",
    });
    expect(() =>
      store.markJobOutcome(scope, projectId, failed.id, {
        status: "completed",
        error: null,
        eventDetailsJson: "{}",
        now: clock(),
      }),
    ).toThrow(InvalidJobTransitionError);
  });

  it("refuses the combined completion when the running job already settled", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const completed = store.addJob(scope, completedJobInput(projectId, clock()));
    expect(() =>
      store.markJobOutcomeWithUsage(scope, projectId, completed.id, {
        outcome: {
          status: "completed",
          model: "retry-model",
          resultJson: "{}",
          error: null,
          eventDetailsJson: "{}",
          now: clock(),
        },
        usage: usageInput(),
      }),
    ).toThrow(InvalidJobTransitionError);
    const usage = store.aggregateProjectUsage(scope, projectId, new Date());
    expect(usage.requestCount).toBe(0);
  });
});
