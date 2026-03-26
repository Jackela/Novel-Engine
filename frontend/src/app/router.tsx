import { Navigate, createBrowserRouter } from 'react-router-dom';

import { AppLayout } from '@/app/AppLayout';
import { RequireSession } from '@/features/auth/RequireSession';
import { LandingPage } from '@/features/auth/LandingPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { DashboardPage } from '@/features/dashboard/DashboardPage';

export const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <AppLayout />,
      children: [
        { index: true, element: <LandingPage /> },
        { path: 'login', element: <LoginPage /> },
        {
          path: 'dashboard',
          element: (
            <RequireSession>
              <DashboardPage />
            </RequireSession>
          ),
        },
        { path: '*', element: <Navigate to="/" replace /> },
      ],
    },
  ],
  {
    future: routerFuture,
  },
);
