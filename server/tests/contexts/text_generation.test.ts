import { describe, expect, it } from "vitest";

import {
  isProviderStep,
  PROVIDER_STEPS,
  TextGenerationProviderError,
  type TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import {
  createTextGenerationProvider,
  textProviderFactory,
} from "../../src/contexts/ai/infrastructure/providers/text_provider_factory.js";

function chapterTask(step: string, overrides: Record<string, unknown> = {}): TextGenerationTask {
  return {
    step,
    systemPrompt: "system",
    userPrompt: "user",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2, title: "The Crossing", ...overrides },
  };
}

function proseBody(markdown: string | undefined): string {
  expect(markdown, "expected chapter_markdown prose").toBeDefined();
  return markdown as string;
}

function testCredential(provider: string): string {
  return ["test", provider, "credential"].join("-");
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

describe("provider step vocabulary", () => {
  it("is closed to the three adjudicated steps", () => {
    expect([...PROVIDER_STEPS]).toEqual(["chapter_draft", "chapter_revision", "editorial_review"]);
    expect(isProviderStep("chapter_draft")).toBe(true);
    expect(isProviderStep("continue")).toBe(false);
    expect(isProviderStep("generate")).toBe(false);
  });
});

describe("deterministic story provider (mock)", () => {
  const provider = new DeterministicStoryProvider();

  it("produces non-empty prose for chapter_draft that reflects the task's chapter", async () => {
    const result = await provider.generateStructured(chapterTask("chapter_draft"));
    const prose = proseBody(result.content.chapter_markdown as string | undefined);

    expect(result.provider).toBe("mock");
    expect(result.model).toBe("deterministic-story-v1");
    expect(prose.length).toBeGreaterThan(400);
    expect(() => JSON.parse(prose)).toThrow();
    expect(prose.toLowerCase()).not.toContain("echo");
    expect(prose).not.toContain('"result"');
    expect(prose).toContain("Chapter 2");
    expect(prose).toContain("The Crossing");
  });

  it("produces different prose for chapter_revision that still reflects the task", async () => {
    const draft = proseBody(
      (await provider.generateStructured(chapterTask("chapter_draft"))).content.chapter_markdown as
        | string
        | undefined,
    );
    const revision = proseBody(
      (await provider.generateStructured(chapterTask("chapter_revision"))).content
        .chapter_markdown as string | undefined,
    );
    expect(revision.length).toBeGreaterThan(400);
    expect(revision).not.toBe(draft);
    expect(revision).toContain("Chapter 2");
    expect(revision).toContain("The Crossing");
  });

  it("varies prose with the chapter number instead of a fixed default", async () => {
    const first = proseBody(
      (await provider.generateStructured(chapterTask("chapter_draft", { chapter_number: 1 })))
        .content.chapter_markdown as string | undefined,
    );
    const third = proseBody(
      (await provider.generateStructured(chapterTask("chapter_draft", { chapter_number: 3 })))
        .content.chapter_markdown as string | undefined,
    );
    expect(first).not.toBe(third);
    expect(first).toContain("Chapter 1");
    expect(third).toContain("Chapter 3");
  });

  it("rejects any step outside its supported set instead of echoing the task", async () => {
    for (const step of ["continue", "rewrite", "generate", "summarize", ""]) {
      const attempt = provider.generateStructured(chapterTask(step));
      await expect(attempt).rejects.toBeInstanceOf(TextGenerationProviderError);
    }
  });

  it("reports no token counts so usage falls back to the word counter", async () => {
    const result = await provider.generateStructured(chapterTask("chapter_draft"));
    expect(result.promptTokens).toBeNull();
    expect(result.completionTokens).toBeNull();
  });
});

describe("text provider factory", () => {
  it("builds the deterministic mock without any credentials", async () => {
    const provider = createTextGenerationProvider({ provider: "mock", apiKeys: {} });
    const nextProvider = createTextGenerationProvider({ provider: "mock", apiKeys: {} });
    const result = await provider.generateStructured(chapterTask("chapter_draft"));

    expect(nextProvider).not.toBe(provider);
    expect(result.provider).toBe("mock");
    expect(result.model).toBe("deterministic-story-v1");
  });

  it("fails loudly for an unconfigured dashscope provider — no mock fallback", async () => {
    const provider = createTextGenerationProvider({
      provider: "dashscope",
      apiKeys: { dashscope: "  " },
    });
    await expect(provider.generateStructured(chapterTask("chapter_revision"))).rejects.toThrow(
      /DASHSCOPE_API_KEY is required when provider is dashscope/,
    );
  });

  it("fails loudly for an unconfigured openai_compatible provider", async () => {
    const provider = createTextGenerationProvider({
      provider: "openai_compatible",
      apiKeys: {},
    });
    await expect(provider.generateStructured(chapterTask("chapter_draft"))).rejects.toThrow(
      /LLM_API_KEY is required when provider is openai_compatible/,
    );
  });

  it("constructs the configured DashScope adapter with the server-resolved default model", async () => {
    const requests: string[] = [];
    const transport: ProviderTransport = (url) => {
      requests.push(String(url));
      return Promise.resolve(
        jsonResponse({
          output: { choices: [{ message: { content: '{"chapter_markdown":"configured"}' } }] },
        }),
      );
    };
    const provider = createTextGenerationProvider({
      provider: "dashscope",
      apiKeys: { dashscope: testCredential("dashscope") },
      adapterOptions: { dashscope: { transport } },
    });
    const result = await provider.generateStructured(chapterTask("chapter_draft"));

    expect(result).toMatchObject({
      provider: "dashscope",
      model: "qwen3.5-flash",
      content: { chapter_markdown: "configured" },
    });
    expect(requests).toEqual([
      "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
    ]);
  });

  it("applies server-only overrides and creates isolated OpenAI-compatible adapters", async () => {
    const requests: string[] = [];
    const transport: ProviderTransport = (url) => {
      requests.push(String(url));
      return Promise.resolve(
        jsonResponse({
          choices: [{ message: { content: '{"chapter_markdown":"overridden"}' } }],
        }),
      );
    };
    const factory = textProviderFactory(
      { openaiCompatible: testCredential("openai-compatible") },
      {
        modelSettings: { openaiCompatibleModel: "server-openai-model" },
        adapterOptions: {
          openaiCompatible: { apiBase: "https://compatible.example.test/v1", transport },
        },
      },
    );
    const first = factory("openai_compatible");
    const second = factory("openai_compatible");
    const result = await first.generateStructured(chapterTask("chapter_revision"));

    expect(second).not.toBe(first);
    expect(result).toMatchObject({
      provider: "openai_compatible",
      model: "server-openai-model",
      content: { chapter_markdown: "overridden" },
    });
    expect(requests).toEqual(["https://compatible.example.test/v1/chat/completions"]);
  });
});
