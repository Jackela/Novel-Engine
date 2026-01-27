#!/usr/bin/env node
import { copyFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const source = resolve(process.cwd(), 'src/styles/design-system.css');
const target = resolve(process.cwd(), 'src/styles/design-system.generated.css');

if (!existsSync(source)) {
  console.error('Design system source CSS not found:', source);
  process.exit(1);
}

copyFileSync(source, target);
console.log('✔ Generated design-system.generated.css');
