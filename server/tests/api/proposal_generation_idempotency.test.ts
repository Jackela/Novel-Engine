import type { FastifyInstance } from "fastify";
import { describe, expect, it, vi } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import {
  jobEvents,
  jobs,
  usageEvents,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, call, type JobPayload, ownerJar, seedProject } from "./studio_helpers.js";

/**
 * DR-027: both proposal-generation routes accept an optional `Idempotency-Key`
 * and replay the stored job for a duplicate — one job row, one usage event,
 * no second provider call — backed by the jobs table's partial unique index
 * (not a process-local guard). The retry route's own durable key and the
 * keyless behavior stay untouched.
 */

interface Evidence {
  readonly jobs: number;
  readonly events: number;
  readonly usage: number;
}

function evidence(app: FastifyInstance): Evidence {
  const database = app.studioDb?.db;
  if (database === undefined) throw new Error("Expected the real Studio database.");
  return {
    jobs: database.select().from(jobs).all().length,
    events: database.select().from(jobEvents).all().length,
    usage: database.select().from(usageEvents).all().length,
  };
}

/** Count provider executions; the sync and streaming paths share one counter. */
function countingProvider(): {
  readonly factory: TextGenerationProviderFactory;
  calls: () => number;
} {
  let calls = 0;
  return {
    calls: () => calls,
    factory: (provider) => ({
      async generateStructured(task) {
        calls += 1;
        return {
          step: task.step,
          provider,
          model: "idempotency-model",
          rawText: JSON.stringify({ chapter_markdown: validProposalProse }),
          content: { chapter_markdown: validProposalProse },
          promptTokens: 3,
          completionTokens: 5,
        };
      },
      async *generateStructuredStreaming(_task, options) {
        calls += 1;
        yield validProposalProse;
        options?.onOutcome?.({ model: "idempotency-model", promptTokens: 3, completionTokens: 5 });
      },
    }),
  };
}

/** Stream accumulated text then fail, landing the DR-006 partial failure frame. */
function failingStreamProvider(): {
  readonly factory: TextGenerationProviderFactory;
  calls: () => number;
} {
  let calls = 0;
  const factory: TextGenerationProviderFactory = (_provider) => ({
    async generateStructured() {
      calls += 1;
      throw new TextGenerationProviderError("the sync path must not run for the stream endpoint");
    },
    async *generateStructuredStreaming() {
      calls += 1;
      yield "A quiet beginning ";
      throw new TextGenerationProviderError("stream exploded");
    },
  });
  return { factory, calls: () => calls };
}

/** Split a buffered SSE response body into its JSON frames. */
function parseFrames(raw: string): ProposalStreamFrame[] {
  return raw
    .split("\n\n")
    .filter((part) => part !== "")
    .map((part) => JSON.parse(part.slice("data: ".length)) as ProposalStreamFrame);
}

function generationUrl(projectId: string, documentId: string): string {
  return `/api/projects/${projectId}/documents/${documentId}/ai-proposals`;
}

function firstDocumentId(project: { documents: Array<{ id: string }> }): string {
  const document = project.documents.at(0);
  if (document === undefined) throw new Error("expected a seeded document");
  return document.id;
}

describe("proposal generation request-key idempotency (DR-027)", () => {
  it("replays one stored job for a duplicate sync key without a second provider call", async () => {
    const provider = countingProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Duplicate sync generation");
      const url = generationUrl(project.id, firstDocumentId(project));
      const body = { operation: "continue", instruction: "One logical submit.", provider: "mock" };
      const headers = { "idempotency-key": "sync-generation-key-0001" };

      const first = await call(app, owner, "POST", url, body, headers);
      const second = await call(app, owner, "POST", url, body, headers);

      expect(first.statusCode, first.body).toBe(200);
      expect(second.statusCode, second.body).toBe(200);
      expect(second.body).toBe(first.body);
      expect(second.json<JobPayload>().status).toBe("completed");
      // One generation, one usage event: the duplicate replayed the stored row.
      expect(provider.calls()).toBe(1);
      expect(evidence(app)).toEqual({ jobs: 1, events: 1, usage: 1 });
    } finally {
      await app.close();
    }
  });

  it("replays the stored done frame for a duplicate stream key", async () => {
    const provider = countingProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Duplicate stream generation");
      const url = `${generationUrl(project.id, firstDocumentId(project))}/stream`;
      const body = { operation: "continue", instruction: "One logical stream.", provider: "mock" };
      const headers = { "idempotency-key": "stream-generation-key-0001" };

      const first = await call(app, owner, "POST", url, body, headers);
      const second = await call(app, owner, "POST", url, body, headers);

      expect(first.statusCode, first.body).toBe(200);
      expect(second.statusCode, second.body).toBe(200);
      const done = parseFrames(first.body).at(-1);
      if (done === undefined || done.type !== "done") {
        throw new Error(`expected a done frame: ${first.body}`);
      }
      // The replay carries exactly the stored terminal outcome, no new protocol.
      expect(parseFrames(second.body)).toEqual([done]);
      expect(provider.calls()).toBe(1);
      expect(evidence(app)).toEqual({ jobs: 1, events: 1, usage: 1 });
    } finally {
      await app.close();
    }
  });

  it("replays the stored failure frame for a duplicate stream key", async () => {
    const provider = failingStreamProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Duplicate failed stream");
      const url = `${generationUrl(project.id, firstDocumentId(project))}/stream`;
      const body = { operation: "continue", instruction: "Fail once.", provider: "mock" };
      const headers = { "idempotency-key": "failed-stream-key-000001" };

      const first = await call(app, owner, "POST", url, body, headers);
      const second = await call(app, owner, "POST", url, body, headers);

      const firstFrames = parseFrames(first.body);
      expect(firstFrames.map((frame) => frame.type)).toEqual(["delta", "error"]);
      const failure = firstFrames.at(-1);
      if (failure === undefined || failure.type !== "error") {
        throw new Error(`expected an error frame: ${first.body}`);
      }
      expect(parseFrames(second.body)).toEqual([failure]);
      expect(provider.calls()).toBe(1);
      // DR-028: the failed stream attempt keeps one zero-token unreported row;
      // the duplicate's replay adds none.
      expect(evidence(app)).toEqual({ jobs: 1, events: 1, usage: 1 });
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("Expected the real Studio database.");
      expect(database.select().from(usageEvents).all()).toMatchObject([
        {
          outcome: "failed",
          token_source: "unreported",
          prompt_tokens: 0,
          completion_tokens: 0,
        },
      ]);
    } finally {
      await app.close();
    }
  });

  it("rejoins the winner when a same-key lookup/insert race interleaves", async () => {
    const provider = countingProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Same-key landing race");
      const url = generationUrl(project.id, firstDocumentId(project));
      const body = { operation: "continue", instruction: "Race the landing.", provider: "mock" };
      const headers = { "idempotency-key": "racing-generation-key-01" };
      const first = await call(app, owner, "POST", url, body, headers);
      expect(first.statusCode, first.body).toBe(200);
      expect(evidence(app)).toEqual({ jobs: 1, events: 1, usage: 1 });

      // Model the lookup/insert interleave deterministically: the duplicate's
      // lookup misses, it runs its own provider, and the landing claim must
      // rejoin the existing row through the partial unique index instead of
      // inserting a second job or a second usage event.
      vi.spyOn(JobStorePart.prototype, "findJobRequest").mockReturnValueOnce(null);
      const duplicate = await call(app, owner, "POST", url, body, headers);

      expect(duplicate.statusCode, duplicate.body).toBe(200);
      expect(duplicate.body).toBe(first.body);
      expect(provider.calls()).toBe(2);
      expect(evidence(app)).toEqual({ jobs: 1, events: 1, usage: 1 });
    } finally {
      vi.restoreAllMocks();
      await app.close();
    }
  });

  it("keeps different keys independent within one project", async () => {
    const provider = countingProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Distinct generation keys");
      const url = generationUrl(project.id, firstDocumentId(project));
      const body = { operation: "continue", instruction: "Two intents.", provider: "mock" };

      const first = await call(app, owner, "POST", url, body, {
        "idempotency-key": "distinct-generation-key-1",
      });
      const second = await call(app, owner, "POST", url, body, {
        "idempotency-key": "distinct-generation-key-2",
      });

      expect(first.statusCode, first.body).toBe(200);
      expect(second.statusCode, second.body).toBe(200);
      expect(first.json<JobPayload>().id).not.toBe(second.json<JobPayload>().id);
      expect(provider.calls()).toBe(2);
      expect(evidence(app)).toEqual({ jobs: 2, events: 2, usage: 2 });
    } finally {
      await app.close();
    }
  });

  it("scopes one key per project across the generation surface", async () => {
    const provider = countingProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const first = await seedProject(app, owner, "Scoped key A");
      const second = await seedProject(app, owner, "Scoped key B");
      const body = {
        operation: "continue",
        instruction: "Shared key, two projects.",
        provider: "mock",
      };
      const headers = { "idempotency-key": "shared-generation-key-0001" };

      const firstResponse = await call(
        app,
        owner,
        "POST",
        generationUrl(first.id, firstDocumentId(first)),
        body,
        headers,
      );
      const secondResponse = await call(
        app,
        owner,
        "POST",
        generationUrl(second.id, firstDocumentId(second)),
        body,
        headers,
      );

      expect(firstResponse.statusCode, firstResponse.body).toBe(200);
      expect(secondResponse.statusCode, secondResponse.body).toBe(200);
      const firstJob = firstResponse.json<JobPayload>();
      const secondJob = secondResponse.json<JobPayload>();
      expect(firstJob.id).not.toBe(secondJob.id);
      expect(secondJob.project_id).toBe(second.id);
      expect(provider.calls()).toBe(2);
      expect(evidence(app)).toEqual({ jobs: 2, events: 2, usage: 2 });
    } finally {
      await app.close();
    }
  });

  it("keeps keyless generation unchanged and validates a present key", async () => {
    const provider = countingProvider();
    const { app } = await buildStudioApp(undefined, { textProviderFactory: provider.factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Keyless generation");
      const url = generationUrl(project.id, firstDocumentId(project));
      const body = { operation: "continue", instruction: "No key.", provider: "mock" };

      const first = await call(app, owner, "POST", url, body);
      const second = await call(app, owner, "POST", url, body);

      expect(first.statusCode, first.body).toBe(200);
      expect(second.statusCode, second.body).toBe(200);
      expect(first.json<JobPayload>().id).not.toBe(second.json<JobPayload>().id);
      expect(evidence(app)).toEqual({ jobs: 2, events: 2, usage: 2 });

      const before = evidence(app);
      const invalid = await call(app, owner, "POST", url, body, { "idempotency-key": "short" });
      expect(invalid.statusCode, invalid.body).toBe(422);
      expect(invalid.json().error.code).toBe("VALIDATION_ERROR");
      expect(evidence(app)).toEqual(before);
      expect(provider.calls()).toBe(2);
    } finally {
      await app.close();
    }
  });
});
