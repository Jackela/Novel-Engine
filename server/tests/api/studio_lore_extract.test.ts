import { describe, expect, it } from "vitest";

import {
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextGenerationResult,
  type TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS } from "../../src/contexts/studio/application/lore_extract_task.js";
import { anonymousCall, buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

/**
 * The lorebook initialization wizard's extraction route (#614, #652 T2):
 * one submitted segment executes synchronously as its own terminal
 * `lore-extract` Job, capacity refusals answer with the stable generation
 * envelope before any job or usage evidence, and provider failures land as
 * failed jobs without upstream-body exposure.
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

/** A provider factory whose handler is swappable between requests. */
function scriptedFactory(
  handler: (task: TextGenerationTask) => Promise<TextGenerationResult>,
): TextGenerationProviderFactory {
  return () => ({
    async generateStructured(task) {
      return handler(task);
    },
  });
}

const SEGMENT_CANDIDATES = [
  {
    kind: "character",
    title: "Mira",
    aliases: ["The Clerk"],
    summary: "Keeps the ledger for the station.",
  },
];

describe("lorebook wizard extraction route (#614)", () => {
  it("answers 401 unauthenticated and 404 for an unknown project", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      await seedProject(app, jar, "Scoped");

      const anonymous = await anonymousCall(app, "POST", "/api/projects/p-1/lore-extractions", {
        segment: "text",
      });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const unknown = await call(
        app,
        jar,
        "POST",
        "/api/projects/00000000-0000-0000-0000-000000000000/lore-extractions",
        { segment: "text" },
      );
      expect(unknown.statusCode, unknown.body).toBe(404);
      expect(unknown.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });

  it("returns the terminal lore-extract job with its candidate set and one usage event", async () => {
    const tasks: TextGenerationTask[] = [];
    const factory = scriptedFactory(async (task) => {
      tasks.push(task);
      return candidateResult(SEGMENT_CANDIDATES);
    });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Wizard scope");

      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/lore-extractions`,
        {
          segment: "Mira keeps the ledger for the station",
        },
      );
      expect(response.statusCode, response.body).toBe(200);
      const job = response.json();
      expect(job).toMatchObject({
        kind: "lore-extract",
        operation: "extract",
        status: "completed",
        document_id: null,
        provider: "mock",
        model: "scripted-model",
        retry_of_job_id: null,
      });
      expect(job.result).toEqual({ candidates: SEGMENT_CANDIDATES });
      expect(job.events.map((event: { status: string }) => event.status)).toEqual(["completed"]);

      // The wizard surface is the jobs surface: the audit listing shows the
      // new kind, and the extraction accounts exactly one usage request.
      const jobs = await call(app, jar, "GET", `/api/projects/${project.id}/jobs`);
      expect(jobs.json().jobs[0]).toMatchObject({ kind: "lore-extract", operation: "extract" });
      const usage = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(usage.json().request_count).toBe(1);
      expect(tasks).toHaveLength(1);
      expect(tasks[0]).toMatchObject({ step: "lore_extract" });
    } finally {
      await app.close();
    }
  });

  it("lands a provider failure as a failed job without usage or body exposure", async () => {
    const factory = scriptedFactory(async () => {
      throw new TextGenerationProviderError("provider transport failed");
    });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Wizard failure");

      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/lore-extractions`,
        {
          segment: "the flood market keeps its bargains",
        },
      );
      expect(response.statusCode, response.body).toBe(200);
      const job = response.json();
      expect(job).toMatchObject({ kind: "lore-extract", status: "failed" });
      expect(job.error).toBe("provider transport failed");
      expect(job.result).toEqual({ candidates: [] });

      const usage = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(usage.json().request_count).toBe(0);
    } finally {
      await app.close();
    }
  });

  it("refuses an over-cap segment with the bounded capacity envelope before any evidence", async () => {
    let providerCalls = 0;
    const factory = scriptedFactory(async () => {
      providerCalls += 1;
      return candidateResult([]);
    });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Wizard capacity");

      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/lore-extractions`,
        {
          segment: "a".repeat(MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS + 1),
        },
      );
      expect(response.statusCode, response.body).toBe(422);
      expect(response.json().error).toEqual({
        code: "GENERATION_CAPACITY_EXCEEDED",
        message: "Generation capacity exceeded.",
        details: {
          resource: "lore_extract_segment",
          limit: MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS,
          observed: MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS + 1,
        },
      });
      expect(providerCalls).toBe(0);
      const jobs = await call(app, jar, "GET", `/api/projects/${project.id}/jobs`);
      expect(jobs.json().jobs).toHaveLength(0);
      const usage = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(usage.json().request_count).toBe(0);
    } finally {
      await app.close();
    }
  });

  it("answers the unified validation envelope for malformed bodies", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Wizard validation");

      // Unknown members are stripped by the platform's shared AJV config
      // (`removeAdditional`) exactly like every sibling route, so the
      // validation surface here covers the missing/empty/enum cases.
      for (const body of [{}, { segment: "" }, { segment: "text", provider: "not-a-provider" }]) {
        const response = await call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/lore-extractions`,
          body,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
      }

      const jobs = await call(app, jar, "GET", `/api/projects/${project.id}/jobs`);
      expect(jobs.json().jobs).toHaveLength(0);
    } finally {
      await app.close();
    }
  });
});
