import { useCallback, useSyncExternalStore } from "react";
import type { MessageKey } from "./dictionaries/en";
import {
  getActiveLanguage,
  type Language,
  setActiveLanguage,
  subscribeActiveLanguage,
} from "./language";
import { translate as translateMessage } from "./translate";

export interface Translation {
  /** Resolve a message key in the language captured for this render. */
  readonly t: (key: MessageKey) => string;
  readonly language: Language;
  readonly setLanguage: (language: Language) => void;
}

/**
 * The phase-2 consumption convention for components: call this hook once
 * at the top of the component and route every user-facing string through
 * the returned `t`. The hook subscribes to language switches via
 * `useSyncExternalStore`, so switching the language re-renders every
 * mounted consumer without any prop drilling or context wiring.
 *
 * Failure semantics: the snapshot is always a defined language (storage
 * and detection degrade per `language.ts`), so there is no loading or
 * error state to handle.
 */
export function useTranslation(): Translation {
  const language = useSyncExternalStore(subscribeActiveLanguage, getActiveLanguage);
  const t = useCallback((key: MessageKey) => translateMessage(language, key), [language]);
  const setLanguage = useCallback((next: Language) => {
    setActiveLanguage(next);
  }, []);
  return { t, language, setLanguage };
}
