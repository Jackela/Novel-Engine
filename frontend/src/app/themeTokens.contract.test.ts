import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  declarations,
  findRule,
  normalized,
  parseRules,
  stripComments,
} from "./themeTokens.testUtils";

/**
 * Executable theme guards (ADR-0010 / T1.6): the two dark token entries and
 * both dark fallback twins must stay literally equal, the fallback chain
 * must degrade to near-opaque blur-free surfaces, the pre-declared badge
 * and row-hover tokens must exist in every entry, and the index.html FOUC
 * script must keep mirroring the theme module's storage contract.
 * Dark value contrast lives in `themeContrast.contract.test.ts`.
 */

const baseCss = readFileSync(resolve(process.cwd(), "src/styles/base.css"), "utf8");
const indexHtml = readFileSync(resolve(process.cwd(), "index.html"), "utf8");

const rules = parseRules(stripComments(baseCss));
const NO_AT_RULES: readonly string[] = [];
const SCHEME_DARK = "@media (prefers-color-scheme: dark)";
const REDUCED_TRANSPARENCY = "@media (prefers-reduced-transparency: reduce)";
const NO_BACKDROP =
  "@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))";

const rootLight = findRule(rules, ":root", NO_AT_RULES);
const darkLock = findRule(rules, '[data-theme="dark"]', NO_AT_RULES);
const darkSystem = findRule(rules, ':root:not([data-theme="light"])', [SCHEME_DARK]);
const rtDarkLock = findRule(rules, '[data-theme="dark"]', [REDUCED_TRANSPARENCY]);
const rtDarkSystem = findRule(rules, ':root:not([data-theme="light"])', [
  REDUCED_TRANSPARENCY,
  SCHEME_DARK,
]);
const noBackdropDarkLock = findRule(rules, '[data-theme="dark"]', [NO_BACKDROP]);
const noBackdropDarkSystem = findRule(rules, ':root:not([data-theme="light"])', [
  NO_BACKDROP,
  SCHEME_DARK,
]);

describe("dark token drift guard", () => {
  it("declares light as the root color-scheme and dark in both dark entries", () => {
    expect(declarations(rootLight.body).get("color-scheme")).toBe("light");
    expect(declarations(darkLock.body).get("color-scheme")).toBe("dark");
    expect(declarations(darkSystem.body).get("color-scheme")).toBe("dark");
  });

  it("keeps the two main dark entries equal after normalization", () => {
    expect(normalized(darkSystem.body)).toEqual(normalized(darkLock.body));
  });

  it("keeps both reduced-transparency dark twins equal after normalization", () => {
    expect(normalized(rtDarkSystem.body)).toEqual(normalized(rtDarkLock.body));
  });

  it("keeps both no-backdrop-filter dark twins equal after normalization", () => {
    expect(normalized(noBackdropDarkSystem.body)).toEqual(normalized(noBackdropDarkLock.body));
  });

  it("keeps the fallback chain near-opaque, blur-free, and shadow-free in dark", () => {
    const rt = declarations(rtDarkLock.body);
    expect(rt.get("--surface-glass")).toBe("rgba(16, 20, 21, 0.97)");
    expect(rt.get("--surface-glass-strong")).toBe("rgba(22, 27, 28, 0.99)");
    expect(rt.get("--surface-glass-faint")).toBe("rgba(12, 16, 17, 0.97)");
    expect(rt.get("--glass-blur")).toBe("0px");
    expect(rt.get("--glass-blur-strong")).toBe("0px");
    expect(rt.get("--glass-shadow")).toBe("none");

    const noBackdrop = declarations(noBackdropDarkLock.body);
    // No-backdrop browsers get fully opaque fills (no rgba, no blur tokens).
    for (const token of ["--surface-glass", "--surface-glass-strong", "--surface-glass-faint"]) {
      expect(noBackdrop.get(token)).toMatch(/^#[0-9a-f]{6}$/i);
    }
    expect(noBackdrop.get("--glass-border")).toBe("#2f383a");
    expect(noBackdrop.get("--glass-shadow")).toBe("none");
  });

  it("keeps theme-invariant material tokens out of the dark entries", () => {
    for (const body of [darkLock.body, darkSystem.body]) {
      const values = declarations(body);
      expect(values.has("--glass-blur")).toBe(false);
      expect(values.has("--glass-blur-strong")).toBe(false);
    }
  });
});

describe("pre-declared badge and row-hover tokens", () => {
  const expected = new Map<string, readonly [string, string]>([
    ["--badge-neutral-bg", ["#e2e8e8", "#252c2e"]],
    ["--badge-neutral-ink", ["#5a6465", "#aeb9bb"]],
    ["--badge-active-bg", ["#cfe4e2", "#11312d"]],
    ["--badge-active-ink", ["#0f6862", "#2dd4bf"]],
    ["--library-row-hover", ["#8dbab6", "#3d7a73"]],
  ]);

  it("declares light values in :root and dark values in both dark entries", () => {
    const light = declarations(rootLight.body);
    const darkLockValues = declarations(darkLock.body);
    const darkSystemValues = declarations(darkSystem.body);
    for (const [token, [lightValue, darkValue]] of expected) {
      expect(light.get(token), token).toBe(lightValue);
      expect(darkLockValues.get(token), token).toBe(darkValue);
      expect(darkSystemValues.get(token), token).toBe(darkValue);
    }
  });
});

describe("index.html theme bootstrap guard", () => {
  it("applies stored locks before the module script and nothing on system", () => {
    const inlineAt = indexHtml.indexOf('localStorage.getItem("novel_engine_theme")');
    const moduleAt = indexHtml.indexOf('<script type="module"');
    expect(inlineAt).toBeGreaterThan(-1);
    expect(moduleAt).toBeGreaterThan(inlineAt);
    expect(indexHtml).toContain("try {");
    expect(indexHtml).toContain("catch");
    expect(indexHtml).toContain("document.documentElement.dataset.theme = theme");
    // Only explicit locks are applied; system/absent/unreadable does nothing.
    expect(indexHtml).toMatch(/if \(theme === "light" \|\| theme === "dark"\)/);
  });

  it("splits theme-color into per-scheme metas", () => {
    expect(indexHtml).toContain(
      'name="theme-color" content="#d9eee9" media="(prefers-color-scheme: light)"',
    );
    expect(indexHtml).toContain(
      'name="theme-color" content="#122b28" media="(prefers-color-scheme: dark)"',
    );
  });
});
