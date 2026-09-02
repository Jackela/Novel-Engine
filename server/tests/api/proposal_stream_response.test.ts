import { EventEmitter } from "node:events";

import { afterEach, describe, expect, it, vi } from "vitest";

import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import {
  ProposalStreamDrainTimeoutError,
  writeProposalStreamResponse,
} from "../../src/contexts/studio/interface/http/proposal_stream_response.js";

class FakeResponse extends EventEmitter {
  readonly chunks: string[] = [];
  readonly writeResults: boolean[] = [];
  destroyError: Error | undefined;
  destroyed = false;
  emitCloseOnEnd = false;
  writableFinished = false;

  writeHead(): this {
    return this;
  }

  write(chunk: string): boolean {
    this.chunks.push(chunk);
    return this.writeResults.shift() ?? true;
  }

  end(): this {
    this.writableFinished = true;
    if (this.emitCloseOnEnd) {
      this.emit("finish");
      this.emit("close");
    }
    return this;
  }

  destroy(error?: Error): this {
    this.destroyError = error;
    this.destroyed = true;
    return this;
  }
}

function scriptedFrames(results: Array<IteratorResult<ProposalStreamFrame, void>>): AsyncGenerator<
  ProposalStreamFrame,
  void,
  void
> & {
  next: ReturnType<typeof vi.fn>;
  return: ReturnType<typeof vi.fn>;
} {
  const next = vi.fn(async () => results.shift() ?? { done: true, value: undefined });
  const close = vi.fn(async () => ({ done: true, value: undefined }) as IteratorReturnResult<void>);
  return {
    next,
    return: close,
    throw: vi.fn(async (error: unknown) => Promise.reject(error)),
    [Symbol.asyncIterator]() {
      return this;
    },
    [Symbol.asyncDispose]: async () => {
      await close();
    },
  } as AsyncGenerator<ProposalStreamFrame, void, void> & {
    next: ReturnType<typeof vi.fn>;
    return: ReturnType<typeof vi.fn>;
  };
}

describe("proposal stream response writer", () => {
  afterEach(() => vi.useRealTimers());

  it("writes an accepted frame once before pulling the next frame", async () => {
    const response = new FakeResponse();
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "first" } },
      { done: true, value: undefined },
    ]);

    await writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect: new AbortController(),
      hijack: () => {},
    });

    expect(response.chunks).toEqual(['data: {"type":"delta","text":"first"}\n\n']);
    expect(frames.next).toHaveBeenCalledTimes(2);
    expect(frames.return).toHaveBeenCalledTimes(1);
    expect(response.writableFinished).toBe(true);
  });

  it("does not pull or rewrite after backpressure until drain", async () => {
    const response = new FakeResponse();
    response.writeResults.push(false);
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "buffered" } },
      { done: true, value: undefined },
    ]);

    const writing = writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect: new AbortController(),
      hijack: () => {},
    });
    await vi.waitFor(() => expect(response.chunks).toHaveLength(1));

    expect(frames.next).toHaveBeenCalledTimes(1);
    expect(response.chunks).toEqual(['data: {"type":"delta","text":"buffered"}\n\n']);
    response.emit("drain");
    await writing;

    expect(frames.next).toHaveBeenCalledTimes(2);
    expect(response.chunks).toHaveLength(1);
  });

  it("resumes once per drain without accumulating temporary listeners", async () => {
    const response = new FakeResponse();
    response.writeResults.push(false, false);
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "one" } },
      { done: false, value: { type: "delta", text: "two" } },
      { done: true, value: undefined },
    ]);
    const writing = writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect: new AbortController(),
      hijack: () => {},
    });

    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));
    response.emit("drain");
    response.emit("drain");
    await vi.waitFor(() => expect(response.chunks).toHaveLength(2));
    expect(frames.next).toHaveBeenCalledTimes(2);
    expect(response.listenerCount("drain")).toBe(1);

    response.emit("drain");
    await writing;
    expect(frames.next).toHaveBeenCalledTimes(3);
    expect(response.listenerCount("drain")).toBe(0);
  });

  it("times out a stalled drain after 30 seconds and ignores late drain", async () => {
    vi.useFakeTimers();
    const response = new FakeResponse();
    response.writeResults.push(false);
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "stalled" } },
      { done: true, value: undefined },
    ]);
    const disconnect = new AbortController();
    const writing = writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect,
      hijack: () => {},
    });
    const outcome = writing.then(
      () => "resolved" as const,
      (error: unknown) => error,
    );
    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));

    await vi.advanceTimersByTimeAsync(29_999);
    expect(frames.next).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    const observed = await Promise.race([
      outcome,
      new Promise<"pending">((resolve) => queueMicrotask(() => resolve("pending"))),
    ]);

    expect(observed).toBeInstanceOf(ProposalStreamDrainTimeoutError);
    expect(observed).toMatchObject({ code: "PROPOSAL_STREAM_DRAIN_TIMEOUT" });
    expect(disconnect.signal.aborted).toBe(true);
    expect(response.destroyed).toBe(true);
    expect(response.destroyError).toBe(observed);
    expect(response.writableFinished).toBe(false);
    expect(frames.return).toHaveBeenCalledTimes(1);
    response.emit("drain");
    await Promise.resolve();
    expect(frames.next).toHaveBeenCalledTimes(1);
    expect(response.listenerCount("drain")).toBe(0);
  });

  it("stops a pending drain when request cancellation wins", async () => {
    vi.useFakeTimers();
    const response = new FakeResponse();
    response.writeResults.push(false);
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "pending" } },
      { done: true, value: undefined },
    ]);
    const disconnect = new AbortController();
    const writing = writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect,
      hijack: () => {},
    });
    const outcome = writing.then(
      () => "resolved" as const,
      (error: unknown) => error,
    );
    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));

    disconnect.abort();
    await vi.waitFor(() => expect(frames.return).toHaveBeenCalledTimes(1));
    const observed = await outcome;

    expect(observed).toBe("resolved");
    expect(frames.next).toHaveBeenCalledTimes(1);
    expect(frames.return).toHaveBeenCalledTimes(1);
    expect(response.writableFinished).toBe(false);
    expect(response.destroyed).toBe(false);
    response.emit("drain");
    await Promise.resolve();
    expect(frames.next).toHaveBeenCalledTimes(1);
  });

  it.each(["response", "socket"] as const)(
    "treats a premature %s close as cancellation while drain is pending",
    async (source) => {
      vi.useFakeTimers();
      const response = new FakeResponse();
      const socket = new EventEmitter();
      response.writeResults.push(false);
      const frames = scriptedFrames([
        { done: false, value: { type: "delta", text: "pending" } },
        { done: true, value: undefined },
      ]);
      const disconnect = new AbortController();
      const writing = writeProposalStreamResponse({
        response,
        socket,
        frames,
        disconnect,
        hijack: () => {},
      });
      await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));

      (source === "response" ? response : socket).emit("close");
      await writing;

      expect(disconnect.signal.aborted).toBe(true);
      expect(frames.next).toHaveBeenCalledTimes(1);
      expect(frames.return).toHaveBeenCalledTimes(1);
      expect(response.writableFinished).toBe(false);
      expect(response.destroyed).toBe(false);
      response.emit("drain");
      await Promise.resolve();
      expect(frames.next).toHaveBeenCalledTimes(1);
    },
  );

  it("keeps the exact response error first when generator cleanup also fails", async () => {
    vi.useFakeTimers();
    const response = new FakeResponse();
    const socket = new EventEmitter();
    response.writeResults.push(false);
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "pending" } },
      { done: true, value: undefined },
    ]);
    const responseError = new Error("response transport failed");
    const cleanupError = new Error("provider cleanup failed");
    frames.return.mockRejectedValueOnce(cleanupError);
    const disconnect = new AbortController();
    const writing = writeProposalStreamResponse({
      response,
      socket,
      frames,
      disconnect,
      hijack: () => {},
    });
    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));

    response.emit("error", responseError);
    response.emit("close");
    socket.emit("close");
    disconnect.abort();
    response.emit("drain");

    const failure = await writing.catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(AggregateError);
    expect((failure as AggregateError).errors).toEqual([responseError, cleanupError]);
    expect(frames.next).toHaveBeenCalledTimes(1);
    expect(frames.return).toHaveBeenCalledTimes(1);
  });

  it("does not treat the normal finish then close sequence as cancellation", async () => {
    const response = new FakeResponse();
    response.emitCloseOnEnd = true;
    const disconnect = new AbortController();
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "complete" } },
      { done: true, value: undefined },
    ]);

    await writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect,
      hijack: () => {},
    });

    expect(disconnect.signal.aborted).toBe(false);
    expect(response.writableFinished).toBe(true);
    expect(frames.return).toHaveBeenCalledTimes(1);
  });
});
