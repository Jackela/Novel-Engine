import { describe, expect, it } from "vitest";

import { ConfigurationError } from "../../src/shared/infrastructure/config/configuration_error.js";
import {
  integerFrom,
  listFrom,
  numberFrom,
  stringFrom,
} from "../../src/shared/infrastructure/config/env_values.js";

function environment(values: Record<string, string> = {}): ReadonlyMap<string, string> {
  return new Map(Object.entries(values).map(([key, value]) => [key.toLowerCase(), value]));
}

function rejected(run: () => number): Error {
  try {
    run();
  } catch (error) {
    expect(error).toBeInstanceOf(ConfigurationError);
    return error as Error;
  }
  throw new Error("Expected the env reader to reject the value");
}

describe("shared env value readers", () => {
  it("looks keys up case-insensitively and reports an unset key as undefined", () => {
    const env = environment({ API_HOST: "127.0.0.1" });

    expect(stringFrom(env, "API_HOST")).toBe("127.0.0.1");
    expect(stringFrom(env, "api_host")).toBe("127.0.0.1");
    expect(stringFrom(env, "API_PORT")).toBeUndefined();
  });

  it("parses comma-separated lists trimmed and lowercased, listing nothing as undefined", () => {
    const env = environment({ SECURITY_TRUSTED_PROXIES: " 10.0.0.7 , 10.0.0.8 " });
    expect(listFrom(env, "SECURITY_TRUSTED_PROXIES")).toEqual(["10.0.0.7", "10.0.0.8"]);

    const candidates: readonly Record<string, string>[] = [
      { SECURITY_TRUSTED_PROXIES: " , , " },
      { SECURITY_TRUSTED_PROXIES: "" },
      {},
    ];
    for (const values of candidates) {
      expect(listFrom(environment(values), "SECURITY_TRUSTED_PROXIES")).toBeUndefined();
    }
  });

  it("keeps the fallback for unset and blank integer values", () => {
    expect(integerFrom(environment(), "LLM_TIMEOUT", 30, 5, 300)).toBe(30);
    expect(integerFrom(environment({ LLM_TIMEOUT: " " }), "LLM_TIMEOUT", 30, 5, 300)).toBe(30);
    expect(integerFrom(environment({ LLM_TIMEOUT: "" }), "LLM_TIMEOUT", 30, 5, 300)).toBe(30);
  });

  it("accepts the inclusive integer boundaries and names key and value when refusing the rest", () => {
    expect(integerFrom(environment({ LLM_TIMEOUT: "5" }), "LLM_TIMEOUT", 30, 5, 300)).toBe(5);
    expect(integerFrom(environment({ LLM_TIMEOUT: "300" }), "LLM_TIMEOUT", 30, 5, 300)).toBe(300);

    for (const raw of ["slow", "4", "301", "1.5"]) {
      const error = rejected(() =>
        integerFrom(environment({ LLM_TIMEOUT: raw }), "LLM_TIMEOUT", 30, 5, 300),
      );
      expect(error.message).toContain("LLM_TIMEOUT");
      expect(error.message).toContain(`(got "${raw}")`);
    }
  });

  it("reads fractional numbers inside the range and keeps the fallback for blanks", () => {
    expect(numberFrom(environment(), "LLM_RETRY_DELAY", 1, 0.1, 10)).toBe(1);
    expect(numberFrom(environment({ LLM_RETRY_DELAY: "  " }), "LLM_RETRY_DELAY", 1, 0.1, 10)).toBe(
      1,
    );
    expect(numberFrom(environment({ LLM_RETRY_DELAY: "0.1" }), "LLM_RETRY_DELAY", 1, 0.1, 10)).toBe(
      0.1,
    );
    expect(numberFrom(environment({ LLM_RETRY_DELAY: "2.5" }), "LLM_RETRY_DELAY", 1, 0.1, 10)).toBe(
      2.5,
    );
    expect(numberFrom(environment({ LLM_RETRY_DELAY: "10" }), "LLM_RETRY_DELAY", 1, 0.1, 10)).toBe(
      10,
    );
  });

  it("refuses non-numeric, non-finite, and out-of-range numbers with key and value", () => {
    for (const raw of ["later", "0.09", "10.1", "Infinity", "NaN"]) {
      const error = rejected(() =>
        numberFrom(environment({ LLM_RETRY_DELAY: raw }), "LLM_RETRY_DELAY", 1, 0.1, 10),
      );
      expect(error.message).toContain("LLM_RETRY_DELAY");
      expect(error.message).toContain(`(got "${raw}")`);
    }
  });
});
