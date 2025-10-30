#!/usr/bin/env node
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const genPath = resolve(process.cwd(), 'src/styles/design-system.generated.css');
const refPath = resolve(process.cwd(), 'src/styles/design-system.css');

function parseVars(css) {
  const map = new Map();
  const varRe = /--([a-z0-9-]+)\s*:\s*([^;]+);/gi;
  let m;
  while ((m = varRe.exec(css))) {
    if (!map.has(m[1])) map.set(m[1], m[2].trim());
  }
  return map;
}

function srgb(c) {
  c /= 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function luminance(hex) {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) return null;
  const num = parseInt(m[1], 16);
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  const R = srgb(r), G = srgb(g), B = srgb(b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function contrast(hex1, hex2) {
  const L1 = luminance(hex1);
  const L2 = luminance(hex2);
  if (L1 == null || L2 == null) return null;
  const [a, b] = L1 >= L2 ? [L1, L2] : [L2, L1];
  return (a + 0.05) / (b + 0.05);
}

if (!existsSync(genPath)) {
  console.error('Generated CSS not found. Run: npm run build:tokens');
  process.exit(1);
}

const genCss = readFileSync(genPath, 'utf8');
const genVars = parseVars(genCss);

const refCss = existsSync(refPath) ? readFileSync(refPath, 'utf8') : '';
const refVars = parseVars(refCss);

// Drift check on a minimal, stable subset (expand later as refs align)
const keys = [
  'color-primary',
  'color-secondary',
  'color-success',
  'color-warning',
  'color-error',
  'color-text-primary',
  'color-text-secondary',
  'color-bg-primary',
  'color-bg-secondary',
  'color-bg-tertiary',
];
let mismatches = [];
for (const k of keys) {
  const g = genVars.get(k);
  const r = refVars.get(k);
  if (r && g && g !== r) mismatches.push({ key: k, generated: g, reference: r });
}

// Contrast checks
let contrastFailures = [];
function ensureContrast(aKey, bKey, min) {
  const a = genVars.get(aKey);
  const b = genVars.get(bKey);
  if (!a || !b) return;
  const ratio = contrast(a, b);
  if (ratio != null && ratio < min) {
    contrastFailures.push({ pair: `${aKey} vs ${bKey}`, ratio: Number(ratio.toFixed(2)), min });
  }
}

// WCAG AA 4.5:1 for normal text on primary background
ensureContrast('color-text-primary', 'color-bg-primary', 4.5);
// Secondary text
ensureContrast('color-text-secondary', 'color-bg-primary', 3.0);
// Primary/secondary indicators on surfaces
ensureContrast('color-primary', 'color-bg-secondary', 3.0);
ensureContrast('color-secondary', 'color-bg-secondary', 3.0);
// Status colors on paper
ensureContrast('color-success', 'color-bg-secondary', 3.0);
ensureContrast('color-warning', 'color-bg-secondary', 3.0);
ensureContrast('color-error', 'color-bg-secondary', 3.0);

if (mismatches.length) {
  console.error('Token drift detected between generated and reference CSS variables:');
  for (const m of mismatches) console.error(` - ${m.key}: generated=${m.generated} reference=${m.reference}`);
  process.exitCode = 1;
}

if (contrastFailures.length) {
  console.error('Contrast checks failed:');
  for (const f of contrastFailures) console.error(` - ${f.pair}: ratio=${f.ratio} (min=${f.min})`);
  process.exitCode = 1;
}

if (process.exitCode === 1) {
  process.exit(1);
} else {
  console.log('✔ Tokens check passed (drift and contrast)');
}
