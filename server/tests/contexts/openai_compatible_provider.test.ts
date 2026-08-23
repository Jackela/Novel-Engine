import { describe, expect, it, vi } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";

interface CapturedRequest {
  readonly url: string;
  readonly init: RequestInit;
}

function chapterTask(step = "chapter_draft"): TextGenerationTask {
  return {
    step,
    systemPrompt: "system prompt",
    userPrompt: "write a chapter",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2, title: "The Crossing" },
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function completionBody(
  content: unknown,
  usage?: Record<string, unknown>,
): Record<string, unknown> {
  return {
    choices: [{ message: { content } }],
    usage: usage ?? { prompt_tokens: 11, completion_tokens: 22 },
  };
}

/** Records public outbound calls and returns the next scripted transport outcome. */
function scriptedTransport(
  script: Array<Response | Error | undefined>,
  capture: CapturedRequest[],
): ProviderTransport {
  let call = 0;
  return (url, init) => {
    capture.push({ url: String(url), init: init ?? {} });
    const answer = script[Math.min(call, script.length - 1)];
    call += 1;
    return answer instanceof Error ? Promise.reject(answer) : Promise.resolve(answer);
  };
}

function provider(
  overrides: Partial<ConstructorParameters<typeof OpenAICompatibleTextProvider>[0]> = {},
): OpenAICompatibleTextProvider {
  return new OpenAICompatibleTextProvider({
    apiKey: "sk-openai-compatible-test",
    model: "server-selected-model",
    retry: { maxAttempts: 3, delayMs: 1_000, sleep: async () => {} },
    ...overrides,
  });
}

describe("OpenAI-compatible adapter request shape", () => {
  it("posts server-resolved model and JSON-object chat messages with bearer auth", async () => {
    const capture: CapturedRequest[] = [];
    const result = await provider({
      transport: scriptedTransport(
        [jsonResponse(200, completionBody('{"chapter_markdown":"# Draft"}'))],
        capture,
      ),
    }).generateStructured(chapterTask());

    expect(capture).toHaveLength(1);
    expect(capture[0]?.url).toBe("https://api.openai.com/v1/chat/completions");
    expect(new Headers(capture[0]?.init.headers).get("authorization")).toBe(
      "Bearer sk-openai-compatible-test",
    );
    expect(new Headers(capture[0]?.init.headers).get("content-type")).toBe("application/json");
    const body = JSON.parse(String(capture[0]?.init.body)) as Record<string, unknown>;
    expect(body.model).toBe("server-selected-model");
    expect(body.response_format).toEqual({ type: "json_object" });
    expect(body.messages).toEqual([
      {
        role: "system",
        content: expect.stringContaining("Return valid JSON only."),
      },
      {
        role: "user",
        content: expect.stringContaining("Task step: chapter_draft"),
      },
    ]);
    expect(result).toMatchObject({
      step: "chapter_draft",
      provider: "openai_compatible",
      model: "server-selected-model",
      content: { chapter_markdown: "# Draft" },
      promptTokens: 11,
      completionTokens: 22,
    });
  });

  it("coerces structured JSON and falls back to chapter prose", async () => {
    const structured = await provider({
      transport: scriptedTransport(
        [jsonResponse(200, completionBody('{"chapter_markdown": 42}'))],
        [],
      ),
    }).generateStructured(chapterTask());
    expect(structured.content).toEqual({ chapter_markdown: "42" });

    const prose = await provider({
      transport: scriptedTransport(
        [jsonResponse(200, completionBody("Plain narrative prose."))],
        [],
      ),
    }).generateStructured(chapterTask("chapter_revision"));
    expect(prose.content).toEqual({ chapter_markdown: "Plain narrative prose." });
  });
});

describe("OpenAI-compatible adapter transient failure handling", () => {
  it("retries a structured 429 and succeeds", async () => {
    const capture: CapturedRequest[] = [];
    const result = await provider({
      transport: scriptedTransport(
        [
          jsonResponse(429, "rate limited"),
          jsonResponse(200, completionBody('{"chapter_markdown":"after retry"}')),
        ],
        capture,
      ),
    }).generateStructured(chapterTask());

    expect(result.content).toEqual({ chapter_markdown: "after retry" });
    expect(capture).toHaveLength(2);
  });

  it("fails immediately on a 401", async () => {
    const capture: CapturedRequest[] = [];
    const generation = provider({
      transport: scriptedTransport([jsonResponse(401, "bad key")], capture),
    }).generateStructured(chapterTask());

    await expect(generation).rejects.toThrow(/401 bad key/);
    expect(capture).toHaveLength(1);
  });

  it("retries malformed JSON and normalized timeout failures", async () => {
    const malformedCalls: CapturedRequest[] = [];
    const malformed = provider({
      transport: scriptedTransport([jsonResponse(200, "not json {{{")], malformedCalls),
    }).generateStructured(chapterTask());
    await expect(malformed).rejects.toThrow(/invalid JSON/);
    expect(malformedCalls).toHaveLength(3);

    const timeoutCalls: CapturedRequest[] = [];
    const timedOut = provider({
      transport: scriptedTransport([new DOMException("timed out", "TimeoutError")], timeoutCalls),
    }).generateStructured(chapterTask("chapter_revision"));
    await expect(timedOut).rejects.toThrow(/timed out after 180s/);
    expect(timeoutCalls).toHaveLength(3);
  });

  it("normalizes an absent transport response but leaves programming errors visible", async () => {
    const missingCalls: CapturedRequest[] = [];
    const missing = provider({
      transport: scriptedTransport([undefined], missingCalls),
    }).generateStructured(chapterTask());
    await expect(missing).rejects.toThrow(TextGenerationProviderError);
    await expect(missing).rejects.toThrow(/transport returned no response/);
    expect(missingCalls).toHaveLength(1);

    const programmingCalls: CapturedRequest[] = [];
    const programmingFailure = provider({
      transport: scriptedTransport([new RangeError("remain visible")], programmingCalls),
    }).generateStructured(chapterTask());
    await expect(programmingFailure).rejects.toThrow(RangeError);
    expect(programmingCalls).toHaveLength(1);
  });
});

describe("OpenAI-compatible adapter boundaries", () => {
  it("rejects an unknown provider step before dispatch", async () => {
    const capture: CapturedRequest[] = [];
    const generation = provider({
      transport: scriptedTransport(
        [jsonResponse(200, completionBody('{"chapter_markdown":"must not dispatch"}'))],
        capture,
      ),
    }).generateStructured(chapterTask("unknown_step"));

    await expect(generation).rejects.toThrow(/Unsupported generation step: unknown_step/);
    expect(capture).toHaveLength(0);
  });

  it("keeps per-instance credentials, model, and transport isolated", async () => {
    const firstCalls: CapturedRequest[] = [];
    const secondCalls: CapturedRequest[] = [];
    const first = provider({
      apiKey: "first-key",
      model: "first-model",
      transport: scriptedTransport(
        [jsonResponse(200, completionBody('{"chapter_markdown":"first"}'))],
        firstCalls,
      ),
    });
    const second = provider({
      apiKey: "second-key",
      model: "second-model",
      apiBase: "https://proxy.example.test/v1/",
      transport: scriptedTransport(
        [jsonResponse(200, completionBody('{"chapter_markdown":"second"}'))],
        secondCalls,
      ),
    });

    await first.generateStructured(chapterTask());
    await second.generateStructured(chapterTask());

    expect(new Headers(firstCalls[0]?.init.headers).get("authorization")).toBe("Bearer first-key");
    expect(JSON.parse(String(firstCalls[0]?.init.body)).model).toBe("first-model");
    expect(secondCalls[0]?.url).toBe("https://proxy.example.test/v1/chat/completions");
    expect(new Headers(secondCalls[0]?.init.headers).get("authorization")).toBe(
      "Bearer second-key",
    );
    expect(JSON.parse(String(secondCalls[0]?.init.body)).model).toBe("second-model");
  });

  it("grants chapter generation the 180-second abort floor and releases the timer", async () => {
    vi.useFakeTimers();
    try {
      let abortFired = false;
      const transport: ProviderTransport = (_url, init) =>
        new Promise<Response>((resolve) => {
          init?.signal?.addEventListener(
            "abort",
            () => {
              abortFired = true;
              resolve(jsonResponse(200, completionBody('{"chapter_markdown":"late"}')));
            },
            { once: true },
          );
        });
      const generation = provider({ transport, timeoutSeconds: 30 }).generateStructured(
        chapterTask("chapter_revision"),
      );

      await vi.advanceTimersByTimeAsync(179_999);
      expect(abortFired).toBe(false);
      await vi.advanceTimersByTimeAsync(1);
      await expect(generation).resolves.toMatchObject({ content: { chapter_markdown: "late" } });
      expect(vi.getTimerCount()).toBe(0);
    } finally {
      vi.useRealTimers();
    }
  });
});
