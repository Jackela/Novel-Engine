import { describe, expect, it, vi } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";

interface CapturedRequest {
  url: string;
  init: RequestInit;
}

function chapterTask(step: string): TextGenerationTask {
  return {
    step,
    systemPrompt: "system prompt",
    userPrompt: "user prompt",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2 },
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function generationBody(content: unknown, usage?: Record<string, number>): Record<string, unknown> {
  return {
    output: { choices: [{ message: { content } }] },
    usage: usage ?? { prompt_tokens: 11, completion_tokens: 22 },
  };
}

/** Records every request and answers from a script (Response or Error); optional per-call behavior. */
function scriptedTransport(
  script: Array<Response | Error>,
  capture: CapturedRequest[],
): ProviderTransport {
  let call = 0;
  return (url, init) => {
    capture.push({ url: String(url), init: init ?? {} });
    const answer = script[Math.min(call, script.length - 1)];
    call += 1;
    if (answer instanceof Error) {
      return Promise.reject(answer);
    }
    return Promise.resolve(answer);
  };
}

function provider(overrides: Partial<ConstructorParameters<typeof DashScopeTextProvider>[0]> = {}) {
  return new DashScopeTextProvider({
    apiKey: "sk-dashscope-test",
    model: "qwen3.5-flash",
    retry: { maxAttempts: 3, delayMs: 1000, sleep: async () => {} },
    ...overrides,
  });
}

describe("dashscope adapter request shape", () => {
  it("posts the multimodal payload to the native endpoint with bearer auth", async () => {
    const capture: CapturedRequest[] = [];
    const transport = scriptedTransport(
      [jsonResponse(200, generationBody('{"chapter_markdown": "# Draft"}'))],
      capture,
    );
    const result = await provider({ transport }).generateStructured(chapterTask("chapter_draft"));

    expect(capture).toHaveLength(1);
    const [request] = capture;
    if (request === undefined) {
      throw new Error("Expected a captured DashScope request.");
    }
    expect(request.url).toBe(
      "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
    );
    expect(new Headers(request.init.headers).get("authorization")).toBe("Bearer sk-dashscope-test");
    const body = JSON.parse(String(request.init.body));
    expect(body.model).toBe("qwen3.5-flash");
    expect(body.parameters).toMatchObject({
      result_format: "message",
      response_format: { type: "json_object" },
    });
    expect(result.content).toEqual({ chapter_markdown: "# Draft" });
    expect(result.provider).toBe("dashscope");
    expect(result.model).toBe("qwen3.5-flash");
    expect(result.promptTokens).toBe(11);
    expect(result.completionTokens).toBe(22);
    expect(JSON.parse(result.rawText)).toEqual({ chapter_markdown: "# Draft" });
  });

  it("rescues fenced JSON and non-object prose through the chapter fallback", async () => {
    const fenced = await provider({
      transport: scriptedTransport(
        [jsonResponse(200, generationBody('```json\n{"chapter_markdown": "fenced"}\n```'))],
        [],
      ),
    }).generateStructured(chapterTask("chapter_draft"));
    expect(fenced.content.chapter_markdown).toBe("fenced");

    const prose = await provider({
      transport: scriptedTransport(
        [jsonResponse(200, generationBody("Just a plain prose chapter."))],
        [],
      ),
    }).generateStructured(chapterTask("chapter_revision"));
    expect(prose.content.chapter_markdown).toBe("Just a plain prose chapter.");
  });

  it("honors a custom base and the responses transport mode", async () => {
    const capture: CapturedRequest[] = [];
    const transport = scriptedTransport(
      [
        jsonResponse(200, {
          output: [{ type: "message", content: [{ text: '{"chapter_markdown": "resp"}' }] }],
        }),
      ],
      capture,
    );
    await provider({
      transport,
      transportMode: "responses",
      apiBase: "https://proxy.example.com/x",
    }).generateStructured(chapterTask("chapter_draft"));
    const [request] = capture;
    if (request === undefined) {
      throw new Error("Expected a captured DashScope request.");
    }
    expect(request.url).toBe(
      "https://proxy.example.com/api/v2/apps/protocols/compatible-mode/v1/responses",
    );
  });
});

describe("dashscope adapter transient failure handling", () => {
  it("retries a single 429 and completes with a proposal", async () => {
    const capture: CapturedRequest[] = [];
    const delays: number[] = [];
    const transport = scriptedTransport(
      [
        jsonResponse(429, "rate limited"),
        jsonResponse(200, generationBody('{"chapter_markdown": "# After 429"}')),
      ],
      capture,
    );
    const result = await provider({
      transport,
      retry: { maxAttempts: 3, delayMs: 1000, sleep: async (ms) => void delays.push(ms) },
    }).generateStructured(chapterTask("chapter_draft"));

    expect(result.content.chapter_markdown).toBe("# After 429");
    expect(capture).toHaveLength(2);
    expect(delays).toEqual([1000]);
  });

  it("fails with the provider error after bounded 503 retries", async () => {
    const capture: CapturedRequest[] = [];
    const attempt = provider({
      transport: scriptedTransport([jsonResponse(503, "unavailable")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(
      /DashScope generation failed for step 'chapter_draft': 503 unavailable/,
    );
    expect(capture).toHaveLength(3);
  });

  it("fails immediately on 401 without any retry", async () => {
    const capture: CapturedRequest[] = [];
    const attempt = provider({
      transport: scriptedTransport([jsonResponse(401, "bad key")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(/401 bad key/);
    expect(capture).toHaveLength(1);
  });

  it("retries transport timeouts with the normalized timeout message", async () => {
    const capture: CapturedRequest[] = [];
    const attempt = provider({
      transport: scriptedTransport([new DOMException("aborted", "TimeoutError")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(/timed out after 180s/);
    expect(capture).toHaveLength(3);
  });

  it("retries malformed JSON responses and fails after the bound", async () => {
    const capture: CapturedRequest[] = [];
    const attempt = provider({
      transport: scriptedTransport([jsonResponse(200, "not json {{{")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(/invalid JSON/);
    expect(capture).toHaveLength(3);
  });

  it("fails immediately when the response shape lacks choices", async () => {
    const capture: CapturedRequest[] = [];
    const attempt = provider({
      transport: scriptedTransport([jsonResponse(200, { output: {} })], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(/missing structured message content/);
    expect(capture).toHaveLength(1);
  });
});

describe("dashscope generation timeout floor", () => {
  it("grants chapter steps at least 180 seconds via the abort signal", async () => {
    vi.useFakeTimers();
    try {
      let requestDispatched = false;
      let abortFired = false;
      const transport: ProviderTransport = (_url, init) => {
        requestDispatched = true;
        return new Promise<Response>((resolve) => {
          init?.signal?.addEventListener(
            "abort",
            () => {
              abortFired = true;
              resolve(jsonResponse(200, generationBody('{"chapter_markdown": "late"}')));
            },
            { once: true },
          );
        });
      };
      const generation = provider({ transport, timeoutSeconds: 30 }).generateStructured(
        chapterTask("chapter_revision"),
      );

      expect(requestDispatched).toBe(true);
      await vi.advanceTimersByTimeAsync(179_999);
      expect(abortFired).toBe(false);
      await vi.advanceTimersByTimeAsync(1);
      expect(abortFired).toBe(true);
      const result = await generation;
      expect(result.content.chapter_markdown).toBe("late");
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the configured timeout for non-chapter steps", async () => {
    vi.useFakeTimers();
    try {
      let transportCalls = 0;
      const transport: ProviderTransport = (_url, init) => {
        transportCalls += 1;
        return new Promise<Response>((resolve) => {
          init?.signal?.addEventListener(
            "abort",
            () => resolve(jsonResponse(200, generationBody("{}"))),
            { once: true },
          );
        });
      };
      const generation = provider({ transport, timeoutSeconds: 30 }).generateStructured({
        ...chapterTask("editorial_review"),
      });
      await vi.advanceTimersByTimeAsync(29_999);
      expect(transportCalls).toBe(1);
      await vi.advanceTimersByTimeAsync(1);
      await generation;
    } finally {
      vi.useRealTimers();
    }
  });
});
