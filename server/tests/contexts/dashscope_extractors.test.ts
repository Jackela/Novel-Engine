import { describe, expect, it } from "vitest";

import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  extractDashscopeGenerationText,
  extractDashscopeResponsesText,
} from "../../src/contexts/ai/infrastructure/providers/dashscope_extractors.js";

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
