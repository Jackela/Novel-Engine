import { afterEach, describe, expect, it, vi } from "vitest";

import { frozenRuntime, randomIds, systemClock } from "../../src/platform/kernel/runtime.js";

afterEach(() => {
  vi.useRealTimers();
});

describe("systemClock", () => {
  it("reports whole Unix seconds, truncating milliseconds", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(1_700_000_000_999));
    expect(systemClock.nowSeconds()).toBe(1_700_000_000);
  });

  it("moves with the wall clock between reads", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(1_700_000_010_000));
    const first = systemClock.nowSeconds();
    vi.setSystemTime(new Date(1_700_000_042_500));
    expect(systemClock.nowSeconds() - first).toBe(32);
  });
});

describe("randomIds", () => {
  it("returns a distinct v4 identifier per call", () => {
    const ids = Array.from({ length: 64 }, () => randomIds.next());
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) {
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    }
  });
});

describe("frozenRuntime", () => {
  it("starts at the requested second and advances one second per read", () => {
    const { clock } = frozenRuntime(1_000);
    expect([clock.nowSeconds(), clock.nowSeconds(), clock.nowSeconds()]).toEqual([
      1_000, 1_001, 1_002,
    ]);
  });

  it("defaults to a fixed start when none is given", () => {
    const { clock: first } = frozenRuntime();
    const { clock: second } = frozenRuntime();
    expect(first.nowSeconds()).toBe(1_700_000_000);
    expect(second.nowSeconds()).toBe(1_700_000_000);
  });

  it("zero-pads ids so string order follows issue order", () => {
    const { ids } = frozenRuntime();
    const issued = Array.from({ length: 12 }, () => ids.next());
    expect(issued[0]).toBe("id-000001");
    expect(issued[11]).toBe("id-000012");
    expect([...issued].sort()).toEqual(issued);
  });

  it("keeps independent runtimes isolated from each other", () => {
    const a = frozenRuntime(10);
    const b = frozenRuntime(10);
    a.clock.nowSeconds();
    a.ids.next();
    expect(b.clock.nowSeconds()).toBe(10);
    expect(b.ids.next()).toBe("id-000001");
  });
});
