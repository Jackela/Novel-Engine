import { EventEmitter } from "node:events";

import { type Mock, vi } from "vitest";

import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";

/**
 * Test doubles for the proposal SSE response writer: one raw response stand-in
 * that records what the writer sent, and one scripted frame generator.
 */

export class FakeResponse extends EventEmitter {
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

/**
 * The scripted generator with its inspectable mock methods typed explicitly, so
 * async implementations stay assignable (untyped `vi.fn()` reads as a void
 * return to the type-aware lint).
 */
export type ScriptedFrames = AsyncGenerator<ProposalStreamFrame, void, void> & {
  next: Mock<() => Promise<IteratorResult<ProposalStreamFrame, void>>>;
  return: Mock<() => Promise<IteratorReturnResult<void>>>;
};

export function scriptedFrames(
  results: Array<IteratorResult<ProposalStreamFrame, void>>,
): ScriptedFrames {
  const next = vi.fn<() => Promise<IteratorResult<ProposalStreamFrame, void>>>(async () => {
    return results.shift() ?? { done: true, value: undefined };
  });
  const close = vi.fn<() => Promise<IteratorReturnResult<void>>>(async () => {
    return { done: true, value: undefined };
  });
  return {
    next,
    return: close,
    throw: vi.fn<(error: unknown) => Promise<never>>(async (error: unknown) =>
      Promise.reject(error),
    ),
    [Symbol.asyncIterator]() {
      return this;
    },
    [Symbol.asyncDispose]: async () => {
      await close();
    },
  } as ScriptedFrames;
}

/** Drain a writer's await chain without touching the fake clock. */
export async function flushMicrotasks(): Promise<void> {
  for (let index = 0; index < 10; index += 1) await Promise.resolve();
}
