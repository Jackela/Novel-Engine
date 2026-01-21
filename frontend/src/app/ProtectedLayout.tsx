/**
 * ProtectedLayout
 * Shared layout wrapper for protected routes.
 */
import { Outlet } from '@tanstack/react-router';
import AppLayout from '@/shared/components/layout/AppLayout';

export function ProtectedLayout() {
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}
