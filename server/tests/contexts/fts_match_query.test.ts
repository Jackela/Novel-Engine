import { describe, expect, it } from "vitest";

import { buildFtsMatchQuery } from "../../src/contexts/studio/application/fts_match_query.js";

describe("match-query reduction (pure)", () => {
  it("reduces the operator-laden spec query to first-8 quoted word tokens joined with AND", () => {
    expect(buildFtsMatchQuery('dragon OR title:( NEAR(a b) wolf* ) "quotes"')).toBe(
      '"dragon" "or" "title" "near" "a" "b" "wolf" "quotes"',
    );
  });

  it("case-folds and de-duplicates preserving first occurrence, capping at 8 tokens", () => {
    expect(buildFtsMatchQuery("Lantern lantern LANTERN glows")).toBe('"lantern" "glows"');
    const crowded = "b b a a c c d d e e f f g g h h i i j j";
    expect(buildFtsMatchQuery(crowded)).toBe('"b" "a" "c" "d" "e" "f" "g" "h"');
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

  it("de-duplicates CJK phrases and caps the match elements at eight", () => {
    expect(buildFtsMatchQuery("黛玉 黛玉 黛玉")).toBe('"黛 玉"');
    const crowded = "一二 三四 五六 七八 九十 甲乙 丙丁 戊己 庚辛";
    expect(buildFtsMatchQuery(crowded)).toBe(
      '"一 二" "三 四" "五 六" "七 八" "九 十" "甲 乙" "丙 丁" "戊 己"',
    );
  });

  it("keeps FTS5 operator characters inert next to CJK input", () => {
    expect(buildFtsMatchQuery('黛玉 OR "x"')).toBe('"黛 玉" "or" "x"');
  });
});
