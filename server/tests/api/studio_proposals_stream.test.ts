import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { isProposalMarkdownProse } from "../../src/contexts/studio/application/sanitization.js";
import { jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { cookieHeader, loginOwner } from "./auth_helpers.js";
import {
  buildStudioApp,
  call,
  type DocumentPayload,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const STREAM_PATH = (projectId: string, documentId: string) =>
  `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;

/** Split a buffered SSE response body into its JSON frames. */
function parseFrames(raw: string): ProposalStreamFrame[] {
  expect(raw.endsWith("\n\n")).toBe(true);
  return raw
    .split("\n\n")
    .filter((part) => part !== "")
    .map((part) => {
      expect(part.startsWith("data: ")).toBe(true);
      return JSON.parse(part.slice("data: ".length)) as ProposalStreamFrame;
    });
}

/** A factory whose provider streams from the given async script. */
function streamingFactory(
  script: (
    task: TextGenerationTask,
    signal: AbortSignal | undefined,
  ) => AsyncGenerator<string, void, void>,
): { factory: TextGenerationProviderFactory; tasks: TextGenerationTask[] } {
  const tasks: TextGenerationTask[] = [];
  const factory: TextGenerationProviderFactory = (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async () => {
        throw new Error("the synchronous path must not run for the stream endpoint");
      },
      async *generateStructuredStreaming(task, options) {
        tasks.push(task);
        yield* script(task, options?.signal);
      },
    };
    void provider;
    return impl;
  };
  return { factory, tasks };
}

describe("proposal stream endpoint (#308)", () => {
  it("streams deterministic deltas then lands the same completed job as sync", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Stream");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");
      const usageBefore = database.select().from(usageEvents).all().length;

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        instruction: "Polish the crossing.",
        provider: "mock",
      });

      expect(response.statusCode, response.body).toBe(200);
      expect(response.headers["content-type"]).toBe("text/event-stream; charset=utf-8");
      const frames = parseFrames(response.body);
      const done = frames.at(-1);
      if (done === undefined || done.type !== "done") {
        throw new Error(`stream must end with a done frame: ${response.body}`);
      }
      const deltas = frames.filter(
        (frame): frame is Extract<ProposalStreamFrame, { type: "delta" }> => frame.type === "delta",
      );
      expect(deltas.length).toBeGreaterThan(1);
      const joined = deltas.map((frame) => frame.text).join("");
      // #440: `done.job` is now the narrowed job-payload SSOT type, so the
      // cast routes through `unknown`; every assertion below is unchanged.
      const job = done.job as unknown as {
        status: string;
        kind: string;
        provider: string;
        model: string;
        request: Record<string, unknown>;
        result: { proposal_markdown: string };
        events: Array<{ status: string }>;
      };
      expect(job.status).toBe("completed");
      expect(job.kind).toBe("proposal");
      expect(job.provider).toBe("mock");
      expect(job.model).toBe("deterministic-story-v1");
      expect(job.request).toEqual({
        operation: "continue",
        instruction: "Polish the crossing.",
        base_revision_id: document.current_revision_id,
      });
      expect(job.result.proposal_markdown).toBe(joined);
      expect(isProposalMarkdownProse(joined)).toBe(true);
      expect(job.events.map((event: { status: string }) => event.status)).toEqual(["completed"]);
      expect(database.select().from(usageEvents).all()).toHaveLength(usageBefore + 1);
    } finally {
      await app.close();
    }
  });

  it("records a failed job and emits an error frame when the provider fails mid-stream", async () => {
    const script = async function* () {
      yield "A quiet beginning ";
      throw new TextGenerationProviderError("stream exploded");
    };
    const overrides = streamingFactory(script);
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: overrides.factory,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Midstream failure");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");
      const usageBefore = database.select().from(usageEvents).all().length;

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "mock",
      });

      expect(response.statusCode).toBe(200);
      const frames = parseFrames(response.body);
      expect(frames.map((frame) => frame.type)).toEqual(["delta", "error"]);
      const error = frames[1];
      if (error === undefined || error.type !== "error") throw new Error("expected error frame");
      expect(error.error).toEqual({ code: "PROVIDER_FAILED", message: "stream exploded" });

      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      const row = rows[0] as { status: string; error: string; result_json: string };
      expect(row.status).toBe("failed");
      expect(row.error).toBe("stream exploded");
      expect(JSON.parse(row.result_json)).toMatchObject({ proposal_markdown: "" });
      expect(database.select().from(usageEvents).all()).toHaveLength(usageBefore);
    } finally {
      await app.close();
    }
  });

  it("fails the job without fabricated text when the accumulated stream is not prose", async () => {
    const script = async function* () {
      yield '{"chapter_markdown":';
      yield ' "no prose"}';
    };
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: streamingFactory(script).factory,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "JSON stream");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "mock",
      });
      const frames = parseFrames(response.body);
      expect(frames.at(-1)?.type).toBe("error");
      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      const row = rows[0] as { status: string; error: string };
      expect(row.status).toBe("failed");
      expect(row.error).toMatch(/not valid story prose/);
      expect(database.select().from(usageEvents).all()).toHaveLength(0);
    } finally {
      await app.close();
    }
  });

  it("lands a failed job when the factory itself raises a known provider failure", async () => {
    const knownFailure = new TextGenerationProviderError(
      "OpenAI-compatible API base must be an absolute URL",
    );
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: () => {
        throw knownFailure;
      },
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Factory failure");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "openai_compatible",
      });
      expect(response.statusCode).toBe(200);
      const frames = parseFrames(response.body);
      expect(frames.map((frame) => frame.type)).toEqual(["error"]);
      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      expect((rows[0] as { status: string }).status).toBe("failed");
    } finally {
      await app.close();
    }
  });

  it("answers unconfigured providers with the envelope error before any stream", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Unconfigured");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "dashscope",
      });
      expect(response.statusCode).toBe(422);
      expect(response.headers["content-type"]).toContain("application/json");
      expect(response.json()).toMatchObject({
        error: { code: "INVALID_OPERATION" },
      });
      expect(response.json().error.message).toMatch(/does not support streaming/);
      expect(database.select().from(jobs).all()).toHaveLength(0);
    } finally {
      await app.close();
    }
  });

  it("rejects anonymous, CSRF-less, and unknown-document streams before any job", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Guards");
      const document = project.documents[0] as DocumentPayload;
      const body = { operation: "continue", provider: "mock" };

      const anonymous = await app.inject({
        method: "POST",
        url: STREAM_PATH(project.id, document.id),
        payload: body,
      });
      expect(anonymous.statusCode).toBe(401);

      const csrfLess = await app.inject({
        method: "POST",
        url: STREAM_PATH(project.id, document.id),
        payload: body,
        headers: { cookie: cookieHeader(jar) },
      });
      expect(csrfLess.statusCode).toBe(403);

      const logged = await loginOwner(app);
      void logged;
      const missing = await call(app, jar, "POST", STREAM_PATH(project.id, "doc-missing"), body);
      expect(missing.statusCode).toBe(404);
      expect(missing.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
