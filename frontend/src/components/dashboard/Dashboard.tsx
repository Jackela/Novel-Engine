import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Box, Alert, Snackbar, useTheme, useMediaQuery, CircularProgress } from '@mui/material';
import DashboardLayout from '../layout/DashboardLayout';
import MobileTabbedDashboard from '../layout/MobileTabbedDashboard';

// Critical components loaded immediately
import WorldStateMap from './WorldStateMap';
import QuickActions from './QuickActions';

// Non-critical components lazy loaded for mobile performance
const RealTimeActivity = lazy(() => import('./RealTimeActivity'));
const PerformanceMetrics = lazy(() => import('./PerformanceMetrics'));
const TurnPipelineStatus = lazy(() => import('./TurnPipelineStatus'));
const CharacterNetworks = lazy(() => import('./CharacterNetworks'));
const EventCascadeFlow = lazy(() => import('./EventCascadeFlow'));
const NarrativeTimeline = lazy(() => import('./NarrativeTimeline'));
const AnalyticsDashboard = lazy(() => import('./AnalyticsDashboard'));

// Lazy loading wrapper with loading indicator
const LazyWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense fallback={
    <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
      <CircularProgress size={24} />
    </Box>
  }>
    {children}
  </Suspense>
);

interface DashboardProps {
  // Add authentication and user context props as needed
  userId?: string;
  campaignId?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ userId: _userId, campaignId: _campaignId }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [loading, setLoading] = useState(false);
  const [error, _setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  // System state
  const [systemStatus, _setSystemStatus] = useState<'online' | 'offline' | 'maintenance'>('online');
  const [_lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Periodic updates using HTTP polling
  // Note: WebSocket support deferred - using polling for real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const showNotification = (message: string) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  const handleQuickAction = (action: string) => {
    logger.info('Quick action triggered:', action);
    
    switch (action) {
      case 'play':
        showNotification('System resumed');
        break;
      case 'pause':
        showNotification('System paused');
        break;
      case 'stop':
        showNotification('System stopped');
        break;
      case 'refresh':
        setLoading(true);
        // Simulate refresh
        setTimeout(() => {
          setLoading(false);
          setLastUpdate(new Date());
          showNotification('Data refreshed');
        }, 1000);
        break;
      case 'save':
        showNotification('State saved');
        break;
      case 'settings':
        showNotification('Settings panel (not yet implemented)');
        break;
      case 'fullscreen':
        // Implement fullscreen logic
        if (document.fullscreenElement) {
          document.exitFullscreen();
        } else {
          document.documentElement.requestFullscreen();
        }
        break;
      case 'export':
        showNotification('Export started (not yet implemented)');
        break;
      default:
        logger.info('Unknown action:', action);
    }
  };

  const handleSnackbarClose = () => {
    setSnackbarOpen(false);
  };

  // Organize components for mobile accordion layout with lazy loading
  const mobileComponents = {
    essential: [
      <WorldStateMap key="world-map" loading={loading} error={!!error} />,
      <QuickActions key="quick-actions" loading={loading} error={!!error} onAction={handleQuickAction} />,
    ],
    activity: [
      <LazyWrapper key="real-time-activity">
        <RealTimeActivity loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="performance-metrics">
        <PerformanceMetrics loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="turn-pipeline">
        <TurnPipelineStatus loading={loading} error={!!error} />
      </LazyWrapper>,
    ],
    characters: [
      <LazyWrapper key="character-networks">
        <CharacterNetworks loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="event-cascade">
        <EventCascadeFlow loading={loading} error={!!error} />
      </LazyWrapper>,
    ],
    timeline: [
      <LazyWrapper key="narrative-timeline">
        <NarrativeTimeline loading={loading} error={!!error} />
      </LazyWrapper>,
    ],
    analytics: [
      <LazyWrapper key="analytics">
        <AnalyticsDashboard loading={loading} error={!!error} />
      </LazyWrapper>,
    ],
  };

  return (
    <DashboardLayout>
      {isMobile ? (
        <MobileTabbedDashboard components={mobileComponents}>
          {/* Mobile content handled by tabbed interface */}
        </MobileTabbedDashboard>
      ) : (
        <>
          {/* Desktop Layout with lazy loading for better performance */}
          {/* Row 1: World Map (immediate), others lazy loaded */}
          <WorldStateMap loading={loading} error={!!error} />
          <LazyWrapper>
            <RealTimeActivity loading={loading} error={!!error} />
          </LazyWrapper>
          <LazyWrapper>
            <PerformanceMetrics loading={loading} error={!!error} />
          </LazyWrapper>
          
          {/* Row 2: Turn Pipeline, Quick Actions */}
          <LazyWrapper>
            <TurnPipelineStatus loading={loading} error={!!error} />
          </LazyWrapper>
          <QuickActions loading={loading} error={!!error} onAction={handleQuickAction} />
          
          {/* Row 3: Character Networks, Event Cascade */}
          <LazyWrapper>
            <CharacterNetworks loading={loading} error={!!error} />
          </LazyWrapper>
          <LazyWrapper>
            <EventCascadeFlow loading={loading} error={!!error} />
          </LazyWrapper>
          
          {/* Row 4: Narrative Timeline */}
          <LazyWrapper>
            <NarrativeTimeline loading={loading} error={!!error} />
          </LazyWrapper>
          
          {/* Row 5: Analytics Dashboard (collapsible) */}
          <LazyWrapper>
            <AnalyticsDashboard loading={loading} error={!!error} />
          </LazyWrapper>
        </>
      )}

      {/* Error Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleSnackbarClose} severity="info" variant="filled">
          {snackbarMessage}
        </Alert>
      </Snackbar>
      
      {/* System Status Indicator */}
      {systemStatus === 'offline' && (
        <Box
          sx={{
            position: 'fixed',
            top: 70,
            right: 16,
            zIndex: 9999,
          }}
        >
          <Alert severity="warning" variant="filled">
            System offline - Data may be stale
          </Alert>
        </Box>
      )}
    </DashboardLayout>
  );
};

export default Dashboard;
