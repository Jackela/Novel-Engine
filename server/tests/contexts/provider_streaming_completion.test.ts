import { describe, expect, it, vi } from "vitest";

import { TextGenerationCancelledError } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import type { StreamingTextRequest } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { streamProviderTextDeltas } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";

function request(signal?: AbortSignal): StreamingTextRequest {
  return {
    url: "https://provider.example/v1/stream",
    headers: {},
    body: "{}",
    signal,
    context: "completion regression",
    timeoutSeconds: 30,
    model: "test-model",
    retry: { maxAttempts: 3, delayMs: 0, sleep: async () => undefined },
  };
}

function delta(chunk: Record<string, unknown>): string | undefined {
  return typeof chunk.content === "string" ? chunk.content : undefined;
}

function usage(): readonly [number | null, number | null] {
  return [null, null];
}

async function collect(stream: AsyncGenerator<string, void, void>): Promise<string[]> {
  const deltas: string[] = [];
  for await (const value of stream) deltas.push(value);
  return deltas;
}

function closedBody(raw: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(raw);
  return new ReadableStream<Uint8Array>({
    start(controller) {
      // Split a UTF-8 sequence as well as SSE boundaries across transport reads.
      for (const byte of bytes) controller.enqueue(Uint8Array.of(byte));
      controller.close();
    },
  });
}

describe("stream completion evidence (#674)", () => {
  it.each([
    { name: "content", raw: ': 心跳\n\ndata: {"content":"章节"}\n\n', frames: 1 },
    { name: "usage-only", raw: 'data: {"usage":{"prompt_tokens":7}}\n\n', frames: 1 },
    { name: "empty", raw: "", frames: 0 },
    { name: "comments and heartbeat fields", raw: ": 心跳\n\nevent: ping\nid: 1\n\n", frames: 0 },
  ])(
    "rejects $name EOF without an outcome or retry and counts raw UTF-8 bytes",
    async ({ raw, frames }) => {
      const transport = vi.fn<ProviderTransport>(() =>
        Promise.resolve(new Response(closedBody(raw))),
      );
      const onOutcome = vi.fn();
      const pending = collect(
        streamProviderTextDeltas(request(), transport, delta, usage, { onOutcome }),
      );

      await expect(pending).rejects.toMatchObject({
        name: "ProviderTransportError",
        retryable: false,
        timedOut: false,
        malformedJson: false,
        message: `completion regression: stream ended without a terminal frame (frames=${frames}, bytes=${new TextEncoder().encode(raw).byteLength}).`,
      });
      expect(transport).toHaveBeenCalledTimes(1);
      expect(onOutcome).not.toHaveBeenCalled();
    },
  );

  it("counts every data payload even when it carries no delta", async () => {
    const raw = 'data: {"content":"first"}\n\n: heartbeat\n\ndata: {}\n\ndata: {"usage":{}}';
    const onOutcome = vi.fn();
    await expect(
      collect(
        streamProviderTextDeltas(
          request(),
          () => Promise.resolve(new Response(closedBody(raw))),
          delta,
          usage,
          { onOutcome },
        ),
      ),
    ).rejects.toThrow(
      `completion regression: stream ended without a terminal frame (frames=3, bytes=${new TextEncoder().encode(raw).byteLength}).`,
    );
    expect(onOutcome).not.toHaveBeenCalled();
  });

  it("finishes on DONE while the body remains open and releases its reader", async () => {
    const cancel = vi.fn();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('data: {"content":"done"}\n\ndata: [DONE]\n\n'),
        );
      },
      cancel,
    });
    const onOutcome = vi.fn();
    const streamed = await collect(
      streamProviderTextDeltas(request(), () => Promise.resolve(new Response(body)), delta, usage, {
        onOutcome,
      }),
    );

    expect(streamed).toEqual(["done"]);
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(body.locked).toBe(false);
    expect(onOutcome).toHaveBeenCalledExactlyOnceWith({
      model: "test-model",
      promptTokens: null,
      completionTokens: null,
    });
  });

  it("accepts an adapter terminal predicate at EOF without treating an ordinary frame as terminal", async () => {
    const raw = 'data: {"content":"done"}\n\ndata: {"complete":true}\n\n';
    const onOutcome = vi.fn();
    const options = {
      onOutcome,
      isTerminalChunk: (chunk: Record<string, unknown>) => chunk.complete === true,
    };
    await expect(
      collect(
        streamProviderTextDeltas(
          request(),
          () => Promise.resolve(new Response(closedBody(raw))),
          delta,
          usage,
          options,
        ),
      ),
    ).resolves.toEqual(["done"]);
    expect(onOutcome).toHaveBeenCalledTimes(1);
  });

  it("keeps external cancellation authoritative when the consumer resumes toward EOF", async () => {
    const controller = new AbortController();
    const onOutcome = vi.fn();
    const stream = streamProviderTextDeltas(
      request(controller.signal),
      () => Promise.resolve(new Response(closedBody('data: {"content":"first"}\n\n'))),
      delta,
      usage,
      { onOutcome },
    );
    await expect(stream.next()).resolves.toMatchObject({ done: false, value: "first" });
    controller.abort();
    await expect(stream.next()).rejects.toThrow(TextGenerationCancelledError);
    expect(onOutcome).not.toHaveBeenCalled();
  });

  it("does not report an outcome when the consumer returns before completion", async () => {
    const onOutcome = vi.fn();
    const stream = streamProviderTextDeltas(
      request(),
      () => Promise.resolve(new Response(closedBody('data: {"content":"first"}\n\n'))),
      delta,
      usage,
      { onOutcome },
    );
    await stream.next();
    await expect(stream.return()).resolves.toEqual({ done: true, value: undefined });
    expect(onOutcome).not.toHaveBeenCalled();
  });
});
