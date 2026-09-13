import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { declarations, findRule, parseRules, stripComments } from "@/app/themeTokens.testUtils";
import { createMountHarness } from "@/test/harness";

import { MarkdownEditor } from "./MarkdownEditor";

/**
 * Dark-pass contract for the editor and inspector surfaces (T2c.1–T2c.2,
 * issue #507). Both feature stylesheets must stay token-only so every
 * surface auto-follows the theme, the editor surface must stay opaque and
 * blur-free per ADR-0009, and the CodeMirror theme must resolve its colors
 * through `base.css` tokens (light-DOM StyleModule), so the editor re-renders
 * dark with no theme-specific code. The CM evidence is the CSSOM the mounted
 * view injects under jsdom.
 */

const editorCss = readFileSync(resolve(process.cwd(), "src/styles/editor.css"), "utf8");
const inspectorCss = readFileSync(resolve(process.cwd(), "src/styles/inspector.css"), "utf8");
const baseCss = readFileSync(resolve(process.cwd(), "src/styles/base.css"), "utf8");

const RAW_COLOR =
  /#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|(?<![\w-])(?:white|black|gray|grey|red|green|blue|teal|orange|yellow|purple|pink|brown|maroon|navy|olive|lime|aqua|cyan|magenta|silver)(?![\w-])/i;

/** Every declaration body in the two stylesheets, comment- and selector-free. */
function colorDeclarations(css: string): readonly string[] {
  return parseRules(stripComments(css)).flatMap((rule) =>
    rule.body
      .split(";")
      .map((declaration) => declaration.trim().replace(/\s+/g, " "))
      .filter((declaration) => declaration.includes(":")),
  );
}

const editorRules = parseRules(stripComments(editorCss));
const inspectorRules = parseRules(stripComments(inspectorCss));
const baseRules = parseRules(stripComments(baseCss));
const SCHEME_DARK = "@media (prefers-color-scheme: dark)";

describe("editor and inspector token discipline (T2c.1)", () => {
  it("keeps editor.css and inspector.css free of raw color literals", () => {
    for (const [name, css] of [
      ["editor.css", editorCss],
      ["inspector.css", inspectorCss],
    ] as const) {
      const offenders = colorDeclarations(css).filter((declaration) => RAW_COLOR.test(declaration));
      expect(offenders, name).toEqual([]);
    }
  });

  it("paints the editor surface with the opaque --surface token", () => {
    const editor = findRule(editorRules, ".studio-editor", []);
    expect(declarations(editor.body).get("background")).toBe("var(--surface)");
  });

  it("keeps the focused CM outline on the accent token", () => {
    const focus = findRule(editorRules, ".editor__markdown .cm-editor.cm-focused", []);
    expect(declarations(focus.body).get("outline")).toBe("3px solid var(--teal-strong)");
  });

  it("keeps the inspector pane on the glass token family", () => {
    const inspector = findRule(inspectorRules, ".studio-inspector", []);
    const declarations_ = declarations(inspector.body);
    expect(declarations_.get("background")).toBe("var(--surface-glass)");
    expect(declarations_.get("backdrop-filter")).toBe("blur(var(--glass-blur))");
  });
});

describe("editor surface opacity (ADR-0009)", () => {
  it("declares no backdrop-filter anywhere in editor.css", () => {
    expect(stripComments(editorCss)).not.toContain("backdrop-filter");
  });

  it("resolves --surface to a fully opaque color in every theme entry", () => {
    const entries = [
      findRule(baseRules, ":root", []),
      findRule(baseRules, '[data-theme="dark"]', []),
      findRule(baseRules, ':root:not([data-theme="light"])', [SCHEME_DARK]),
    ];
    for (const entry of entries) {
      const surface = declarations(entry.body).get("--surface");
      expect(surface, entry.selector).toMatch(/^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i);
    }
  });
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

/** CSSOM rules of every stylesheet the mounted document carries. */
function cssomRuleText(): readonly string[] {
  return Array.from(document.styleSheets).flatMap((sheet) =>
    Array.from(sheet.cssRules).map((rule) => rule.cssText),
  );
}

describe("CodeMirror dark rendering through tokens (T2c.2)", () => {
  /** Mount the real lazy-loaded view; dynamic imports settle on macro tasks. */
  async function mountEditor(): Promise<void> {
    harness.mount(<MarkdownEditor value="# Opening" onChange={() => {}} />);
    await vi.waitFor(() => {
      expect(document.querySelector(".editor__markdown .cm-editor")).toBeTruthy();
    });
  }

  it("mounts the real view and resolves every surface color from tokens", async () => {
    await mountEditor();

    // The component theme paints the opaque page, caret, focus outline, and
    // selection exclusively with base.css tokens (text color inherits from
    // the shell's --ink), so the same rules render dark when the token
    // values flip — no CM dark theme code exists or is needed.
    const cssText = cssomRuleText().join("\n");
    expect(cssText).toContain("background-color: var(--surface)");
    expect(cssText).toContain("caret-color: var(--teal-strong)");
    expect(cssText).toContain("outline: 3px solid var(--teal-strong)");
    expect(cssText).toContain("background-color: var(--focus-ring)");
  });

  it("injects no backdrop-filter into the CodeMirror CSSOM", async () => {
    await mountEditor();

    expect(cssomRuleText().join("\n")).not.toContain("backdrop-filter");
  });
});
