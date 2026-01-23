import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = () =>
    ({
      matches: false,
      media: '',
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

type WindowWithTesting = Window &
  typeof globalThis & {
    scrollTo?: (options?: ScrollToOptions | number, y?: number) => void;
    ResizeObserver?: typeof ResizeObserver;
  };

if (typeof window !== 'undefined') {
  const testWindow = window as WindowWithTesting;
  testWindow.scrollTo = () => {};
}

if (typeof window !== 'undefined' && !(window as WindowWithTesting).ResizeObserver) {
  class ResizeObserverMock implements ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (window as WindowWithTesting).ResizeObserver = ResizeObserverMock;
}
