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
import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import { JobHistoryService } from "../../src/contexts/studio/application/job_history_service.js";
import { LoreExtractService } from "../../src/contexts/studio/application/lore_extract_service.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import { jobPageLimit } from "../../src/contexts/studio/application/ports/job_records.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProposalGenerationPipeline } from "../../src/contexts/studio/application/proposal_pipeline.js";
import { ReviewService } from "../../src/contexts/studio/application/review_service.js";
import type { StudioPersistence } from "../../src/contexts/studio/application/studio_services.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { LoreStorePart } from "../../src/contexts/studio/infrastructure/lore_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { ProposalAcceptanceStorePart } from "../../src/contexts/studio/infrastructure/proposal_acceptance_store_part.js";
import { ProposalContextStorePart } from "../../src/contexts/studio/infrastructure/proposal_context_store_part.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { VolumeStorePart } from "../../src/contexts/studio/infrastructure/volume_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

/**
 * Executor-level integration of the wizard's lore-extract retry chain
 * (#614, #652 T2.1): a failed segment job retried through
 * `JobHistoryService.reexecuteProjectJob` — the same entry point the jobs
 * retry route uses — one completing and one failing retry, each landing on
 * its own reserved row with the usage-singularity contract intact.
 */

const CANDIDATES = [
  {
    kind: "world",
    title: "Flood Market",
    aliases: ["Market"],
    summary: "A drowned bazaar.",
  },
];

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

async function openHarness(handler: (task: TextGenerationTask) => Promise<TextGenerationResult>) {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-lore-reexecute-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const cleanup = async (): Promise<void> => {
    studio.close();
    await rm(directory, { recursive: true, force: true });
  };
  try {
    const now = new Date("2026-09-14T00:00:00.000Z");
    const jobs = new JobStorePart(studio.db);
    const factory: TextGenerationProviderFactory = () => ({
      generateStructured: handler,
    });
    const inFlight = new InFlightOperationGuard();
    const loreExtractions = new LoreExtractService(jobs, factory, () => now);
    const exportStore = new ExportStorePart(studio.db);
    const persistence: StudioPersistence = {
      projects: new ProjectStorePart(studio.db),
      documents: new DocumentStorePart(studio.db),
      volumes: new VolumeStorePart(studio.db),
      lore: new LoreStorePart(studio.db),
      jobs,
      reviewOutcomes: new ReviewStorePart(studio.db),
      proposalContext: new ProposalContextStorePart(studio.db),
      proposalAcceptance: new ProposalAcceptanceStorePart(studio.db),
    };
    const jobHistory = new JobHistoryService(
      jobs,
      persistence.reviewOutcomes,
      new ReviewService(persistence.reviewOutcomes, { providerFactory: factory, now: () => now }),
      new SnapshotArtifactService(exportStore, {
        async writeSnapshotArtifact() {
          throw new Error("unexpected artifact write");
        },
        async readArtifactBytes() {
          throw new Error("unexpected artifact read");
        },
      }),
      {
        now: () => now,
        inFlight,
        proposals: new ProposalGenerationPipeline(
          persistence.proposalContext,
          jobs,
          factory,
          inFlight,
          () => now,
        ),
        loreExtractions,
      },
    );
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "lore-reexecute-test-secret",
      now: () => now,
    });
    await auth.configureOwner("lore-reexecute-owner", "long-test-password");
    const { principal } = await auth.createOwnerSession(
      "lore-reexecute-owner",
      "long-test-password",
    );
    const scope = scopeForPrincipal(principal);
    const { project } = persistence.projects.addProject(scope, {
      title: "Lore reexecute",
      description: "",
      settingsJson: "{}",
      seed: null,
      now,
    });
    return {
      cleanup,
      jobHistory,
      jobs,
      loreExtractions,
      now,
      principal,
      projectId: project.id,
      scope,
    };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

describe("lore-extract retry through JobHistoryService.reexecuteProjectJob", () => {
  it("retries a failed segment to a completed job with one usage event, then replays stored", async () => {
    let failing = true;
    const { cleanup, jobHistory, jobs, loreExtractions, now, principal, projectId, scope } =
      await openHarness(async () => {
        if (failing) {
          throw new TextGenerationProviderError("provider unavailable");
        }
        return candidateResult(CANDIDATES);
      });
    try {
      const failed = await loreExtractions.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "the flood market keeps its bargains" },
        () => undefined,
      );
      expect(failed).toMatchObject({ kind: "lore-extract", status: "failed" });
      expect(jobs.aggregateProjectUsage(scope, projectId, now).requestCount).toBe(0);

      failing = false;
      const retried = await jobHistory.reexecuteProjectJob(
        principal,
        projectId,
        failed.id as string,
        "lore-reexecute-ok-0001",
        () => undefined,
      );

      expect(retried).toMatchObject({
        kind: "lore-extract",
        operation: "extract",
        status: "completed",
        retry_of_job_id: failed.id,
        provider: "mock",
        model: "scripted-model",
      });
      expect(retried.result).toEqual({ candidates: CANDIDATES });
      const retriedEvents = retried.events as Array<{ status: string }>;
      expect(retriedEvents.map((event) => event.status)).toEqual(["running", "completed"]);
      expect(jobs.aggregateProjectUsage(scope, projectId, now).requestCount).toBe(1);

      // A keyed replay returns the stored terminal job without new work.
      const replay = await jobHistory.reexecuteProjectJob(
        principal,
        projectId,
        failed.id as string,
        "lore-reexecute-ok-0001",
        () => undefined,
      );
      expect(replay).toEqual(retried);
      expect(jobs.aggregateProjectUsage(scope, projectId, now).requestCount).toBe(1);
      expect(
        jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) }).jobs,
      ).toHaveLength(2);
    } finally {
      await cleanup();
    }
  });

  it("lands a still-failing retry as a failed job without usage, keeping the source", async () => {
    const { cleanup, jobHistory, jobs, loreExtractions, now, principal, projectId, scope } =
      await openHarness(async () => {
        throw new TextGenerationProviderError("provider transport failed");
      });
    try {
      const failed = await loreExtractions.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "an empty ledger is still a ledger" },
        () => undefined,
      );
      expect(failed.status).toBe("failed");

      const retried = await jobHistory.reexecuteProjectJob(
        principal,
        projectId,
        failed.id as string,
        "lore-reexecute-fail-01",
        () => undefined,
      );

      expect(retried).toMatchObject({
        kind: "lore-extract",
        status: "failed",
        retry_of_job_id: failed.id,
      });
      expect(retried.error).toBe("provider transport failed");
      const retriedEvents = retried.events as Array<{ status: string }>;
      expect(retriedEvents.map((event) => event.status)).toEqual(["running", "failed"]);
      expect(jobs.aggregateProjectUsage(scope, projectId, now).requestCount).toBe(0);

      const page = jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) });
      expect(page.jobs).toHaveLength(2);
      expect(page.jobs[0]).toMatchObject({ status: "failed" });
      expect(page.jobs[1]).toMatchObject({ status: "failed" });
    } finally {
      await cleanup();
    }
  });
});
