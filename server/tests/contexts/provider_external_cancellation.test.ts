import { afterEach, describe, expect, it, vi } from "vitest";

import { TextGenerationCancelledError } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import { startProviderResponseDeadline } from "../../src/contexts/ai/infrastructure/providers/provider_response_lifecycle.js";
import type { StreamingTextRequest } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";
import { streamProviderTextDeltas } from "../../src/contexts/ai/infrastructure/providers/streaming_generation.js";

function request(signal: AbortSignal): StreamingTextRequest {
  return {
    url: "https://provider.example/v1/stream",
    headers: {},
    body: "{}",
    signal,
    context: "cancelled provider stream",
    timeoutSeconds: 60,
    model: "cancel-model",
    firstByteTimeoutMs: 120_000,
    idleTimeoutMs: 120_000,
  };
}

function delta(chunk: Record<string, unknown>): string | undefined {
  return typeof chunk.content === "string" ? chunk.content : undefined;
}

function usage(): readonly [number | null, number | null] {
  return [null, null];
}

function doneBody(cancel: () => Promise<void> | void): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"));
    },
    cancel,
  });
}

async function consume(transport: ProviderTransport, signal: AbortSignal): Promise<string[]> {
  const values: string[] = [];
  for await (const value of streamProviderTextDeltas(request(signal), transport, delta, usage)) {
    values.push(value);
  }
  return values;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("explicit external cancellation races", () => {
  it("rejects a pre-aborted request before an injected transport is called", async () => {
    const controller = new AbortController();
    controller.abort();
    const transport = vi.fn<ProviderTransport>(() => new Promise<Response>(() => undefined));

    await expect(consume(transport, controller.signal)).rejects.toThrow(
      TextGenerationCancelledError,
    );
    expect(transport).not.toHaveBeenCalled();
  });

  it("interrupts dispatch even when the injected transport ignores its signal", async () => {
    const controller = new AbortController();
    const transport = vi.fn<ProviderTransport>(() => new Promise<Response>(() => undefined));
    const pending = consume(transport, controller.signal);
    await Promise.resolve();

    controller.abort();

    await expect(pending).rejects.toThrow(TextGenerationCancelledError);
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it("interrupts a body wait and completes reader cleanup before rejecting", async () => {
    const controller = new AbortController();
    let cancelCompleted = false;
    const cleanupFailure = new Error("cleanup must not replace cancellation");
    const body = new ReadableStream<Uint8Array>({
      start(streamController) {
        streamController.enqueue(
          new TextEncoder().encode(`data: ${JSON.stringify({ content: "first" })}\n\n`),
        );
      },
      async cancel() {
        await Promise.resolve();
        cancelCompleted = true;
        throw cleanupFailure;
      },
    });
    const stream = streamProviderTextDeltas(
      request(controller.signal),
      () => Promise.resolve(new Response(body, { status: 200 })),
      delta,
      usage,
    );
    await expect(stream.next()).resolves.toMatchObject({ done: false, value: "first" });
    const pending = stream.next();

    controller.abort();

    await expect(pending).rejects.toThrow(TextGenerationCancelledError);
    expect(cancelCompleted).toBe(true);
  });

  it("bounds cleanup when an injected stream never settles cancellation", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const body = new ReadableStream<Uint8Array>({
      start(streamController) {
        streamController.enqueue(
          new TextEncoder().encode(`data: ${JSON.stringify({ content: "first" })}\n\n`),
        );
      },
      cancel: () => new Promise<void>(() => undefined),
    });
    const stream = streamProviderTextDeltas(
      request(controller.signal),
      () => Promise.resolve(new Response(body, { status: 200 })),
      delta,
      usage,
    );
    await expect(stream.next()).resolves.toMatchObject({ done: false, value: "first" });
    const pending = stream.next();
    const settled = expect(pending).rejects.toThrow(TextGenerationCancelledError);

    controller.abort();
    await vi.advanceTimersByTimeAsync(999);
    await vi.advanceTimersByTimeAsync(1);

    await settled;
  });

  it("keeps the first deadline or external-cancellation cause authoritative", async () => {
    vi.useFakeTimers();
    const deadlineFirstController = new AbortController();
    const deadlineFirst = startProviderResponseDeadline(
      "deadline first",
      1,
      deadlineFirstController.signal,
    );
    await vi.advanceTimersByTimeAsync(1_000);
    deadlineFirstController.abort();
    expect(() => deadlineFirst.assertActive()).toThrow(/timed out after 1s/);
    deadlineFirst.finish();

    const cancellationFirstController = new AbortController();
    const cancellationFirst = startProviderResponseDeadline(
      "cancellation first",
      1,
      cancellationFirstController.signal,
    );
    cancellationFirstController.abort();
    await vi.advanceTimersByTimeAsync(1_000);
    expect(() => cancellationFirst.assertActive()).toThrow(TextGenerationCancelledError);
    cancellationFirst.finish();
  });

  it("removes the external listener when the lifecycle finishes", () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const remove = vi.spyOn(controller.signal, "removeEventListener");
    const deadline = startProviderResponseDeadline("finished lifecycle", 60, controller.signal);

    deadline.finish();
    controller.abort();

    expect(remove).toHaveBeenCalledWith("abort", expect.any(Function));
    expect(() => deadline.assertActive()).not.toThrow();
  });

  it("does not report an outcome when DONE cleanup triggers external cancellation", async () => {
    const controller = new AbortController();
    let outcome = false;
    const body = doneBody(() => {
      controller.abort();
    });
    const pending = consumeWithOutcome(
      () => Promise.resolve(new Response(body, { status: 200 })),
      request(controller.signal),
      () => {
        outcome = true;
      },
    );

    await expect(pending).rejects.toThrow(TextGenerationCancelledError);
    expect(outcome).toBe(false);
  });

  it("does not report an outcome when the deadline elapses during DONE cleanup", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    let cleanupStarted: (() => void) | undefined;
    const started = new Promise<void>((resolve) => {
      cleanupStarted = resolve;
    });
    let outcome = false;
    const body = doneBody(() => {
      cleanupStarted?.();
      return new Promise<void>(() => undefined);
    });
    const pending = consumeWithOutcome(
      () => Promise.resolve(new Response(body, { status: 200 })),
      { ...request(controller.signal), timeoutSeconds: 1 },
      () => {
        outcome = true;
      },
    );
    const settled = expect(pending).rejects.toThrow(/timed out after 1s/);

    await started;
    await vi.advanceTimersByTimeAsync(1_000);

    await settled;
    expect(outcome).toBe(false);
  });
});

async function consumeWithOutcome(
  transport: ProviderTransport,
  streamRequest: StreamingTextRequest,
  onOutcome: () => void,
): Promise<string[]> {
  const values: string[] = [];
  for await (const value of streamProviderTextDeltas(streamRequest, transport, delta, usage, {
    onOutcome,
  })) {
    values.push(value);
  }
  return values;
}
