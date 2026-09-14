import { describe, expect, it } from "vitest";

import {
  coercePayloadToSchema,
  parseProviderJsonObject,
  payloadFromResponseText,
} from "../../src/contexts/ai/infrastructure/providers/provider_payload.js";

describe("provider JSON object parsing", () => {
  it("parses plain, fenced, and embedded JSON objects", () => {
    expect(parseProviderJsonObject('{"a": 1}')).toEqual({ a: 1 });
    expect(parseProviderJsonObject('```json\n{"a": 1}\n```')).toEqual({ a: 1 });
    expect(parseProviderJsonObject('Sure! {"a": {"b": 2}} hope that helps')).toEqual({
      a: { b: 2 },
    });
    expect(parseProviderJsonObject('[{"a": 1}, {"b": 2}]')).toEqual({ a: 1, b: 2 });
  });

  it("brackets inside string literals do not confuse the fragment scanner", () => {
    expect(parseProviderJsonObject('prefix {"a": "value } with bracket {"} suffix')).toEqual({
      a: "value } with bracket {",
    });
  });

  it("raises a provider error naming the non-object response", () => {
    expect(() => parseProviderJsonObject("plain prose only")).toThrow(/not a JSON object/);
  });
});

describe("provider payload coercion", () => {
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
