import { type Dictionary, en, type MessageKey } from "./dictionaries/en";
import { zh } from "./dictionaries/zh";
import { getActiveLanguage, type Language } from "./language";

const DICTIONARIES: Record<Language, Dictionary> = { en, zh };

/**
 * Resolve one message key against an explicit language. Pure — React
 * components resolve the language once per render (through
 * `useTranslation`) and pass it here, keeping re-renders cheap and the
 * lookup deterministic. Unknown keys are a compile error via `MessageKey`.
 */
export function translate(language: Language, key: MessageKey): string {
  return DICTIONARIES[language][key];
}

/**
 * Resolve one message key against the active language for non-React
 * callers (label helpers and other plain functions that render outside the
 * hook's ownership). Components should prefer `useTranslation` so a
 * language switch re-renders them.
 */
export function translateActive(key: MessageKey): string {
  return translate(getActiveLanguage(), key);
}
