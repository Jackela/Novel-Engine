import { describe, expect, it, vi } from "vitest";

const factoryCalls = vi.hoisted(() => {
  return [] as Array<[unknown, unknown]>;
});

vi.mock("../../src/contexts/ai/infrastructure/providers/text_provider_factory.js", () => ({
  textProviderFactory: (...args: unknown[]) => {
    factoryCalls.push([args[0], args[1]]);
    return () => {
      throw new Error("factory must not be invoked by assembly tests");
    };
  },
}));

import { buildProviderRuntime } from "../../src/apps/api/provider_runtime.js";
import type { TextProviderFactoryConfiguration } from "../../src/contexts/ai/infrastructure/providers/text_provider_factory.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";

function configFrom(env: Record<string, string>) {
  return loadServerConfig({ env, envFile: null, workingDirectory: "/tmp" });
}

function assembledConfiguration(): TextProviderFactoryConfiguration {
  const lastCall = factoryCalls[factoryCalls.length - 1];
  if (lastCall === undefined) {
    throw new Error("textProviderFactory was never assembled");
  }
  const [, configuration] = lastCall;
  return configuration as TextProviderFactoryConfiguration;
}

describe("provider runtime assembly", () => {
  it("carries the configured stream silence budgets into both HTTP adapters", () => {
    factoryCalls.length = 0;
    buildProviderRuntime(
      configFrom({
        LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "45000",
        LLM_STREAM_IDLE_TIMEOUT_MS: "90000",
        LLM_API_KEY: "assembly-test-credential",
      }),
      {},
    );

    const { adapterOptions } = assembledConfiguration();
    expect(adapterOptions?.dashscope).toMatchObject({
      firstByteTimeoutMs: 45_000,
      idleTimeoutMs: 90_000,
    });
    expect(adapterOptions?.openaiCompatible).toMatchObject({
      firstByteTimeoutMs: 45_000,
      idleTimeoutMs: 90_000,
    });
  });

  it("omits adapter options entirely when no server configuration is present", () => {
    factoryCalls.length = 0;
    buildProviderRuntime(undefined, {});

    const configuration = assembledConfiguration();
    expect(configuration.adapterOptions).toBeUndefined();
  });
});
