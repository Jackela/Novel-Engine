import { describe, expect, it } from "vitest";

import { ConfigurationError } from "../../src/shared/infrastructure/config/configuration_error.js";
import { loadLlmServerConfig } from "../../src/shared/infrastructure/config/provider_config.js";

function environment(values: Record<string, string> = {}): ReadonlyMap<string, string> {
  return new Map(Object.entries(values).map(([key, value]) => [key.toLowerCase(), value]));
}

function rejected(values: Record<string, string>): Error {
  try {
    loadLlmServerConfig(environment(values));
  } catch (error) {
    expect(error).toBeInstanceOf(ConfigurationError);
    return error as Error;
  }
  throw new Error("Expected provider configuration to be rejected");
}

describe("provider configuration parser", () => {
  it("uses the server-owned defaults without exposing a model choice", () => {
    expect(loadLlmServerConfig(environment())).toEqual({
      defaultProvider: "mock",
      genericModel: undefined,
      dashscopeModel: undefined,
      dashscopeReviewModel: undefined,
      openaiCompatibleModel: undefined,
      dashscopeApiKey: undefined,
      dashscopeApiBase: undefined,
      openaiCompatibleApiKey: undefined,
      openaiCompatibleApiBase: undefined,
      dashscopeTransportMode: "multimodal_generation",
      timeoutSeconds: 30,
      retryAttempts: 3,
      retryDelayMs: 1_000,
      streamFirstByteTimeoutMs: 30_000,
      streamIdleTimeoutMs: 60_000,
    });
  });

  it("treats blank provider settings and credentials as unset", () => {
    expect(
      loadLlmServerConfig(
        environment({
          LLM_PROVIDER: "  ",
          LLM_MODEL: "  ",
          DASHSCOPE_MODEL: " ",
          DASHSCOPE_REVIEW_MODEL: " ",
          OPENAI_COMPATIBLE_MODEL: " ",
          DASHSCOPE_API_KEY: " ",
          DASHSCOPE_API_BASE: " ",
          LLM_API_KEY: " ",
          OPENAI_API_KEY: " ",
          LLM_API_BASE: " ",
          OPENAI_API_BASE: " ",
          DASHSCOPE_TRANSPORT_MODE: " ",
          LLM_TIMEOUT: " ",
          LLM_RETRY_ATTEMPTS: " ",
          LLM_RETRY_DELAY: " ",
          LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: " ",
          LLM_STREAM_IDLE_TIMEOUT_MS: " ",
        }),
      ),
    ).toMatchObject({
      defaultProvider: "mock",
      dashscopeTransportMode: "multimodal_generation",
      timeoutSeconds: 30,
      retryAttempts: 3,
      retryDelayMs: 1_000,
      streamFirstByteTimeoutMs: 30_000,
      streamIdleTimeoutMs: 60_000,
      dashscopeApiKey: undefined,
      openaiCompatibleApiKey: undefined,
    });
  });

  it("rejects invalid controls without leaking credential-shaped values", () => {
    const credential = "test-credential-must-not-leak";
    const cases: readonly [Record<string, string>, string][] = [
      [{ LLM_PROVIDER: credential }, "LLM_PROVIDER"],
      [{ DASHSCOPE_TRANSPORT_MODE: "legacy" }, "DASHSCOPE_TRANSPORT_MODE"],
      [{ LLM_TIMEOUT: "slow" }, "LLM_TIMEOUT"],
      [{ LLM_TIMEOUT: "4" }, "LLM_TIMEOUT"],
      [{ LLM_RETRY_ATTEMPTS: "0" }, "LLM_RETRY_ATTEMPTS"],
      [{ LLM_RETRY_ATTEMPTS: "4" }, "LLM_RETRY_ATTEMPTS"],
      [{ LLM_RETRY_DELAY: "later" }, "LLM_RETRY_DELAY"],
      [{ LLM_RETRY_DELAY: "0.09" }, "LLM_RETRY_DELAY"],
      [{ LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "soon" }, "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS"],
      [{ LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "0" }, "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS"],
      [{ LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "-5" }, "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS"],
      [{ LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "300001" }, "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS"],
      [{ LLM_STREAM_IDLE_TIMEOUT_MS: "soon" }, "LLM_STREAM_IDLE_TIMEOUT_MS"],
      [{ LLM_STREAM_IDLE_TIMEOUT_MS: "0" }, "LLM_STREAM_IDLE_TIMEOUT_MS"],
      [{ LLM_STREAM_IDLE_TIMEOUT_MS: "-5" }, "LLM_STREAM_IDLE_TIMEOUT_MS"],
      [{ LLM_STREAM_IDLE_TIMEOUT_MS: "300001" }, "LLM_STREAM_IDLE_TIMEOUT_MS"],
    ];

    for (const [values, expectedSetting] of cases) {
      const error = rejected(values);
      expect(error.message).toContain(expectedSetting);
      expect(error.message).not.toContain(credential);
    }
  });

  it("parses configured stream silence budgets within the adjudicated bounds", () => {
    expect(
      loadLlmServerConfig(
        environment({
          LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "45000",
          LLM_STREAM_IDLE_TIMEOUT_MS: "90000",
        }),
      ),
    ).toMatchObject({
      streamFirstByteTimeoutMs: 45_000,
      streamIdleTimeoutMs: 90_000,
    });
    expect(
      loadLlmServerConfig(
        environment({
          LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "1",
          LLM_STREAM_IDLE_TIMEOUT_MS: "300000",
        }),
      ),
    ).toMatchObject({
      streamFirstByteTimeoutMs: 1,
      streamIdleTimeoutMs: 300_000,
    });
  });
});
