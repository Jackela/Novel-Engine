/**
 * Root Layout
 * Minimal shell with skip link and outlet
 */
import { Outlet, ScrollRestoration } from '@tanstack/react-router';
import { Suspense } from 'react';
import { LoadingSpinner } from '@/shared/components/feedback/LoadingSpinner';

export function RootLayout() {
  return (
    <>
      <Suspense fallback={<LoadingSpinner fullScreen />}>
        <Outlet />
      </Suspense>
      <ScrollRestoration />
    </>
  );
}
