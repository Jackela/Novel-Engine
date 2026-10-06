import { describe, expect, it } from "vitest";

import type { TextGenerationStreamOutcome } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import type { StreamingTextRequest } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { streamProviderTextDeltas } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";

/**
 * DR-006: the SSE engine retries a transient failure only while the upstream
 * has not produced any frame yet — a retry after that point would replay an
 * incremental unwrapper that already consumed fragments.
 */

function streamRequest(overrides: Partial<StreamingTextRequest> = {}): StreamingTextRequest {
  return {
    url: "https://provider.example/v1/chat/completions",
    headers: {},
    body: "{}",
    signal: undefined,
    context: "test provider stream",
    timeoutSeconds: 30,
    model: "test-model",
    retry: { maxAttempts: 3, delayMs: 0, sleep: async () => {} },
    ...overrides,
  };
}

function extractDelta(chunk: Record<string, unknown>): string | undefined {
  const content = chunk.content;
  return typeof content === "string" && content !== "" ? content : undefined;
}

function extractUsage(): readonly [number | null, number | null] {
  return [null, null];
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

/** A transport whose script repeats its final entry and counts every call. */
function scriptedTransport(script: Response[]): {
  transport: ProviderTransport;
  callCount: () => number;
} {
  let calls = 0;
  return {
    transport: () => {
      const answer = script[Math.min(calls, script.length - 1)];
      calls += 1;
      if (answer === undefined) throw new Error("Expected a scripted response.");
      return Promise.resolve(answer);
    },
    callCount: () => calls,
  };
}

async function collect(
  request: StreamingTextRequest,
  transport: ProviderTransport,
  onOutcome?: (outcome: TextGenerationStreamOutcome) => void,
): Promise<string[]> {
  const deltas: string[] = [];
  for await (const delta of streamProviderTextDeltas(
    request,
    transport,
    extractDelta,
    extractUsage,
    {
      onOutcome,
    },
  )) {
    deltas.push(delta);
  }
  return deltas;
}

describe("streamProviderTextDeltas pre-delta retry (DR-006)", () => {
  it("retries a transient failure before any frame and streams the successful attempt", async () => {
    const { transport, callCount } = scriptedTransport([
      new Response("throttled", { status: 429, headers: { "content-type": "text/plain" } }),
      sseResponse([
        JSON.stringify({ content: "recovered " }),
        JSON.stringify({ content: "text" }),
        "[DONE]",
      ]),
    ]);
    let outcome: TextGenerationStreamOutcome | undefined;

    const deltas = await collect(streamRequest(), transport, (reported) => {
      outcome = reported;
    });

    expect(deltas).toEqual(["recovered ", "text"]);
    expect(callCount()).toBe(2);
    expect(outcome).toEqual({ model: "test-model", promptTokens: null, completionTokens: null });
  });

  it("exhausts the attempt budget when every attempt fails before any frame", async () => {
    const { transport, callCount } = scriptedTransport([
      new Response("busy", { status: 503, headers: { "content-type": "text/plain" } }),
    ]);

    await expect(collect(streamRequest(), transport)).rejects.toThrow(/HTTP 503/);
    expect(callCount()).toBe(3);
  });

  it("does not retry a failure after the first delta reached the consumer", async () => {
    const stalling = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(`data: ${JSON.stringify({ content: "first" })}\n\n`),
        );
      },
    });
    const { transport, callCount } = scriptedTransport([new Response(stalling, { status: 200 })]);
    const stream = streamProviderTextDeltas(
      streamRequest({ firstByteTimeoutMs: 5_000, idleTimeoutMs: 20 }),
      transport,
      extractDelta,
      extractUsage,
    );

    await expect(stream.next()).resolves.toMatchObject({ done: false, value: "first" });
    await expect(stream.next()).rejects.toMatchObject({
      name: "ProviderTransportError",
      retryable: true,
    });
    expect(callCount()).toBe(1);
  });
});
