import { afterEach, describe, expect, it, vi } from "vitest";

import type { TextGenerationStreamOptions } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { ProviderTransportError } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import type { StreamingTextRequest } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { streamProviderTextDeltas } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";

function streamRequest(overrides: Partial<StreamingTextRequest> = {}): StreamingTextRequest {
  return {
    url: "https://provider.example/v1/chat/completions",
    headers: {},
    body: "{}",
    signal: undefined,
    context: "test provider stream",
    timeoutSeconds: 30,
    model: "test-model",
    ...overrides,
  };
}

function extractDelta(chunk: Record<string, unknown>): string | undefined {
  const content = chunk.content;
  return typeof content === "string" && content !== "" ? content : undefined;
}

function extractUsage(): readonly [number | null, number | null] {
  return [null, null];
}

/** An SSE body that never enqueues and never closes. */
function hangingStream(): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({ start() {} });
}

/** An SSE body that emits the given events, then stalls without closing. */
function stallingStream(events: string[]): ReadableStream<Uint8Array> {
  const body = events.map((event) => `data: ${event}\n\n`).join("");
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body));
    },
  });
}

function sseTransport(body: ReadableStream<Uint8Array>): ProviderTransport {
  return () =>
    Promise.resolve(
      new Response(body, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      }),
    );
}

async function consume(
  transport: ProviderTransport,
  request: StreamingTextRequest,
): Promise<{ deltas: string[]; outcome: boolean }> {
  const deltas: string[] = [];
  let outcome = false;
  const options: TextGenerationStreamOptions = {
    onOutcome: () => {
      outcome = true;
    },
  };
  for await (const delta of streamProviderTextDeltas(
    request,
    transport,
    extractDelta,
    extractUsage,
    options,
  )) {
    deltas.push(delta);
  }
  return { deltas, outcome };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("streamProviderTextDeltas internal timeouts (#342)", () => {
  it("aborts with a transport timeout when the first byte never arrives", async () => {
    vi.useFakeTimers();
    const request = streamRequest({ firstByteTimeoutMs: 5_000 });
    const pending = consume(sseTransport(hangingStream()), request);
    const settled = expect(pending).rejects.toThrow(ProviderTransportError);
    await vi.advanceTimersByTimeAsync(4_999);
    await vi.advanceTimersByTimeAsync(1);
    await settled;
  });

  it("reports the timeout as a retryable transport failure with its budget", async () => {
    vi.useFakeTimers();
    const request = streamRequest({ firstByteTimeoutMs: 5_000 });
    const pending = consume(sseTransport(hangingStream()), request);
    const settled = expect(pending).rejects.toMatchObject({
      name: "ProviderTransportError",
      timedOut: true,
      retryable: true,
    });
    await vi.advanceTimersByTimeAsync(5_000);
    await settled;
  });

  it("names the first-byte budget and its real duration in the timeout message", async () => {
    vi.useFakeTimers();
    const request = streamRequest({ firstByteTimeoutMs: 5_000, timeoutSeconds: 30 });
    const pending = consume(sseTransport(hangingStream()), request);
    const settled = expect(pending).rejects.toThrow(/first-byte timeout after 5s/);
    await vi.advanceTimersByTimeAsync(5_000);
    await settled;
  });

  it("aborts with an idle timeout when frames stall mid-stream", async () => {
    vi.useFakeTimers();
    const request = streamRequest({ firstByteTimeoutMs: 5_000, idleTimeoutMs: 10_000 });
    const transport = sseTransport(
      stallingStream([JSON.stringify({ content: "first " }), JSON.stringify({ content: "bit" })]),
    );
    const deltas: string[] = [];
    let outcome = false;
    const pending = (async () => {
      for await (const delta of streamProviderTextDeltas(
        request,
        transport,
        extractDelta,
        extractUsage,
        {
          onOutcome: () => {
            outcome = true;
          },
        },
      )) {
        deltas.push(delta);
      }
    })();
    const settled = expect(pending).rejects.toThrow(ProviderTransportError);
    await vi.advanceTimersByTimeAsync(9_999);
    expect(deltas.join("")).toBe("first bit");
    expect(outcome).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await settled;
  });

  it("names the idle budget and its real duration in the timeout message", async () => {
    vi.useFakeTimers();
    const request = streamRequest({ firstByteTimeoutMs: 5_000, idleTimeoutMs: 10_000 });
    const transport = sseTransport(stallingStream([JSON.stringify({ content: "bit" })]));
    const pending = consume(transport, request);
    const settled = expect(pending).rejects.toThrow(/idle timeout after 10s of silence/);
    await vi.advanceTimersByTimeAsync(10_000);
    await settled;
  });

  it("lets a healthy stream finish without reporting an outcome loss", async () => {
    vi.useFakeTimers();
    const events = [
      JSON.stringify({ content: "one " }),
      JSON.stringify({ content: "two" }),
      "[DONE]",
    ];
    const body = events.map((event) => `data: ${event}\n\n`).join("");
    const transport = sseTransport(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(body));
          controller.close();
        },
      }),
    );
    const request = streamRequest({ firstByteTimeoutMs: 5_000, idleTimeoutMs: 10_000 });
    const pending = consume(transport, request);
    const settled = pending;
    await vi.advanceTimersByTimeAsync(0);
    await expect(settled).resolves.toEqual({ deltas: ["one ", "two"], outcome: true });
  });

  it("does not fire before its configured budget elapses", async () => {
    vi.useFakeTimers();
    const request = streamRequest({ firstByteTimeoutMs: 5_000 });
    const probe = Symbol("probe");
    const pending = consume(sseTransport(hangingStream()), request);
    const outcome = Promise.race([
      pending.then(
        () => "resolved",
        () => "rejected",
      ),
      new Promise((resolve) => {
        setTimeout(() => resolve(probe), 4_999);
      }),
    ]);
    await vi.advanceTimersByTimeAsync(4_999);
    expect(await outcome).toBe(probe);
  });
});
