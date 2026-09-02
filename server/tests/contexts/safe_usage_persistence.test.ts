import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  type AddJobInput,
  jobPageLimit,
} from "../../src/contexts/studio/application/ports/job_records.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-09-02T00:00:00.000Z");
  return () => {
    milliseconds += 1;
    return new Date(milliseconds);
  };
}

function completedJob(projectId: string, now: Date, model = "alpha"): AddJobInput {
  return {
    projectId,
    documentId: null,
    kind: "proposal",
    operation: "continue",
    status: "completed",
    provider: "mock",
    model,
    requestJson: "{}",
    resultJson: "{}",
    error: null,
    eventDetailsJson: "{}",
    now,
  };
}

function usage(model = "alpha") {
  return {
    provider: "mock",
    model,
    promptTokens: 3,
    completionTokens: 5,
    requestEvidenceJson: "{}",
  };
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-safe-usage-store-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const clock = monotonicClock();
  const store = new DrizzleStudioStore({ database: studio.db });
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "safe-usage-test-secret",
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
  return { clock, store, scope, projectId: project.id };
}

describe("safe usage persistence", () => {
  it("rejects unsafe counts and rolls back the paired completed job", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const invalid = [Number.MAX_SAFE_INTEGER + 1, 1e308, Number.POSITIVE_INFINITY, -1, 1.5];
    for (const promptTokens of invalid) {
      expect(() =>
        store.recordCompletedProposalJob(scope, {
          job: completedJob(projectId, clock()),
          usage: { ...usage(), promptTokens },
        }),
      ).toThrow("prompt token count must be a non-negative safe integer");
    }
    for (const completionTokens of invalid) {
      expect(() =>
        store.recordCompletedProposalJob(scope, {
          job: completedJob(projectId, clock()),
          usage: { ...usage(), completionTokens },
        }),
      ).toThrow("completion token count must be a non-negative safe integer");
    }
    expect(
      store.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) }).jobs,
    ).toEqual([]);
    expect(store.aggregateProjectUsage(scope, projectId, clock()).requestCount).toBe(0);
  });

  it("rejects unsafe usage and leaves the paired retry running", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    const running = store.addJob(scope, {
      ...completedJob(projectId, clock()),
      status: "running",
    });
    expect(() =>
      store.markJobOutcomeWithUsage(scope, projectId, running.id, {
        outcome: {
          status: "completed",
          model: "retry-model",
          resultJson: "{}",
          error: null,
          eventDetailsJson: "{}",
          now: clock(),
        },
        usage: { ...usage(), completionTokens: Number.MAX_SAFE_INTEGER + 1 },
      }),
    ).toThrow("completion token count must be a non-negative safe integer");
    expect(store.findJob(scope, projectId, running.id)).toMatchObject({
      status: "running",
      events: [{ status: "running" }],
    });
    expect(store.aggregateProjectUsage(scope, projectId, clock()).requestCount).toBe(0);
  });

  it("keeps per-model, project, and daily totals exact at the safe boundary", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    store.recordCompletedProposalJob(scope, {
      job: completedJob(projectId, clock()),
      usage: {
        ...usage(),
        promptTokens: Number.MAX_SAFE_INTEGER - 3,
        completionTokens: Number.MAX_SAFE_INTEGER - 5,
      },
    });
    store.recordCompletedProposalJob(scope, {
      job: completedJob(projectId, clock(), "beta"),
      usage: { ...usage("beta"), promptTokens: 3, completionTokens: 5 },
    });
    const result = store.aggregateProjectUsage(scope, projectId, clock());
    expect(result).toMatchObject({
      requestCount: 2,
      promptTokens: Number.MAX_SAFE_INTEGER,
      completionTokens: Number.MAX_SAFE_INTEGER,
      perModel: [
        { model: "alpha", promptTokens: Number.MAX_SAFE_INTEGER - 3 },
        { model: "beta", promptTokens: 3 },
      ],
    });
    expect(result.daily.at(-1)).toMatchObject({
      requestCount: 2,
      promptTokens: Number.MAX_SAFE_INTEGER,
      completionTokens: Number.MAX_SAFE_INTEGER,
    });
  });

  it("fails when one model's individually safe rows have an unsafe sum", async () => {
    const { scope, clock, store, projectId } = await openHarness();
    store.recordCompletedProposalJob(scope, {
      job: completedJob(projectId, clock()),
      usage: { ...usage(), promptTokens: Number.MAX_SAFE_INTEGER },
    });
    store.recordCompletedProposalJob(scope, {
      job: completedJob(projectId, clock()),
      usage: { ...usage(), promptTokens: 1 },
    });
    expect(() => store.aggregateProjectUsage(scope, projectId, clock())).toThrow(
      "prompt token count must be a non-negative safe integer",
    );
  });
});
