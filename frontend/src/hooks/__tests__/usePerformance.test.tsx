import React from 'react';
import { render } from '@testing-library/react';
import { vi } from 'vitest';
import { usePerformance } from '../usePerformance';

const TestComponent = () => {
  usePerformance();
  return null;
};

describe('usePerformance', () => {
  it('does not attempt to load web-vitals or warn during vitest environment', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    render(<TestComponent />);

    const warnedAboutWebVitals = warnSpy.mock.calls.some(
      ([message]) => typeof message === 'string' && message.includes('Web Vitals monitoring skipped')
    );

    expect(warnedAboutWebVitals).toBe(false);

    warnSpy.mockRestore();
  });
});
