import type { RateLimitDecision, RateLimiter } from "../../application/ports/rate_limit.js";

export interface TokenBucketOptions {
  /** Tokens refilled per second. */
  ratePerSecond: number;
  /** Maximum tokens a bucket can hold (the burst size). */
  capacity: number;
  /** Idle keys are removed after this many seconds to bound memory. */
  keyTtlSeconds?: number;
  /** Monotonic clock in seconds (injectable for tests). */
  clock?: (() => number) | undefined;
  /** check() calls between expired-key sweeps. */
  cleanupInterval?: number;
}

interface Bucket {
  tokens: number;
  lastUpdate: number;
}

/**
 * In-memory token-bucket rate limiter for single-node deployments: each key
 * holds one bucket, requests consume a token, and tokens refill continuously
 * up to the capacity. Keys live in memory only and expire after their TTL.
 */
export class TokenBucketRateLimiter implements RateLimiter {
  private readonly ratePerSecond: number;
  private readonly capacity: number;
  private readonly keyTtlSeconds: number;
  private readonly clock: () => number;
  private readonly cleanupInterval: number;
  private readonly buckets = new Map<string, Bucket>();
  private calls = 0;

  constructor(options: TokenBucketOptions) {
    if (options.ratePerSecond <= 0) {
      throw new Error("ratePerSecond must be positive");
    }
    if (options.capacity < 1) {
      throw new Error("capacity must be at least 1");
    }
    const keyTtlSeconds = options.keyTtlSeconds ?? 3600;
    if (keyTtlSeconds <= 0) {
      throw new Error("keyTtlSeconds must be positive");
    }
    this.ratePerSecond = options.ratePerSecond;
    this.capacity = options.capacity;
    this.keyTtlSeconds = keyTtlSeconds;
    this.clock = options.clock ?? (() => performance.now() / 1000);
    this.cleanupInterval = options.cleanupInterval ?? 100;
  }

  check(key: string): RateLimitDecision {
    const now = this.clock();
    this.calls += 1;
    if (this.calls % this.cleanupInterval === 0) {
      this.sweep(now);
    }
    const bucket = this.buckets.get(key);
    const lastUpdate = bucket?.lastUpdate ?? now;
    const refilled = Math.min(
      this.capacity,
      (bucket?.tokens ?? this.capacity) + (now - lastUpdate) * this.ratePerSecond,
    );
    if (refilled >= 1) {
      this.buckets.set(key, { tokens: refilled - 1, lastUpdate: now });
      return { allowed: true, retryAfterSeconds: 0 };
    }
    this.buckets.set(key, { tokens: refilled, lastUpdate: now });
    const retryAfterSeconds = Math.max(1, Math.ceil((1 - refilled) / this.ratePerSecond));
    return { allowed: false, retryAfterSeconds };
  }

  private sweep(now: number): void {
    for (const [key, bucket] of this.buckets) {
      if (now - bucket.lastUpdate > this.keyTtlSeconds) {
        this.buckets.delete(key);
      }
    }
  }
}
