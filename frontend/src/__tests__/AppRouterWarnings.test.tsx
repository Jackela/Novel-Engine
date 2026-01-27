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
  window.matchMedia = () => {
    const mediaQueryList: MediaQueryList = {
      matches: false,
      media: '',
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    };
    return mediaQueryList;
  };
}

const routerFutureConfig = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

const providerFutureConfig = {
  v7_startTransition: true,
} as const;

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
      future: routerFutureConfig as unknown as {
        v7_relativeSplatPath?: boolean;
        v7_startTransition?: boolean;
      },
    }
  );

const renderRouter = (router: ReturnType<typeof createTestRouter>) =>
  render(<RouterProvider router={router} future={providerFutureConfig} />);

describe('App router configuration', () => {
  // Store original console methods to restore after each test
  let warnSpy: ReturnType<typeof vi.spyOn>;
  let errorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    warnSpy.mockRestore();
    errorSpy.mockRestore();
    cleanup();
  });

  it('does not emit React Router Future Flag warnings with current configuration', () => {
    const router = createTestRouter([
      { path: '/', element: <TestPage /> },
      { path: '/dashboard', element: <TestPage /> },
    ]);
    renderRouter(router);

    // Check for React Router Future Flag warnings
    const hasFutureFlagWarning = warnSpy.mock.calls.some((call: unknown[]) => {
      const message = call[0];
      return (
        typeof message === 'string' &&
        message.includes('React Router Future Flag Warning')
      );
    });

    expect(hasFutureFlagWarning).toBe(false);
  });

  it('does not emit act-wrapping warnings during router initialization', () => {
    const router = createTestRouter([{ path: '/', element: <TestPage /> }]);
    renderRouter(router);

    // Check for act-wrapping warnings
    const hasActWarning = errorSpy.mock.calls.some((call: unknown[]) => {
      const message = call[0];
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
