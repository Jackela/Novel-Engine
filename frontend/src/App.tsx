import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from 'react-query';
import theme from './styles/theme';
import { store } from './store/store';
import EmergentDashboardSimple from './components/EmergentDashboardSimple';
import { useAppSelector } from './hooks/redux';
import { initializeMobileOptimizations } from './utils/serviceWorkerRegistration';
import './styles/design-system.generated.css';
import './styles/design-system.css';
import './components/EmergentDashboard.css';

// Query client (React Query v3)
const queryClient = new QueryClient();

// Protected route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  
  // For now, allow access without authentication for development
  // TODO: Implement proper authentication flow
  const devMode = process.env.NODE_ENV === 'development';
  
  if (!devMode && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Main App component with routing
const AppRoutes: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Main dashboard route */}
        <Route 
          path="/dashboard" 
          element={<EmergentDashboardSimple />} 
        />
        
        {/* Default route shows dashboard directly */}
        <Route path="/" element={<EmergentDashboardSimple />} />
        
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
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
};

// Root App component
const App: React.FC = () => {
  useEffect(() => {
    // Initialize mobile optimizations
    initializeMobileOptimizations({
      onSuccess: (_registration) => {
        console.log('Mobile optimizations: Service worker registered successfully');
      },
      onUpdate: (_registration) => {
        console.log('Mobile optimizations: Service worker updated');
        // Optionally show update notification to user
      },
      onOfflineReady: () => {
        console.log('Mobile optimizations: App ready to work offline');
      }
    });

    // Listen for mobile memory pressure events
    const handleMemoryPressure = (event: CustomEvent) => {
      console.warn('Memory pressure detected:', event.detail);
      // Could dispatch Redux action to trigger cleanup
      store.dispatch({ type: '@@mobile-memory/FORCE_CLEANUP' });
    };

    // Listen for mobile connection changes
    const handleConnectionChange = (event: CustomEvent) => {
      console.log('Connection changed:', event.detail);
      // Could adjust app behavior based on connection quality
      if (event.detail.saveData) {
        console.log('Data saver mode detected - reducing feature set');
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
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AppRoutes />
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
};

export default App;
