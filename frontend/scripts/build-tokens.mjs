#!/usr/bin/env node
// Simple generator for CSS variables from token values.
// NOTE: For safety, this writes to design-system.generated.css to avoid overwriting manual styles.
import { writeFileSync, mkdirSync } from 'fs';
import { dirname, resolve } from 'path';

const outPath = resolve(process.cwd(), 'src/styles/design-system.generated.css');
mkdirSync(dirname(outPath), { recursive: true });

const css = `/* Generated from build-tokens.mjs */
:root {
  --color-primary: #1a4fdc;
  --color-primary-50: #eef3ff;
  --color-primary-100: #dbe6ff;
  --color-primary-200: #b5c8ff;
  --color-primary-300: #8aa7ff;
  --color-primary-400: #5f86f5;
  --color-primary-500: #1a4fdc;
  --color-primary-600: #1240b8;
  --color-primary-700: #0c3292;
  --color-primary-800: #0a276f;
  --color-primary-900: #081c4d;
  --color-primary-glow: rgba(26, 79, 220, 0.18);
  --color-primary-light: #8aa7ff;
  --color-primary-dim: rgba(26, 79, 220, 0.12);

  --color-secondary: #111111;
  --color-secondary-50: #f7f6f2;
  --color-secondary-100: #efede7;
  --color-secondary-200: #e0ddd4;
  --color-secondary-300: #c8c4b7;
  --color-secondary-400: #a9a395;
  --color-secondary-500: #111111;
  --color-secondary-600: #0f0f0f;
  --color-secondary-700: #0c0c0c;
  --color-secondary-800: #0a0a0a;
  --color-secondary-900: #050505;
  --color-secondary-glow: rgba(17, 17, 17, 0.12);

  --color-bg-primary: #f7f6f2;
  --color-bg-secondary: #ffffff;
  --color-bg-tertiary: #f0eee8;
  --color-bg-elevated: #ffffff;
  --color-bg-interactive: #f5f4f0;
  --color-bg-paper: #ffffff;
  --color-bg-hover: #f5f4f0;

  --color-border-primary: #e2dfd6;
  --color-border-secondary: #cbc6ba;
  --color-border-tertiary: #b3ad9f;
  --color-border-subtle: #ede9de;
  --color-border-focus: #1a4fdc;
  --color-border-hover: #b9b3a7;

  --color-text-primary: #111111;
  --color-text-secondary: #4b4b4b;
  --color-text-tertiary: #7a7a7a;
  --color-text-quaternary: #a6a6a6;
  --color-text-dim: #8f8f8f;

  --color-success: #2f7d55;
  --color-success-bg: rgba(47, 125, 85, 0.12);
  --color-success-border: rgba(47, 125, 85, 0.24);
  --color-success-text: #1d5b3b;

  --color-warning: #b7791f;
  --color-warning-bg: rgba(183, 121, 31, 0.12);
  --color-warning-border: rgba(183, 121, 31, 0.24);
  --color-warning-text: #7a4b09;

  --color-error: #b42318;
  --color-error-bg: rgba(180, 35, 24, 0.12);
  --color-error-border: rgba(180, 35, 24, 0.24);
  --color-error-text: #7d1a12;

  --color-info: #2563eb;
  --color-info-bg: rgba(37, 99, 235, 0.12);
  --color-info-border: rgba(37, 99, 235, 0.24);
  --color-info-text: #1d4ed8;

  --color-accent-primary: #1a4fdc;
  --color-border: #e2dfd6;

  --font-primary: "Manrope", "Space Grotesk", "Helvetica Neue", sans-serif;
  --font-heading: "Space Grotesk", "Manrope", "Helvetica Neue", sans-serif;
  --font-mono: "IBM Plex Mono", "JetBrains Mono", monospace;

  --radius-sm: 8px;

  --spacing-0: 0;
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-5: 1.25rem;
  --spacing-6: 1.5rem;
  --spacing-8: 2rem;
  --spacing-10: 2.5rem;
  --spacing-12: 3rem;
  --spacing-16: 4rem;
  --spacing-20: 5rem;
}`;

writeFileSync(outPath, css);
console.log(`✔ Wrote ${outPath}`);
