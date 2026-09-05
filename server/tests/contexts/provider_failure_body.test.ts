import { afterEach, describe, expect, it, vi } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { ProviderTransportError } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import {
  fixtureApiKey,
  hostileProviderFailureBody,
  PROVIDER_FAILURE_CANARIES,
} from "../credential_fixtures.js";

type ProviderName = "dashscope" | "openai_compatible";

const CASES = [
  {
    provider: "dashscope",
    label: "DashScope",
    apiKey: fixtureApiKey("dashscope", "failure-body", "credential"),
  },
  {
    provider: "openai_compatible",
    label: "OpenAI-compatible",
    apiKey: fixtureApiKey("openai", "failure-body", "credential"),
  },
] as const;

function chapterTask(): TextGenerationTask {
  return {
    step: "chapter_draft",
    systemPrompt: "system prompt",
    userPrompt: "Draft the chapter.",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: {},
  };
}

function unreadFailureResponse(
  status: number,
  body: string,
): {
  response: Response;
  text: ReturnType<typeof vi.fn>;
  cancel: ReturnType<typeof vi.fn>;
} {
  const cancel = vi.fn();
  const response = new Response(new ReadableStream<Uint8Array>({ cancel }), {
    status,
    headers: { "content-type": "text/html" },
  });
  const text = vi.spyOn(response, "text").mockResolvedValue(body);
  return { response, text, cancel };
}

function providerFor(
  provider: ProviderName,
  apiKey: string,
  transport: ProviderTransport,
): DashScopeTextProvider | OpenAICompatibleTextProvider {
  const retry = { maxAttempts: 1, delayMs: 0, sleep: async () => {} };
  return provider === "dashscope"
    ? new DashScopeTextProvider({ apiKey, retry, transport })
    : new OpenAICompatibleTextProvider({ apiKey, retry, transport });
}

async function collect(stream: AsyncIterable<string>): Promise<string[]> {
  const chunks: string[] = [];
  for await (const chunk of stream) chunks.push(chunk);
  return chunks;
}

function expectSafeFailure(failure: unknown, label: string, apiKey: string): void {
  expect(failure).toBeInstanceOf(ProviderTransportError);
  expect((failure as Error).message).toBe(
    `${label} generation failed for step 'chapter_draft': provider returned HTTP 401.`,
  );
  for (const marker of [apiKey, ...PROVIDER_FAILURE_CANARIES, "[REDACTED]"]) {
    expect((failure as Error).message).not.toContain(marker);
  }
}

afterEach(() => {
  vi.useRealTimers();
});

describe("Provider HTTP failure-body boundary", () => {
  it.each(CASES)(
    "does not read a $provider synchronous failure body",
    async ({ provider, label, apiKey }) => {
      const hostile = unreadFailureResponse(401, hostileProviderFailureBody(apiKey));
      const transport = vi.fn(async () => hostile.response);
      const failure = await providerFor(provider, apiKey, transport)
        .generateStructured(chapterTask())
        .catch((error: unknown) => error);

      expectSafeFailure(failure, label, apiKey);
      expect(hostile.text).not.toHaveBeenCalled();
      expect(hostile.cancel).toHaveBeenCalledTimes(1);
      expect(transport).toHaveBeenCalledTimes(1);
    },
  );

  it.each(CASES)(
    "does not read a $provider streaming failure body",
    async ({ provider, label, apiKey }) => {
      const hostile = unreadFailureResponse(401, hostileProviderFailureBody(apiKey));
      const transport = vi.fn(async () => hostile.response);
      const failure = await collect(
        providerFor(provider, apiKey, transport).generateStructuredStreaming(chapterTask()),
      ).catch((error: unknown) => error);

      expectSafeFailure(failure, label, apiKey);
      expect(hostile.text).not.toHaveBeenCalled();
      expect(hostile.cancel).toHaveBeenCalledTimes(1);
      expect(transport).toHaveBeenCalledTimes(1);
    },
  );

  it("keeps HTTP status authoritative when failure-body cancellation rejects", async () => {
    const sentinel = new Error("response cancellation sentinel");
    const response = new Response(
      new ReadableStream<Uint8Array>({
        cancel() {
          throw sentinel;
        },
      }),
      { status: 503 },
    );
    const transport = vi.fn(async () => response);
    const generation = new DashScopeTextProvider({
      apiKey: fixtureApiKey("dashscope", "cancel-sentinel"),
      retry: { maxAttempts: 1, delayMs: 0, sleep: async () => {} },
      transport,
    }).generateStructured(chapterTask());

    await expect(generation).rejects.toMatchObject({
      name: "ProviderTransportError",
      status: 503,
      message: "DashScope generation failed for step 'chapter_draft': provider returned HTTP 503.",
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it.each(["synchronous", "streaming"] as const)(
    "bounds a hung $mode failure-body cancellation without replacing HTTP status",
    async (mode) => {
      vi.useFakeTimers();
      let markCleanupStarted: (() => void) | undefined;
      const cleanupStarted = new Promise<void>((resolve) => {
        markCleanupStarted = resolve;
      });
      const response = new Response(
        new ReadableStream<Uint8Array>({
          cancel() {
            markCleanupStarted?.();
            return new Promise<void>(() => undefined);
          },
        }),
        { status: 401 },
      );
      const transport = vi.fn(async () => response);
      const provider = new DashScopeTextProvider({
        apiKey: fixtureApiKey("dashscope", `hung-${mode}-failure-body`),
        retry: { maxAttempts: 1, delayMs: 0, sleep: async () => {} },
        transport,
      });
      const operation =
        mode === "synchronous"
          ? provider.generateStructured(chapterTask())
          : collect(provider.generateStructuredStreaming(chapterTask()));
      const settled = expect(operation).rejects.toMatchObject({
        name: "ProviderTransportError",
        status: 401,
      });

      await cleanupStarted;
      await vi.advanceTimersByTimeAsync(1_000);

      await settled;
      expect(transport).toHaveBeenCalledTimes(1);
    },
  );
});
