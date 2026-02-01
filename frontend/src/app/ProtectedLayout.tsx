/**
 * ProtectedLayout
 * Shared layout wrapper for protected routes.
 */
import { Outlet } from '@tanstack/react-router';
import AppLayout from '@/shared/components/layout/AppLayout';
import { GlobalSearch } from '@/components/GlobalSearch';

export function ProtectedLayout() {
  return (
    <AppLayout>
      <Outlet />
      <GlobalSearch />
    </AppLayout>
  );
}
