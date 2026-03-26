import type { PropsWithChildren } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';

export function RequireSession({ children }: PropsWithChildren) {
  const { isLoading, session } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="route-state">Restoring session...</div>;
  }

  if (!session) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
