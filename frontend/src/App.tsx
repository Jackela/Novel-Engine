import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, theme as antTheme } from 'antd';
import { store } from './store/store';
import EmergentDashboardSimple from './components/EmergentDashboardSimple';
import { useAppSelector } from './hooks/redux';
import { initializeMobileOptimizations } from './utils/serviceWorkerRegistration';
import './styles/design-system.css';
import './components/EmergentDashboard.css';
import 'antd/dist/reset.css';

const { Header, Content, Footer } = Layout;

// Professional Dark Theme for Emergent Narrative Dashboard
const customTheme = {
  algorithm: antTheme.darkAlgorithm,
  token: {
    // Colors
    colorPrimary: '#6366f1',              // Sophisticated indigo
    colorSuccess: '#10b981',              // Success green
    colorWarning: '#f59e0b',              // Warning amber
    colorError: '#ef4444',                // Error red
    colorInfo: '#3b82f6',                 // Info blue
    colorTextBase: '#f0f0f2',             // Primary text
    colorBgBase: '#0a0a0b',               // Primary background
    colorBgContainer: '#111113',          // Secondary background for cards
    colorBgElevated: '#1a1a1d',           // Tertiary surfaces
    colorBorder: '#2a2a30',               // Professional borders
    colorBorderSecondary: '#3a3a42',      // Hover borders
    
    // Typography
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontSize: 14,
    fontSizeHeading1: 36,                 // 2.25rem
    fontSizeHeading2: 30,                 // 1.875rem
    fontSizeHeading3: 24,                 // 1.5rem
    fontSizeHeading4: 20,                 // 1.25rem
    fontSizeHeading5: 18,                 // 1.125rem
    
    // Layout
    borderRadius: 12,                     // Rounded corners matching design spec
    borderRadiusLG: 16,
    borderRadiusSM: 8,
    borderRadiusXS: 6,
    
    // Spacing
    marginXS: 4,
    marginSM: 8,
    marginMD: 12,
    marginLG: 16,
    marginXL: 20,
    marginXXL: 24,
    paddingXS: 4,
    paddingSM: 8,
    paddingMD: 12,
    paddingLG: 16,
    paddingXL: 20,
    paddingXXL: 24,
    
    // Motion
    motionDurationSlow: '0.3s',
    motionDurationMid: '0.2s',
    motionDurationFast: '0.1s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    
    // Component specific
    colorBgLayout: '#0a0a0b',
    colorBgHeader: '#111113',
    colorTextSecondary: '#b0b0b8',
    colorTextTertiary: '#808088',
    colorTextQuaternary: '#606068',
  },
  components: {
    Layout: {
      colorBgHeader: '#111113',
      colorBgBody: '#0a0a0b',
      colorBgTrigger: '#1a1a1d',
    },
    Card: {
      colorBgContainer: '#111113',
      colorBorderSecondary: '#2a2a30',
      paddingLG: 20,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    },
    Button: {
      borderRadiusLG: 8,
      controlHeight: 36,
      fontWeight: 500,
    },
    Input: {
      colorBgContainer: '#1a1a1d',
      colorBorder: '#2a2a30',
      colorBorderHover: '#3a3a42',
      borderRadius: 8,
    },
    Menu: {
      colorBgContainer: '#111113',
      colorItemBgHover: '#1a1a1d',
      colorItemBgSelected: '#1a1a1d',
      borderRadiusLG: 12,
    },
    Typography: {
      titleMarginBottom: 0.5,
      titleMarginTop: 0,
    },
  },
};

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
      <Layout style={{ minHeight: '100vh', background: '#0a0a0b' }}>
        <Header style={{ 
          background: '#111113', 
          padding: '0 24px',
          borderBottom: '1px solid #2a2a30',
          display: 'flex',
          alignItems: 'center',
          height: 64
        }}>
          <h1 style={{ 
            color: '#f0f0f2', 
            margin: 0,
            fontSize: '1.5rem',
            fontWeight: 700
          }}>
            Emergent Narrative Dashboard
          </h1>
        </Header>
        <Content style={{ 
          padding: '24px',
          background: '#0a0a0b',
          overflow: 'auto'
        }}>
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
                  height: '100%',
                  background: '#111113',
                  borderRadius: 12
                }}>
                  <h2 style={{ color: '#f0f0f2' }}>Login Page (Not Yet Implemented)</h2>
                </div>
              } 
            />
            
            {/* Fallback for unknown routes */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Content>
        <Footer style={{ 
          textAlign: 'center',
          background: '#111113',
          borderTop: '1px solid #2a2a30',
          color: '#808088',
          padding: '16px 24px'
        }}>
          Novel Engine ©{new Date().getFullYear()} - Emergent Narrative Platform
        </Footer>
      </Layout>
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
      <ConfigProvider theme={customTheme}>
        <AppRoutes />
      </ConfigProvider>
    </Provider>
  );
};

export default App;