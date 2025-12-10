import React, { useEffect, Suspense, lazy } from 'react';
import { Provider } from 'react-redux';
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
  Route,
  Outlet,
  createRoutesFromElements,
} from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from 'react-query';
import theme from './styles/theme';
import { store } from './store/store';
// Route-based code splitting
const Dashboard = lazy(() => import('./components/dashboard/Dashboard'));
const LandingPage = lazy(() => import('./pages/LandingPage'));
const CharactersPage = lazy(() => import('./pages/CharactersPage'));
const StoriesPage = lazy(() => import('./pages/StoriesPage'));
const CampaignsPage = lazy(() => import('./pages/CampaignsPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));

import { initializeMobileOptimizations } from './utils/serviceWorkerRegistration';
import { logger } from './services/logging/LoggerFactory';
import { ErrorBoundary } from './components/error-boundaries/ErrorBoundary';
import { AuthProvider, useAuthContext } from './contexts/AuthContext';
import { SkipLink } from './components/a11y';
import { SkeletonDashboard } from './components/loading';
import { usePerformance } from './hooks/usePerformance';
import CommandLayout from './components/layout/CommandLayout'; // Import Layout
import './styles/design-system.generated.css';
import './styles/design-system.css';

const queryClient = new QueryClient();

// Protected route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthContext();
  
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        background: 'var(--color-bg-primary)'
      }}>
        <h2>Loading...</h2>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    logger.warn('Unauthenticated access to protected route, redirecting to landing', {
      component: 'ProtectedRoute',
      action: 'authCheck',
    });
    return <Navigate to="/" replace />;
  }
  
  return <>{children}</>;
};

// Loading fallback
const LoadingFallback: React.FC = () => <SkeletonDashboard />;

// Root Shell (SkipLink + Outlet)
const AppShell: React.FC = () => (
  <>
    <SkipLink targetId="main-content" text="Skip to main content" />
    <Outlet />
  </>
);

// Layout Wrapper for Authenticated Routes (SSOT: Sidebar lives here)
const LayoutWrapper: React.FC = () => (
  <CommandLayout>
    <Suspense fallback={<LoadingFallback />}>
      <Outlet />
    </Suspense>
  </CommandLayout>
);

const appRouter = createBrowserRouter(
  createRoutesFromElements(
    <Route element={<AppShell />}>
      {/* Public Routes */}
      <Route
        path="/"
        element={
          <Suspense fallback={<LoadingFallback />}>
            <LandingPage />
          </Suspense>
        }
      />
      <Route 
        path="/login" 
        element={
          <Suspense fallback={<LoadingFallback />}>
            <LoginPage />
          </Suspense>
        } 
      />

      {/* Authenticated Routes with Persistent Sidebar */}
      <Route element={<ProtectedRoute><LayoutWrapper /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/campaigns" element={<CampaignsPage />} />
        <Route path="/characters" element={<CharactersPage />} />
        <Route path="/stories" element={<StoriesPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  ),
  {
    // Future flags removed
  }
);

const AppRoutes: React.FC = () => {
  return (
    <RouterProvider
      router={appRouter}
      fallbackElement={<LoadingFallback />}
      future={{
        v7_startTransition: true,
      }}
    />
  );
};

const App: React.FC = () => {
  usePerformance({
    onMetric: (metric) => {
      logger.info('Web Vital metric', {
        name: metric.name,
        value: metric.value,
        rating: metric.rating,
        delta: metric.delta,
      });
    },
    reportToAnalytics: import.meta.env.PROD,
  });

  useEffect(() => {
    initializeMobileOptimizations({
      onSuccess: () => logger.info('Mobile optimizations: Service worker registered'),
      onUpdate: () => logger.info('Mobile optimizations: Service worker updated'),
      onOfflineReady: () => logger.info('Mobile optimizations: App ready to work offline')
    });
  }, []);

  return (
    <ErrorBoundary componentName="RootErrorBoundary">
      <Provider store={store}>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={theme}>
              <CssBaseline />
              <AppRoutes />
            </ThemeProvider>
          </QueryClientProvider>
        </AuthProvider>
      </Provider>
    </ErrorBoundary>
  );
};

export default App;