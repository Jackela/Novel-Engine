/**
 * Root Layout
 * Minimal shell with skip link and outlet
 */
import { Outlet, ScrollRestoration } from '@tanstack/react-router';
import { Suspense } from 'react';
import { SkipLink } from '@/shared/components/a11y/SkipLink';
import { LoadingSpinner } from '@/shared/components/feedback/LoadingSpinner';

export function RootLayout() {
  return (
    <>
      <SkipLink targetId="main-content" />
      <Suspense fallback={<LoadingSpinner fullScreen />}>
        <Outlet />
      </Suspense>
      <ScrollRestoration />
    </>
  );
}
