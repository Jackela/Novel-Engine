#!/usr/bin/env node
import { readdirSync, statSync, readFileSync } from 'fs';
import { resolve, join } from 'path';

const root = resolve(process.cwd(), 'src');
const allowList = new Set([
  join('src', 'styles', 'tokens.ts').replace(/\\/g, '/'),
]);

const hexRe = /#[0-9A-Fa-f]{3,8}\b/;
const problems = [];
const excludePatterns = [
  // Keep tests excluded; they can contain inline samples
  /src\/tests\//,
];

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    const st = statSync(p);
    if (st.isDirectory()) {
      walk(p);
    } else if (/\.(tsx)$/.test(p)) {
      const rel = p.replace(process.cwd() + '/', '').replace(/\\/g, '/');
      if (excludePatterns.some((re) => re.test(rel))) continue;
      if (allowList.has(rel)) continue;
      if (/\.test\.(ts|tsx)$/.test(p)) continue;
      const text = readFileSync(p, 'utf8');
      if (hexRe.test(text)) {
        problems.push(rel);
      }
    }
  }
}

walk(root);

if (problems.length) {
  console.error('Hex color literals found in TS/TSX files (use tokens/theme):');
  for (const f of problems) console.error(' -', f);
  process.exit(1);
} else {
  console.log('✔ No hex color literals in TS/TSX');
}
