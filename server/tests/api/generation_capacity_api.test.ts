import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { documentRevisions } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { jobEvents, jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { seedRetryableProposal, studioDatabase } from "./job_test_helpers.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import {
  buildStudioApp,
  type CookieJar,
  call,
  type DocumentSummaryPayload,
  getProject,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

const PROMPT_LIMIT = 8_388_608;
const CAPACITY_ERROR = {
  code: "GENERATION_CAPACITY_EXCEEDED",
  message: "Generation capacity exceeded.",
  details: { resource: "prompt_bytes", limit: PROMPT_LIMIT, observed: PROMPT_LIMIT + 1 },
} as const;

function observedProviderFactory(): {
  factory: TextGenerationProviderFactory;
  constructions: () => number;
} {
  let constructions = 0;
  const factory: TextGenerationProviderFactory = (provider) => {
    constructions += 1;
    const result = {
      step: "chapter_draft",
      provider,
      model: "capacity-test-model",
      rawText: validProposalProse,
      content: { chapter_markdown: validProposalProse },
      promptTokens: 1,
      completionTokens: 1,
    } as const;
    const implementation: TextGenerationProvider = {
      generateStructured: async () => result,
      async *generateStructuredStreaming(_task, options) {
        yield validProposalProse;
        options?.onOutcome?.({ model: result.model, promptTokens: 1, completionTokens: 1 });
      },
    };
    return implementation;
  };
  return { factory, constructions: () => constructions };
}

async function seedOversizedGenerationContext(
  app: Parameters<typeof studioDatabase>[0],
  owner: CookieJar,
): Promise<{
  projectId: string;
  target: DocumentSummaryPayload;
  outline: DocumentSummaryPayload;
}> {
  const project = await seedProject(app, owner, "Generation capacity");
  const target = (await getProject(app, owner, project.id)).documents[0];
  if (target === undefined) throw new Error("expected seeded document");
  const outline = await seedDocument(app, owner, project.id, {
    kind: "outline",
    title: "Outline",
    content_markdown: "small",
  });
  const oversizedPart = "x".repeat(4_194_304);
  const database = studioDatabase(app);
  for (const revisionId of [target.current_revision_id, outline.current_revision_id]) {
    database
      .update(documentRevisions)
      .set({ contentMarkdown: oversizedPart })
      .where(eq(documentRevisions.id, revisionId))
      .run();
  }
  return { projectId: project.id, target, outline };
}

describe("generation capacity HTTP contract", () => {
  it("returns the same JSON 422 before provider work for fresh sync and pre-SSE requests", async () => {
    const provider = observedProviderFactory();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const fixture = await seedOversizedGenerationContext(app, owner);
      const database = studioDatabase(app);
      const revisionsBefore = database.select().from(documentRevisions).all().length;
      const request = { operation: "generate", provider: "mock" };
      const path = `/api/projects/${fixture.projectId}/documents/${fixture.target.id}/ai-proposals`;

      const sync = await call(app, owner, "POST", path, request);
      expect(sync.statusCode, sync.body).toBe(422);
      expect(sync.json().error).toEqual(CAPACITY_ERROR);
      expect(sync.headers["content-type"]).toContain("application/json");

      const stream = await call(app, owner, "POST", `${path}/stream`, request);
      expect(stream.statusCode, stream.body).toBe(422);
      expect(stream.body).toBe(sync.body);
      expect(stream.headers["content-type"]).toContain("application/json");
      expect(provider.constructions()).toBe(0);
      expect(database.select().from(jobs).all()).toEqual([]);
      expect(database.select().from(jobEvents).all()).toEqual([]);
      expect(database.select().from(usageEvents).all()).toEqual([]);
      expect(database.select().from(documentRevisions).all()).toHaveLength(revisionsBefore);
    } finally {
      await app.close();
    }
  });

  it("persists one closed failed retry outcome and replays its 422 by key", async () => {
    const provider = observedProviderFactory();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const fixture = await seedOversizedGenerationContext(app, owner);
      const sourceId = seedRetryableProposal(app, fixture.projectId, fixture.target.id);
      const database = studioDatabase(app);
      database
        .update(jobs)
        .set({
          operation: "generate",
          request_json: JSON.stringify({
            instruction: "",
            provider: "mock",
            base_revision_id: fixture.target.current_revision_id,
          }),
        })
        .where(eq(jobs.id, sourceId))
        .run();
      const url = `/api/projects/${fixture.projectId}/jobs/${sourceId}/retry`;
      const first = await retryJobRequest(app, owner, url, "generation-capacity-key-0001");

      expect(first.statusCode, first.body).toBe(422);
      expect(first.json().error).toEqual(CAPACITY_ERROR);
      expect(provider.constructions()).toBe(0);
      const retryRows = database
        .select()
        .from(jobs)
        .all()
        .filter((job) => job.id !== sourceId);
      expect(retryRows).toHaveLength(1);
      expect(retryRows[0]?.status).toBe("failed");
      expect(JSON.parse(retryRows[0]?.result_json ?? "{}")).toEqual({
        proposal_markdown: "",
        base_revision_id: fixture.target.current_revision_id,
        accepted_revision_id: null,
        capacity_error: { code: CAPACITY_ERROR.code, ...CAPACITY_ERROR.details },
      });
      const evidenceAfterFirst = database.select().from(jobEvents).all();
      expect(evidenceAfterFirst.map((event) => event.status)).toEqual(["running", "failed"]);
      expect(JSON.parse(evidenceAfterFirst[1]?.details_json ?? "{}")).toEqual({
        error: CAPACITY_ERROR.message,
        capacity_error: { code: CAPACITY_ERROR.code, ...CAPACITY_ERROR.details },
      });
      expect(database.select().from(usageEvents).all()).toEqual([]);

      const reduced = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${fixture.projectId}/documents/${fixture.outline.id}`,
        {
          content_markdown: "# Outline\n\nSmall again.",
          base_revision_id: fixture.outline.current_revision_id,
        },
      );
      expect(reduced.statusCode, reduced.body).toBe(200);
      const replay = await retryJobRequest(app, owner, url, "generation-capacity-key-0001");
      expect(replay.statusCode, replay.body).toBe(422);
      expect(replay.body).toBe(first.body);
      expect(provider.constructions()).toBe(0);
      expect(database.select().from(jobEvents).all()).toEqual(evidenceAfterFirst);

      const distinct = await retryJobRequest(app, owner, url, "generation-capacity-key-0002");
      expect(distinct.statusCode, distinct.body).toBe(200);
      expect(distinct.json().status).toBe("completed");
      expect(provider.constructions()).toBe(1);
      expect(database.select().from(jobs).all()).toHaveLength(3);
      expect(
        database
          .select()
          .from(jobEvents)
          .all()
          .map((event) => event.status),
      ).toEqual(["running", "failed", "running", "completed"]);
      expect(database.select().from(usageEvents).all()).toHaveLength(1);
    } finally {
      await app.close();
    }
  });

  it("publishes structured capacity alternatives without replacing validation errors", async () => {
    const app = await buildApp({ logger: false });
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      for (const path of [
        "/api/projects/{projectId}/documents/{documentId}/ai-proposals",
        "/api/projects/{projectId}/documents/{documentId}/ai-proposals/stream",
      ]) {
        const alternatives =
          document.paths[path].post.responses["422"].content["application/json"].schema.oneOf;
        const codes = alternatives.map(
          (schema: { properties: { error: { properties: { code: { enum: string[] } } } } }) =>
            schema.properties.error.properties.code.enum[0],
        );
        expect(codes).toEqual([
          "INVALID_OPERATION",
          "GENERATION_CAPACITY_EXCEEDED",
          "VALIDATION_ERROR",
        ]);
        const capacityDetails = alternatives[1].properties.error.properties.details.properties;
        expect(capacityDetails.limit).toEqual({ type: "integer", enum: [PROMPT_LIMIT] });
        expect(capacityDetails.observed).toEqual({
          type: "integer",
          enum: [PROMPT_LIMIT + 1],
        });
      }
      const retryAlternatives =
        document.paths["/api/projects/{projectId}/jobs/{jobId}/retry"].post.responses["422"]
          .content["application/json"].schema.oneOf;
      expect(
        retryAlternatives.map(
          (schema: { properties: { error: { properties: { code: { enum: string[] } } } } }) =>
            schema.properties.error.properties.code.enum[0],
        ),
      ).toEqual([
        "INVALID_OPERATION",
        "EXPORT_CAPACITY_EXCEEDED",
        "GENERATION_CAPACITY_EXCEEDED",
        "VALIDATION_ERROR",
      ]);
      const retryCapacityDetails =
        retryAlternatives[2].properties.error.properties.details.properties;
      expect(retryCapacityDetails.limit).toEqual({ type: "integer", enum: [PROMPT_LIMIT] });
      expect(retryCapacityDetails.observed).toEqual({
        type: "integer",
        enum: [PROMPT_LIMIT + 1],
      });
    } finally {
      await app.close();
    }
  });
});
