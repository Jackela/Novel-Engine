import { getActiveLanguage, type Language } from "./language";

/**
 * DR-046: one locale-aware formatting boundary for the studio surfaces that
 * previously pinned `en-US` or used the browser default implicitly. Formatter
 * instances are built once per language at module scope (react-doctor's
 * `js-hoist-intl`), but the language itself is resolved on every call — never
 * cached — so a language switch changes subsequent renders; components
 * re-render through `useTranslation` and call these helpers while rendering.
 * Failure semantics: an invalid date reaches Intl as an invalid Date — Intl
 * throws a RangeError, which surfaces as a render error rather than a
 * silently wrong string.
 */

const COUNT_FORMATTERS: Record<Language, Intl.NumberFormat> = {
  en: new Intl.NumberFormat("en"),
  zh: new Intl.NumberFormat("zh"),
};

const DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "numeric",
  second: "numeric",
};

const DATE_TIME_FORMATTERS: Record<Language, Intl.DateTimeFormat> = {
  en: new Intl.DateTimeFormat("en", DATE_TIME_OPTIONS),
  zh: new Intl.DateTimeFormat("zh", DATE_TIME_OPTIONS),
};

const DATE_OPTIONS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "numeric",
  day: "numeric",
};

const DATE_FORMATTERS: Record<Language, Intl.DateTimeFormat> = {
  en: new Intl.DateTimeFormat("en", DATE_OPTIONS),
  zh: new Intl.DateTimeFormat("zh", DATE_OPTIONS),
};

/** Grouped decimal counts (token totals, word totals) in the active language. */
export function formatCount(value: number): string {
  return COUNT_FORMATTERS[getActiveLanguage()].format(value);
}

/** Full date and time in the active language's own conventions. */
export function formatDateTime(value: string | number | Date): string {
  return DATE_TIME_FORMATTERS[getActiveLanguage()].format(new Date(value));
}

/** Date-only (no time part) in the active language's own conventions. */
export function formatDate(value: string | number | Date): string {
  return DATE_FORMATTERS[getActiveLanguage()].format(new Date(value));
}
