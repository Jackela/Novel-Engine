import { describe, it, expect } from 'vitest';
import { getDensityMode } from '../density';

describe('getDensityMode', () => {
  it('returns relaxed below threshold', () => {
    expect(getDensityMode({ count: 3, relaxedThreshold: 5 })).toBe('relaxed');
  });

  it('returns compact when count exceeds threshold', () => {
    expect(getDensityMode({ count: 7, relaxedThreshold: 5 })).toBe('compact');
  });
});
