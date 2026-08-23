import { describe, expect, it } from "vitest";

import {
  buildProviderCatalog,
  HARD_DEFAULT_MODELS,
  type LlmModelSettings,
  resolveProviderModel,
  resolveReviewModel,
} from "../../src/contexts/ai/application/model_resolution.js";

const noSettings: LlmModelSettings = {};

describe("server-side model resolution chain", () => {
  it("ends at the hard defaults when nothing is configured", () => {
    expect(resolveProviderModel("dashscope", noSettings)).toBe("qwen3.5-flash");
    expect(resolveProviderModel("openai_compatible", noSettings)).toBe("gpt-4o-mini");
    expect(resolveProviderModel("mock", noSettings)).toBe("deterministic-story-v1");
  });

  it("resolves in order: per-provider override, generic fallback, hard default", () => {
    const settings: LlmModelSettings = {
      genericModel: "generic-fallback",
      dashscopeModel: "qwen-override",
      openaiCompatibleModel: "gpt-override",
    };
    expect(resolveProviderModel("dashscope", settings)).toBe("qwen-override");
    expect(resolveProviderModel("openai_compatible", settings)).toBe("gpt-override");
    // The generic fallback applies to providers without their own override.
    expect(resolveProviderModel("mock", settings)).toBe("generic-fallback");
    const fallbackOnly: LlmModelSettings = { genericModel: "generic-fallback" };
    expect(resolveProviderModel("dashscope", fallbackOnly)).toBe("generic-fallback");
    expect(resolveProviderModel("openai_compatible", fallbackOnly)).toBe("generic-fallback");
  });

  it("treats blank overrides as unset so the chain keeps falling through", () => {
    const settings: LlmModelSettings = {
      genericModel: "  ",
      dashscopeModel: "",
      openaiCompatibleModel: "  ",
    };
    expect(resolveProviderModel("dashscope", settings)).toBe("qwen3.5-flash");
    expect(resolveProviderModel("openai_compatible", settings)).toBe("gpt-4o-mini");
    expect(resolveProviderModel("mock", settings)).toBe("deterministic-story-v1");
  });

  it("pins the adjudicated hard defaults", () => {
    expect(HARD_DEFAULT_MODELS).toEqual({
      mock: "deterministic-story-v1",
      dashscope: "qwen3.5-flash",
      openai_compatible: "gpt-4o-mini",
    });
  });
});

describe("review model override groundwork", () => {
  it("uses the review-specific dashscope model when configured", () => {
    const settings: LlmModelSettings = { dashscopeReviewModel: "qwen-reviewer" };
    expect(resolveReviewModel("dashscope", settings)).toBe("qwen-reviewer");
  });

  it("falls back to the resolved dashscope model without the override", () => {
    expect(resolveReviewModel("dashscope", noSettings)).toBe("qwen3.5-flash");
    const settings: LlmModelSettings = { dashscopeModel: "qwen-override" };
    expect(resolveReviewModel("dashscope", settings)).toBe("qwen-override");
  });

  it("resolves non-dashscope review models through the normal chain", () => {
    expect(resolveReviewModel("mock", noSettings)).toBe("deterministic-story-v1");
    expect(resolveReviewModel("openai_compatible", noSettings)).toBe("gpt-4o-mini");
  });
});

describe("provider catalog (GET /api/providers payload)", () => {
  it("lists all three providers with configured/default flags and resolved models", () => {
    const catalog = buildProviderCatalog({
      defaultProvider: "mock",
      settings: noSettings,
      credentials: {},
    });
    expect(catalog).toEqual([
      {
        provider: "mock",
        configured: true,
        model: "deterministic-story-v1",
        is_default: true,
      },
      { provider: "dashscope", configured: false, model: "qwen3.5-flash", is_default: false },
      {
        provider: "openai_compatible",
        configured: false,
        model: "gpt-4o-mini",
        is_default: false,
      },
    ]);
  });

  it("marks keyed providers configured and honors model overrides and the default", () => {
    const catalog = buildProviderCatalog({
      defaultProvider: "dashscope",
      settings: { dashscopeModel: "qwen-override", openaiCompatibleModel: "gpt-override" },
      credentials: { dashscope: "sk-dash", openaiCompatible: "" },
    });
    expect(catalog).toEqual([
      { provider: "mock", configured: true, model: "deterministic-story-v1", is_default: false },
      { provider: "dashscope", configured: true, model: "qwen-override", is_default: true },
      {
        provider: "openai_compatible",
        configured: false,
        model: "gpt-override",
        is_default: false,
      },
    ]);
  });
});
