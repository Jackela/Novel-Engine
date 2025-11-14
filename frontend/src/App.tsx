import React, { useEffect, Suspense, lazy } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from 'react-query';
import theme from './styles/theme';
import { store } from './store/store';
// Route-based code splitting with React.lazy() (T050)
const Dashboard = lazy(() => import('./components/dashboard/Dashboard'));
const LandingPage = lazy(() => import('./pages/LandingPage'));
// import { useAppSelector } from './hooks/redux'; // Unused after auth refactor
import { initializeMobileOptimizations } from './utils/serviceWorkerRegistration';
import { logger } from './services/logging/LoggerFactory';
import { ErrorBoundary } from './components/error-boundaries/ErrorBoundary';
import { AuthProvider, useAuthContext } from './contexts/AuthContext';
import { SkipLink } from './components/a11y';
import { SkeletonDashboard } from './components/loading';
import { usePerformance } from './hooks/usePerformance';
import './styles/design-system.generated.css';
import './styles/design-system.css';
import './components/EmergentDashboard.css';

// Query client (React Query v3)
const queryClient = new QueryClient();

// Protected route wrapper (T051-T052: Dev bypass removed, uses AuthContext)
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthContext();
  
  // Show loading state while auth is initializing
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
  
  // T051: No dev mode bypass - authentication enforced in all environments
  if (!isAuthenticated) {
    logger.warn('Unauthenticated access to protected route, redirecting to landing', {
      component: 'ProtectedRoute',
      action: 'authCheck',
    });
    return <Navigate to="/" replace />;
  }
  
  return <>{children}</>;
};

// Loading fallback using SkeletonDashboard (T059)
const LoadingFallback: React.FC = () => <SkeletonDashboard />;

// Main App component with routing
const AppRoutes: React.FC = () => {
  return (
    <Router>
      <SkipLink targetId="main-content" text="Skip to main content" />
      <Routes>
        {/* Main dashboard route with Suspense boundary */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Suspense fallback={<LoadingFallback />}>
                <Dashboard />
              </Suspense>
            </ProtectedRoute>
          }
        />
        
        {/* Landing route */}
        <Route
          path="/"
          element={
            <Suspense fallback={<LoadingFallback />}>
              <LandingPage />
            </Suspense>
          }
        />
        
        {/* Login route (placeholder for future implementation) */}
        <Route 
          path="/login" 
          element={
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '100vh',
              background: 'var(--color-bg-primary)'
            }}>
              <h2>Login Page (Not Yet Implemented)</h2>
            </div>
          } 
        />
        
        {/* Fallback for unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

// Root App component
const App: React.FC = () => {
  // T075: Core Web Vitals tracking in production
  usePerformance({
    onMetric: (metric) => {
      // Send to LoggerFactory for analytics
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
    // Initialize mobile optimizations
    initializeMobileOptimizations({
      onSuccess: (_registration) => {
        logger.info('Mobile optimizations: Service worker registered successfully');
      },
      onUpdate: (_registration) => {
        logger.info('Mobile optimizations: Service worker updated');
        // Optionally show update notification to user
      },
      onOfflineReady: () => {
        logger.info('Mobile optimizations: App ready to work offline');
      }
    });

    // Listen for mobile memory pressure events
    const handleMemoryPressure = (event: CustomEvent) => {
      logger.warn('Memory pressure detected:', event.detail);
      // Could dispatch Redux action to trigger cleanup
      store.dispatch({ type: '@@mobile-memory/FORCE_CLEANUP' });
    };

    // Listen for mobile connection changes
    const handleConnectionChange = (event: CustomEvent) => {
      logger.info('Connection changed:', event.detail);
      // Could adjust app behavior based on connection quality
      if (event.detail.saveData) {
        logger.info('Data saver mode detected - reducing feature set');
      }
    };

    window.addEventListener('mobile-memory-pressure', handleMemoryPressure as EventListener);
    window.addEventListener('mobile-connection-change', handleConnectionChange as EventListener);

    return () => {
      window.removeEventListener('mobile-memory-pressure', handleMemoryPressure as EventListener);
      window.removeEventListener('mobile-connection-change', handleConnectionChange as EventListener);
    };
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
