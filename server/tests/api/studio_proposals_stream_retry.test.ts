import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { jobs, usageEvents } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  type DocumentPayload,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

/**
 * DR-006 acceptance (a): a streaming request whose provider fails before the
 * first delta is retried through the shared provider policy, lands exactly one
 * completed job, and records its usage exactly once.
 */

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

function sseResponse(events: string[]): Response {
  const body = events.map((event) => `data: ${event}\n\n`).join("");
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(body));
        controller.close();
      },
    }),
    { status: 200, headers: { "content-type": "text/event-stream" } },
  );
}

/** One json_object-mode completion split the way the provider relays it. */
function wrappedProseEvents(): string[] {
  return [
    JSON.stringify({ choices: [{ delta: { role: "assistant", content: "" } }] }),
    JSON.stringify({
      choices: [{ delta: { content: JSON.stringify({ chapter_markdown: validProposalProse }) } }],
    }),
    JSON.stringify({ choices: [], usage: { prompt_tokens: 21, completion_tokens: 34 } }),
    "[DONE]",
  ];
}

describe("proposal stream pre-delta recovery (DR-006)", () => {
  it("retries a failure before the first delta and records usage exactly once", async () => {
    const capture: Array<{ url: string; init: RequestInit }> = [];
    let calls = 0;
    const transport: ProviderTransport = (url, init) => {
      capture.push({ url: String(url), init: init ?? {} });
      calls += 1;
      if (calls === 1) {
        return Promise.resolve(
          new Response("throttled", { status: 429, headers: { "content-type": "text/plain" } }),
        );
      }
      return Promise.resolve(sseResponse(wrappedProseEvents()));
    };
    const textProviderFactory: TextGenerationProviderFactory = (_provider) =>
      new OpenAICompatibleTextProvider({
        apiKey: fixtureApiKey("openai", "stream-retry"),
        model: "stream-retry-model",
        retry: { maxAttempts: 3, delayMs: 0, sleep: async () => {} },
        transport,
      });
    const { app } = await buildStudioApp(undefined, { textProviderFactory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Stream retry");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "openai_compatible",
      });

      expect(response.statusCode, response.body).toBe(200);
      const frames = parseFrames(response.body);
      expect(frames.map((frame) => frame.type)).toEqual(["delta", "done"]);
      const done = frames.at(-1);
      if (done === undefined || done.type !== "done") {
        throw new Error(`stream must end with a done frame: ${response.body}`);
      }
      const job = done.job as unknown as {
        id: string;
        status: string;
        model: string;
        result: { proposal_markdown: string };
      };
      expect(job.status).toBe("completed");
      expect(job.model).toBe("stream-retry-model");
      expect(job.result.proposal_markdown).toBe(validProposalProse);
      // The 429 was abandoned before any frame; only the successful second
      // attempt is visible to the pipeline landing.
      expect(capture).toHaveLength(2);

      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      expect(rows[0]?.status).toBe("completed");
      const usage = database.select().from(usageEvents).all();
      expect(usage).toHaveLength(1);
      expect(usage[0]).toMatchObject({
        job_id: job.id,
        model: "stream-retry-model",
        prompt_tokens: 21,
        completion_tokens: 34,
      });
    } finally {
      await app.close();
    }
  });
});
