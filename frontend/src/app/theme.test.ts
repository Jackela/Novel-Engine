import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyTheme,
  onSystemThemeChange,
  readThemePreference,
  resolveSystemScheme,
  setThemePreference,
  THEME_STORAGE_KEY,
  writeThemePreference,
} from "./theme";

type MediaListener = (event: { matches: boolean }) => void;

interface SystemThemeStub {
  readonly listeners: Set<MediaListener>;
  flip(next: boolean): void;
}

/** jsdom has no matchMedia; stub the MediaQueryList surface theme.ts uses. */
function stubSystemTheme(matchesDark: boolean): SystemThemeStub {
  const listeners = new Set<MediaListener>();
  let dark = matchesDark;
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: dark,
    media: query,
    addEventListener: (_type: "change", listener: MediaListener) => {
      listeners.add(listener);
    },
    removeEventListener: (_type: "change", listener: MediaListener) => {
      listeners.delete(listener);
    },
  }));
  return {
    listeners,
    flip(next: boolean) {
      dark = next;
      for (const listener of [...listeners]) {
        listener({ matches: next });
      }
    },
  };
}

function seedThemeMeta(media: "light" | "dark"): HTMLMetaElement {
  const meta = document.createElement("meta");
  meta.name = "theme-color";
  meta.content = media === "light" ? "#d9eee9" : "#122b28";
  meta.setAttribute("media", `(prefers-color-scheme: ${media})`);
  document.head.appendChild(meta);
  return meta;
}

function clearThemeMetas(): void {
  for (const meta of [...document.head.querySelectorAll('meta[name="theme-color"]')]) {
    meta.remove();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  clearThemeMetas();
  delete document.documentElement.dataset.theme;
});

describe("theme preference storage", () => {
  it("degrades to system when the key is absent or invalid", () => {
    expect(readThemePreference()).toBe("system");

    window.localStorage.setItem(THEME_STORAGE_KEY, "sepia");
    expect(readThemePreference()).toBe("system");
  });

  it("persists and reads back an explicit lock", () => {
    setThemePreference("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(readThemePreference()).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    setThemePreference("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("writeThemePreference persists without touching the document", () => {
    writeThemePreference("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.dataset.theme).toBeUndefined();
  });

  it("falls back to system on storage read failures", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });
    expect(readThemePreference()).toBe("system");
  });

  it("swallows storage write failures and still applies the lock", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage full");
    });
    expect(() => setThemePreference("dark")).not.toThrow();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("theme application", () => {
  it("removes the data-theme attribute for the system path", () => {
    applyTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    applyTheme("system");
    expect(document.documentElement.dataset.theme).toBeUndefined();
  });

  it("holds a light lock under a dark OS via the explicit attribute", () => {
    stubSystemTheme(true);
    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("overrides both theme-color metas with the lock color", () => {
    const light = seedThemeMeta("light");
    const dark = seedThemeMeta("dark");

    applyTheme("dark");
    expect(light.getAttribute("content")).toBe("#122b28");
    expect(dark.getAttribute("content")).toBe("#122b28");

    applyTheme("light");
    expect(light.getAttribute("content")).toBe("#d9eee9");
    expect(dark.getAttribute("content")).toBe("#d9eee9");
  });

  it("restores per-media theme-color content on the system path", () => {
    const light = seedThemeMeta("light");
    const dark = seedThemeMeta("dark");

    applyTheme("dark");
    applyTheme("system");
    expect(light.getAttribute("content")).toBe("#d9eee9");
    expect(dark.getAttribute("content")).toBe("#122b28");
  });

  it("leaves the document untouched when no theme-color metas exist", () => {
    expect(() => applyTheme("dark")).not.toThrow();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("system theme following", () => {
  it("reports the OS scheme and degrades to light without matchMedia", () => {
    expect(resolveSystemScheme()).toBe("light");

    stubSystemTheme(true);
    expect(resolveSystemScheme()).toBe("dark");

    stubSystemTheme(false);
    expect(resolveSystemScheme()).toBe("light");
  });

  it("re-applies only while unlocked and reports the stored preference", () => {
    const stub = stubSystemTheme(true);
    const listener = vi.fn();
    const unsubscribe = onSystemThemeChange(listener);

    // System mode: OS flip re-syncs the system path.
    stub.flip(false);
    expect(listener).toHaveBeenCalledWith("system");
    expect(document.documentElement.dataset.theme).toBeUndefined();

    // Light lock: OS flips must not touch the applied attribute.
    setThemePreference("light");
    stub.flip(true);
    expect(listener).toHaveBeenLastCalledWith("light");
    expect(document.documentElement.dataset.theme).toBe("light");

    unsubscribe();
    stub.flip(false);
    expect(listener).toHaveBeenCalledTimes(2);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("is inert without matchMedia support", () => {
    const listener = vi.fn();
    expect(() => {
      const unsubscribe = onSystemThemeChange(listener);
      unsubscribe();
    }).not.toThrow();
    expect(listener).not.toHaveBeenCalled();
  });
});
