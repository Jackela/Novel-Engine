import { describe, it, expect } from 'vitest';

const HEX_RE = /#[0-9A-Fa-f]{3,8}\b/;

describe('US1: No hex literals in in-scope components', () => {
  it('layout components and App entry contain no hex color literals', async () => {
    // Use Vite raw imports to read source files without Node fs
    const layoutModules = import.meta.glob('/src/components/layout/**/*.tsx', { query: '?raw', import: 'default', eager: true });
    const appModule = import.meta.glob('/src/App.tsx', { query: '?raw', import: 'default', eager: true });
    const navbarModule = import.meta.glob('/src/components/Navbar.tsx', { query: '?raw', import: 'default', eager: true });

    const offenders: string[] = [];
    for (const [path, content] of Object.entries({ ...layoutModules, ...appModule, ...navbarModule })) {
      const text = content as unknown as string;
      if (HEX_RE.test(text)) offenders.push(path);
    }
    expect(offenders, `Hex literals found: ${offenders.join(', ')}`).toEqual([]);
  });
});
