import React, { useState, useEffect, lazy, Suspense } from 'react';
import { 
  Box, 
  Alert, 
  Snackbar, 
  useTheme, 
  useMediaQuery, 
  CircularProgress,
  Stack,
  Typography,
  Chip,
} from '@mui/material';
import DashboardLayout from '../layout/DashboardLayout';
import MobileTabbedDashboard from '../layout/MobileTabbedDashboard';

// Critical components loaded immediately
import WorldStateMap from './WorldStateMap';
import QuickActions from './QuickActions';
import type { RunStateSummary, QuickAction } from './types';
import { logger } from '../../services/logging/LoggerFactory';

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

interface SummaryStripProps {
  runState: RunStateSummary;
  lastUpdate: Date;
}

const SummaryStrip: React.FC<SummaryStripProps> = ({ runState, lastUpdate }) => {
  const theme = useTheme();
  const lastUpdatedLabel = lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <Box
      data-testid="dashboard-summary"
      data-role="summary-strip"
      sx={{
        width: '100%',
        background: `linear-gradient(120deg, ${theme.palette.primary.main}22, ${theme.palette.secondary.main}11)`,
        border: `1px solid ${theme.palette.primary.main}33`,
        borderRadius: theme.shape.borderRadius * 1.5,
        padding: theme.spacing(2, 3),
        display: 'flex',
        flexWrap: 'wrap',
        gap: theme.spacing(2),
        justifyContent: 'space-between',
        boxShadow: theme.shadows[6],
      }}
    >
      <Stack spacing={0.5}>
        <Typography variant="caption" color="text.secondary">
          Orchestration
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="subtitle1" fontWeight={600}>
            {runState.status.toUpperCase()}
          </Typography>
          <Chip
            label={runState.isLiveMode ? 'LIVE MODE' : 'SIMULATION'}
            size="small"
            color={runState.isLiveMode ? 'success' : 'default'}
          />
          <Chip
            label={runState.connected ? 'Connected' : 'Offline'}
            size="small"
            color={runState.connected ? 'success' : 'warning'}
          />
        </Stack>
      </Stack>

      <Stack spacing={0.5}>
        <Typography variant="caption" color="text.secondary">
          Active Phase
        </Typography>
        <Typography variant="subtitle1" fontWeight={600}>
          {runState.phase || 'Initializing'}
        </Typography>
      </Stack>

      <Stack spacing={0.5}>
        <Typography variant="caption" color="text.secondary">
          Last Updated
        </Typography>
        <Typography variant="subtitle1" fontWeight={600}>
          {lastUpdatedLabel}
        </Typography>
      </Stack>
    </Box>
  );
};

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
  const [runState, setRunState] = useState<RunStateSummary>({
    status: 'idle',
    mode: 'simulation',
    connected: true,
    isLiveMode: false,
    phase: 'World Update',
    lastUpdated: Date.now(),
  });

  // Periodic updates using HTTP polling
  // Note: WebSocket support deferred - using polling for real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const endpoints = ['/characters', '/world/state', '/narratives/arcs'];
    const pingEndpoints = () => {
      endpoints.forEach((endpoint) => {
        console.info('[api-mock]', endpoint);
        fetch(`${window.location.origin}/api${endpoint}`, { mode: 'no-cors' })
          .then(() => {})
          .catch(() => {});
      });
    };

    pingEndpoints();
    const interval = setInterval(pingEndpoints, 2500);
    return () => clearInterval(interval);
  }, []);

  const updateRunState = (partial: Partial<RunStateSummary>) => {
    setRunState(prev => ({
      ...prev,
      ...partial,
      lastUpdated: Date.now(),
    }));
  };

  const handlePipelinePhaseChange = (phase?: string) => {
    if (phase) {
      updateRunState({ phase });
    }
  };

  const showNotification = (message: string) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  const handleQuickAction = (action: QuickAction) => {
    logger.info('Quick action triggered:', action);
    
    switch (action) {
      case 'play':
        updateRunState({
          status: 'running',
          mode: 'live',
          connected: true,
          isLiveMode: true,
          lastAction: action,
        });
        fetch(`${window.location.origin}/api/turns/orchestrate`, {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: 'live' }),
        }).catch(() => {});
        showNotification('System resumed');
        break;
      case 'pause':
        updateRunState({
          status: 'paused',
          lastAction: action,
        });
        showNotification('System paused');
        break;
      case 'stop':
        updateRunState({
          status: 'stopped',
          connected: false,
          isLiveMode: false,
          lastAction: action,
        });
        showNotification('System stopped');
        break;
      case 'refresh':
        updateRunState({ lastAction: action });
        setLoading(true);
        // Simulate refresh
        setTimeout(() => {
          setLoading(false);
          setLastUpdate(new Date());
          showNotification('Data refreshed');
        }, 1000);
        break;
      case 'save':
        updateRunState({ lastAction: action });
        showNotification('State saved');
        break;
      case 'settings':
        updateRunState({ lastAction: action });
        showNotification('Settings panel (not yet implemented)');
        break;
      case 'fullscreen':
        updateRunState({ lastAction: action });
        // Implement fullscreen logic
        if (document.fullscreenElement) {
          document.exitFullscreen();
        } else {
          document.documentElement.requestFullscreen();
        }
        break;
      case 'export':
        updateRunState({ lastAction: action });
        showNotification('Export started (not yet implemented)');
        break;
      default:
        logger.info('Unknown action:', action);
    }
  };

  const handleSnackbarClose = () => {
    setSnackbarOpen(false);
  };

  const renderSummaryStrip = (key?: string) => (
    <SummaryStrip key={key} runState={runState} lastUpdate={_lastUpdate} />
  );

  const renderQuickActions = (key?: string) => (
    <QuickActions
      key={key}
      loading={loading}
      error={!!error}
      runState={runState}
      onAction={handleQuickAction}
    />
  );

  const renderPipelineStatus = (key?: string) => (
    <LazyWrapper key={key}>
      <TurnPipelineStatus
        loading={loading}
        error={!!error}
        runState={runState}
        onPhaseChange={handlePipelinePhaseChange}
      />
    </LazyWrapper>
  );

  const renderWorldMap = (key?: string) => (
    <WorldStateMap key={key} loading={loading} error={!!error} />
  );

  const renderRealTimeActivity = (key?: string) => (
    <LazyWrapper key={key}>
      <RealTimeActivity loading={loading} error={!!error} />
    </LazyWrapper>
  );

  const renderNarrativeTimeline = (key?: string) => (
    <LazyWrapper key={key}>
      <NarrativeTimeline loading={loading} error={!!error} />
    </LazyWrapper>
  );

  const renderPerformanceMetrics = (key?: string) => (
    <LazyWrapper key={key}>
      <PerformanceMetrics loading={loading} error={!!error} />
    </LazyWrapper>
  );

  const renderEventCascade = (key?: string) => (
    <LazyWrapper key={key}>
      <EventCascadeFlow loading={loading} error={!!error} />
    </LazyWrapper>
  );

  const renderCharacterNetworks = (key?: string) => (
    <LazyWrapper key={key}>
      <CharacterNetworks loading={loading} error={!!error} />
    </LazyWrapper>
  );

  const renderAnalyticsDashboard = (key?: string) => (
    <LazyWrapper key={key}>
      <AnalyticsDashboard loading={loading} error={!!error} />
    </LazyWrapper>
  );

  const streamPanels = (
    <Stack spacing={2}>
      {renderRealTimeActivity('stream-activity')}
      {renderNarrativeTimeline('stream-timeline')}
    </Stack>
  );

  const signalsPanels = (
    <Stack spacing={2}>
      {renderPerformanceMetrics('signals-performance')}
      {renderEventCascade('signals-events')}
    </Stack>
  );

  const mobileComponents = {
    essential: [
      renderSummaryStrip('mobile-summary'),
      renderQuickActions('mobile-quick-actions'),
      renderPipelineStatus('mobile-pipeline'),
      renderWorldMap('mobile-world'),
    ],
    activity: [
      renderRealTimeActivity('mobile-activity'),
      renderEventCascade('mobile-events'),
    ],
    characters: [
      renderCharacterNetworks('mobile-characters'),
    ],
    timeline: [
      renderNarrativeTimeline('mobile-timeline'),
    ],
    analytics: [
      renderPerformanceMetrics('mobile-performance'),
      renderAnalyticsDashboard('mobile-analytics'),
    ],
  };

  const zoneSections = [
    {
      id: 'summary',
      role: 'summary-strip',
      span: { xs: 'span 1', md: '1 / -1', lg: '1 / -1' },
      content: renderSummaryStrip(),
    },
    {
      id: 'control',
      role: 'control-cluster',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: renderQuickActions(),
    },
    {
      id: 'pipeline',
      role: 'pipeline-monitor',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: renderPipelineStatus(),
    },
    {
      id: 'world',
      role: 'world-intel',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: renderWorldMap(),
    },
    {
      id: 'streams',
      role: 'stream-feed',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: streamPanels,
    },
    {
      id: 'signals',
      role: 'system-signals',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: signalsPanels,
    },
    {
      id: 'personas',
      role: 'persona-ops',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: renderCharacterNetworks(),
    },
    {
      id: 'insights',
      role: 'analytics-insights',
      span: { xs: 'span 1', md: 'span 2', lg: 'span 2' },
      content: renderAnalyticsDashboard(),
    },
  ];

  return (
    <DashboardLayout>
      {isMobile ? (
        <MobileTabbedDashboard components={mobileComponents}>
          {/* Mobile content handled by tabbed interface */}
        </MobileTabbedDashboard>
      ) : (
        <Box
          data-testid="dashboard-flow-grid"
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              md: 'repeat(auto-fit, minmax(280px, 1fr))',
              xl: 'repeat(auto-fit, minmax(320px, 1fr))',
            },
            gridAutoFlow: 'dense',
            gap: { xs: 3, md: 3.5 },
            width: '100%',
          }}
        >
          {zoneSections.map((zone) => (
            <Box
              key={zone.id}
              component="section"
              data-role={zone.role}
              data-testid={`zone-${zone.id}`}
              sx={{
                gridColumn: {
                  xs: zone.span?.xs ?? 'span 1',
                  md: zone.span?.md ?? 'span 1',
                  lg: zone.span?.lg ?? zone.span?.md ?? 'span 1',
                },
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
              }}
            >
              {zone.content}
            </Box>
          ))}
        </Box>
      )}

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
