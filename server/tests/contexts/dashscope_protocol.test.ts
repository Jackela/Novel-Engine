import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { parseDashscopeJsonObject } from "../../src/contexts/ai/infrastructure/providers/dashscope_json.js";
import {
  coercePayloadToSchema,
  payloadFromResponseText,
} from "../../src/contexts/ai/infrastructure/providers/dashscope_payload.js";
import {
  extractDashscopeGenerationText,
  extractDashscopeResponsesText,
  resolveDashscopeTransport,
} from "../../src/contexts/ai/infrastructure/providers/dashscope_protocol.js";

const DASHSCOPE_API_PATH_SEGMENTS = {
  root: "api",
  nativeVersion: "v1",
  compatibleVersion: "v2",
  applications: "apps",
  protocols: "protocols",
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

function expectedCompatibleModeApiBase(origin: string): string {
  return expectedApiBase(origin, [
    DASHSCOPE_API_PATH_SEGMENTS.root,
    DASHSCOPE_API_PATH_SEGMENTS.compatibleVersion,
    DASHSCOPE_API_PATH_SEGMENTS.applications,
    DASHSCOPE_API_PATH_SEGMENTS.protocols,
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
      expectedCompatibleModeApiBase("https://dashscope.aliyuncs.com"),
    );
    const payload = transport.buildRequestPayload("qwen3.5-flash", task());
    expect(typeof payload.input).toBe("string");
    expect(payload.input).toContain("System:\n");
    expect(payload.input).toContain("User:\n");
    expect(payload.temperature).toBe(0.7);
  });

  it("rewrites a compatible-mode base back to the native generation base", () => {
    const transport = resolveDashscopeTransport("multimodal_generation");
    expect(
      transport.normalizeApiBase(
        `${expectedCompatibleModeApiBase("https://dashscope.example.com")}/`,
      ),
    ).toBe(expectedNativeApiBase("https://dashscope.example.com"));
  });

  it("forces the compatible-mode base for the responses transport", () => {
    const transport = resolveDashscopeTransport("responses");
    expect(transport.normalizeApiBase("https://proxy.example.com/custom")).toBe(
      expectedCompatibleModeApiBase("https://proxy.example.com"),
    );
  });
});

describe("dashscope response text extraction", () => {
  it("reads the first choice message content, joining multimodal text parts", () => {
    expect(
      extractDashscopeGenerationText({
        output: { choices: [{ message: { content: [{ text: "part one " }, { text: "two" }] } }] },
      }),
    ).toBe("part one two");
  });

  it("falls back to output.text when no choices exist", () => {
    expect(extractDashscopeGenerationText({ output: { text: "  prose  " } })).toBe("prose");
  });

  it("rejects shapeless responses", () => {
    expect(() => extractDashscopeGenerationText({})).toThrow(TextGenerationProviderError);
    expect(() => extractDashscopeGenerationText({ output: {} })).toThrow(
      /missing structured message content/,
    );
  });

  it("reads the responses API message output", () => {
    expect(
      extractDashscopeResponsesText({
        output: [{ type: "reasoning" }, { type: "message", content: [{ text: "answer" }] }],
      }),
    ).toBe("answer");
    expect(() => extractDashscopeResponsesText({ output: [] })).toThrow(/missing message text/);
  });
});

describe("dashscope JSON object parsing", () => {
  it("parses plain, fenced, and embedded JSON objects", () => {
    expect(parseDashscopeJsonObject('{"a": 1}')).toEqual({ a: 1 });
    expect(parseDashscopeJsonObject('```json\n{"a": 1}\n```')).toEqual({ a: 1 });
    expect(parseDashscopeJsonObject('Sure! {"a": {"b": 2}} hope that helps')).toEqual({
      a: { b: 2 },
    });
    expect(parseDashscopeJsonObject('[{"a": 1}, {"b": 2}]')).toEqual({ a: 1, b: 2 });
  });

  it("brackets inside string literals do not confuse the fragment scanner", () => {
    expect(parseDashscopeJsonObject('prefix {"a": "value } with bracket {"} suffix')).toEqual({
      a: "value } with bracket {",
    });
  });

  it("raises a provider error naming the non-object response", () => {
    expect(() => parseDashscopeJsonObject("plain prose only")).toThrow(/not a JSON object/);
  });
});

describe("dashscope payload coercion", () => {
  const schema = {
    chapter_markdown: { type: "string" },
    items: { type: "array" },
    count: { type: "integer" },
    nested: { type: "object", properties: { inner: { type: "string" } } },
  };

  it("coerces scalars into the wrapper shapes and keeps arrays", () => {
    const coerced = coercePayloadToSchema(
      { chapter_markdown: "  trimmed  ", items: ["a"], count: "7", nested: { inner: 5 } },
      schema,
    );
    expect(coerced.chapter_markdown).toBe("trimmed");
    expect(coerced.items).toEqual(["a"]);
    expect(coerced.count).toBe(7);
    expect(coerced.nested).toEqual({ inner: "5" });
  });

  it("wraps non-array items and falls back to chapter prose for non-object responses", () => {
    const coerced = coercePayloadToSchema({ items: "single" }, schema);
    expect(coerced.items).toEqual(["single"]);
    const fallback = payloadFromResponseText("# Just prose\n\nChapter text.", {
      chapter_markdown: { type: "string" },
    });
    expect(fallback).toEqual({ chapter_markdown: "# Just prose\n\nChapter text." });
  });

  it("re-raises the parse error when the schema cannot rescue non-object text", () => {
    expect(() => payloadFromResponseText("prose without a chapter schema", {})).toThrow(
      /not a JSON object/,
    );
  });
});
