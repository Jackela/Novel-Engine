import { describe, expect, it } from "vitest";

import { createShutdownSignalLatch } from "../../../src/apps/cli/shutdown_signals.js";
import { FakeShutdownSignalSource } from "./shutdown_signal_fixtures.js";

describe("shutdown signal latch", () => {
  it.each([
    ["SIGINT", "SIGTERM"],
    ["SIGTERM", "SIGINT"],
  ] as const)("keeps %s as the first cause when %s follows", async (first, second) => {
    const source = new FakeShutdownSignalSource();
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
    const source = new FakeShutdownSignalSource(registrationFailure);

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
