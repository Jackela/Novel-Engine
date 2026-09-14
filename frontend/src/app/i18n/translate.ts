import { type Dictionary, en, type MessageKey, type MessageParams } from "./dictionaries/en";
import { zh } from "./dictionaries/zh";
import { getActiveLanguage, type Language } from "./language";

const DICTIONARIES: Record<Language, Dictionary> = { en, zh };

const PLACEHOLDER_PATTERN = /\{(\w+)\}/g;

/**
 * Resolve one message key against an explicit language, substituting
 * `{name}` placeholders with `params`. Pure — React components resolve the
 * language once per render (through `useTranslation`) and pass it here,
 * keeping re-renders cheap and the lookup deterministic. Unknown keys are a
 * compile error via `MessageKey`; a placeholder without a matching param is
 * left verbatim so a missing value stays visible instead of corrupting the
 * message silently.
 */
export function translate(language: Language, key: MessageKey, params?: MessageParams): string {
  const template = DICTIONARIES[language][key];
  if (params === undefined) return template;
  return template.replace(PLACEHOLDER_PATTERN, (placeholder, name: string) =>
    Object.hasOwn(params, name) ? String(params[name]) : placeholder,
  );
}

/**
 * Resolve one message key against the active language for non-React
 * callers (label helpers, hook-level error fallbacks and other plain
 * functions that render outside the hook's ownership). Components should
 * prefer `useTranslation` so a language switch re-renders them.
 */
export function translateActive(key: MessageKey, params?: MessageParams): string {
  return translate(getActiveLanguage(), key, params);
}
