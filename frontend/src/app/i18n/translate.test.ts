import { describe, expect, it } from "vitest";

import { translate } from "./translate";

/**
 * Placeholder-interpolation contract: templates carry `{name}` slots,
 * substitution is a pure `String()` cast, and an unknown placeholder name
 * is left verbatim so a missing param stays visible instead of silently
 * corrupting the message.
 */
describe("translate placeholder interpolation", () => {
  it("returns the template untouched when no params are given", () => {
    expect(translate("en", "review.heading")).toBe("Review findings");
    expect(translate("zh", "review.heading")).toBe("评审发现");
  });

  it("substitutes named placeholders in template order, not argument order", () => {
    expect(translate("en", "wholeBook.status.generating", { total: 5, current: 2 })).toBe(
      "Generating chapter 2 of 5…",
    );
    expect(translate("zh", "wholeBook.status.generating", { total: 5, current: 2 })).toBe(
      "正在生成第 2 章，共 5 章…",
    );
  });

  it("stringifies number params without reformatting them", () => {
    expect(translate("en", "history.row.restore", { id: "abc12345" })).toBe(
      "Restore revision abc12345",
    );
    expect(
      translate("en", "history.row.meta", { count: 1200, unit: "words", id: "abc12345" }),
    ).toBe("1200 words · abc12345");
  });

  it("leaves unknown placeholders verbatim instead of dropping them", () => {
    expect(translate("en", "usage.total.cardLabel", { label: "Requests" })).toBe(
      "Requests: {value}",
    );
  });
});
