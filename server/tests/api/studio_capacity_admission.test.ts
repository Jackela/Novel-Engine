import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import {
  exports as exportArtifacts,
  exportPublicationCleanupIntents,
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { jobEvents, jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

function deferredFirstProvider(): {
  factory: TextGenerationProviderFactory;
  started: Promise<void>;
  release: () => void;
  factoryCalls: () => number;
  generationCalls: () => number;
} {
  let announceStarted: (() => void) | undefined;
  let finishFirst: (() => void) | undefined;
  let factoryCalls = 0;
  let generationCalls = 0;
  const started = new Promise<void>((resolve) => {
    announceStarted = resolve;
  });
  const firstGate = new Promise<void>((resolve) => {
    finishFirst = resolve;
  });

  const factory: TextGenerationProviderFactory = (provider) => {
    const requestIndex = factoryCalls;
    factoryCalls += 1;
    const implementation: TextGenerationProvider = {
      async generateStructured(task) {
        generationCalls += 1;
        if (requestIndex === 0) {
          announceStarted?.();
          await firstGate;
        }
        const content =
          task.step === "editorial_review"
            ? { findings: [] }
            : { chapter_markdown: validProposalProse };
        return {
          step: task.step,
          provider,
          model: "capacity-api-model",
          rawText: JSON.stringify(content),
          content,
          promptTokens: 1,
          completionTokens: 1,
        };
      },
      async *generateStructuredStreaming() {
        generationCalls += 1;
        yield validProposalProse;
      },
    };
    return implementation;
  };

  return {
    factory,
    started,
    release: () => finishFirst?.(),
    factoryCalls: () => factoryCalls,
    generationCalls: () => generationCalls,
  };
}

function countingArtifactGateway(): {
  gateway: ExportArtifactGateway;
  writes: () => number;
} {
  let writes = 0;
  return {
    gateway: {
      async writeSnapshotArtifact(request) {
        writes += 1;
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => undefined,
        };
      },
      async readArtifactBytes() {
        throw new Error("unexpected artifact read");
      },
    },
    writes: () => writes,
  };
}

function evidenceCounts(app: FastifyInstance): Record<string, number> {
  const database = studioDatabase(app);
  return {
    jobs: database.select().from(jobs).all().length,
    jobEvents: database.select().from(jobEvents).all().length,
    usageEvents: database.select().from(usageEvents).all().length,
    projectSnapshots: database.select().from(projectSnapshots).all().length,
    snapshotDocuments: database.select().from(snapshotDocuments).all().length,
    reviews: database.select().from(reviews).all().length,
    reviewIssues: database.select().from(reviewIssues).all().length,
    exports: database.select().from(exportArtifacts).all().length,
    cleanupIntents: database.select().from(exportPublicationCleanupIntents).all().length,
  };
}

function seedRetryableProposal(
  app: FastifyInstance,
  projectId: string,
  documentId: string,
): string {
  const id = "capacity-api-retry-fixture";
  const now = new Date("2026-09-02T08:00:00.000Z");
  studioDatabase(app)
    .insert(jobs)
    .values({
      id,
      project_id: projectId,
      document_id: documentId,
      kind: "proposal",
      operation: "continue",
      status: "failed",
      provider: "mock",
      model: "fixture-model",
      request_json: '{"instruction":"","provider":"mock"}',
      result_json: "{}",
      error: "fixture failure",
      created_at: now,
      updated_at: now,
      started_at: now,
      finished_at: now,
    })
    .run();
  return id;
}

describe("Studio workflow capacity admission API", () => {
  it("refuses all five counted POSTs before side effects and recovers after release", async () => {
    const provider = deferredFirstProvider();
    const artifacts = countingArtifactGateway();
    const { app } = await buildStudioApp(undefined, {
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
      textProviderFactory: provider.factory,
      exportArtifactGateway: artifacts.gateway,
    });
    let blockingReview: Promise<Awaited<ReturnType<typeof call>>> | undefined;
    try {
      const owner = await ownerJar(app);
      const activeProject = await seedProject(app, owner, "Capacity blocker");
      const refusedProject = await seedProject(app, owner, "Capacity refusals");
      const document = refusedProject.documents[0];
      if (document === undefined) throw new Error("Expected the seeded chapter.");
      const retryJobId = seedRetryableProposal(app, refusedProject.id, document.id);

      blockingReview = call(app, owner, "POST", `/api/projects/${activeProject.id}/reviews`, {});
      await provider.started;
      const before = evidenceCounts(app);

      const requests = [
        {
          name: "synchronous proposal",
          url: `/api/projects/${refusedProject.id}/documents/${document.id}/ai-proposals`,
          payload: { operation: "continue", provider: "mock" },
        },
        {
          name: "streaming proposal",
          url: `/api/projects/${refusedProject.id}/documents/${document.id}/ai-proposals/stream`,
          payload: { operation: "continue", provider: "mock" },
        },
        {
          name: "editorial review",
          url: `/api/projects/${refusedProject.id}/reviews`,
          payload: {},
        },
        {
          name: "export",
          url: `/api/projects/${refusedProject.id}/exports`,
          payload: { format: "markdown" },
        },
        {
          name: "retry",
          url: `/api/projects/${refusedProject.id}/jobs/${retryJobId}/retry`,
          payload: undefined,
        },
      ] as const;

      for (const request of requests) {
        const response = await call(app, owner, "POST", request.url, request.payload);
        expect(response.statusCode, `${request.name}: ${response.body}`).toBe(503);
        expect(response.headers["content-type"]).toContain("application/json");
        expect(response.headers["retry-after"]).toBe("5");
        expect(response.json()).toEqual({
          error: {
            code: "OPERATION_CAPACITY_EXCEEDED",
            message: "Studio operation capacity is exhausted.",
            details: {
              scope: "application",
              limit: 1,
              in_flight: 1,
              project_id: refusedProject.id,
              retry_after_seconds: 5,
            },
          },
        });
      }

      expect(provider.factoryCalls()).toBe(1);
      expect(provider.generationCalls()).toBe(1);
      expect(artifacts.writes()).toBe(0);
      expect(evidenceCounts(app)).toEqual(before);

      provider.release();
      const completedReview = await blockingReview;
      blockingReview = undefined;
      expect(completedReview.statusCode, completedReview.body).toBe(201);
      const recovered = await call(
        app,
        owner,
        "POST",
        `/api/projects/${refusedProject.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", provider: "mock" },
      );
      expect(recovered.statusCode, recovered.body).toBe(200);
    } finally {
      provider.release();
      await blockingReview?.catch(() => undefined);
      await app.close();
    }
  });

  it("reports project scope while another project can use the remaining app capacity", async () => {
    const provider = deferredFirstProvider();
    const { app } = await buildStudioApp(undefined, {
      operationCapacity: { applicationLimit: 2, projectLimit: 1 },
      textProviderFactory: provider.factory,
    });
    let blockingReview: Promise<Awaited<ReturnType<typeof call>>> | undefined;
    try {
      const owner = await ownerJar(app);
      const saturatedProject = await seedProject(app, owner, "Project capacity blocker");
      const availableProject = await seedProject(app, owner, "Remaining app capacity");
      const saturatedDocument = saturatedProject.documents[0];
      const availableDocument = availableProject.documents[0];
      if (saturatedDocument === undefined || availableDocument === undefined) {
        throw new Error("Expected both seeded chapters.");
      }

      blockingReview = call(app, owner, "POST", `/api/projects/${saturatedProject.id}/reviews`, {});
      await provider.started;

      const refused = await call(
        app,
        owner,
        "POST",
        `/api/projects/${saturatedProject.id}/documents/${saturatedDocument.id}/ai-proposals`,
        { operation: "continue", provider: "mock" },
      );
      expect(refused.statusCode, refused.body).toBe(503);
      expect(refused.headers["retry-after"]).toBe("5");
      expect(refused.json()).toEqual({
        error: {
          code: "OPERATION_CAPACITY_EXCEEDED",
          message: "Studio operation capacity is exhausted.",
          details: {
            scope: "project",
            limit: 1,
            in_flight: 1,
            project_id: saturatedProject.id,
            retry_after_seconds: 5,
          },
        },
      });

      const otherProject = await call(
        app,
        owner,
        "POST",
        `/api/projects/${availableProject.id}/documents/${availableDocument.id}/ai-proposals`,
        { operation: "continue", provider: "mock" },
      );
      expect(otherProject.statusCode, otherProject.body).toBe(200);
      expect(provider.factoryCalls()).toBe(2);

      provider.release();
      const completedReview = await blockingReview;
      blockingReview = undefined;
      expect(completedReview.statusCode, completedReview.body).toBe(201);

      const recovered = await call(
        app,
        owner,
        "POST",
        `/api/projects/${saturatedProject.id}/documents/${saturatedDocument.id}/ai-proposals`,
        { operation: "continue", provider: "mock" },
      );
      expect(recovered.statusCode, recovered.body).toBe(200);
    } finally {
      provider.release();
      await blockingReview?.catch(() => undefined);
      await app.close();
    }
  });
});
