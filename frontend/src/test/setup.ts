import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Global test setup for Novel Engine frontend tests

// Mock all network requests at the global level
Object.defineProperty(window, 'fetch', {
  writable: true,
  value: vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        api: 'healthy',
        config: 'loaded',
        version: '1.0.0',
      }),
    })
  ),
});

// Mock axios for any direct usage
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({
        data: {
          api: 'healthy',
          config: 'loaded', 
          version: '1.0.0',
        },
      })),
      post: vi.fn(() => Promise.resolve({
        data: { success: true },
      })),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      getSystemStatus: vi.fn(() => Promise.resolve({
        data: {
          api: 'healthy',
          config: 'loaded',
          version: '1.0.0',
        },
      })),
    })),
    get: vi.fn(() => Promise.resolve({
      data: {
        api: 'healthy',
        config: 'loaded',
        version: '1.0.0',
      },
    })),
    post: vi.fn(() => Promise.resolve({
      data: { success: true },
    })),
  },
}));

// Suppress console warnings during tests
const originalConsoleWarn = console.warn;
console.warn = (...args: any[]) => {
  // Filter out specific warnings that are expected in test environment
  const message = args[0];
  if (
    typeof message === 'string' && 
    (message.includes('ReactDOMTestUtils.act') ||
     message.includes('validateDOMNesting'))
  ) {
    return;
  }
  originalConsoleWarn(...args);
};