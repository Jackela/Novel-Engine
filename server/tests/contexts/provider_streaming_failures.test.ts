import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { fixtureApiKey } from "../credential_fixtures.js";

/**
 * DR-026 gap B: a 200 SSE stream can carry a provider error payload
 * (OpenAI-compatible `{"error":{...}}` or native DashScope `{"code","message"}`).
 * Both adapters must raise it as a normalized provider failure naming the
 * provider message and code, instead of ignoring it until a later JSON or
 * contract error. Chunks without an error payload keep their previous behavior
 * (covered by provider_streaming.test.ts).
 */

function chapterTask(): TextGenerationTask {
  return {
    step: "chapter_draft",
    systemPrompt: "system prompt",
    userPrompt: "write a chapter",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2 },
  };
}

function sseResponse(events: string[]): Response {
  const body = events.map((event) => `data: ${event}\n\n`).join("");
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(body));
        controller.close();
      },
    }),
    { status: 200, headers: { "content-type": "text/event-stream" } },
  );
}

function scriptedTransport(script: Response[]): ProviderTransport {
  return () => {
    const answer = script.shift();
    if (answer === undefined) throw new Error("Expected a scripted response.");
    return Promise.resolve(answer);
  };
}

async function collected(stream: AsyncGenerator<string, void, void>): Promise<string[]> {
  const deltas: string[] = [];
  for await (const delta of stream) deltas.push(delta);
  return deltas;
}

const singleAttemptRetry = { maxAttempts: 1, delayMs: 0, sleep: async () => undefined };

function openAiProvider(transport: ProviderTransport): OpenAICompatibleTextProvider {
  return new OpenAICompatibleTextProvider({
    apiKey: fixtureApiKey("sk-openai", "stream-failure-frames"),
    retry: singleAttemptRetry,
    transport,
  });
}

function dashscopeProvider(transport: ProviderTransport): DashScopeTextProvider {
  return new DashScopeTextProvider({
    apiKey: fixtureApiKey("sk-dashscope", "stream-failure-frames"),
    retry: singleAttemptRetry,
    transport,
  });
}

describe("streaming adapter failure frames (DR-026 gap B)", () => {
  it("surfaces an OpenAI-compatible error payload after completed prose instead of resolving", async () => {
    const transport = scriptedTransport([
      sseResponse([
        JSON.stringify({
          choices: [{ delta: { content: '{"chapter_markdown": "finished prose"}' } }],
        }),
        JSON.stringify({
          error: { message: "rate limit reached mid-flight", code: "RateLimitExceeded" },
        }),
      ]),
    ]);
    await expect(
      collected(openAiProvider(transport).generateStructuredStreaming(chapterTask())),
    ).rejects.toThrow(
      "OpenAI-compatible generation failed for step 'chapter_draft': provider reported rate limit reached mid-flight (code RateLimitExceeded)",
    );
  });

  it("maps a sole OpenAI-compatible error frame to the provider failure, not the JSON contract error", async () => {
    const transport = scriptedTransport([
      sseResponse([
        JSON.stringify({ error: { message: "upstream overloaded", type: "server_error" } }),
      ]),
    ]);
    await expect(
      collected(openAiProvider(transport).generateStructuredStreaming(chapterTask())),
    ).rejects.toThrow(
      "OpenAI-compatible generation failed for step 'chapter_draft': provider reported upstream overloaded (code server_error)",
    );
  });

  it("surfaces a native DashScope error frame mid-stream with the provider message and code", async () => {
    const transport = scriptedTransport([
      sseResponse([
        JSON.stringify({
          output: { choices: [{ message: { content: '{"chapter_markdown": "done"}' } }] },
        }),
        JSON.stringify({ code: "InvalidParameter", message: "input length exceeds the limit" }),
      ]),
    ]);
    await expect(
      collected(dashscopeProvider(transport).generateStructuredStreaming(chapterTask())),
    ).rejects.toThrow(
      "DashScope generation failed for step 'chapter_draft': provider reported input length exceeds the limit (code InvalidParameter)",
    );
  });

  it("surfaces a compatible-mode error frame on the DashScope adapter", async () => {
    const transport = scriptedTransport([
      sseResponse([
        JSON.stringify({ choices: [{ delta: { content: '{"chapter_markdown": "done"}' } }] }),
        JSON.stringify({ error: { message: "quota exceeded", code: "insufficient_quota" } }),
      ]),
    ]);
    await expect(
      collected(dashscopeProvider(transport).generateStructuredStreaming(chapterTask())),
    ).rejects.toThrow(
      "DashScope generation failed for step 'chapter_draft': provider reported quota exceeded (code insufficient_quota)",
    );
  });
});
