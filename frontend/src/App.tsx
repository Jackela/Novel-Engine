import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { store } from './store/store';
import EmergentDashboardSimple from './components/EmergentDashboardSimple';
import { useAppSelector } from './hooks/redux';
import { initializeMobileOptimizations } from './utils/serviceWorkerRegistration';
import './styles/design-system.css';
import './components/EmergentDashboard.css';

// Professional Dark Theme for Emergent Narrative Dashboard
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#6366f1',       // Sophisticated indigo
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#8b5cf6',       // Elegant purple
      light: '#a855f7',
      dark: '#7c3aed',
      contrastText: '#ffffff',
    },
    background: {
      default: '#0a0a0b',    // Primary background
      paper: '#111113',      // Secondary background for tiles
    },
    surface: '#1a1a1d',      // Tertiary surfaces
    divider: '#2a2a30',      // Professional borders
    text: {
      primary: '#f0f0f2',    // Primary text
      secondary: '#b0b0b8',  // Secondary text
      disabled: '#606068',   // Quaternary text
    },
    error: {
      main: '#ef4444',
      light: '#fca5a5',
      dark: '#991b1b',
      contrastText: '#ffffff',
    },
    warning: {
      main: '#f59e0b',
      light: '#fcd34d',
      dark: '#92400e',
      contrastText: '#ffffff',
    },
    info: {
      main: '#3b82f6',
      light: '#93c5fd',
      dark: '#1e40af',
      contrastText: '#ffffff',
    },
    success: {
      main: '#10b981',
      light: '#6ee7b7',
      dark: '#065f46',
      contrastText: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: '2.25rem',
      fontWeight: 700,
      lineHeight: 1.2,
      color: '#f0f0f2',
    },
    h2: {
      fontSize: '1.875rem',
      fontWeight: 700,
      lineHeight: 1.3,
      color: '#f0f0f2',
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.4,
      color: '#f0f0f2',
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 600,
      lineHeight: 1.4,
      color: '#f0f0f2',
    },
    h5: {
      fontSize: '1.125rem',
      fontWeight: 500,
      lineHeight: 1.4,
      color: '#f0f0f2',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
      lineHeight: 1.4,
      color: '#f0f0f2',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
      color: '#b0b0b8',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.4,
      color: '#b0b0b8',
    },
    caption: {
      fontSize: '0.75rem',
      lineHeight: 1.3,
      color: '#808088',
    },
  },
  shape: {
    borderRadius: 12,        // Rounded corners matching design spec
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0a0a0b',
          backgroundImage: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#111113',
          backgroundImage: 'none',
          border: '1px solid #2a2a30',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#111113',
          border: '1px solid #2a2a30',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
          '&:hover': {
            borderColor: '#3a3a42',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontSize: '0.75rem',
          fontWeight: 500,
          borderRadius: '6px',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: '8px',
          transition: 'all 250ms cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-1px)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#1a1a1d',
            '& fieldset': {
              borderColor: '#2a2a30',
            },
            '&:hover fieldset': {
              borderColor: '#3a3a42',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#6366f1',
            },
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
        standardSuccess: {
          backgroundColor: '#064e3b',
          color: '#6ee7b7',
          '& .MuiAlert-icon': {
            color: '#10b981',
          },
        },
        standardError: {
          backgroundColor: '#7f1d1d',
          color: '#fca5a5',
          '& .MuiAlert-icon': {
            color: '#ef4444',
          },
        },
        standardWarning: {
          backgroundColor: '#78350f',
          color: '#fcd34d',
          '& .MuiAlert-icon': {
            color: '#f59e0b',
          },
        },
        standardInfo: {
          backgroundColor: '#1e3a8a',
          color: '#93c5fd',
          '& .MuiAlert-icon': {
            color: '#3b82f6',
          },
        },
      },
    },
  },
});

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
              background: '#f5f5f5'
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
      onSuccess: (registration) => {
        console.log('Mobile optimizations: Service worker registered successfully');
      },
      onUpdate: (registration) => {
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
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppRoutes />
      </ThemeProvider>
    </Provider>
  );
};

export default App;