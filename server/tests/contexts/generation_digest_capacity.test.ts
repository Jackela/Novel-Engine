import { describe, expect, it } from "vitest";

import {
  chapterDigest,
  PRIOR_STORY_DIGEST_CODE_POINT_LIMIT,
  PRIOR_STORY_DIGEST_WORD_LIMIT,
} from "../../src/contexts/studio/application/resident_context.js";

function codePoints(text: string): number {
  return [...text].length;
}

describe("bounded prior-story digests", () => {
  it("keeps 60 words and truncates the 61st exactly once", () => {
    const words = Array.from({ length: 61 }, (_, index) => `w${index + 1}`);

    expect(chapterDigest(words.slice(0, 60).join(" "))).toBe(words.slice(0, 60).join(" "));
    expect(chapterDigest(words.join(" "))).toBe(`${words.slice(0, 60).join(" ")}…`);
  });

  it.each([
    ["Chinese", "界"],
    ["emoji", "🙂"],
    ["unpaired surrogate", "\ud800"],
  ])("keeps 512 %s code points and bounds the 513th", (_label, unit) => {
    const exact = unit.repeat(PRIOR_STORY_DIGEST_CODE_POINT_LIMIT);
    const truncated = chapterDigest(`${exact}${unit}`);

    expect(chapterDigest(exact)).toBe(exact);
    expect(codePoints(truncated)).toBe(PRIOR_STORY_DIGEST_CODE_POINT_LIMIT);
    expect(truncated).toBe(`${unit.repeat(PRIOR_STORY_DIGEST_CODE_POINT_LIMIT - 1)}…`);
  });

  it("applies both dimensions after preserving mixed-whitespace flattening", () => {
    expect(chapterDigest("one\t two\nthree\r\nfour")).toBe("one two three four");

    const longWords = Array.from({ length: PRIOR_STORY_DIGEST_WORD_LIMIT }, () => "x".repeat(20));
    const digest = chapterDigest(longWords.join(" \t\n"));
    expect(codePoints(digest)).toBe(PRIOR_STORY_DIGEST_CODE_POINT_LIMIT);
    expect(digest.split(/\s+/u).length).toBeLessThanOrEqual(PRIOR_STORY_DIGEST_WORD_LIMIT);
    expect(digest.endsWith("…")).toBe(true);
  });

  it("does not change a short benign digest", () => {
    expect(chapterDigest("Only a door remained.")).toBe("Only a door remained.");
  });
});
