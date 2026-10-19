import { rm } from "node:fs/promises";
import { eq } from "drizzle-orm";
import { describe, expect, it, vi } from "vitest";

import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../../src/contexts/studio/application/generation_capacity.js";
import {
  documentRevisions,
  jobEvents,
  jobs,
  usageEvents,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { expectNoReviewEvidence, studioDatabase } from "./job_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const REFUSAL = {
  error: {
    code: "GENERATION_CAPACITY_EXCEEDED",
    message: "Generation capacity exceeded.",
    details: {
      resource: "prompt_bytes",
      limit: GENERATION_PROMPT_BYTE_LIMIT,
      observed: GENERATION_PROMPT_BYTE_LIMIT + 1,
    },
  },
};

function setContent(
  app: Parameters<typeof studioDatabase>[0],
  revisionId: string,
  contentMarkdown: string,
): void {
  studioDatabase(app)
    .update(documentRevisions)
    .set({ contentMarkdown })
    .where(eq(documentRevisions.id, revisionId))
    .run();
}

function oversizedContent(): string {
  return "界".repeat(Math.ceil(GENERATION_PROMPT_BYTE_LIMIT / 3));
}

describe("review prompt capacity admission", () => {
  it("publishes only prompt-byte refusals alongside Review validation errors", async () => {
    const { app, directory } = await buildStudioApp();
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const alternatives =
        document.paths["/api/projects/{projectId}/reviews"].post.responses["422"].content[
          "application/json"
        ].schema.oneOf;
      expect(alternatives).toHaveLength(2);
      expect(alternatives[0].properties.error.properties.code.enum).toEqual([
        "GENERATION_CAPACITY_EXCEEDED",
      ]);
      expect(alternatives[0].properties.error.properties.details).toEqual({
        type: "object",
        additionalProperties: false,
        properties: {
          resource: { type: "string", enum: ["prompt_bytes"] },
          limit: { type: "integer", enum: [GENERATION_PROMPT_BYTE_LIMIT] },
          observed: { type: "integer", enum: [GENERATION_PROMPT_BYTE_LIMIT + 1] },
        },
        required: ["resource", "limit", "observed"],
      });
      expect(alternatives[1].properties.error.properties.code.enum).toEqual(["VALIDATION_ERROR"]);
    } finally {
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("refuses oversized saved chapters before provider construction without durable evidence", async () => {
    let constructions = 0;
    const { app, directory } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: (provider) => {
        constructions += 1;
        return {
          generateStructured: async () => ({
            step: "editorial_review",
            provider,
            model: "unused",
            rawText: '{"findings":[]}',
            content: { findings: [] },
            promptTokens: null,
            completionTokens: null,
          }),
        };
      },
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Oversized review");
      const chapter = (await getProject(app, owner, project.id)).documents[0];
      if (chapter === undefined) throw new Error("Expected seed chapter.");
      setContent(app, chapter.current_revision_id, oversizedContent());
      const reviewed = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(reviewed.statusCode, reviewed.body).toBe(422);
      expect(reviewed.json()).toEqual(REFUSAL);
      expect(constructions).toBe(0);
      expectNoReviewEvidence(app);
      const db = studioDatabase(app);
      expect(db.select().from(jobs).all()).toEqual([]);
      expect(db.select().from(jobEvents).all()).toEqual([]);
      expect(db.select().from(usageEvents).all()).toEqual([]);
      expect(db.select().from(documentRevisions).all()).toHaveLength(1);
    } finally {
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("lands one failed capacity retry and replays the identical refusal without reading newer chapters", async () => {
    let constructions = 0;
    const sourceReads = vi.spyOn(ReviewStorePart.prototype, "readReviewSource");
    const { app, directory } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: (provider) => {
        constructions += 1;
        return {
          generateStructured: async () => {
            if (constructions === 1) throw new TextGenerationProviderError("Known review failure");
            return {
              step: "editorial_review",
              provider,
              model: "recovered-review",
              rawText: '{"findings":[]}',
              content: { findings: [] },
              promptTokens: null,
              completionTokens: null,
            };
          },
        };
      },
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Capacity retry");
      const chapter = (await getProject(app, owner, project.id)).documents[0];
      if (chapter === undefined) throw new Error("Expected seed chapter.");
      const failed = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(failed.json().status).toBe("failed");
      setContent(app, chapter.current_revision_id, oversizedContent());
      const path = `/api/projects/${project.id}/jobs/${failed.json().id}/retry`;
      const first = await retryJobRequest(app, owner, path, "review-capacity-key-0001");
      expect(first.statusCode, first.body).toBe(422);
      expect(first.json()).toEqual(REFUSAL);
      expect(constructions).toBe(1);
      expect(sourceReads).toHaveBeenCalledTimes(2);
      const db = studioDatabase(app);
      const before = {
        jobs: db.select().from(jobs).all(),
        events: db.select().from(jobEvents).all(),
      };
      expect(before.jobs).toHaveLength(2);
      expect(before.jobs[1]?.status).toBe("failed");
      expect(JSON.parse(before.jobs[1]?.result_json ?? "{}")).toEqual({
        capacity_error: { code: REFUSAL.error.code, ...REFUSAL.error.details },
      });
      expect(before.events.map((event) => event.status)).toEqual(["failed", "running", "failed"]);
      expectNoReviewEvidence(app);
      setContent(app, chapter.current_revision_id, "Saved small chapter again.");
      const replay = await retryJobRequest(app, owner, path, "review-capacity-key-0001");
      expect(replay.statusCode, replay.body).toBe(422);
      expect(replay.body).toBe(first.body);
      expect(sourceReads).toHaveBeenCalledTimes(2);
      expect(constructions).toBe(1);
      expect(db.select().from(jobs).all()).toEqual(before.jobs);
      expect(db.select().from(jobEvents).all()).toEqual(before.events);
      expect(db.select().from(usageEvents).all()).toEqual([]);
      expectNoReviewEvidence(app);
      const distinct = await retryJobRequest(app, owner, path, "review-capacity-key-0002");
      expect(distinct.statusCode, distinct.body).toBe(200);
      expect(distinct.json().status).toBe("completed");
      expect(sourceReads).toHaveBeenCalledTimes(3);
      expect(constructions).toBe(2);
    } finally {
      sourceReads.mockRestore();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
