import { describe, it, expect } from 'vitest';
import { tokens } from '@/styles/tokens';

describe('US2: Generated CSS variables from tokens', () => {
  it('tokens contain expected keys that drive generated CSS', () => {
    expect(tokens.colors.primary[500]).toBeDefined();
    expect(tokens.colors.background.default).toBeDefined();
    expect(tokens.colors.border.primary).toBeDefined();
    expect(tokens.colors.text.primary).toBeDefined();
  });
});
