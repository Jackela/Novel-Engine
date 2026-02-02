/**
 * ProtectedLayout
 * Shared layout wrapper for protected routes.
 */
import { Outlet } from '@tanstack/react-router';
import { AppShell } from '@/components/composed';
import { GlobalSearch } from '@/components/GlobalSearch';

export function ProtectedLayout() {
  return (
    <AppShell>
      <Outlet />
      <GlobalSearch />
    </AppShell>
  );
}
