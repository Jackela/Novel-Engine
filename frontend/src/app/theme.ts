/**
 * Theme selection controller (ADR-0010): one tri-state preference —
 * `system` | `light` | `dark` — persisted in localStorage under
 * `novel_engine_theme`. Absent, invalid, or unreadable storage always
 * degrades silently to `system`, whose rendering path is pure CSS
 * (`prefers-color-scheme` media entry in base.css) and needs no JS.
 *
 * The pre-paint part of this contract (stored locks applied before first
 * frame) lives in a duplicated minimal inline script in `index.html`; the
 * theme contract test guards the two against drift.
 */

export type ThemePreference = "system" | "light" | "dark";

/** localStorage key; follows the `novel_engine_` storage-naming family. */
export const THEME_STORAGE_KEY = "novel_engine_theme";

/** `theme-color` meta values; must match the two metas in index.html. */
const THEME_COLOR_LIGHT = "#d9eee9";
const THEME_COLOR_DARK = "#122b28";

const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";

const THEME_COLOR_BY_THEME: Record<"light" | "dark", string> = {
  light: THEME_COLOR_LIGHT,
  dark: THEME_COLOR_DARK,
};

function isThemePreference(value: unknown): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

/** Read the stored preference; any absence/invalid/storage error → `system`. */
export function readThemePreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (isThemePreference(stored)) {
      return stored;
    }
  } catch {
    return "system";
  }
  return "system";
}

/**
 * Persist the preference. Per design.md, failed writes are swallowed by
 * contract: the selection just does not persist for the session.
 */
export function writeThemePreference(preference: ThemePreference): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    return;
  }
}

/**
 * Project a preference onto the document: `system` removes the
 * `data-theme` attribute so the CSS media entry decides; a lock sets it.
 * Also syncs the `theme-color` metas so the browser chrome follows locks
 * that contradict the OS preference.
 */
export function applyTheme(preference: ThemePreference): void {
  if (preference === "system") {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = preference;
  }
  const metas = document.head.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]');
  metas.forEach((meta) => {
    const media = meta.getAttribute("media") ?? "";
    const metaTheme = media.includes("prefers-color-scheme: dark") ? "dark" : "light";
    meta.setAttribute(
      "content",
      preference === "system" ? THEME_COLOR_BY_THEME[metaTheme] : THEME_COLOR_BY_THEME[preference],
    );
  });
}

/** Persist and apply in one step (the ThemeSwitch activation path). */
export function setThemePreference(preference: ThemePreference): void {
  writeThemePreference(preference);
  applyTheme(preference);
}

/** The OS scheme right now; `light` when `matchMedia` is unavailable. */
export function resolveSystemScheme(): "light" | "dark" {
  if (typeof window.matchMedia !== "function") {
    return "light";
  }
  return window.matchMedia(SYSTEM_DARK_QUERY).matches ? "dark" : "light";
}

/**
 * Subscribe to OS scheme flips. On every flip the stored preference is
 * re-read: only an unlocked (`system`) selection re-applies `data-theme`;
 * explicit locks hold. The listener always receives the stored preference
 * so callers can refresh resolved labels. Returns an unsubscribe function.
 */
export function onSystemThemeChange(listener: (preference: ThemePreference) => void): () => void {
  if (typeof window.matchMedia !== "function") {
    return () => undefined;
  }
  const media = window.matchMedia(SYSTEM_DARK_QUERY);
  const handler = () => {
    const stored = readThemePreference();
    if (stored === "system") {
      applyTheme("system");
    }
    listener(stored);
  };
  media.addEventListener("change", handler);
  return () => {
    media.removeEventListener("change", handler);
  };
}
