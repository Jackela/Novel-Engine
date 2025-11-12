import React, { useState, useEffect, useMemo, lazy, Suspense } from 'react';
import { Box, Alert, Snackbar, Typography, useTheme, useMediaQuery, CircularProgress, Chip } from '@mui/material';
import { formatDistanceToNow } from 'date-fns';
import DashboardLayout from '../layout/DashboardLayout';
import MobileTabbedDashboard from '../layout/MobileTabbedDashboard';
import DashboardZones from './DashboardZones';
import NarrativeActivityPanel from './NarrativeActivityPanel';
import SystemSignalsPanel from './SystemSignalsPanel';
import { getDensityMode } from '@/utils/density';
import { logger } from '@/services/logging/LoggerFactory';
import './Dashboard.css';

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

type PipelineStatus = 'idle' | 'running' | 'paused';

interface SummaryItem {
  label: string;
  value: React.ReactNode;
  helper?: React.ReactNode;
}

const SummaryStrip: React.FC<{ items: SummaryItem[] }> = ({ items }) => (
  <Box
    data-testid="dashboard-summary"
    className="dashboard-summary"
    sx={{
      display: 'grid',
      gridTemplateColumns: { xs: 'repeat(auto-fit, minmax(160px, 1fr))', md: 'repeat(4, minmax(180px, 1fr))' },
      gap: 2,
      mb: 3,
    }}
  >
    {items.map((item) => (
      <Box
        key={item.label}
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          p: 2,
          bgcolor: 'background.paper',
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
          {item.label}
        </Typography>
        <Typography variant="h5" fontWeight={600} sx={{ mt: 1 }}>
          {item.value}
        </Typography>
        {item.helper && (
          <Typography variant="caption" color="text.secondary">
            {item.helper}
          </Typography>
        )}
      </Box>
    ))}
  </Box>
);

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
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>('idle');
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [activityCount, setActivityCount] = useState(0);
  const [eventCount, setEventCount] = useState(0);

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
        setPipelineStatus('running');
        setIsLiveMode(true);
        showNotification('System resumed');
        break;
      case 'pause':
        setPipelineStatus('paused');
        setIsLiveMode(false);
        showNotification('System paused');
        break;
      case 'stop':
        setPipelineStatus('idle');
        setIsLiveMode(false);
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
      <QuickActions
        key="quick-actions"
        loading={loading}
        error={!!error}
        onAction={handleQuickAction}
        status={pipelineStatus}
        isLive={isLiveMode}
        runSummary={runSummary}
        density={controlDensity}
      />,
    ],
    activity: [
      <LazyWrapper key="real-time-activity">
        <RealTimeActivity
          loading={loading}
          error={!!error}
          isLive={isLiveMode}
          onActivityCountChange={setActivityCount}
        />
      </LazyWrapper>,
      <LazyWrapper key="performance-metrics">
        <PerformanceMetrics loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="turn-pipeline">
        <TurnPipelineStatus
          loading={loading}
          error={!!error}
          status={pipelineStatus}
          isLive={isLiveMode}
          runSummary={runSummary}
          density={pipelineDensity}
        />
      </LazyWrapper>,
    ],
    characters: [
      <LazyWrapper key="character-networks">
        <CharacterNetworks loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="event-cascade">
        <EventCascadeFlow loading={loading} error={!!error} onCountChange={setEventCount} />
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

  const summaryItems: SummaryItem[] = [
    {
      label: 'System Status',
      value: systemStatus === 'online' ? 'Online' : systemStatus === 'maintenance' ? 'Maintenance' : 'Offline',
      helper: `Updated ${formatDistanceToNow(_lastUpdate, { addSuffix: true })}`,
    },
    {
      label: 'Pipeline',
      value: pipelineStatus === 'running' ? 'Running' : pipelineStatus === 'paused' ? 'Paused' : 'Idle',
      helper: isLiveMode ? 'Live mode active' : 'Live mode off',
    },
    {
      label: 'Next Refresh',
      value: formatDistanceToNow(new Date(_lastUpdate.getTime() + 10000), { addSuffix: true }),
      helper: 'Auto-poll every 10s',
    },
    {
      label: 'Notifications',
      value: snackbarOpen ? '1 open' : 'None',
      helper: snackbarOpen ? snackbarMessage : 'All clear',
    },
  ];

  const runSummary = useMemo(() => {
    const basePhase =
      pipelineStatus === 'running'
        ? 'Interaction Orchestration'
        : pipelineStatus === 'paused'
        ? 'Paused'
        : 'Idle';
    return {
      phase: basePhase,
      completed: pipelineStatus === 'running' ? 2 : pipelineStatus === 'paused' ? 4 : 0,
      total: 5,
      lastSignal: formatDistanceToNow(_lastUpdate, { addSuffix: true }),
    };
  }, [pipelineStatus, _lastUpdate]);

  const controlDensity = getDensityMode({
    count: snackbarOpen || pipelineStatus !== 'idle' ? 5 : 1,
    relaxedThreshold: 3,
  });

  const streamDensity = getDensityMode({
    count: activityCount,
    relaxedThreshold: 6,
  });

  const signalsDensity = getDensityMode({
    count: eventCount,
    relaxedThreshold: 5,
  });

  const pipelineDensity = getDensityMode({
    count: pipelineStatus === 'running' ? 5 : 1,
    relaxedThreshold: 3,
  });

  const desktopZones = [
    {
      id: 'world-map',
      role: 'spatial-map',
      priority: 5,
      testId: 'zone-world-map',
      children: <WorldStateMap loading={loading} error={!!error} />,
    },
    {
      id: 'quick-actions',
      role: 'control-cluster',
      priority: 4,
      testId: 'zone-quick-actions',
      density: controlDensity,
      children: (
        <QuickActions
          loading={loading}
          error={!!error}
          onAction={handleQuickAction}
          status={pipelineStatus}
          isLive={isLiveMode}
          runSummary={runSummary}
          density={controlDensity}
        />
      ),
    },
    {
      id: 'character-networks',
      role: 'spatial-network',
      priority: 3,
      testId: 'zone-character-networks',
      children: (
        <LazyWrapper>
          <CharacterNetworks loading={loading} error={!!error} />
        </LazyWrapper>
      ),
    },
    {
      id: 'streams',
      role: 'stream-feed',
      priority: 2,
      testId: 'zone-streams',
      density: streamDensity,
      volumeLabel: activityCount > 6 ? 'high-activity' : undefined,
      children: (
        <LazyWrapper>
          <NarrativeActivityPanel
            density={streamDensity}
            timelineProps={{ loading, error: !!error }}
            activityProps={{
              loading,
              error: !!error,
              isLive: isLiveMode,
              onActivityCountChange: setActivityCount,
            }}
          />
        </LazyWrapper>
      ),
    },
    {
      id: 'signals',
      role: 'system-signals',
      priority: 1,
      testId: 'zone-signals',
      density: signalsDensity,
      volumeLabel: eventCount > 5 ? 'high-events' : undefined,
      children: (
        <LazyWrapper>
          <SystemSignalsPanel
            density={signalsDensity}
            performanceProps={{ loading, error: !!error }}
            eventProps={{ loading, error: !!error, onCountChange: setEventCount }}
          />
        </LazyWrapper>
      ),
    },
    {
      id: 'pipeline',
      role: 'pipeline',
      priority: 0,
      testId: 'zone-pipeline',
      className: 'pipeline-zone',
      density: pipelineDensity,
      children: (
        <LazyWrapper>
          <TurnPipelineStatus
            loading={loading}
            error={!!error}
            status={pipelineStatus}
            isLive={isLiveMode}
            runSummary={runSummary}
            density={pipelineDensity}
          />
        </LazyWrapper>
      ),
    },
  ];

  return (
    <DashboardLayout>
      <SummaryStrip items={summaryItems} />
      {isMobile ? (
        <MobileTabbedDashboard components={mobileComponents}>
          {/* Mobile content handled by tabbed interface */}
        </MobileTabbedDashboard>
      ) : (
        <DashboardZones zones={desktopZones} />
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
