import { expect, it, vi } from "vitest";

const defaultModels = vi.hoisted(() => ({
  mock: "mock-default-sentinel",
  dashscope: "dashscope-default-sentinel",
  openai_compatible: "openai-compatible-default-sentinel",
}));

vi.mock("../../src/contexts/ai/application/model_resolution.js", () => ({
  HARD_DEFAULT_MODELS: defaultModels,
}));

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";

function chapterTask(): TextGenerationTask {
  return {
    step: "chapter_draft",
    systemPrompt: "You write a novel chapter.",
    userPrompt: "Draft the next scene.",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 3, title: "The Signal" },
  };
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function noDelayRetry() {
  return { maxAttempts: 1, delayMs: 0, sleep: async () => {} };
}

function capturedJsonTransport(
  payloads: Record<string, unknown>[],
  response: Response,
): ProviderTransport {
  return async (_url, init) => {
    payloads.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
    return response;
  };
}

it("uses the mocked hard default when the deterministic adapter omits its model", async () => {
  const result = await new DeterministicStoryProvider().generateStructured(chapterTask());

  expect(result.model).toBe(defaultModels.mock);
  expect(result.content.chapter_markdown).toContain("# Chapter 3");
});

it("uses the mocked DashScope default in both its result and outbound JSON", async () => {
  const payloads: Record<string, unknown>[] = [];
  const provider = new DashScopeTextProvider({
    apiKey: "dashscope-test-key",
    retry: noDelayRetry(),
    transport: capturedJsonTransport(
      payloads,
      jsonResponse({
        output: { choices: [{ message: { content: '{"chapter_markdown":"# DashScope"}' } }] },
        usage: { prompt_tokens: 5, completion_tokens: 8 },
      }),
    ),
  });

  const result = await provider.generateStructured(chapterTask());

  expect(result.model).toBe(defaultModels.dashscope);
  expect(result.content).toEqual({ chapter_markdown: "# DashScope" });
  expect(payloads).toEqual([expect.objectContaining({ model: defaultModels.dashscope })]);
});

it("uses the mocked OpenAI-compatible default in both its result and outbound JSON", async () => {
  const payloads: Record<string, unknown>[] = [];
  const provider = new OpenAICompatibleTextProvider({
    apiKey: "openai-compatible-test-key",
    retry: noDelayRetry(),
    transport: capturedJsonTransport(
      payloads,
      jsonResponse({
        choices: [{ message: { content: '{"chapter_markdown":"# OpenAI compatible"}' } }],
        usage: { prompt_tokens: 13, completion_tokens: 21 },
      }),
    ),
  });

  const result = await provider.generateStructured(chapterTask());

  expect(result.model).toBe(defaultModels.openai_compatible);
  expect(result.content).toEqual({ chapter_markdown: "# OpenAI compatible" });
  expect(payloads).toEqual([expect.objectContaining({ model: defaultModels.openai_compatible })]);
});
