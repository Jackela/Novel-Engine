import { describe, expect, it, vi } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { fixtureApiKey } from "../credential_fixtures.js";

type Shape = "openai" | "dashscope-compatible" | "native-message" | "native-text" | "responses";
const shapes: Shape[] = [
  "openai",
  "dashscope-compatible",
  "native-message",
  "native-text",
  "responses",
];
const task: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "system",
  userPrompt: "write a chapter",
  responseSchema: { chapter_markdown: { type: "string" } },
  metadata: {},
};
const prose = '{"chapter_markdown":"finished 章节"}';

function contentChunk(shape: Shape): Record<string, unknown> {
  if (shape === "responses") return { type: "response.output_text.delta", delta: prose };
  if (shape === "native-text") return { output: { text: prose } };
  if (shape === "native-message") return { output: { choices: [{ message: { content: prose } }] } };
  return { choices: [{ delta: { content: prose } }] };
}

function terminalChunk(shape: Shape, reason: unknown = "stop"): Record<string, unknown> {
  if (shape === "responses")
    return { type: "response.completed", response: { status: "completed" } };
  if (shape === "native-text") return { output: { text: "", finish_reason: reason } };
  if (shape === "native-message")
    return { output: { choices: [{ message: { content: "" }, finish_reason: reason }] } };
  return { choices: [{ delta: {}, finish_reason: reason }] };
}

function harness(shape: Shape, events: Array<Record<string, unknown> | string>) {
  const raw = events
    .map((event) => `data: ${typeof event === "string" ? event : JSON.stringify(event)}\n\n`)
    .join("");
  const transport = vi.fn<ProviderTransport>(() =>
    Promise.resolve(
      new Response(
        new ReadableStream<Uint8Array>({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(raw));
            controller.close();
          },
        }),
      ),
    ),
  );
  const options = {
    apiKey: fixtureApiKey("sk-provider", "terminal-frames"),
    model: "test-model",
    transport,
    retry: { maxAttempts: 3, delayMs: 0, sleep: async () => undefined },
  };
  const provider =
    shape === "openai"
      ? new OpenAICompatibleTextProvider(options)
      : new DashScopeTextProvider({
          ...options,
          transportMode:
            shape === "responses"
              ? "responses"
              : shape === "native-text"
                ? "text_generation"
                : "multimodal_generation",
        });
  const onOutcome = vi.fn();
  const deltas: string[] = [];
  const consume = async () => {
    for await (const delta of provider.generateStructuredStreaming(task, { onOutcome }))
      deltas.push(delta);
    return deltas.join("");
  };
  return { consume, deltas, transport, onOutcome, raw };
}

describe("adapter terminal frames (#674)", () => {
  it.each(shapes)("rejects complete JSON at EOF without %s completion evidence", async (shape) => {
    const test = harness(shape, [contentChunk(shape)]);
    const providerName = shape === "openai" ? "OpenAI-compatible" : "DashScope";
    await expect(test.consume()).rejects.toMatchObject({
      name: "ProviderTransportError",
      retryable: false,
      message: `${providerName} generation failed for step 'chapter_draft': stream ended without a terminal frame (frames=1, bytes=${new TextEncoder().encode(test.raw).byteLength}).`,
    });
    expect(test.deltas.join("")).toBe("finished 章节");
    expect(test.transport).toHaveBeenCalledTimes(1);
    expect(test.onOutcome).not.toHaveBeenCalled();
  });

  it.each(shapes)(
    "accepts %s completion at EOF and keeps usage after its terminal frame",
    async (shape) => {
      const test = harness(shape, [
        contentChunk(shape),
        terminalChunk(shape),
        { usage: { prompt_tokens: 11, completion_tokens: 23 } },
      ]);
      await expect(test.consume()).resolves.toBe("finished 章节");
      expect(test.transport).toHaveBeenCalledTimes(1);
      expect(test.onOutcome).toHaveBeenCalledExactlyOnceWith({
        model: "test-model",
        promptTokens: 11,
        completionTokens: 23,
      });
    },
  );

  it.each(shapes)("keeps a provider error after %s completion authoritative", async (shape) => {
    const failure = shape.startsWith("native")
      ? { code: "LateFailure", message: "late upstream failure" }
      : { error: { code: "LateFailure", message: "late upstream failure" } };
    const test = harness(shape, [contentChunk(shape), terminalChunk(shape), failure]);
    await expect(test.consume()).rejects.toThrow(
      /provider reported late upstream failure \(code LateFailure\)/,
    );
    expect(test.transport).toHaveBeenCalledTimes(1);
    expect(test.onOutcome).not.toHaveBeenCalled();
  });

  it("accepts every documented chat finish reason on both compatible adapters", async () => {
    for (const shape of ["openai", "dashscope-compatible"] as const) {
      for (const reason of ["stop", "length", "content_filter", "tool_calls", "function_call"]) {
        const test = harness(shape, [contentChunk(shape), terminalChunk(shape, reason)]);
        await expect(test.consume()).resolves.toBe("finished 章节");
        expect(test.onOutcome).toHaveBeenCalledTimes(1);
      }
    }
  });

  it("accepts documented native finish reasons for message and text output", async () => {
    for (const shape of ["native-message", "native-text"] as const) {
      for (const reason of ["stop", "length", "tool_calls"]) {
        const test = harness(shape, [contentChunk(shape), terminalChunk(shape, reason)]);
        await expect(test.consume()).resolves.toBe("finished 章节");
        expect(test.onOutcome).toHaveBeenCalledTimes(1);
      }
    }
  });

  it("rejects null, blank, unknown, and non-string finish reasons on every finish-reason shape", async () => {
    for (const shape of [
      "openai",
      "dashscope-compatible",
      "native-message",
      "native-text",
    ] as const) {
      for (const reason of [null, "null", "", " ", "unknown", 1, true, {}, []]) {
        const test = harness(shape, [contentChunk(shape), terminalChunk(shape, reason)]);
        await expect(test.consume()).rejects.toThrow(/stream ended without a terminal frame/);
        expect(test.onOutcome).not.toHaveBeenCalled();
        expect(test.transport).toHaveBeenCalledTimes(1);
      }
    }
  });

  it("requires finish evidence at the authoritative position for each output shape", async () => {
    const examples: Array<{ shape: Shape; misplaced: Record<string, unknown>[] }> = [
      {
        shape: "openai",
        misplaced: [
          { finish_reason: "stop" },
          { choices: [{ delta: { finish_reason: "stop" } }] },
          { choices: [{}, { finish_reason: "stop" }] },
          { choices: [null, { finish_reason: "stop" }] },
        ],
      },
      {
        shape: "dashscope-compatible",
        misplaced: [{ finish_reason: "stop" }, { choices: [null, { finish_reason: "stop" }] }],
      },
      {
        shape: "native-message",
        misplaced: [
          { finish_reason: "stop" },
          { output: { choices: [{ message: { finish_reason: "stop" } }] } },
          { output: { choices: [null, { finish_reason: "stop" }] } },
        ],
      },
      {
        shape: "native-text",
        misplaced: [
          { finish_reason: "stop" },
          { output: { text: "", finish_reason: "content_filter" } },
        ],
      },
    ];
    for (const { shape, misplaced } of examples) {
      for (const marker of misplaced) {
        const test = harness(shape, [contentChunk(shape), marker]);
        await expect(test.consume()).rejects.toThrow(/stream ended without a terminal frame/);
        expect(test.onOutcome).not.toHaveBeenCalled();
      }
    }
  });

  it("requires response.completed with completed response status, rather than an item or text ending", async () => {
    for (const marker of [
      { type: "response.output_text.done" },
      { type: "response.output_item.done", item: { status: "completed" } },
      { type: "response.completed" },
      { type: "response.completed", response: { status: "incomplete" } },
      { type: "response.completed", response: { status: "failed" } },
      { type: "response.completed", response: { status: null } },
      { type: "response.output_text.done", response: { status: "completed" } },
      { response: { status: "completed" } },
      { choices: [{ finish_reason: "stop" }] },
    ]) {
      const test = harness("responses", [contentChunk("responses"), marker]);
      await expect(test.consume()).rejects.toThrow(/stream ended without a terminal frame/);
      expect(test.onOutcome).not.toHaveBeenCalled();
      expect(test.transport).toHaveBeenCalledTimes(1);
    }
  });

  it("accepts DONE for all adapter shapes without requiring a finish reason", async () => {
    for (const shape of shapes) {
      const test = harness(shape, [contentChunk(shape), "[DONE]"]);
      await expect(test.consume()).resolves.toBe("finished 章节");
      expect(test.onOutcome).toHaveBeenCalledTimes(1);
    }
  });
});
