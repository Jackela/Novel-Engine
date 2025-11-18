import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { vi } from 'vitest';
import App from '../App.tsx';

if (!window.matchMedia) {
  window.matchMedia = () =>
    ({
      matches: false,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

describe('App router configuration', () => {
  it('does not emit React Router or act-wrapping warnings', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const container = document.createElement('div');
    document.body.appendChild(container);
    let root: ReturnType<typeof createRoot> | null = null;

    await act(async () => {
      root = createRoot(container);
      root.render(<App />);
    });

    await act(async () => {
      await Promise.resolve();
    });

    const hasFutureFlagWarning = warnSpy.mock.calls.some(([message]) =>
      typeof message === 'string' && message.includes('React Router Future Flag Warning')
    );
    const hasActWarning = errorSpy.mock.calls.some(([message]) => {
      if (typeof message !== 'string') {
        return false;
      }
      return message.includes('ReactDOMTestUtils.act') || message.includes('wrapped in act');
    });

    expect(hasFutureFlagWarning).toBe(false);
    expect(hasActWarning).toBe(false);

    await act(async () => {
      root?.unmount();
    });
    container.remove();

    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });
});
