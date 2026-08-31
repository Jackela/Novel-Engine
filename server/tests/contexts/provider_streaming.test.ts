import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { sseDataPayloads } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { fixtureApiKey } from "../credential_fixtures.js";

function chapterTask(step = "chapter_draft"): TextGenerationTask {
  return {
    step,
    systemPrompt: "system prompt",
    userPrompt: "write a chapter",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2, title: "The Crossing" },
  };
}

function sseResponse(events: string[]): Response {
  const body = events.map((event) => `data: ${event}\n\n`).join("");
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

interface CapturedRequest {
  readonly url: string;
  readonly init: RequestInit;
}

function scriptedTransport(
  script: Array<Response | Error>,
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

async function collected(
  stream: AsyncGenerator<string, void, void>,
): Promise<{ deltas: string[]; joined: string }> {
  const deltas: string[] = [];
  for await (const delta of stream) {
    deltas.push(delta);
  }
  return { deltas, joined: deltas.join("") };
}

describe("deterministic provider streaming (#308)", () => {
  it("chunks chapter prose in word groups whose join equals the sync output", async () => {
    const provider = new DeterministicStoryProvider();
    for (const step of ["chapter_draft", "chapter_revision"] as const) {
      const sync = await provider.generateStructured(chapterTask(step));
      const streamed = await collected(provider.generateStructuredStreaming(chapterTask(step)));
      expect(streamed.deltas.length).toBeGreaterThan(1);
      expect(streamed.joined).toBe(sync.content.chapter_markdown);
      // Adjudicated granularity: small word groups, several words per delta.
      const wordsPerDelta = streamed.deltas.map((delta) => delta.trim().split(/\s+/u).length);
      expect(Math.max(...wordsPerDelta)).toBeLessThanOrEqual(5);
      expect(Math.min(...wordsPerDelta)).toBeGreaterThanOrEqual(1);
    }
  });

  it("rejects an unsupported step before yielding", async () => {
    const provider = new DeterministicStoryProvider();
    await expect(
      collected(provider.generateStructuredStreaming(chapterTask("unknown"))),
    ).rejects.toThrow(TextGenerationProviderError);
  });

  it("stops yielding after an abort and reports no outcome", async () => {
    const provider = new DeterministicStoryProvider();
    const controller = new AbortController();
    const deltas: string[] = [];
    let outcome = false;
    for await (const delta of provider.generateStructuredStreaming(chapterTask(), {
      signal: controller.signal,
      onOutcome: () => {
        outcome = true;
      },
    })) {
      deltas.push(delta);
      controller.abort();
    }
    expect(deltas.length).toBe(1);
    expect(outcome).toBe(false);
  });
});

describe("SSE data payload parsing", () => {
  it("parses LF and CRLF events, joins multi-line data, and ignores other fields", async () => {
    const body = [
      "data: one\n\n",
      ": comment\n",
      "event: keepalive\n",
      "data: two\ndata: three\n\n",
      "data: four\r\n\r\n",
    ].join("");
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(body));
        controller.close();
      },
    });
    const payloads: string[] = [];
    for await (const payload of sseDataPayloads(stream)) {
      payloads.push(payload);
    }
    expect(payloads).toEqual(["one", "two\nthree", "four"]);
  });

  it("flushes a final event missing its terminating blank line", async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("data: tail"));
        controller.close();
      },
    });
    const payloads: string[] = [];
    for await (const payload of sseDataPayloads(stream)) {
      payloads.push(payload);
    }
    expect(payloads).toEqual(["tail"]);
  });
});

describe("OpenAI-compatible adapter streaming", () => {
  function provider(
    overrides: Partial<ConstructorParameters<typeof OpenAICompatibleTextProvider>[0]> = {},
  ) {
    return new OpenAICompatibleTextProvider({
      apiKey: fixtureApiKey("sk-openai", "stream"),
      model: "server-selected-model",
      ...overrides,
    });
  }

  it("relays chat deltas, requests usage, and reports the final-chunk outcome", async () => {
    const capture: CapturedRequest[] = [];
    const transport = scriptedTransport(
      [
        sseResponse([
          JSON.stringify({ choices: [{ delta: { role: "assistant", content: "" } }] }),
          JSON.stringify({ choices: [{ delta: { content: "Night fell " } }] }),
          JSON.stringify({ choices: [{ delta: { content: "over the harbor." } }] }),
          JSON.stringify({ choices: [], usage: { prompt_tokens: 11, completion_tokens: 22 } }),
          "[DONE]",
        ]),
      ],
      capture,
    );
    let outcome:
      | { model: string; promptTokens: number | null; completionTokens: number | null }
      | undefined;
    const streamed = await collected(
      provider({ transport }).generateStructuredStreaming(chapterTask(), {
        onOutcome: (reported) => {
          outcome = reported;
        },
      }),
    );

    expect(streamed.deltas).toEqual(["Night fell ", "over the harbor."]);
    expect(outcome).toEqual({
      model: "server-selected-model",
      promptTokens: 11,
      completionTokens: 22,
    });
    const request = capture[0];
    if (request === undefined) throw new Error("Expected a captured request.");
    expect(request.url).toBe("https://api.openai.com/v1/chat/completions");
    expect(new Headers(request.init.headers).get("accept")).toBe("text/event-stream");
    const body = JSON.parse(String(request.init.body)) as Record<string, unknown>;
    expect(body.stream).toBe(true);
    expect(body.stream_options).toEqual({ include_usage: true });
  });

  it("normalizes a non-OK stream response without retrying", async () => {
    const capture: CapturedRequest[] = [];
    const failure = provider({
      transport: scriptedTransport(
        [new Response("bad key", { status: 401, headers: { "content-type": "text/plain" } })],
        capture,
      ),
    });
    await expect(collected(failure.generateStructuredStreaming(chapterTask()))).rejects.toThrow(
      "OpenAI-compatible generation failed for step 'chapter_draft': provider returned HTTP 401.",
    );
    expect(capture).toHaveLength(1);
  });

  it("surfaces malformed stream chunks as malformed JSON failures", async () => {
    const transport = scriptedTransport([sseResponse(["{broken json"])], []);
    await expect(
      collected(provider({ transport }).generateStructuredStreaming(chapterTask())),
    ).rejects.toThrow(/invalid JSON/);
  });
});

describe("DashScope adapter streaming", () => {
  function provider(
    overrides: Partial<ConstructorParameters<typeof DashScopeTextProvider>[0]> = {},
  ) {
    return new DashScopeTextProvider({
      apiKey: fixtureApiKey("sk-dashscope", "stream"),
      model: "qwen3.5-flash",
      ...overrides,
    });
  }

  it("enables incremental native output and relays message-content deltas", async () => {
    const capture: CapturedRequest[] = [];
    const transport = scriptedTransport(
      [
        sseResponse([
          JSON.stringify({ output: { choices: [{ message: { content: "The tide " } }] } }),
          JSON.stringify({ output: { choices: [{ message: { content: "turned early." } }] } }),
          JSON.stringify({
            output: { choices: [{ message: { content: "" }, finish_reason: "stop" }] },
            usage: { prompt_tokens: 7, completion_tokens: 9 },
          }),
        ]),
      ],
      capture,
    );
    let outcome:
      | { model: string; promptTokens: number | null; completionTokens: number | null }
      | undefined;
    const streamed = await collected(
      provider({ transport }).generateStructuredStreaming(chapterTask("chapter_revision"), {
        onOutcome: (reported) => {
          outcome = reported;
        },
      }),
    );

    expect(streamed.deltas).toEqual(["The tide ", "turned early."]);
    expect(outcome).toEqual({ model: "qwen3.5-flash", promptTokens: 7, completionTokens: 9 });
    const request = capture[0];
    if (request === undefined) throw new Error("Expected a captured request.");
    expect(new Headers(request.init.headers).get("x-dashscope-sse")).toBe("enable");
    const body = JSON.parse(String(request.init.body)) as {
      parameters: Record<string, unknown>;
    };
    expect(body.parameters.incremental_output).toBe(true);
  });

  it("keeps whitespace-bearing deltas untrimmed", async () => {
    const transport = scriptedTransport(
      [
        sseResponse([
          JSON.stringify({ output: { choices: [{ message: { content: "  padded  " } }] } }),
        ]),
      ],
      [],
    );
    const streamed = await collected(
      provider({ transport }).generateStructuredStreaming(chapterTask()),
    );
    expect(streamed.joined).toBe("  padded  ");
  });
});
