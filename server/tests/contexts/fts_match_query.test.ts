import { describe, expect, it } from "vitest";

import { buildFtsMatchQuery } from "../../src/contexts/studio/application/fts_match_query.js";

/**
 * DR-030 renamed and re-pinned the two cap tests: the match-element cap moved
 * from eight to three (the eight-element worst case measured 453–970ms of
 * synchronous loop freeze), so expectations that used to pin the first eight
 * tokens now pin the first three with the same de-duplication and AND
 * semantics. The malicious-input guarantees are unchanged and covered below.
 */
describe("match-query reduction (pure)", () => {
  it("reduces the operator-laden spec query to its first three quoted word tokens joined with AND (DR-030 cap)", () => {
    expect(buildFtsMatchQuery('dragon OR title:( NEAR(a b) wolf* ) "quotes"')).toBe(
      '"dragon" "or" "title"',
    );
  });

  it("case-folds and de-duplicates preserving first occurrence, capping at three (DR-030 cap)", () => {
    expect(buildFtsMatchQuery("Lantern lantern LANTERN glows")).toBe('"lantern" "glows"');
    const crowded = "b b a a c c d d e e f f g g h h i i j j";
    expect(buildFtsMatchQuery(crowded)).toBe('"b" "a" "c"');
  });

  it("returns null for empty and punctuation-only input", () => {
    expect(buildFtsMatchQuery("")).toBeNull();
    expect(buildFtsMatchQuery("!!! ??? *** ( ) \" '")).toBeNull();
  });

  it("turns each CJK run into one quoted character phrase so subwords stay findable", () => {
    expect(buildFtsMatchQuery("林黛玉")).toBe('"林 黛 玉"');
    expect(buildFtsMatchQuery("黛玉")).toBe('"黛 玉"');
    expect(buildFtsMatchQuery("黛玉 talks")).toBe('"黛 玉" "talks"');
    expect(buildFtsMatchQuery("用Node写")).toBe('"用" "node" "写"');
  });

  it("de-duplicates CJK phrases and caps the match elements at three (DR-030 cap)", () => {
    expect(buildFtsMatchQuery("黛玉 黛玉 黛玉")).toBe('"黛 玉"');
    const crowded = "一二 三四 五六 七八 九十 甲乙 丙丁 戊己 庚辛";
    expect(buildFtsMatchQuery(crowded)).toBe('"一 二" "三 四" "五 六"');
  });

  it("keeps FTS5 operator characters inert next to CJK input", () => {
    expect(buildFtsMatchQuery('黛玉 OR "x"')).toBe('"黛 玉" "or" "x"');
  });

  it("quotes every element so no unquoted FTS5 syntax can cross the MATCH boundary", () => {
    for (const hostile of [
      "\" '; DROP TABLE document_search; --",
      "NEAR(a b) OR * ^",
      "龙 OR 黛玉 banner'",
    ]) {
      const built = buildFtsMatchQuery(hostile) ?? "";
      expect(built.length, hostile).toBeGreaterThan(0);
      expect(built, hostile).toMatch(/^"[^"]*"(?: "[^"]*")*$/u);
    }
  });
});
