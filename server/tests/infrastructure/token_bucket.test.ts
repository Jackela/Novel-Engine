import { describe, expect, it } from "vitest";

import { TokenBucketRateLimiter } from "../../src/shared/infrastructure/rate_limit/token_bucket.js";

/** Manual clock in seconds; tests advance it directly, so no sleeps are needed. */
function manualClock(): { clock: () => number; advanceBy: (seconds: number) => void } {
  let now = 0;
  return {
    clock: () => now,
    advanceBy: (seconds: number) => {
      now += seconds;
    },
  };
}

describe("token-bucket rate limiter", () => {
  it("refills tokens over time so a limited key is allowed again once the window passes", () => {
    const { clock, advanceBy } = manualClock();
    const limiter = new TokenBucketRateLimiter({ ratePerSecond: 1, capacity: 2, clock });

    expect(limiter.check("ip:1").allowed).toBe(true);
    expect(limiter.check("ip:1").allowed).toBe(true);
    expect(limiter.check("ip:1").allowed).toBe(false);

    // Refill is continuous: half a token after half a second must not unblock.
    advanceBy(0.5);
    expect(limiter.check("ip:1").allowed).toBe(false);

    // Two seconds later the bucket is clamped back to full capacity, handing
    // the key two fresh tokens. A limiter that never refills would keep the
    // key denied forever while every test here stays green — that regression
    // is what this pins down.
    advanceBy(2);
    expect(limiter.check("ip:1").allowed).toBe(true);
    expect(limiter.check("ip:1").allowed).toBe(true);
    expect(limiter.check("ip:1").allowed).toBe(false);
  });

  it("rounds retryAfterSeconds up to whole seconds with a floor of one", () => {
    const { clock, advanceBy } = manualClock();
    const limiter = new TokenBucketRateLimiter({ ratePerSecond: 0.45, capacity: 1, clock });

    limiter.check("ip:1");
    // 1 / 0.45 = 2.22… seconds must round up to 3, not down to 2.
    expect(limiter.check("ip:1")).toEqual({ allowed: false, retryAfterSeconds: 3 });

    // After 0.9 s the bucket holds 0.405 tokens; the remaining 0.595 s worth
    // of refill is 1.32… seconds and still rounds up to 2.
    advanceBy(0.9);
    expect(limiter.check("ip:1")).toEqual({ allowed: false, retryAfterSeconds: 2 });

    // A fast refill that needs only 0.01 s more still reports a whole second:
    // the port contract floors retryAfterSeconds at 1 when the key is denied.
    const fast = new TokenBucketRateLimiter({ ratePerSecond: 10, capacity: 1, clock });
    fast.check("ip:2");
    advanceBy(0.09);
    expect(fast.check("ip:2")).toEqual({ allowed: false, retryAfterSeconds: 1 });
  });

  it("sweeps idle keys after the TTL so expired buckets restart fresh", () => {
    const { clock, advanceBy } = manualClock();
    const limiter = new TokenBucketRateLimiter({
      ratePerSecond: 0.001, // refill stays negligible over the test horizon
      capacity: 1,
      keyTtlSeconds: 10,
      cleanupInterval: 1,
      clock,
    });

    expect(limiter.check("stale").allowed).toBe(true);
    advanceBy(10.5);
    // Without the sweep the drained bucket (0.011 tokens after refill) would
    // still deny; a swept key starts over from a fresh full bucket.
    expect(limiter.check("stale").allowed).toBe(true);
  });

  it("keeps recently active keys across sweeps", () => {
    const { clock, advanceBy } = manualClock();
    const limiter = new TokenBucketRateLimiter({
      ratePerSecond: 0.001,
      capacity: 1,
      keyTtlSeconds: 10,
      cleanupInterval: 1,
      clock,
    });

    expect(limiter.check("a").allowed).toBe(true);
    expect(limiter.check("b").allowed).toBe(true);

    // Both buckets are drained; refreshing b resets its TTL stamp.
    advanceBy(5);
    expect(limiter.check("b").allowed).toBe(false);

    advanceBy(5.5);
    // a has been idle for 10.5 s and is swept away, so it restarts fresh;
    // b was active 5.5 s ago and keeps its drained bucket, staying denied.
    expect(limiter.check("a").allowed).toBe(true);
    expect(limiter.check("b").allowed).toBe(false);
  });
});
