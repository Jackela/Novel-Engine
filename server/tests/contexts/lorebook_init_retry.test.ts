import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextGenerationResult,
  type TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  LoreExtractService,
  recoverLoreExtractSegment,
} from "../../src/contexts/studio/application/lore_extract_service.js";
import { jobSummaryPayload } from "../../src/contexts/studio/application/payloads.js";
import { jobPageLimit } from "../../src/contexts/studio/application/ports/job_records.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

/**
 * Retry-side coverage of the wizard's lore-extract Jobs (#614, #272 chain):
 * a failed segment job is retried onto its own reserved row with exactly one
 * usage event, replays of the same key return the stored terminal Job
 * without new evidence, and the summary/detail serializers round-trip the
 * new kind. The fresh-extraction contract lives in
 * `lorebook_init_extract.test.ts`.
 */

function candidateResult(candidates: unknown[]): TextGenerationResult {
  return {
    step: "lore_extract",
    provider: "mock",
    model: "scripted-model",
    rawText: "",
    content: { candidates },
    promptTokens: null,
    completionTokens: null,
  };
}

async function openHarness(factory: TextGenerationProviderFactory) {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-lorebook-retry-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const cleanup = async (): Promise<void> => {
    studio.close();
    await rm(directory, { recursive: true, force: true });
  };
  try {
    const now = new Date("2026-09-14T00:00:00.000Z");
    const jobs = new JobStorePart(studio.db);
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "lore-retry-test-secret",
      now: () => now,
    });
    await auth.configureOwner("lore-retry-owner", "long-test-password");
    const { principal } = await auth.createOwnerSession("lore-retry-owner", "long-test-password");
    const scope = scopeForPrincipal(principal);
    const { project } = new ProjectStorePart(studio.db).addProject(scope, {
      title: "Lore retry",
      description: "",
      settingsJson: "{}",
      seed: null,
      now,
    });
    const service = new LoreExtractService(jobs, factory, () => now);
    return { cleanup, jobs, now, principal, projectId: project.id, scope, service };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

function usageRequests(
  jobs: JobStorePart,
  scope: ProjectScope,
  projectId: string,
  now: Date,
): number {
  return jobs.aggregateProjectUsage(scope, projectId, now).requestCount;
}

describe("lorebook wizard retry chain", () => {
  it("retries a failed segment onto its own row with exactly one usage event", async () => {
    let failing = true;
    const factory: TextGenerationProviderFactory = () => ({
      async generateStructured(_task: TextGenerationTask) {
        if (failing) {
          throw new TextGenerationProviderError("provider unavailable");
        }
        return candidateResult([
          {
            kind: "world",
            title: "Flood Market",
            aliases: ["Market"],
            summary: "A drowned bazaar.",
          },
        ]);
      },
    });
    const { cleanup, jobs, now, principal, projectId, scope, service } = await openHarness(factory);
    try {
      const failed = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "the flood market keeps its bargains" },
        () => undefined,
      );
      expect(failed).toMatchObject({ kind: "lore-extract", status: "failed" });
      expect(usageRequests(jobs, scope, projectId, now)).toBe(0);

      const claim = jobs.claimJobRetry(scope, {
        projectId,
        sourceJobId: failed.id as string,
        requestKey: "lore-retry-key-0001",
        now,
      });
      expect(claim).toMatchObject({ created: true });
      expect(claim.job).toMatchObject({
        kind: "lore-extract",
        operation: "extract",
        status: "running",
        retryOfJobId: failed.id,
      });

      failing = false;
      const retried = await service.retry({
        scope,
        retry: claim.job,
        reportCleanupFailure: () => undefined,
        now: () => now,
      });

      expect(retried).toMatchObject({ kind: "lore-extract", status: "completed" });
      expect(JSON.parse(retried.resultJson)).toEqual({
        candidates: [
          {
            kind: "world",
            title: "Flood Market",
            aliases: ["Market"],
            summary: "A drowned bazaar.",
          },
        ],
      });
      expect(usageRequests(jobs, scope, projectId, now)).toBe(1);
    } finally {
      await cleanup();
    }
  });

  it("replays a terminal keyed retry without new jobs, events, or usage", async () => {
    const { cleanup, jobs, now, principal, projectId, scope, service } = await openHarness(() => ({
      async generateStructured() {
        return candidateResult([]);
      },
    }));
    try {
      const completed = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "an empty ledger is still a ledger" },
        () => undefined,
      );
      expect(completed.status).toBe("completed");
      // Force a retryable source by landing a failed row through the store.
      const failedRow = jobs.addJob(scope, {
        projectId,
        documentId: null,
        kind: "lore-extract",
        operation: "extract",
        status: "failed",
        provider: "mock",
        model: "",
        requestJson: '{"segment":"an empty ledger is still a ledger"}',
        resultJson: '{"candidates":[]}',
        error: "fixture failure",
        eventDetailsJson: '{"error":"fixture failure"}',
        now,
      });
      const claim = jobs.claimJobRetry(scope, {
        projectId,
        sourceJobId: failedRow.id,
        requestKey: "lore-retry-key-0002",
        now,
      });
      const retried = await service.retry({
        scope,
        retry: claim.job,
        reportCleanupFailure: () => undefined,
        now: () => now,
      });

      const usageAfterRetry = usageRequests(jobs, scope, projectId, now);
      const replay = jobs.claimJobRetry(scope, {
        projectId,
        sourceJobId: failedRow.id,
        requestKey: "lore-retry-key-0002",
        now: new Date(now.getTime() + 1),
      });

      expect(replay).toEqual({ job: retried, created: false });
      expect(usageRequests(jobs, scope, projectId, now)).toBe(usageAfterRetry);
      const page = jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) });
      expect(page.jobs).toHaveLength(3);
      expect(retried.events.map((event) => event.status)).toEqual(["running", "completed"]);
    } finally {
      await cleanup();
    }
  });

  it("round-trips the new kind through the summary and detail serializers", async () => {
    const { cleanup, jobs, now, principal, projectId, service } = await openHarness(() => ({
      async generateStructured() {
        return candidateResult([
          {
            kind: "character",
            title: "Mira",
            aliases: ["The Clerk"],
            summary: "Keeps the ledger.",
          },
        ]);
      },
    }));
    try {
      const payload = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "Mira keeps the ledger for the station" },
        () => undefined,
      );
      const job = jobs.findJob(scopeForPrincipal(principal), projectId, payload.id as string);

      const summary = jobSummaryPayload(job);
      expect(summary).toMatchObject({
        kind: "lore-extract",
        operation: "extract",
        status: "completed",
      });
      expect(Object.keys(summary).sort()).toEqual([
        "created_at",
        "document_id",
        "error",
        "id",
        "kind",
        "model",
        "operation",
        "project_id",
        "provider",
        "retry_of_job_id",
        "status",
        "updated_at",
      ]);
      expect(JSON.parse(job.resultJson).candidates).toEqual([
        { kind: "character", title: "Mira", aliases: ["The Clerk"], summary: "Keeps the ledger." },
      ]);
      expect(job.events.map((event) => event.status)).toEqual(["completed"]);
      expect(now.toISOString()).toBe("2026-09-14T00:00:00.000Z");
    } finally {
      await cleanup();
    }
  });

  it("refuses a retry whose stored request context is lost", () => {
    expect(() => recoverLoreExtractSegment("{}")).toThrow(InvalidOperationError);
    expect(() => recoverLoreExtractSegment('{"segment":42}')).toThrow(
      "Original lore extraction job is missing its request context.",
    );
    expect(recoverLoreExtractSegment('{"segment":"kept"}')).toBe("kept");
  });
});
