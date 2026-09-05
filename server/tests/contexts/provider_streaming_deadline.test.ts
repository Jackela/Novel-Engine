import { afterEach, describe, expect, it, vi } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { fixtureApiKey } from "../credential_fixtures.js";

function chapterTask(step: "chapter_draft" | "chapter_revision"): TextGenerationTask {
  return {
    step,
    systemPrompt: "system prompt",
    userPrompt: "write a chapter",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2 },
  };
}

async function collect(stream: AsyncGenerator<string, void, void>): Promise<string[]> {
  const deltas: string[] = [];
  for await (const delta of stream) deltas.push(delta);
  return deltas;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("chapter streaming absolute timeout floor", () => {
  for (const providerName of ["OpenAI-compatible", "DashScope"] as const) {
    it(`grants ${providerName} chapter streams the effective 180-second floor`, async () => {
      vi.useFakeTimers();
      let signal: AbortSignal | undefined;
      const transport: ProviderTransport = (_url, init) => {
        signal = init?.signal ?? undefined;
        return new Promise<Response>(() => undefined);
      };
      const provider =
        providerName === "OpenAI-compatible"
          ? new OpenAICompatibleTextProvider({
              apiKey: fixtureApiKey("sk-openai", "stream-floor"),
              timeoutSeconds: 30,
              firstByteTimeoutMs: 240_000,
              idleTimeoutMs: 240_000,
              transport,
            })
          : new DashScopeTextProvider({
              apiKey: fixtureApiKey("sk-dashscope", "stream-floor"),
              timeoutSeconds: 30,
              firstByteTimeoutMs: 240_000,
              idleTimeoutMs: 240_000,
              transport,
            });
      const pending = collect(
        provider.generateStructuredStreaming(chapterTask("chapter_revision")),
      );
      const settled = expect(pending).rejects.toThrow(/timed out after 180s/);

      await vi.advanceTimersByTimeAsync(179_999);
      expect(signal?.aborted).toBe(false);
      await vi.advanceTimersByTimeAsync(1);
      expect(signal?.aborted).toBe(true);
      await settled;
    });
  }
});
