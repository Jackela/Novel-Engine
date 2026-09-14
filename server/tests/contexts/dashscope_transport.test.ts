import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { resolveDashscopeTransport } from "../../src/contexts/ai/infrastructure/providers/dashscope_transport.js";

const DASHSCOPE_API_PATH_SEGMENTS = {
  root: "api",
  nativeVersion: "v1",
  compatibleMode: "compatible-mode",
} as const;

function expectedApiBase(origin: string, segments: readonly string[]): string {
  return new URL(segments.join("/"), `${origin}/`).toString().replace(/\/$/u, "");
}

function expectedNativeApiBase(origin: string): string {
  return expectedApiBase(origin, [
    DASHSCOPE_API_PATH_SEGMENTS.root,
    DASHSCOPE_API_PATH_SEGMENTS.nativeVersion,
  ]);
}

/** Official OpenAI-compatible Responses path (#502), without the responses endpoint suffix. */
function expectedResponsesApiBase(origin: string): string {
  return expectedApiBase(origin, [
    DASHSCOPE_API_PATH_SEGMENTS.compatibleMode,
    DASHSCOPE_API_PATH_SEGMENTS.nativeVersion,
  ]);
}

function task(): TextGenerationTask {
  return {
    step: "chapter_draft",
    systemPrompt: "be an author",
    userPrompt: "write chapter 2",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2 },
  };
}

describe("dashscope transport modes", () => {
  it("defaults to multimodal generation against the native base", () => {
    const transport = resolveDashscopeTransport("multimodal_generation");
    expect(transport.endpointPath()).toBe("/services/aigc/multimodal-generation/generation");
    expect(transport.normalizeApiBase(undefined)).toBe(
      expectedNativeApiBase("https://dashscope.aliyuncs.com"),
    );
    const payload = transport.buildRequestPayload("qwen3.5-flash", task());
    expect(payload.model).toBe("qwen3.5-flash");
    expect(payload.input).toEqual({
      messages: [
        { role: "system", content: [{ text: expect.stringContaining("be an author") }] },
        { role: "user", content: [{ text: expect.stringContaining("write chapter 2") }] },
      ],
    });
    expect(payload.parameters).toEqual({
      temperature: 0.7,
      enable_thinking: false,
      result_format: "message",
      response_format: { type: "json_object" },
    });
  });

  it("uses plain string message content for the text-generation mode", () => {
    const transport = resolveDashscopeTransport("text_generation");
    expect(transport.endpointPath()).toBe("/services/aigc/text-generation/generation");
    const payload = transport.buildRequestPayload("qwen3.5-flash", task());
    expect(payload.input.messages[0]).toEqual({
      role: "system",
      content: expect.any(String),
    });
  });

  it("uses the responses API endpoint and single input string", () => {
    const transport = resolveDashscopeTransport("responses");
    expect(transport.endpointPath()).toBe("/responses");
    expect(transport.normalizeApiBase(undefined)).toBe(
      expectedResponsesApiBase("https://dashscope.aliyuncs.com"),
    );
    const payload = transport.buildRequestPayload("qwen3.5-flash", task());
    expect(typeof payload.input).toBe("string");
    expect(payload.input).toContain("System:\n");
    expect(payload.input).toContain("User:\n");
    expect(payload.temperature).toBe(0.7);
    expect(payload.response_format).toEqual({ type: "json_object" });
  });

  it("rewrites a compatible-mode base back to the native generation base", () => {
    const transport = resolveDashscopeTransport("multimodal_generation");
    expect(
      transport.normalizeApiBase(`${expectedResponsesApiBase("https://dashscope.example.com")}/`),
    ).toBe(expectedNativeApiBase("https://dashscope.example.com"));
  });

  it("passes an explicit api base through for the responses transport", () => {
    const transport = resolveDashscopeTransport("responses");
    expect(transport.normalizeApiBase("https://proxy.example.com/custom")).toBe(
      "https://proxy.example.com/custom",
    );
    expect(transport.normalizeApiBase("https://proxy.example.com/custom/")).toBe(
      "https://proxy.example.com/custom",
    );
  });

  it("rejects a non-absolute api base for the responses transport", () => {
    const transport = resolveDashscopeTransport("responses");
    expect(() => transport.normalizeApiBase("not-an-absolute-url")).toThrow(
      TextGenerationProviderError,
    );
  });
});
