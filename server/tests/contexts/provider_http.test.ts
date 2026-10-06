import { describe, expect, it } from "vitest";

import {
  classifyTransportRejection,
  effectiveTimeoutSeconds,
  httpStatusFailure,
  LONG_FORM_TIMEOUT_FLOOR_SECONDS,
  malformedJsonFailure,
  ProviderTransportError,
  providerFailureIsRetryable,
  runWithRetryPolicy,
  timeoutFailure,
  usageToken,
} from "../../src/contexts/ai/infrastructure/providers/provider_http.js";

const IMMEDIATE_SLEEP = async () => {};

describe("provider usage token parsing", () => {
  it.each([
    { value: 0, expected: 0 },
    { value: Number.MAX_SAFE_INTEGER, expected: Number.MAX_SAFE_INTEGER },
    { value: Number.MAX_SAFE_INTEGER + 1, expected: null },
    { value: 1e308, expected: null },
    { value: Number.POSITIVE_INFINITY, expected: null },
    { value: -1, expected: null },
    { value: 1.5, expected: null },
  ])("normalizes $value to $expected", ({ value, expected }) => {
    expect(usageToken(value)).toBe(expected);
  });
});

describe("retry decisions read structured fields only", () => {
  it("retries exactly the adjudicated HTTP status set", () => {
    for (const status of [429, 500, 502, 503, 504]) {
      const failure = httpStatusFailure("context", status);
      expect(providerFailureIsRetryable(failure), `status ${status}`).toBe(true);
      expect(failure.status).toBe(status);
    }
    for (const status of [400, 401, 403, 404, 422, 501]) {
      const failure = httpStatusFailure("context", status);
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
          throw httpStatusFailure("context", 429);
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
        throw httpStatusFailure("context", 503);
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
        throw httpStatusFailure("context", 401);
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

  it("caps caller-supplied retry attempts at three total calls", async () => {
    let calls = 0;
    const attempt = runWithRetryPolicy(
      { maxAttempts: 4, delayMs: 1, sleep: IMMEDIATE_SLEEP },
      async () => {
        calls += 1;
        throw httpStatusFailure("context", 503);
      },
    );
    await expect(attempt).rejects.toBeInstanceOf(ProviderTransportError);
    expect(calls).toBe(3);
  });
});

describe("provider public failures", () => {
  it("builds an HTTP failure only from trusted context and numeric status", () => {
    const failure = httpStatusFailure("context", 401);

    expect(failure.message).toBe("context: provider returned HTTP 401.");
    expect(failure.status).toBe(401);
    expect(providerFailureIsRetryable(failure)).toBe(false);
  });
});

describe("long-form timeout floor", () => {
  it("grants every whole-manuscript step at least 180 seconds (DR-025: review included)", () => {
    expect(LONG_FORM_TIMEOUT_FLOOR_SECONDS).toBe(180);
    for (const step of [
      "chapter_draft",
      "chapter_revision",
      "editorial_review",
      "lore_extract",
    ] as const) {
      expect(effectiveTimeoutSeconds(30, step), step).toBe(180);
      expect(effectiveTimeoutSeconds(1, step), step).toBe(180);
    }
  });

  it("keeps a larger configured timeout and still raises a shorter one to the floor", () => {
    expect(effectiveTimeoutSeconds(300, "chapter_draft")).toBe(300);
    expect(effectiveTimeoutSeconds(300, "editorial_review")).toBe(300);
    expect(effectiveTimeoutSeconds(180, "editorial_review")).toBe(180);
    // Every step of today's closed vocabulary is long-form; a shorter step
    // would keep its base timeout only by staying out of the floor list.
    expect(effectiveTimeoutSeconds(40, "chapter_draft")).toBe(180);
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
    const credential = "transport-credential-that-must-not-reach-a-job";
    const prefix = "transport-prefix-that-must-not-reach-a-job";
    const failure = classifyTransportRejection(
      new TypeError(`${prefix}:${credential}:${prefix}`),
      "ctx",
      30,
    );
    expect(providerFailureIsRetryable(failure)).toBe(false);
    expect(failure.message).toBe("ctx: transport request failed.");
    expect(failure.message).not.toContain(credential);
    expect(failure.message).not.toContain(prefix);
  });

  it("keeps programming errors visible instead of swallowing them", () => {
    expect(() => classifyTransportRejection(new RangeError("boom"), "ctx", 30)).toThrow(RangeError);
  });
});
