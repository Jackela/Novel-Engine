#!/usr/bin/env node
// Simple generator for CSS variables from token values.
// NOTE: For safety, this writes to design-system.generated.css to avoid overwriting manual styles.
import { writeFileSync, mkdirSync } from 'fs';
import { dirname, resolve } from 'path';

const outPath = resolve(process.cwd(), 'src/styles/design-system.generated.css');
mkdirSync(dirname(outPath), { recursive: true });

const css = `/* Generated from build-tokens.mjs */
:root {
  --color-primary: #00f0ff;
  --color-secondary: #bc13fe;
  --color-bg-primary: #050508;
  --color-bg-secondary: #0b0b12;
  --color-bg-tertiary: #12121a;
  --color-border-primary: #1f1f2e;
  --color-text-primary: #ffffff;
  --color-text-secondary: #94a3b8;
  --color-success: #00ff9d;
  --color-warning: #ffb800;
  --color-error: #ff0055;
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-5: 1.25rem;
  --spacing-6: 1.5rem;
}`;

writeFileSync(outPath, css);
console.log(`✔ Wrote ${outPath}`);
