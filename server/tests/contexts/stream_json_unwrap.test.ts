import { describe, expect, it } from "vitest";

import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { createChapterMarkdownUnwrapper } from "../../src/contexts/ai/infrastructure/providers/stream_json_unwrap.js";

/** Feeds each fragment in order, finishes the stream, and joins the prose pieces. */
function unwrapped(fragments: readonly string[]): string {
  const unwrapper = createChapterMarkdownUnwrapper();
  const pieces: string[] = [];
  for (const fragment of fragments) {
    const piece = unwrapper.feed(fragment);
    if (piece !== undefined) pieces.push(piece);
  }
  unwrapper.finish();
  return pieces.join("");
}

function expectContractFailure(run: () => void): void {
  expect(run).toThrow(TextGenerationProviderError);
  expect(run).toThrow(/chapter_markdown JSON contract/);
}

describe("stream chapter_markdown unwrapper (#496)", () => {
  it("unwraps a whole payload fed in one fragment", () => {
    const value = "# The Crossing\n\nNight fell over the harbor.";
    expect(unwrapped([JSON.stringify({ chapter_markdown: value })])).toBe(value);
  });

  it("reproduces the value byte-for-byte when fed one character at a time", () => {
    const value =
      '# Title\n\nA "quoted" \\backslash\\, a /slash/, \t tab, \r cr, \b and \f form feed — é \u{1F600}';
    const payload = JSON.stringify({ chapter_markdown: value });
    expect(unwrapped([...payload])).toBe(value);
  });

  it("decodes escape sequences split across fragment boundaries", () => {
    expect(unwrapped(['{"chapter_markdown": "a\\', 'nb" }'])).toBe("a\nb");
    expect(unwrapped(['{"chapter_markdown": "say \\', '"hi" }'])).toBe('say "hi');
    expect(unwrapped(['{"chapter_markdown": "a\\', '\\b" }'])).toBe("a\\b");
    expect(unwrapped(['{"chapter_markdown": "a\\/b" }'])).toBe("a/b");
    expect(unwrapped(['{"chapter_markdown": "\\', 'u0041" }'])).toBe("A");
    expect(unwrapped(['{"chapter_markdown": "\\u0', '041" }'])).toBe("A");
    expect(unwrapped(['{"chapter_markdown": "\\ud83d', '\\ude00" }'])).toBe("\u{1F600}");
  });

  it("tolerates pretty-printed payloads", () => {
    const pretty = `{\n  "chapter_number": 3,\n  "chapter_markdown": "Prose.\\n\\nMore prose.\\n"\n}`;
    expect(unwrapped([pretty])).toBe("Prose.\n\nMore prose.\n");
  });

  it("skips scalar sibling keys before and after the target key", () => {
    const payload = JSON.stringify({
      chapter_number: 12,
      enable_thinking: false,
      note: 'mentions "chapter_markdown" and : colons inside',
      missing: null,
      chapter_markdown: "Inner prose.",
      trailing: 1.5,
    });
    expect(unwrapped([payload])).toBe("Inner prose.");
  });

  it("throws at finish when chapter_markdown never appears", () => {
    expect(() => unwrapped([JSON.stringify({ other: "value" })])).toThrow(
      TextGenerationProviderError,
    );
    expectContractFailure(() => unwrapped(["{}"]));
    expectContractFailure(() => unwrapped(["{"]));
  });

  it("throws at finish when the target string never closes", () => {
    expectContractFailure(() => unwrapped(['{"chapter_markdown": "unfinished prose']));
    expectContractFailure(() => unwrapped(['{"chapter_markdown": "split escape \\', "\\u00"]));
  });

  it("rejects bare prose immediately instead of passing it through", () => {
    expectContractFailure(() => unwrapped(["Night fell over the harbor."]));
  });

  it("rejects a non-string chapter_markdown value", () => {
    expectContractFailure(() => unwrapped(['{"chapter_markdown": 42}']));
  });

  it("rejects nested object and array sibling values", () => {
    expectContractFailure(() => unwrapped(['{"meta": {"deep": 1}, "chapter_markdown": "x"}']));
    expectContractFailure(() => unwrapped(['{"meta": [1, 2], "chapter_markdown": "x"}']));
  });
});
