/**
 * Shared parsing and colorimetry utilities for the theme contract guards
 * (ADR-0010 / T1.6). Deliberately not a `*.test.ts` file: it is imported by
 * `themeTokens.contract.test.ts` and `themeContrast.contract.test.ts` and
 * stays free of test-runner imports. Lookup and parse failures throw; the
 * importing tests surface those throws as failures.
 */

export type Rgb = readonly [number, number, number];

export interface CssRule {
  readonly atRules: readonly string[];
  readonly selector: string;
  readonly body: string;
}

export function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

/** Brace-aware parser that flattens nested at-rules into at-rule chains. */
export function parseRules(source: string, atRules: readonly string[] = []): CssRule[] {
  const rules: CssRule[] = [];
  let index = 0;
  while (index < source.length) {
    while (index < source.length && /[\s;]/.test(source[index])) {
      index += 1;
    }
    if (index >= source.length) {
      break;
    }
    const preludeStart = index;
    while (index < source.length && source[index] !== "{") {
      index += 1;
    }
    if (index >= source.length) {
      break;
    }
    const prelude = source.slice(preludeStart, index).trim();
    index += 1;
    const bodyStart = index;
    let depth = 1;
    while (index < source.length && depth > 0) {
      if (source[index] === "{") {
        depth += 1;
      } else if (source[index] === "}") {
        depth -= 1;
      }
      index += 1;
    }
    const body = source.slice(bodyStart, index - 1);
    if (prelude.startsWith("@")) {
      rules.push(...parseRules(body, [...atRules, prelude]));
    } else {
      rules.push({ atRules, selector: prelude, body });
    }
  }
  return rules;
}

export function declarations(body: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const declaration of body.split(";")) {
    const at = declaration.indexOf(":");
    if (at === -1) {
      continue;
    }
    map.set(
      declaration.slice(0, at).replace(/\s+/g, " ").trim(),
      declaration
        .slice(at + 1)
        .replace(/\s+/g, " ")
        .trim(),
    );
  }
  return map;
}

/** Order-insensitive normalized form used for block-equality assertions. */
export function normalized(body: string): readonly string[] {
  return [...declarations(body).entries()]
    .map(([property, value]) => `${property}: ${value}`)
    .sort();
}

/** Exactly-one lookup by selector plus at-rule chain; mismatch throws. */
export function findRule(
  rules: readonly CssRule[],
  selector: string,
  atRules: readonly string[],
): CssRule {
  const matches = rules.filter(
    (candidate) =>
      candidate.selector === selector && candidate.atRules.join(" > ") === atRules.join(" > "),
  );
  if (matches.length !== 1) {
    throw new Error(
      `expected exactly one block for ${selector} under [${atRules.join(", ")}], found ${matches.length}`,
    );
  }
  return matches[0];
}

export function parseHex(value: string): Rgb {
  const hex = value.trim();
  if (!/^#[0-9a-f]{6}$/i.test(hex)) {
    throw new Error(`not a 6-digit hex color: ${value}`);
  }
  return [
    Number.parseInt(hex.slice(1, 3), 16),
    Number.parseInt(hex.slice(3, 5), 16),
    Number.parseInt(hex.slice(5, 7), 16),
  ];
}

export function parseRgba(value: string): { readonly rgb: Rgb; readonly alpha: number } {
  const match = value.trim().match(/^rgba\((\d+), (\d+), (\d+), (0?\.\d+)\)$/i);
  if (!match) {
    throw new Error(`not an rgba() literal: ${value}`);
  }
  return {
    rgb: [Number(match[1]), Number(match[2]), Number(match[3])],
    alpha: Number(match[4]),
  };
}

export function linearize(channel: number): number {
  const x = channel / 255;
  return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
}

export function luminanceSrgb(rgb: Rgb): number {
  return 0.2126 * linearize(rgb[0]) + 0.7152 * linearize(rgb[1]) + 0.0722 * linearize(rgb[2]);
}

export function luminanceLinear(channels: readonly number[]): number {
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

export function contrastRatio(a: number, b: number): number {
  const [hi, lo] = a >= b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}
