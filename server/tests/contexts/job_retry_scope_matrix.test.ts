import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import type { AddJobInput } from "../../src/contexts/studio/application/ports/job_records.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const SUPPORTED_KINDS = ["proposal", "review", "export"] as const;

function failedJob(projectId: string, kind: string, now: Date): AddJobInput {
  return {
    projectId,
    documentId: null,
    kind,
    operation: kind === "proposal" ? "continue" : kind,
    status: "failed",
    provider: kind === "export" ? "studio" : "mock",
    model: "fixture-model",
    requestJson: kind === "export" ? '{"format":"markdown"}' : "{}",
    resultJson: "{}",
    error: "fixture failure",
    eventDetailsJson: '{"error":"fixture failure"}',
    now,
  };
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-job-retry-scope-"));
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const cleanup = async (): Promise<void> => {
    database.close();
    await rm(directory, { recursive: true, force: true });
  };
  try {
    const now = new Date("2026-09-02T00:00:00.000Z");
    const store = new DrizzleStudioStore({ database: database.db });
    const auth = new AuthService({
      store: new DrizzleAuthStore(database.db),
      sessionSecret: "job-retry-scope-test-secret",
      now: () => now,
    });
    await auth.configureOwner("retry-owner", "long-test-password");
    const session = await auth.createOwnerSession("retry-owner", "long-test-password");
    const scope = scopeForPrincipal(session.principal);
    const { project } = store.addProject(scope, {
      title: "Retry source scope",
      description: "",
      settingsJson: "{}",
      seed: null,
      now,
    });
    return { cleanup, now, projectId: project.id, scope, store };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

describe("job retry source scope matrix", () => {
  it("treats one key as independent for different source Jobs in one project", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const firstSource = store.addJob(scope, failedJob(projectId, "proposal", now));
      const secondSource = store.addJob(scope, failedJob(projectId, "proposal", now));

      const first = store.claimJobRetry(scope, {
        projectId,
        sourceJobId: firstSource.id,
        requestKey: "shared-source-key-0001",
        now,
      });
      const second = store.claimJobRetry(scope, {
        projectId,
        sourceJobId: secondSource.id,
        requestKey: "shared-source-key-0001",
        now,
      });

      expect([first.created, second.created]).toEqual([true, true]);
      expect(first.job.id).not.toBe(second.job.id);
      expect([first.job.retryOfJobId, second.job.retryOfJobId]).toEqual([
        firstSource.id,
        secondSource.id,
      ]);
    } finally {
      await cleanup();
    }
  });

  it.each(SUPPORTED_KINDS)("accepts a prior %s retry Job as a new source", async (kind) => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const fresh = store.addJob(scope, failedJob(projectId, kind, now));
      const priorRetry = store.claimJobRetry(scope, {
        projectId,
        sourceJobId: fresh.id,
        requestKey: `first-${kind}-retry-key`,
        now,
      });
      const failedRetry = store.markJobOutcome(scope, projectId, priorRetry.job.id, {
        status: "failed",
        error: "prior retry failed",
        eventDetailsJson: '{"error":"prior retry failed"}',
        now: new Date(now.getTime() + 1),
      });

      const nextRetry = store.claimJobRetry(scope, {
        projectId,
        sourceJobId: failedRetry.id,
        requestKey: `second-${kind}-retry-key`,
        now: new Date(now.getTime() + 2),
      });

      expect(nextRetry.created).toBe(true);
      expect(nextRetry.job).toMatchObject({
        kind,
        retryOfJobId: failedRetry.id,
        status: "running",
      });
    } finally {
      await cleanup();
    }
  });

  it("rejects an unsupported failed Job kind before reserving a retry", async () => {
    const { cleanup, now, projectId, scope, store } = await openHarness();
    try {
      const unsupported = store.addJob(scope, failedJob(projectId, "maintenance", now));

      expect(() =>
        store.claimJobRetry(scope, {
          projectId,
          sourceJobId: unsupported.id,
          requestKey: "unsupported-kind-key-0001",
          now,
        }),
      ).toThrow(InvalidOperationError);
      expect(
        store.findJobRetry(scope, projectId, unsupported.id, "unsupported-kind-key-0001"),
      ).toBeNull();
    } finally {
      await cleanup();
    }
  });
});
