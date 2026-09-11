import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  contrastRatio,
  declarations,
  findRule,
  linearize,
  luminanceLinear,
  luminanceSrgb,
  parseHex,
  parseRgba,
  parseRules,
  type Rgb,
  stripComments,
} from "./themeTokens.testUtils";

/*
 * WCAG contrast guard for the dark token set (ADR-0010 / T1.6). Model,
 * verified to reproduce every design.md estimate within ±0.06: direct pairs
 * use plain WCAG 2.x relative luminance; "on glass" pairs composite the
 * text over the worst-case backdrop — the brightest gradient region (teal
 * radial glow at 0.09 alpha over canvas-hint-teal, composited in sRGB
 * space, region L ≈ 0.034) seen through the faint glass tier (alpha
 * composited in linear space).
 */

const baseCss = readFileSync(resolve(process.cwd(), "src/styles/base.css"), "utf8");

const darkLock = findRule(parseRules(stripComments(baseCss)), '[data-theme="dark"]', []);
const dark = declarations(darkLock.body);
const backdrop = (() => {
  const hintTeal = parseHex(dark.get("--canvas-hint-teal") ?? "");
  const glow = parseRgba("rgba(45, 212, 191, 0.09)");
  // Brightest gradient region: glow over hint, composited in sRGB, then linearized.
  const regionSrgb = glow.rgb.map(
    (channel, i) => channel * glow.alpha + hintTeal[i] * (1 - glow.alpha),
  );
  const regionLinear = regionSrgb.map(linearize);
  const glass = parseRgba(dark.get("--surface-glass-faint") ?? "");
  // Faint glass tier: alpha composited in linear space over the region.
  return glass.rgb.map(
    (channel, i) => linearize(channel) * glass.alpha + regionLinear[i] * (1 - glass.alpha),
  );
})();

function textColor(token: string): Rgb {
  return parseHex(dark.get(token) ?? "");
}

type Background = { readonly kind: "srgb"; readonly color: Rgb } | { readonly kind: "composite" };

const surface = (token: string): Background => ({ kind: "srgb", color: textColor(token) });
const glass: Background = { kind: "composite" };

interface Pair {
  readonly name: string;
  readonly fg: Rgb;
  readonly bg: Background;
  readonly recorded: number;
}

const pairs: readonly Pair[] = [
  {
    name: "ink vs surface (opaque editor)",
    fg: textColor("--ink"),
    bg: surface("--surface"),
    recorded: 14.6,
  },
  { name: "ink vs faint-glass composite", fg: textColor("--ink"), bg: glass, recorded: 12.2 },
  {
    name: "ink-soft vs faint-glass composite",
    fg: textColor("--ink-soft"),
    bg: glass,
    recorded: 9.3,
  },
  {
    name: "ink-soft vs surface-hover",
    fg: textColor("--ink-soft"),
    bg: surface("--surface-hover"),
    recorded: 8.9,
  },
  { name: "muted vs faint-glass composite", fg: textColor("--muted"), bg: glass, recorded: 7.4 },
  {
    name: "muted-soft vs faint-glass composite",
    fg: textColor("--muted-soft"),
    bg: glass,
    recorded: 6.4,
  },
  {
    name: "muted-faint vs faint-glass composite",
    fg: textColor("--muted-faint"),
    bg: glass,
    recorded: 5.7,
  },
  {
    name: "teal-strong vs faint-glass composite",
    fg: textColor("--teal-strong"),
    bg: glass,
    recorded: 7.9,
  },
  {
    name: "teal-strong vs teal-soft",
    fg: textColor("--teal-strong"),
    bg: surface("--teal-soft"),
    recorded: 7.5,
  },
  {
    name: "ink vs focus-ring",
    fg: textColor("--ink"),
    bg: surface("--focus-ring"),
    recorded: 10.2,
  },
  { name: "danger vs faint-glass composite", fg: textColor("--danger"), bg: glass, recorded: 6.2 },
  {
    name: "danger vs danger-soft",
    fg: textColor("--danger"),
    bg: surface("--danger-soft"),
    recorded: 6.9,
  },
  { name: "warn vs faint-glass composite", fg: textColor("--warn"), bg: glass, recorded: 7.4 },
  {
    name: "warn-ink vs warn-soft",
    fg: textColor("--warn-ink"),
    bg: surface("--warn-soft"),
    recorded: 10.5,
  },
  {
    name: "on-accent vs teal-strong",
    fg: textColor("--on-accent"),
    bg: surface("--teal-strong"),
    recorded: 7.7,
  },
  {
    name: "badge-neutral-ink vs badge-neutral-bg (T1 dark twins)",
    fg: textColor("--badge-neutral-ink"),
    bg: surface("--badge-neutral-bg"),
    recorded: 7.07,
  },
  {
    name: "badge-active-ink vs badge-active-bg (T1 dark twins)",
    fg: textColor("--badge-active-ink"),
    bg: surface("--badge-active-bg"),
    recorded: 7.52,
  },
  {
    name: "badge-deprecated-ink vs badge-deprecated-bg (T2b-finding dark twins)",
    fg: textColor("--badge-deprecated-ink"),
    bg: surface("--badge-deprecated-bg"),
    recorded: 6.91,
  },
  {
    name: "badge-draft-active-ink vs badge-draft-active-bg (T2b-finding dark twins)",
    fg: textColor("--badge-draft-active-ink"),
    bg: surface("--badge-draft-active-bg"),
    recorded: 7.53,
  },
];

describe("dark contrast guard", () => {
  it("binds the backdrop model to the dark gradient's bright-source literal", () => {
    expect(dark.get("--canvas-gradient")).toContain("rgba(45, 212, 191, 0.09)");
  });

  it("matches the design.md draft table within ±0.2 and keeps AA above 4.5:1", () => {
    const measured: { readonly name: string; readonly ratio: number; readonly recorded: number }[] =
      [];
    for (const pair of pairs) {
      const fgLuminance = luminanceSrgb(pair.fg);
      const bgLuminance =
        pair.bg.kind === "composite" ? luminanceLinear(backdrop) : luminanceSrgb(pair.bg.color);
      const ratio = contrastRatio(fgLuminance, bgLuminance);
      measured.push({ name: pair.name, ratio, recorded: pair.recorded });
      expect(
        Math.abs(ratio - pair.recorded),
        `${pair.name}: ${ratio.toFixed(2)} vs recorded ${pair.recorded}`,
      ).toBeLessThanOrEqual(0.2);
      expect(ratio, `${pair.name} must keep AA`).toBeGreaterThanOrEqual(4.5);
    }
    // The floor pair (faint text tier) carries the stricter design target.
    const floor = measured.find((entry) => entry.name.startsWith("muted-faint"));
    expect(floor?.ratio).toBeGreaterThanOrEqual(5.5);
  });
});
