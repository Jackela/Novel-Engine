import { describe, expect, it } from "vitest";

import {
  createShutdownSignalLatch,
  type ShutdownSignal,
  type ShutdownSignalHandler,
  type ShutdownSignalSource,
} from "../../../src/apps/cli/shutdown_signals.js";

class FakeSignalSource implements ShutdownSignalSource {
  readonly added: Array<{ signal: ShutdownSignal; handler: ShutdownSignalHandler }> = [];
  readonly removed: Array<{ signal: ShutdownSignal; handler: ShutdownSignalHandler }> = [];
  readonly listeners = new Map<ShutdownSignal, Set<ShutdownSignalHandler>>();

  constructor(private readonly registrationFailure?: Error) {}

  add(signal: ShutdownSignal, handler: ShutdownSignalHandler): void {
    if (signal === "SIGTERM" && this.registrationFailure !== undefined) {
      throw this.registrationFailure;
    }
    this.added.push({ signal, handler });
    const handlers = this.listeners.get(signal) ?? new Set<ShutdownSignalHandler>();
    handlers.add(handler);
    this.listeners.set(signal, handlers);
  }

  remove(signal: ShutdownSignal, handler: ShutdownSignalHandler): void {
    this.removed.push({ signal, handler });
    this.listeners.get(signal)?.delete(handler);
  }

  emit(signal: ShutdownSignal): void {
    for (const handler of this.listeners.get(signal) ?? []) handler();
  }

  listenerCount(signal: ShutdownSignal): number {
    return this.listeners.get(signal)?.size ?? 0;
  }
}

describe("shutdown signal latch", () => {
  it.each([
    ["SIGINT", "SIGTERM"],
    ["SIGTERM", "SIGINT"],
  ] as const)("keeps %s as the first cause when %s follows", async (first, second) => {
    const source = new FakeSignalSource();
    const latch = createShutdownSignalLatch(source);

    source.emit(first);
    source.emit(second);
    source.emit(first);

    await expect(latch.wait).resolves.toBe(first);
    expect(source.listenerCount("SIGINT")).toBe(1);
    expect(source.listenerCount("SIGTERM")).toBe(1);

    latch.dispose();
    latch.dispose();

    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
    expect(source.removed).toEqual(source.added);
  });

  it("rolls back the first exact handler when the second registration fails", () => {
    const registrationFailure = new Error("SIGTERM registration failed");
    const source = new FakeSignalSource(registrationFailure);

    let thrown: unknown;
    try {
      createShutdownSignalLatch(source);
    } catch (error) {
      thrown = error;
    }

    expect(thrown).toBe(registrationFailure);
    expect(source.added).toHaveLength(1);
    expect(source.removed).toEqual(source.added);
    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
  });
});
