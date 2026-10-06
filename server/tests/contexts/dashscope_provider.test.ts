import { describe, expect, it, vi } from "vitest";

import {
  type CapturedRequest,
  chapterTask,
  DASHSCOPE_ORIGIN,
  expectedEndpoint,
  generationBody,
  jsonResponse,
  NATIVE_GENERATION_PATH_SEGMENTS,
  provider,
  RESPONSES_DEFAULT_PATH_SEGMENTS,
  scriptedTransport,
} from "./dashscope_provider.test-helpers.js";

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
    if (request === undefined) throw new Error("Expected a captured DashScope request.");
    expect(request.url).toBe(expectedEndpoint(DASHSCOPE_ORIGIN, NATIVE_GENERATION_PATH_SEGMENTS));
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

  it("posts responses-mode requests to the official compatible-mode path by default", async () => {
    const capture: CapturedRequest[] = [];
    const transport = scriptedTransport(
      [
        jsonResponse(200, {
          output: [{ type: "message", content: [{ text: '{"chapter_markdown": "resp"}' }] }],
        }),
      ],
      capture,
    );
    await provider({ transport, transportMode: "responses" }).generateStructured(
      chapterTask("chapter_draft"),
    );
    const [request] = capture;
    if (request === undefined) throw new Error("Expected a captured DashScope request.");
    expect(request.url).toBe(expectedEndpoint(DASHSCOPE_ORIGIN, RESPONSES_DEFAULT_PATH_SEGMENTS));
  });

  it("honors a custom base verbatim with the responses transport mode", async () => {
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
    if (request === undefined) throw new Error("Expected a captured DashScope request.");
    expect(request.url).toBe("https://proxy.example.com/x/responses");
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
      transport: scriptedTransport([() => jsonResponse(503, "unavailable")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(
      "DashScope generation failed for step 'chapter_draft': provider returned HTTP 503.",
    );
    expect(capture).toHaveLength(3);
  });

  it("fails immediately on 401 without any retry", async () => {
    const capture: CapturedRequest[] = [];
    const attempt = provider({
      transport: scriptedTransport([jsonResponse(401, "bad key")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(
      "DashScope generation failed for step 'chapter_draft': provider returned HTTP 401.",
    );
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
      transport: scriptedTransport([() => jsonResponse(200, "not json {{{")], capture),
    }).generateStructured(chapterTask("chapter_draft"));
    await expect(attempt).rejects.toThrow(/invalid JSON/);
    expect(capture).toHaveLength(3);
  });

  it("rethrows a post-read programming error without retrying", async () => {
    const capture: CapturedRequest[] = [];
    const programmingError = new TypeError("response parser programming error");
    const decode = vi.spyOn(TextDecoder.prototype, "decode").mockImplementation(() => {
      throw programmingError;
    });
    try {
      const attempt = provider({
        transport: scriptedTransport(
          [jsonResponse(200, generationBody('{"chapter_markdown":"draft"}'))],
          capture,
        ),
      }).generateStructured(chapterTask("chapter_draft"));

      await expect(attempt).rejects.toBe(programmingError);
      expect(capture).toHaveLength(1);
    } finally {
      decode.mockRestore();
    }
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
