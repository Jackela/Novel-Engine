import { afterEach, describe, expect, it, vi } from "vitest";

import type { TextGenerationProvider } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { createTextGenerationProvider } from "../../src/contexts/ai/infrastructure/providers/text_provider_factory.js";
import { chapterTask, testCredential } from "./text_generation.test-helpers.js";

/** An SSE body that never enqueues and never closes. */
function hangingStream(): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({ start() {} });
}

/** An SSE body that emits the given events, then stalls without closing. */
function stallingStream(events: string[]): ReadableStream<Uint8Array> {
  const body = events.map((event) => `data: ${event}\n\n`).join("");
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body));
    },
  });
}

function sseTransport(body: ReadableStream<Uint8Array>): ProviderTransport {
  return () =>
    Promise.resolve(
      new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } }),
    );
}

async function consume(provider: TextGenerationProvider): Promise<string[]> {
  const { generateStructuredStreaming } = provider;
  if (generateStructuredStreaming === undefined) {
    throw new Error("streaming budgets require a streaming-capable provider");
  }
  const deltas: string[] = [];
  for await (const delta of generateStructuredStreaming.call(
    provider,
    chapterTask("chapter_draft"),
  )) {
    deltas.push(delta);
  }
  return deltas;
}

describe("server-configured stream silence budgets (#443)", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("applies the configured first-byte budget to the OpenAI-compatible stream", async () => {
    vi.useFakeTimers();
    const provider = createTextGenerationProvider({
      provider: "openai_compatible",
      apiKeys: { openaiCompatible: testCredential("openai-compatible") },
      adapterOptions: {
        openaiCompatible: {
          firstByteTimeoutMs: 5_000,
          idleTimeoutMs: 10_000,
          transport: sseTransport(hangingStream()),
          // One attempt: this case pins the budget, not the retry policy.
          retry: { maxAttempts: 1, delayMs: 0, sleep: async () => undefined },
        },
      },
    });
    const pending = consume(provider);
    const settled = expect(pending).rejects.toThrow(/first-byte timeout after 5s/);
    await vi.advanceTimersByTimeAsync(4_999);
    await vi.advanceTimersByTimeAsync(1);
    await settled;
  });

  it("applies the configured idle budget to the DashScope stream mid-flight", async () => {
    vi.useFakeTimers();
    const provider = createTextGenerationProvider({
      provider: "dashscope",
      apiKeys: { dashscope: testCredential("dashscope") },
      adapterOptions: {
        dashscope: {
          firstByteTimeoutMs: 5_000,
          idleTimeoutMs: 3_000,
          transport: sseTransport(
            stallingStream([JSON.stringify({ output: { choices: [{ delta: { text: "bit" } }] } })]),
          ),
        },
      },
    });
    const pending = consume(provider);
    const settled = expect(pending).rejects.toThrow(/idle timeout after 3s of silence/);
    await vi.advanceTimersByTimeAsync(2_999);
    await vi.advanceTimersByTimeAsync(1);
    await settled;
  });

  it("falls back to the engine defaults when no adapter budgets are configured", async () => {
    vi.useFakeTimers();
    const provider = createTextGenerationProvider({
      provider: "openai_compatible",
      apiKeys: { openaiCompatible: testCredential("openai-compatible") },
      adapterOptions: {
        openaiCompatible: {
          transport: sseTransport(hangingStream()),
          // One attempt: this case pins the default budget, not the retry policy.
          retry: { maxAttempts: 1, delayMs: 0, sleep: async () => undefined },
        },
      },
    });
    const pending = consume(provider);
    const settled = expect(pending).rejects.toThrow(/first-byte timeout after 30s/);
    await vi.advanceTimersByTimeAsync(30_000);
    await settled;
  });
});
