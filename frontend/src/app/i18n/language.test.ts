import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyLanguage,
  getActiveLanguage,
  LANGUAGE_STORAGE_KEY,
  readStoredLanguage,
  resolveBrowserLanguage,
  setActiveLanguage,
  subscribeActiveLanguage,
} from "./language";

const INITIAL_LANG = document.documentElement.lang;

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.lang = INITIAL_LANG;
  vi.unstubAllGlobals();
});

describe("resolveBrowserLanguage", () => {
  it("selects zh for any zh-prefixed BCP-47 tag", () => {
    expect(resolveBrowserLanguage(["zh"])).toBe("zh");
    expect(resolveBrowserLanguage(["zh-CN"])).toBe("zh");
    expect(resolveBrowserLanguage(["zh-Hant-TW"])).toBe("zh");
    expect(resolveBrowserLanguage(["ZH-tw"])).toBe("zh");
  });

  it("keeps en as the default for every non-zh candidate", () => {
    expect(resolveBrowserLanguage(["en-US"])).toBe("en");
    expect(resolveBrowserLanguage(["fr-FR", "de-DE"])).toBe("en");
    expect(resolveBrowserLanguage([])).toBe("en");
  });

  it("scans the candidate list in priority order", () => {
    expect(resolveBrowserLanguage(["pt-BR", "zh-CN"])).toBe("zh");
    expect(resolveBrowserLanguage(["en-US", "zh-CN"])).toBe("zh");
  });
});

describe("readStoredLanguage", () => {
  it("returns only valid stored values", () => {
    expect(readStoredLanguage()).toBeNull();
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    expect(readStoredLanguage()).toBe("zh");
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "klingon");
    expect(readStoredLanguage()).toBeNull();
  });

  it("degrades silently when storage is unreadable", () => {
    vi.spyOn(window.localStorage, "getItem").mockImplementation(() => {
      throw new DOMException("denied");
    });
    expect(readStoredLanguage()).toBeNull();
  });
});

describe("getActiveLanguage", () => {
  it("prefers the stored manual choice over browser detection", () => {
    stubNavigator(["en-US"]);
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    expect(getActiveLanguage()).toBe("zh");
  });

  it("falls back to browser detection without a stored choice", () => {
    stubNavigator(["zh-CN"]);
    expect(getActiveLanguage()).toBe("zh");
    stubNavigator(["en-US"]);
    expect(getActiveLanguage()).toBe("en");
  });

  it("defaults to en when navigator is unavailable", () => {
    vi.stubGlobal("navigator", undefined);
    expect(getActiveLanguage()).toBe("en");
  });
});

describe("setActiveLanguage", () => {
  it("persists, applies to <html lang>, and notifies subscribers", () => {
    const seen: string[] = [];
    const unsubscribe = subscribeActiveLanguage((language) => seen.push(language));

    setActiveLanguage("zh");

    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("zh");
    expect(document.documentElement.lang).toBe("zh");
    expect(seen).toEqual(["zh"]);
    unsubscribe();
  });

  it("stops notifying after unsubscribe", () => {
    const seen: string[] = [];
    const unsubscribe = subscribeActiveLanguage((language) => seen.push(language));
    unsubscribe();

    setActiveLanguage("zh");

    expect(seen).toEqual([]);
  });

  it("still applies and notifies when the write fails", () => {
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new DOMException("quota");
    });
    const seen: string[] = [];
    subscribeActiveLanguage((language) => seen.push(language));

    setActiveLanguage("zh");

    expect(document.documentElement.lang).toBe("zh");
    expect(seen).toEqual(["zh"]);
  });
});

describe("applyLanguage", () => {
  it("mirrors the language onto the document element", () => {
    applyLanguage("zh");
    expect(document.documentElement.lang).toBe("zh");
    applyLanguage("en");
    expect(document.documentElement.lang).toBe("en");
  });
});

/** jsdom ships an en-US navigator; tests pin candidates explicitly. */
function stubNavigator(languages: string[]): void {
  vi.stubGlobal("navigator", {
    language: languages[0],
    languages,
  });
}
