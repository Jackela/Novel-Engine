import { describe, expect, it } from "vitest";

import { extractDashscopeIncrementalText } from "../../src/contexts/ai/infrastructure/providers/dashscope_protocol.js";

describe("dashscope incremental stream extraction", () => {
  it("reads the top-level delta string without trimming whitespace", () => {
    expect(extractDashscopeIncrementalText({ delta: " hello " })).toBe(" hello ");
    expect(extractDashscopeIncrementalText({ delta: "" })).toBeUndefined();
    expect(extractDashscopeIncrementalText({})).toBeUndefined();
  });

  it("reads native generation incremental chunks via output.choices", () => {
    expect(
      extractDashscopeIncrementalText({
        output: { choices: [{ message: { content: "chunk one" } }] },
      }),
    ).toBe("chunk one");
  });

  it("reads compatible-mode chunks via choices delta content", () => {
    expect(extractDashscopeIncrementalText({ choices: [{ delta: { content: "piece" } }] })).toBe(
      "piece",
    );
  });

  it("reads responses-mode events with an array output of message items", () => {
    expect(
      extractDashscopeIncrementalText({
        output: [
          { type: "reasoning" },
          { type: "message", content: [{ type: "output_text", text: "answer part" }] },
        ],
      }),
    ).toBe("answer part");
  });

  it("reads responses-mode item deltas carrying plain string text", () => {
    expect(
      extractDashscopeIncrementalText({
        output: [{ type: "message", delta: "stream piece" }],
      }),
    ).toBe("stream piece");
    expect(extractDashscopeIncrementalText({ output: [{ text: "fallback text" }] })).toBe(
      "fallback text",
    );
  });

  it("keeps whitespace-only responses-mode deltas significant", () => {
    expect(
      extractDashscopeIncrementalText({
        output: [{ type: "message", content: [{ text: " " }] }],
      }),
    ).toBe(" ");
  });

  it("does not leak reasoning item content or text into stream deltas", () => {
    expect(
      extractDashscopeIncrementalText({
        output: [
          {
            type: "reasoning",
            content: [{ type: "reasoning_text", text: "chain of thought" }],
            text: "chain of thought",
          },
        ],
      }),
    ).toBeUndefined();
    expect(
      extractDashscopeIncrementalText({
        output: [
          { type: "tool_call", content: [{ type: "output_text", text: "tool payload" }] },
          { type: "message", content: [{ type: "output_text", text: "real answer" }] },
        ],
      }),
    ).toBe("real answer");
  });

  it("accepts non-message items only via a top-level string delta", () => {
    expect(
      extractDashscopeIncrementalText({
        output: [{ type: "reasoning", delta: "visible delta" }],
      }),
    ).toBe("visible delta");
    expect(
      extractDashscopeIncrementalText({ output: [{ type: "reasoning", text: "hidden" }] }),
    ).toBeUndefined();
  });

  it("returns undefined for responses-mode events without text", () => {
    expect(extractDashscopeIncrementalText({ output: [] })).toBeUndefined();
    expect(extractDashscopeIncrementalText({ output: [{ type: "reasoning" }] })).toBeUndefined();
  });
});
