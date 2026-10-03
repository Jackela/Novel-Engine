import { describe, expect, it } from "vitest";

import { formatCount, formatDate, formatDateTime } from "./format";
import { setActiveLanguage } from "./language";

/** Local-noon fixture so rendering cannot roll across a day boundary. */
const SAMPLE = new Date(2026, 9, 3, 12, 30, 0);

/**
 * DR-046: the shared formatters resolve the active language at call time;
 * switching the language must change the rendered date conventions (the
 * language store resets between tests through the shared test-setup
 * cleanup, so each case starts from the English default).
 */
describe("Intl formatting follows the active language (DR-046)", () => {
  it("groups counts with locale separators in both languages", () => {
    expect(formatCount(1234567)).toBe("1,234,567");
    expect(formatCount(42)).toBe("42");

    setActiveLanguage("zh");

    expect(formatCount(1234567)).toBe("1,234,567");
  });

  it("formats date-times through the language's own conventions", () => {
    const en = formatDateTime(SAMPLE);

    setActiveLanguage("zh");
    const zh = formatDateTime(SAMPLE);

    // Byte-identical to the pre-DR-046 `new Date(value).toLocaleString()`.
    expect(en).toBe("10/3/2026, 12:30:00 PM");
    expect(zh).toMatch(/2026\/10\/3 12:30:00/);
    expect(en).not.toBe(zh);
  });

  it("formats date-only values without a time part", () => {
    const en = formatDate(SAMPLE);

    setActiveLanguage("zh");
    const zh = formatDate(SAMPLE);

    expect(en).toBe("10/3/2026");
    expect(zh).toBe("2026/10/3");
  });
});
