/**
 * Language controller for the EN/zh dictionary (phase 1 of #629): one
 * bilingual preference — `en` | `zh` — persisted in localStorage under the
 * `novel_engine_` storage-naming family. With no stored preference the
 * browser's own language list decides (`zh*` tags select Chinese,
 * everything else falls back to the English default), so the resolved
 * language is always defined.
 *
 * Like `theme.ts`, failed reads and failed writes degrade silently: an
 * unreadable store behaves as "not stored", and a failed write only means
 * the choice does not persist for the session. The active language is
 * deliberately not cached in module state — every read resolves fresh from
 * storage, so clearing the store (including the shared test-setup cleanup)
 * deterministically returns the app to its detected default.
 */

export type Language = "en" | "zh";

/** localStorage key; follows the `novel_engine_` storage-naming family. */
export const LANGUAGE_STORAGE_KEY = "novel_engine_language";

export const LANGUAGES: readonly Language[] = ["en", "zh"];

function isLanguage(value: unknown): value is Language {
  return value === "en" || value === "zh";
}

/**
 * The stored preference; `null` when absent/invalid or when storage is
 * unreadable (privacy modes, disabled storage). Callers fall back to
 * detection — never to a thrown error.
 */
export function readStoredLanguage(): Language | null {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (isLanguage(stored)) {
      return stored;
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * Scan BCP-47 candidates in priority order; the first candidate whose
 * primary subtag is `zh` selects Chinese, anything else (including an
 * empty list) keeps the English default. Pure in the candidate list so
 * detection rules are unit-testable without touching `navigator`.
 */
export function resolveBrowserLanguage(candidates: readonly string[]): Language {
  for (const tag of candidates) {
    if (tag.split("-")[0]?.toLowerCase() === "zh") {
      return "zh";
    }
  }
  return "en";
}

/** The browser's language tags in preference order; `[]` when unavailable. */
function browserLanguageCandidates(): readonly string[] {
  const languages = typeof navigator === "undefined" ? undefined : navigator.languages;
  if (languages && languages.length > 0) {
    return languages;
  }
  return typeof navigator === "undefined" || !navigator.language ? [] : [navigator.language];
}

/**
 * The active language right now: a stored manual choice wins, otherwise
 * the browser's own languages decide. Reads storage on every call by
 * design (see module docblock) — resolve once per render through
 * `useTranslation` rather than per string.
 */
export function getActiveLanguage(): Language {
  return readStoredLanguage() ?? resolveBrowserLanguage(browserLanguageCandidates());
}

/**
 * Project a language onto the document so assistive tech (screen-reader
 * pronunciation, translation prompts) follows the active UI language.
 */
export function applyLanguage(language: Language): void {
  document.documentElement.lang = language;
}

/** Persist and apply in one step (the LanguageSwitch activation path). */
export function setActiveLanguage(language: Language): void {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // Contract: a failed write only skips persistence (see module docblock).
  }
  applyLanguage(language);
  notifyListeners(language);
}

type LanguageListener = (language: Language) => void;

const listeners = new Set<LanguageListener>();

/**
 * Subscribe to active-language changes triggered through
 * `setActiveLanguage`. Returns an unsubscribe function. Language is not an
 * OS-streamed preference like the theme's `system` state, so there is no
 * media-query listener to bridge — only explicit switches notify.
 */
export function subscribeActiveLanguage(listener: LanguageListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notifyListeners(language: Language): void {
  for (const listener of listeners) {
    listener(language);
  }
}
