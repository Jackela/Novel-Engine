import { readFileSync } from "node:fs";
import path from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { getActiveLanguage, LANGUAGE_STORAGE_KEY } from "./language";

/**
 * Contract anchor for the pre-paint language resolution in `index.html`:
 * the inline script must run before React mounts and set
 * `document.documentElement.lang` from the same resolution `language.ts`
 * uses (stored choice wins, then zh* browser tags, then the English
 * default). The test extracts the inline script from the real
 * `index.html` and evaluates it against stubs, so editing the script away
 * from the documented resolution fails here first.
 */
const INDEX_HTML = path.resolve(import.meta.dirname, "../../../index.html");

function languagePrepaintScript(): string {
  const html = readFileSync(INDEX_HTML, "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
  const script = scripts.find((body) => body.includes("novel_engine_language"));
  expect(script, "index.html must keep the language pre-paint inline script").toBeDefined();
  return script as string;
}

function runPrepaintScript(options: {
  script: string;
  stored: string | null;
  storageThrows?: boolean;
  languages?: string[];
}): string {
  const storage = {
    getItem: (key: string) => {
      if (options.storageThrows) throw new Error("storage unavailable");
      return key === LANGUAGE_STORAGE_KEY ? options.stored : null;
    },
  };
  const navigatorStub = { languages: options.languages ?? [], language: options.languages?.[0] };
  const documentStub: { documentElement: { lang: string } } = {
    documentElement: { lang: "" },
  };
  new Function("localStorage", "navigator", "document", options.script)(
    storage,
    navigatorStub,
    documentStub,
  );
  return documentStub.documentElement.lang;
}

/** Mirror `language.ts`'s OS-streamed inputs onto the test navigator. */
function stubNavigatorLanguages(languages: string[]): void {
  Object.defineProperty(window.navigator, "languages", {
    value: languages,
    configurable: true,
  });
}

describe("index.html pre-paint language script", () => {
  const script = languagePrepaintScript();

  afterEach(() => {
    window.localStorage.clear();
    stubNavigatorLanguages([]);
  });

  it("applies the stored language to <html lang> before any mount", () => {
    expect(runPrepaintScript({ script, stored: "zh", languages: ["en-US"] })).toBe("zh");
    expect(runPrepaintScript({ script, stored: "en", languages: ["zh-CN", "en"] })).toBe("en");
  });

  it("falls back to browser detection when nothing usable is stored", () => {
    expect(runPrepaintScript({ script, stored: null, languages: ["zh-CN", "en"] })).toBe("zh");
    expect(runPrepaintScript({ script, stored: null, languages: ["en-US"] })).toBe("en");
    expect(runPrepaintScript({ script, stored: "bogus", languages: ["zh-TW"] })).toBe("zh");
  });

  it("keeps the English default when storage is unreadable and detection is empty", () => {
    expect(runPrepaintScript({ script, stored: null, storageThrows: true })).toBe("en");
  });

  it("resolves the same language as language.ts for the shared decision table", () => {
    // Mirrored-semantics guard: the inline script and `getActiveLanguage`
    // must agree on every combination a real session can present.
    const cases: Array<{ stored: string | null; languages: string[] }> = [
      { stored: "zh", languages: ["en-US"] },
      { stored: "en", languages: ["zh-CN"] },
      { stored: null, languages: ["fr-FR", "zh-CN"] },
      { stored: null, languages: ["de-DE"] },
      { stored: null, languages: [] },
    ];
    for (const testCase of cases) {
      window.localStorage.clear();
      if (testCase.stored !== null) {
        window.localStorage.setItem(LANGUAGE_STORAGE_KEY, testCase.stored);
      }
      stubNavigatorLanguages(testCase.languages);
      const expected = getActiveLanguage();
      expect(
        runPrepaintScript({ script, stored: testCase.stored, languages: testCase.languages }),
        JSON.stringify(testCase),
      ).toBe(expected);
    }
  });
});
