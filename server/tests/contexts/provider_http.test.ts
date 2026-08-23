import { describe, expect, it } from "vitest";

import {
  classifyTransportRejection,
  effectiveTimeoutSeconds,
  GENERATION_TIMEOUT_FLOOR_SECONDS,
  httpStatusFailure,
  malformedJsonFailure,
  ProviderTransportError,
  providerFailureIsRetryable,
  runWithRetryPolicy,
  timeoutFailure,
} from "../../src/contexts/ai/infrastructure/providers/provider_http.js";

const IMMEDIATE_SLEEP = async () => {};

describe("retry decisions read structured fields only", () => {
  it("retries exactly the adjudicated HTTP status set", () => {
    for (const status of [429, 500, 502, 503, 504]) {
      const failure = httpStatusFailure("context", status, "body");
      expect(providerFailureIsRetryable(failure), `status ${status}`).toBe(true);
      expect(failure.status).toBe(status);
    }
    for (const status of [400, 401, 403, 404, 422, 501]) {
      const failure = httpStatusFailure("context", status, "body");
      expect(providerFailureIsRetryable(failure), `status ${status}`).toBe(false);
    }
  });

  it("retries transport timeouts and malformed JSON responses", () => {
    expect(providerFailureIsRetryable(timeoutFailure("context", 30))).toBe(true);
    expect(providerFailureIsRetryable(malformedJsonFailure("context"))).toBe(true);
    const timeout = timeoutFailure("context", 180);
    expect(timeout.timedOut).toBe(true);
    const malformed = malformedJsonFailure("context");
    expect(malformed.malformedJson).toBe(true);
  });

  it("never consults message text — identical messages, different fields, different decisions", () => {
    const byStatus = new ProviderTransportError("identical message", { status: 503 });
    const byStatusOther = new ProviderTransportError("identical message", { status: 401 });
    expect(providerFailureIsRetryable(byStatus)).toBe(true);
    expect(providerFailureIsRetryable(byStatusOther)).toBe(false);
  });
});

describe("runWithRetryPolicy", () => {
  it("succeeds after a retryable transient failure", async () => {
    let calls = 0;
    const delays: number[] = [];
    const result = await runWithRetryPolicy(
      { maxAttempts: 3, delayMs: 1000, sleep: async (ms) => void delays.push(ms) },
      async () => {
        calls += 1;
        if (calls === 1) {
          throw httpStatusFailure("context", 429, "slow down");
        }
        return "proposal";
      },
    );
    expect(result).toBe("proposal");
    expect(calls).toBe(2);
    expect(delays).toEqual([1000]);
  });

  it("fails with the provider error after the bounded retries", async () => {
    let calls = 0;
    const attempt = runWithRetryPolicy(
      { maxAttempts: 3, delayMs: 1000, sleep: IMMEDIATE_SLEEP },
      async () => {
        calls += 1;
        throw httpStatusFailure("context", 503, "unavailable");
      },
    );
    await expect(attempt).rejects.toBeInstanceOf(ProviderTransportError);
    await expect(attempt).rejects.toThrow(/503/);
    expect(calls).toBe(3);
  });

  it("fails immediately on a non-retryable failure", async () => {
    let calls = 0;
    const attempt = runWithRetryPolicy(
      { maxAttempts: 3, delayMs: 1000, sleep: IMMEDIATE_SLEEP },
      async () => {
        calls += 1;
        throw httpStatusFailure("context", 401, "bad key");
      },
    );
    await expect(attempt).rejects.toThrow(/401/);
    expect(calls).toBe(1);
  });

  it("propagates non-provider errors without retrying", async () => {
    let calls = 0;
    const attempt = runWithRetryPolicy(
      { maxAttempts: 3, delayMs: 1000, sleep: IMMEDIATE_SLEEP },
      async () => {
        calls += 1;
        throw new RangeError("programming error stays visible");
      },
    );
    await expect(attempt).rejects.toBeInstanceOf(RangeError);
    expect(calls).toBe(1);
  });

  it("still applies at least one attempt when configured with zero", async () => {
    let calls = 0;
    await runWithRetryPolicy({ maxAttempts: 0, delayMs: 1, sleep: IMMEDIATE_SLEEP }, async () => {
      calls += 1;
      return 42;
    });
    expect(calls).toBe(1);
  });
});

describe("generation timeout floor", () => {
  it("grants chapter steps at least 180 seconds", () => {
    expect(GENERATION_TIMEOUT_FLOOR_SECONDS).toBe(180);
    expect(effectiveTimeoutSeconds(30, "chapter_draft")).toBe(180);
    expect(effectiveTimeoutSeconds(30, "chapter_revision")).toBe(180);
  });

  it("keeps a larger configured timeout and the base timeout for other steps", () => {
    expect(effectiveTimeoutSeconds(300, "chapter_draft")).toBe(300);
    expect(effectiveTimeoutSeconds(30, "editorial_review")).toBe(30);
  });
});

describe("transport rejection classification", () => {
  it("classifies abort/timeout rejections as retryable timeouts", () => {
    for (const name of ["TimeoutError", "AbortError"]) {
      const rejection = new DOMException("aborted", name);
      const failure = classifyTransportRejection(rejection, "ctx", 180);
      expect(failure.timedOut, name).toBe(true);
      expect(providerFailureIsRetryable(failure)).toBe(true);
      expect(failure.message).toContain("timed out after 180s");
    }
  });

  it("classifies network rejections as non-retryable", () => {
    const failure = classifyTransportRejection(new TypeError("fetch failed"), "ctx", 30);
    expect(providerFailureIsRetryable(failure)).toBe(false);
    expect(failure.message).toContain("fetch failed");
  });

  it("keeps programming errors visible instead of swallowing them", () => {
    expect(() => classifyTransportRejection(new RangeError("boom"), "ctx", 30)).toThrow(
      RangeError,
    );
  });
});
