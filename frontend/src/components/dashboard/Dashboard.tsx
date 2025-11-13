import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Box, Alert, Snackbar, useTheme, useMediaQuery, CircularProgress, Stack } from '@mui/material';
import { styled } from '@mui/material/styles';
import DashboardLayout from '../layout/DashboardLayout';
import MobileTabbedDashboard from '../layout/MobileTabbedDashboard';
import { logger } from '../../services/logging/LoggerFactory';
import WorldStateMap from './WorldStateMapV2';
import QuickActions, { type QuickAction } from './QuickActions';
import SummaryStrip from './SummaryStrip';

const RealTimeActivity = lazy(() => import('./RealTimeActivity'));
const PerformanceMetrics = lazy(() => import('./PerformanceMetrics'));
const TurnPipelineStatus = lazy(() => import('./TurnPipelineStatus'));
const CharacterNetworks = lazy(() => import('./CharacterNetworks'));
const EventCascadeFlow = lazy(() => import('./EventCascadeFlow'));
const NarrativeTimeline = lazy(() => import('./NarrativeTimeline'));
const AnalyticsDashboard = lazy(() => import('./AnalyticsDashboard'));

const LazyWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense
    fallback={
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
        <CircularProgress size={24} />
      </Box>
    }
  >
    {children}
  </Suspense>
);

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';

interface DashboardProps {
  userId?: string;
  campaignId?: string;
}

interface ZoneSpan {
  desktop?: number;
  tablet?: number;
  mobile?: number;
}

interface ZoneConfig {
  id: string;
  role: string;
  span?: ZoneSpan;
  content: React.ReactNode;
}

const ZoneWrapper = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(1.5),
}));

const Dashboard: React.FC<DashboardProps> = ({ userId: _userId, campaignId: _campaignId }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [loading, setLoading] = useState(false);
  const [error, _setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [systemStatus, _setSystemStatus] = useState<'online' | 'offline' | 'maintenance'>('online');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [pipelineStatus, setPipelineStatus] = useState<PipelineState>('idle');
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [isOnline, setIsOnline] = useState(() => {
    if (typeof navigator === 'undefined') {
      return true;
    }
    return navigator.onLine;
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleOnline = () => {
      setIsOnline(true);
      showNotification('Connection restored. Resuming live data.');
    };

    const handleOffline = () => {
      setIsOnline(false);
      setIsLiveMode(false);
      showNotification('Connection lost. Working offline.');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const showNotification = (message: string) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  const handleQuickAction = (action: QuickAction) => {
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
        setPipelineStatus('stopped');
        setIsLiveMode(false);
        showNotification('System stopped');
        break;
      case 'refresh':
        setLoading(true);
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

  const mobileComponents = {
    essential: [
      <SummaryStrip key="summary-strip" lastUpdate={lastUpdate} pipelineStatus={pipelineStatus} isLive={isLiveMode} isOnline={isOnline} />,
      <WorldStateMap key="world-map" loading={loading} error={!!error} />,
      <QuickActions
        key="quick-actions"
        loading={loading}
        error={!!error}
        status={pipelineStatus}
        isLive={isLiveMode}
        isOnline={isOnline}
        onAction={handleQuickAction}
      />,
      <LazyWrapper key="turn-pipeline">
        <TurnPipelineStatus loading={loading} error={!!error} status={pipelineStatus} isLive={isLiveMode} />
      </LazyWrapper>,
    ],
    activity: [
      <LazyWrapper key="real-time-activity">
        <RealTimeActivity loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="narrative-timeline">
        <NarrativeTimeline loading={loading} error={!!error} />
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
    analytics: [
      <LazyWrapper key="performance-metrics">
        <PerformanceMetrics loading={loading} error={!!error} />
      </LazyWrapper>,
      <LazyWrapper key="analytics">
        <AnalyticsDashboard loading={loading} error={!!error} />
      </LazyWrapper>,
    ],
  };

  const zoneConfigs: ZoneConfig[] = [
    {
      id: 'summary',
      role: 'summary-strip',
      span: { desktop: 3, tablet: 2 },
      content: (
        <SummaryStrip
          lastUpdate={lastUpdate}
          pipelineStatus={pipelineStatus}
          isLive={isLiveMode}
          isOnline={isOnline}
        />
      ),
    },
    {
      id: 'world-map',
      role: 'hero-map',
      span: { desktop: 3, tablet: 2 },
      content: <WorldStateMap loading={loading} error={!!error} />,
    },
    {
      id: 'control-cluster',
      role: 'control-cluster',
      span: { desktop: 1, tablet: 2 },
      content: (
        <QuickActions
          loading={loading}
          error={!!error}
          status={pipelineStatus}
          isLive={isLiveMode}
          isOnline={isOnline}
          onAction={handleQuickAction}
        />
      ),
    },
    {
      id: 'pipeline',
      role: 'pipeline',
      span: { desktop: 2, tablet: 2 },
      content: (
        <LazyWrapper>
          <TurnPipelineStatus loading={loading} error={!!error} status={pipelineStatus} isLive={isLiveMode} />
          <TurnPipelineStatus loading={loading} error={!!error} status={pipelineStatus} isLive={isLiveMode} />
        </LazyWrapper>
      ),
    },
    {
      id: 'streams',
      role: 'stream-feed',
      span: { desktop: 2, tablet: 2 },
      content: (
        <Stack spacing={2}>
          <LazyWrapper>
            <RealTimeActivity loading={loading} error={!!error} />
          </LazyWrapper>
          <LazyWrapper>
            <NarrativeTimeline loading={loading} error={!!error} />
          </LazyWrapper>
        </Stack>
      ),
    },
    {
      id: 'signals',
      role: 'system-signals',
      span: { desktop: 2, tablet: 2 },
      content: (
        <Stack spacing={2}>
          <LazyWrapper>
            <PerformanceMetrics loading={loading} error={!!error} />
          </LazyWrapper>
          <LazyWrapper>
            <EventCascadeFlow loading={loading} error={!!error} />
          </LazyWrapper>
        </Stack>
      ),
    },
    {
      id: 'characters',
      role: 'network-visuals',
      span: { desktop: 2, tablet: 2 },
      content: (
        <LazyWrapper>
          <CharacterNetworks loading={loading} error={!!error} />
        </LazyWrapper>
      ),
    },
    {
      id: 'insights',
      role: 'insights',
      span: { desktop: 2, tablet: 2 },
      content: (
        <LazyWrapper>
          <AnalyticsDashboard loading={loading} error={!!error} />
        </LazyWrapper>
      ),
    },
  ];

  const renderZoneWrapper = (zone: ZoneConfig) => (
    <ZoneWrapper
      key={zone.id}
      data-role={zone.role}
      sx={{
        gridColumn: {
          lg: zone.span?.desktop ? `span ${zone.span.desktop}` : 'span 1',
          md: zone.span?.tablet ? `span ${zone.span.tablet}` : 'span 2',
          xs: zone.span?.mobile ? `span ${zone.span.mobile}` : 'span 1',
        },
      }}
    >
      {zone.content}
    </ZoneWrapper>
  );

  return (
    <DashboardLayout>
      {isMobile ? (
        <MobileTabbedDashboard components={mobileComponents}>
          {/* Mobile view handled via tabs */}
        </MobileTabbedDashboard>
      ) : (
        zoneConfigs.map(renderZoneWrapper)
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
