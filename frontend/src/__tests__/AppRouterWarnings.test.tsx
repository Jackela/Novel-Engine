import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createMemoryRouter, RouterProvider, Outlet } from 'react-router-dom';

// Minimal test component that uses router features
const TestLayout: React.FC = () => (
  <div data-testid="test-layout">
    <Outlet />
  </div>
);
const TestPage: React.FC = () => <div data-testid="test-page">Test Page</div>;

// Match media mock for MUI components
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

const createTestRouter = (routes: { path: string; element: React.ReactNode }[]) =>
  createMemoryRouter(
    [
      {
        element: <TestLayout />,
        children: routes,
      },
    ],
    {
      initialEntries: ['/'],
      future: {
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      },
    }
  );

const renderRouter = (router: ReturnType<typeof createTestRouter>) =>
  render(
    <RouterProvider
      router={router}
      future={{
        v7_startTransition: true,
      }}
    />
  );

describe('App router configuration', () => {
  // Store original console methods to restore after each test
  let originalWarn: typeof console.warn;
  let originalError: typeof console.error;
  let warnSpy: ReturnType<typeof vi.fn>;
  let errorSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Capture original console methods (may have been modified by test setup)
    originalWarn = console.warn;
    originalError = console.error;

    // Create fresh spies that capture ALL calls
    warnSpy = vi.fn();
    errorSpy = vi.fn();

    // Replace console methods directly to bypass any test setup filtering
    console.warn = warnSpy;
    console.error = errorSpy;
  });

  afterEach(() => {
    // Restore original console methods
    console.warn = originalWarn;
    console.error = originalError;
    cleanup();
  });

  it('does not emit React Router Future Flag warnings with current configuration', () => {
    const router = createTestRouter([
      { path: '/', element: <TestPage /> },
      { path: '/dashboard', element: <TestPage /> },
    ]);
    renderRouter(router);

    // Check for React Router Future Flag warnings
    const hasFutureFlagWarning = warnSpy.mock.calls.some(
      ([message]: [unknown]) =>
        typeof message === 'string' &&
        message.includes('React Router Future Flag Warning')
    );

    expect(hasFutureFlagWarning).toBe(false);
  });

  it('does not emit act-wrapping warnings during router initialization', () => {
    const router = createTestRouter([{ path: '/', element: <TestPage /> }]);
    renderRouter(router);

    // Check for act-wrapping warnings
    const hasActWarning = errorSpy.mock.calls.some(([message]: [unknown]) => {
      if (typeof message !== 'string') {
        return false;
      }
      return (
        message.includes('ReactDOMTestUtils.act') || message.includes('wrapped in act')
      );
    });

    expect(hasActWarning).toBe(false);
  });
});
