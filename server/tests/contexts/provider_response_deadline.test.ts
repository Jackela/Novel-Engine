import { afterEach, describe, expect, it, vi } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { fixtureApiKey } from "../credential_fixtures.js";

function reviewTask(): TextGenerationTask {
  return {
    step: "editorial_review",
    systemPrompt: "system prompt",
    userPrompt: "review this chapter",
    responseSchema: { summary: { type: "string" } },
    metadata: {},
  };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("synchronous provider response deadline", () => {
  it("sanitizes a synchronous TypeError thrown at the transport boundary", async () => {
    const diagnostic = "transport-secret";
    const provider = new OpenAICompatibleTextProvider({
      apiKey: fixtureApiKey("sk-openai", "sync-transport-failure"),
      retry: { maxAttempts: 1, delayMs: 0, sleep: async () => {} },
      transport: () => {
        throw new TypeError(`failed near ${diagnostic}`);
      },
    });
    const landed = await provider.generateStructured(reviewTask()).catch((error: unknown) => error);

    expect((landed as Error).message).toMatch(/transport request failed/);
    expect((landed as Error).message).not.toContain(diagnostic);
  });

  it("keeps the dispatch deadline active through the complete response body", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | undefined;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("{"));
      },
    });
    const transport: ProviderTransport = (_url, init) => {
      signal = init?.signal ?? undefined;
      return Promise.resolve(new Response(body, { status: 200 }));
    };
    const provider = new OpenAICompatibleTextProvider({
      apiKey: fixtureApiKey("sk-openai", "sync-body-deadline"),
      timeoutSeconds: 1,
      retry: { maxAttempts: 1, delayMs: 0, sleep: async () => {} },
      transport,
    });
    const generation = provider.generateStructured(reviewTask());
    // DR-025: an editorial review never runs on the 1s base — the long-form
    // floor raises it to 180s — so the assertion pins the floored deadline and
    // the body still stays under it for the complete read.
    const settled = expect(generation).rejects.toThrow(/timed out after 180s/);

    await vi.advanceTimersByTimeAsync(179_999);
    expect(signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(signal?.aborted).toBe(true);
    await settled;
  });
});
