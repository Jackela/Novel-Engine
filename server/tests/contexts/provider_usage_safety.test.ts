import { describe, expect, it } from "vitest";

import type {
  TextGenerationStreamOutcome,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { fixtureApiKey } from "../credential_fixtures.js";

const CASES = [
  { label: "zero", value: 0, expected: 0 },
  {
    label: "maximum safe integer",
    value: Number.MAX_SAFE_INTEGER,
    expected: Number.MAX_SAFE_INTEGER,
  },
  { label: "maximum safe integer plus one", value: Number.MAX_SAFE_INTEGER + 1, expected: null },
  { label: "huge finite integer", value: 1e308, expected: null },
  { label: "non-finite number", value: Number.POSITIVE_INFINITY, expected: null },
  { label: "negative integer", value: -1, expected: null },
  { label: "fraction", value: 1.5, expected: null },
  { label: "missing field", value: undefined, expected: null },
  { label: "malformed field", value: "12", expected: null },
] as const;

const task: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "system prompt",
  userPrompt: "write a chapter",
  responseSchema: { chapter_markdown: { type: "string" } },
  metadata: {},
};

function jsonResponse(body: string): Response {
  return new Response(body, {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function sseResponse(events: readonly unknown[]): Response {
  const body = events
    .map((event) => `data: ${typeof event === "string" ? event : JSON.stringify(event)}\n\n`)
    .join("");
  return new Response(body, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

function transport(response: Response): ProviderTransport {
  return async () => response;
}

function usageJson(value: unknown): string {
  if (value === undefined) return "{}";
  const encoded = value === Number.POSITIVE_INFINITY ? "1e9999" : JSON.stringify(value);
  return `{"prompt_tokens":${encoded},"completion_tokens":${encoded}}`;
}

function openai(response: Response): OpenAICompatibleTextProvider {
  return new OpenAICompatibleTextProvider({
    apiKey: fixtureApiKey("openai-usage", "safe"),
    model: "openai-usage-model",
    transport: transport(response),
  });
}

function dashscope(response: Response): DashScopeTextProvider {
  return new DashScopeTextProvider({
    apiKey: fixtureApiKey("dashscope-usage", "safe"),
    model: "dashscope-usage-model",
    transport: transport(response),
  });
}

async function streamOutcome(
  stream: AsyncGenerator<string, void, void>,
  read: () => TextGenerationStreamOutcome | undefined,
): Promise<TextGenerationStreamOutcome | undefined> {
  for await (const _delta of stream) {
    // Exhaustion is required before a provider may report its terminal usage.
  }
  return read();
}

describe("provider usage safe-integer normalization", () => {
  it.each(CASES)("normalizes $label in both synchronous adapters", async ({ value, expected }) => {
    const openaiResult = await openai(
      jsonResponse(
        `{"choices":[{"message":{"content":"{\\"chapter_markdown\\":\\"OpenAI prose.\\"}"}}],"usage":${usageJson(value)}}`,
      ),
    ).generateStructured(task);
    const dashscopeResult = await dashscope(
      jsonResponse(
        `{"output":{"choices":[{"message":{"content":"{\\"chapter_markdown\\":\\"DashScope prose.\\"}"}}]},"usage":${usageJson(value)}}`,
      ),
    ).generateStructured(task);

    expect(openaiResult.promptTokens).toBe(expected);
    expect(openaiResult.completionTokens).toBe(expected);
    expect(dashscopeResult.promptTokens).toBe(expected);
    expect(dashscopeResult.completionTokens).toBe(expected);
  });

  it.each(CASES)("normalizes $label in both streaming adapters", async ({ value, expected }) => {
    let openaiReported: TextGenerationStreamOutcome | undefined;
    const openaiOutcome = await streamOutcome(
      openai(
        sseResponse([
          { choices: [{ delta: { content: "OpenAI prose." } }] },
          `{"choices":[],"usage":${usageJson(value)}}`,
          "[DONE]",
        ]),
      ).generateStructuredStreaming(task, {
        onOutcome: (reported) => {
          openaiReported = reported;
        },
      }),
      () => openaiReported,
    );

    let dashscopeReported: TextGenerationStreamOutcome | undefined;
    const dashscopeOutcome = await streamOutcome(
      dashscope(
        sseResponse([
          { output: { choices: [{ message: { content: "DashScope prose." } }] } },
          `{"output":{"choices":[{"message":{"content":""},"finish_reason":"stop"}]},"usage":${usageJson(value)}}`,
        ]),
      ).generateStructuredStreaming(task, {
        onOutcome: (reported) => {
          dashscopeReported = reported;
        },
      }),
      () => dashscopeReported,
    );

    expect(openaiOutcome?.promptTokens).toBe(expected);
    expect(openaiOutcome?.completionTokens).toBe(expected);
    expect(dashscopeOutcome?.promptTokens).toBe(expected);
    expect(dashscopeOutcome?.completionTokens).toBe(expected);
  });
});
