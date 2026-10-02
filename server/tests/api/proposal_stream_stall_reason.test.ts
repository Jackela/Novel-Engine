import { describe, expect, it } from "vitest";
import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import type { StreamingTextRequest } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { streamProviderTextDeltas } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { jobs } from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  buildStudioApp,
  call,
  type DocumentPayload,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

/**
 * DR-026: a provider stream that goes silent mid-flight must end the proposal
 * stream with a diagnosable error - the stall phase and its real budget reach
 * the error frame and the failed job row, never a bare "the stream broke".
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

/** A factory whose provider streams from the given async script. */
function streamingFactory(
  script: (
    task: TextGenerationTask,
    signal: AbortSignal | undefined,
  ) => AsyncGenerator<string, void, void>,
): TextGenerationProviderFactory {
  return (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async () => {
        throw new Error("the synchronous path must not run for the stream endpoint");
      },
      async *generateStructuredStreaming(task, options) {
        yield* script(task, options?.signal);
      },
    };
    void provider;
    return impl;
  };
}

/** An SSE body that emits one frame and then goes silent without closing. */
function stallingBody(): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(
        new TextEncoder().encode(`data: ${JSON.stringify({ content: "A quiet beginning " })}\n\n`),
      );
    },
  });
}

/** A transport that answers every dispatch with the given SSE body. */
function sseTransport(body: ReadableStream<Uint8Array>): ProviderTransport {
  return () =>
    Promise.resolve(
      new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } }),
    );
}

describe("proposal stream stall diagnostics (#308, DR-026)", () => {
  it("fails the job with the stall reason when the provider stream goes silent mid-flight", async () => {
    const request: StreamingTextRequest = {
      url: "https://provider.example/v1/chat/completions",
      headers: {},
      body: "{}",
      signal: undefined,
      context: "Test provider stream",
      timeoutSeconds: 10,
      model: "stalling-model",
      firstByteTimeoutMs: 1_000,
      idleTimeoutMs: 1_000,
    };
    const script = async function* (_task: TextGenerationTask, signal: AbortSignal | undefined) {
      yield* streamProviderTextDeltas(
        { ...request, signal },
        sseTransport(stallingBody()),
        (chunk) => (typeof chunk.content === "string" ? chunk.content : undefined),
        () => [null, null],
      );
    };
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: streamingFactory(script),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Stalled stream");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "mock",
      });

      expect(response.statusCode).toBe(200);
      const frames = parseFrames(response.body);
      expect(frames.map((frame) => frame.type)).toEqual(["delta", "error"]);
      const error = frames[1];
      if (error === undefined || error.type !== "error") throw new Error("expected error frame");
      // The stall names its phase and real budget instead of a generic
      // connection failure, and the same reason lands in the job row.
      expect(error.error.code).toBe("PROVIDER_FAILED");
      expect(error.error.message).toMatch(/idle timeout after 1s of silence/);
      expect(error.error.message).not.toMatch(/timed out after 10s/);

      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      const row = rows[0] as { status: string; error: string; result_json: string };
      expect(row.status).toBe("failed");
      expect(row.error).toBe(error.error.message);
      expect(JSON.parse(row.result_json)).toMatchObject({ partial_markdown: "A quiet beginning" });
    } finally {
      await app.close();
    }
  });
});
