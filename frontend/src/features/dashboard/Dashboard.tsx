/**
 * Dashboard Component
 *
 * Minimal Command Center for the Novel Engine.
 * Focused, low-distraction UI for core telemetry and orchestration.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { Alert, Snackbar, Box, Button, IconButton, Tabs, Tab, Stack } from '@mui/material';
import CommandTopBar from '@/components/layout/CommandTopBar';
import GridTile from '@/components/layout/GridTile';
import { logger } from '@/services/logging/LoggerFactory';
import { dashboardAPI } from '@/services/api/dashboardAPI';
import { DecisionPointDialog } from '@/components/decision';
import CharacterCreationDialog from '../characters/CharacterCreationDialog';
import { useRealtimeEvents, type RealtimeEvent } from '@/hooks/useRealtimeEvents';
import { setDecisionPoint, clearDecisionPoint, type DecisionPoint } from '@/store/slices/decisionSlice';
import { fetchDashboardData } from '@/store/slices/dashboardSlice';
import type { AppDispatch } from '@/store/store';
import { useCharactersQuery } from '@/services/queries';
import EmptyState from '@/components/common/EmptyState';
import { SkeletonDashboard } from '@/components/loading/SkeletonDashboard';
import { ApiError } from '@/lib/api/errors';
import { FALLBACK_DASHBOARD_CHARACTERS } from '@/hooks/useDashboardCharactersDataset';
import { useAuthContext } from '@/contexts/useAuthContext';

// Import panels
import WorldPanel from './panels/WorldPanel';
import NarrativePanel from './panels/NarrativePanel';
import CharacterNetworks from './CharacterNetworks';
import NarrativeTimeline from './NarrativeTimeline';
import TurnPipelineStatus from './TurnPipelineStatus';
import AnalyticsDashboard from './AnalyticsDashboard';
import EventCascadeFlow from './EventCascadeFlow';
import PerformanceMetrics from './PerformanceMetrics';

// Icons
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Add as AddIcon,
  Map as MapIcon,
  Hub as HubIcon,
  Timeline as TimelineIcon,
  AutoStories as StoryIcon,
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon,
  AccountTree as FlowIcon,
  PersonAdd as PersonAddIcon,
} from '@mui/icons-material';

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';
type DashboardView = 'world' | 'network' | 'timeline' | 'narrative' | 'analytics' | 'signals';

interface DashboardProps {
  userId?: string;
  campaignId?: string;
}

const isConnectionError = (error: unknown) =>
  error instanceof ApiError && (error.kind === 'network' || error.kind === 'timeout');

const buildDecisionPoint = (event: RealtimeEvent): DecisionPoint | null => {
  if (event.type !== 'decision_required' || !event.data) {
    return null;
  }

  const data = event.data as Record<string, unknown>;
  return {
    decisionId: data.decision_id as string,
    decisionType: data.decision_type as DecisionPoint['decisionType'],
    turnNumber: data.turn_number as number,
    title: data.title as string,
    description: data.description as string,
    narrativeContext: (data.narrative_context as string) || '',
    options: ((data.options as Array<Record<string, unknown>>) || []).map((opt) => ({
      optionId: opt.option_id as number,
      label: opt.label as string,
      description: opt.description as string,
      ...(opt.icon ? { icon: opt.icon as string } : {}),
      ...(opt.impact_preview ? { impactPreview: opt.impact_preview as string } : {}),
      ...(opt.is_default !== undefined ? { isDefault: opt.is_default as boolean } : {}),
    })),
    ...(data.default_option_id !== undefined ? { defaultOptionId: data.default_option_id as number } : {}),
    timeoutSeconds: (data.timeout_seconds as number) || 120,
    dramaticTension: (data.dramatic_tension as number) || 7,
    emotionalIntensity: (data.emotional_intensity as number) || 7,
    createdAt: data.created_at as string,
    expiresAt: data.expires_at as string,
  };
};

const useSnackbar = () => {
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  const showNotification = (message: string) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  const handleSnackbarClose = () => setSnackbarOpen(false);

  return { snackbarOpen, snackbarMessage, showNotification, handleSnackbarClose };
};

const useDashboardCharacters = () => {
  const { data: characters, isLoading, isError, error } = useCharactersQuery();
  const effectiveCharacters = characters && Array.isArray(characters) && characters.length > 0
    ? characters.map((character) => character.id)
    : FALLBACK_DASHBOARD_CHARACTERS.map((character) => character.name);
  const shouldShowFallbackAlert = isError || Boolean(error);

  return {
    characters,
    isLoading,
    error: error as Error | undefined,
    isError,
    effectiveCharacters,
    shouldShowFallbackAlert,
  };
};

const useOnlineStatus = (showNotification: (message: string) => void) => {
  const [isOnline, setIsOnline] = useState(() => {
    if (typeof navigator === 'undefined') return true;
    return navigator.onLine;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      setIsOnline(true);
      showNotification('Connection restored.');
    };

    const handleOffline = () => {
      setIsOnline(false);
      showNotification('Connection lost.');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const syncNavigatorStatus = () => {
      if (typeof navigator === 'undefined') return;
      const online = navigator.onLine;
      setIsOnline((prev) => (prev === online ? prev : online));
    };

    const intervalId = window.setInterval(syncNavigatorStatus, 1000);
    syncNavigatorStatus();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.clearInterval(intervalId);
    };
  }, [showNotification]);

  return isOnline;
};

const useAutoRefreshTimestamp = () => {
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    const interval = setInterval(() => setLastUpdate(new Date()), 10000);
    return () => clearInterval(interval);
  }, []);

  const refreshNow = () => setLastUpdate(new Date());

  return { lastUpdate, refreshNow };
};

const useBackendStatus = () => {
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'error'>('offline');
  const [backendVersion, setBackendVersion] = useState<string | undefined>(undefined);

  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await dashboardAPI.getHealth();
        if (response.data && response.data.status === 'healthy') {
          setBackendStatus('online');
          setBackendVersion(response.data.version || undefined);
        } else {
          setBackendStatus('error');
        }
      } catch (error) {
        logger.error('Backend health check failed', error as Error);
        setBackendStatus('offline');
        setBackendVersion(undefined);
      }
    };

    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return { backendStatus, backendVersion };
};

const useLivePolling = (isLiveMode: boolean, dispatch: AppDispatch) => {
  useEffect(() => {
    let pollingInterval: NodeJS.Timeout | undefined;

    if (isLiveMode) {
      pollingInterval = setInterval(() => {
        dispatch(fetchDashboardData());
      }, 3000);
    }

    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [isLiveMode, dispatch]);
};

const useDecisionEvents = (isOnline: boolean, showNotification: (message: string) => void) => {
  const dispatch = useDispatch<AppDispatch>();

  const handleDecisionEvent = useCallback(
    (event: RealtimeEvent) => {
      logger.info('Decision event received in Dashboard:', { type: event.type, id: event.id });
      const decisionPoint = buildDecisionPoint(event);

      if (decisionPoint) {
        dispatch(setDecisionPoint(decisionPoint));
        showNotification('Decision point reached - your input is needed!');
        return;
      }

      if (event.type === 'decision_accepted' || event.type === 'decision_finalized') {
        dispatch(clearDecisionPoint());
      }
    },
    [dispatch, showNotification]
  );

  const { events } = useRealtimeEvents({
    enabled: isOnline,
    onDecisionEvent: handleDecisionEvent,
  });

  return events;
};

const createStartHandler = (params: {
  effectiveCharacters: string[];
  setPipelineStatus: (status: PipelineState) => void;
  setIsLiveMode: (value: boolean) => void;
  setActiveView: (view: DashboardView) => void;
  showNotification: (message: string) => void;
  refreshTimestamp: () => void;
  dispatch: AppDispatch;
  setLoading: (value: boolean) => void;
}) => async () => {
  params.setLoading(true);
  try {
    if (params.effectiveCharacters.length === 0) {
      params.showNotification('No characters available to start simulation');
      params.setLoading(false);
      return;
    }

    const response = await dashboardAPI.startOrchestration({
      character_names: params.effectiveCharacters,
      total_turns: 3,
    });

    if (response.data.success) {
      const status = response.data.data?.status || 'running';
      params.setPipelineStatus(status as PipelineState);
      params.setIsLiveMode(status === 'running');
      params.setActiveView('narrative');
      params.dispatch(fetchDashboardData());
      params.showNotification(`Orchestration started with ${params.effectiveCharacters.length} characters`);
    } else {
      params.showNotification('Failed to start orchestration');
    }
  } catch (err) {
    params.showNotification(`Failed to start: ${(err as Error).message}`);
  } finally {
    params.setLoading(false);
  }
};

const createPauseHandler = (params: {
  setPipelineStatus: (status: PipelineState) => void;
  setIsLiveMode: (value: boolean) => void;
  showNotification: (message: string) => void;
  dispatch: AppDispatch;
  setLoading: (value: boolean) => void;
}) => async () => {
  params.setLoading(true);
  try {
    const response = await dashboardAPI.pauseOrchestration();
    if (response.data.success) {
      params.setPipelineStatus('paused');
      params.setIsLiveMode(false);
      params.dispatch(fetchDashboardData());
      params.showNotification('Orchestration paused');
    }
  } catch (err) {
    params.showNotification(`Failed to pause: ${(err as Error).message}`);
  } finally {
    params.setLoading(false);
  }
};

const createStopHandler = (params: {
  setPipelineStatus: (status: PipelineState) => void;
  setIsLiveMode: (value: boolean) => void;
  showNotification: (message: string) => void;
  dispatch: AppDispatch;
  setLoading: (value: boolean) => void;
}) => async () => {
  params.setLoading(true);
  try {
    const response = await dashboardAPI.stopOrchestration();
    if (response.data.success) {
      params.setPipelineStatus('stopped');
      params.setIsLiveMode(false);
      params.dispatch(fetchDashboardData());
      params.showNotification('Orchestration stopped');
    }
  } catch (err) {
    params.showNotification(`Failed to stop: ${(err as Error).message}`);
  } finally {
    params.setLoading(false);
  }
};

const createRefreshHandler = (params: {
  setPipelineStatus: (status: PipelineState) => void;
  setIsLiveMode: (value: boolean) => void;
  showNotification: (message: string) => void;
  refreshTimestamp: () => void;
  setLoading: (value: boolean) => void;
}) => async () => {
  params.setLoading(true);
  try {
    const [_statusRes, orchestrationRes] = await Promise.all([
      dashboardAPI.getSystemStatus(),
      dashboardAPI.getOrchestrationStatus(),
    ]);
    if (orchestrationRes.data.success && orchestrationRes.data.data) {
      params.setPipelineStatus(orchestrationRes.data.data.status as PipelineState);
      params.setIsLiveMode(orchestrationRes.data.data.status === 'running');
    }
    params.refreshTimestamp();
    params.showNotification('Data refreshed');
  } catch {
    params.showNotification('Failed to refresh data');
  } finally {
    params.setLoading(false);
  }
};

const usePipelineActions = (params: {
  effectiveCharacters: string[];
  setPipelineStatus: (status: PipelineState) => void;
  setIsLiveMode: (value: boolean) => void;
  setActiveView: (view: DashboardView) => void;
  showNotification: (message: string) => void;
  refreshTimestamp: () => void;
  dispatch: AppDispatch;
  setLoading: (value: boolean) => void;
}) => {
  const {
    effectiveCharacters,
    setPipelineStatus,
    setIsLiveMode,
    setActiveView,
    showNotification,
    refreshTimestamp,
    dispatch,
    setLoading,
  } = params;

  const handleStartOrchestration = createStartHandler({
    effectiveCharacters,
    setPipelineStatus,
    setIsLiveMode,
    setActiveView,
    showNotification,
    refreshTimestamp,
    dispatch,
    setLoading,
  });
  const handlePauseOrchestration = createPauseHandler({
    setPipelineStatus,
    setIsLiveMode,
    showNotification,
    dispatch,
    setLoading,
  });
  const handleStopOrchestration = createStopHandler({
    setPipelineStatus,
    setIsLiveMode,
    showNotification,
    dispatch,
    setLoading,
  });
  const handleRefresh = createRefreshHandler({
    setPipelineStatus,
    setIsLiveMode,
    showNotification,
    refreshTimestamp,
    setLoading,
  });

  return { handleStartOrchestration, handlePauseOrchestration, handleStopOrchestration, handleRefresh };
};

const DashboardGuestBanner: React.FC<{ workspaceId?: string }> = ({ workspaceId }) => (
  <Box sx={{ px: { xs: 2, md: 3 }, pb: 2 }}>
    <Alert
      severity="info"
      variant="outlined"
      data-testid="guest-mode-banner"
      sx={{ borderColor: 'var(--color-border-secondary)' }}
    >
      Guest session active{workspaceId ? ` (${workspaceId})` : ''}. Work is stored in this browser session.
    </Alert>
  </Box>
);

const DashboardEmptyState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <Box sx={{ height: 'calc(100vh - 120px)', p: 4, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
    <EmptyState
      title="System Standby: No Operatives Detected"
      description="The command deck requires at least one active operative to initialize the world simulation. Create a character to bring the system online."
      actionLabel="Initialize Operative"
      onAction={onCreate}
      icon={<PersonAddIcon />}
    />
  </Box>
);

const DashboardFallbackAlert: React.FC<{ isConnectionError: boolean }> = ({ isConnectionError }) => (
  <div data-testid="fallback-dataset-alert">
    <Alert severity="warning" sx={{ gridColumn: '1 / -1', mb: 2 }}>
      Live character data unavailable; showing fallback dataset. {isConnectionError ? 'Offline mode detected.' : ''}
    </Alert>
  </div>
);

const DashboardViewTabs: React.FC<{
  activeView: DashboardView;
  onChange: (_event: React.SyntheticEvent, view: DashboardView) => void;
  onRefresh: () => void;
  backendStatus?: 'online' | 'offline' | 'error';
  backendVersion?: string;
}> = ({ activeView, onChange, onRefresh, backendStatus, backendVersion }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    <Tabs
      value={activeView}
      onChange={onChange}
      textColor="primary"
      indicatorColor="primary"
      sx={{ minHeight: '36px' }}
    >
      <Tab icon={<MapIcon fontSize="small" />} iconPosition="start" label="Map" value="world" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
      <Tab icon={<HubIcon fontSize="small" />} iconPosition="start" label="Network" value="network" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
      <Tab icon={<TimelineIcon fontSize="small" />} iconPosition="start" label="Timeline" value="timeline" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
      <Tab icon={<StoryIcon fontSize="small" />} iconPosition="start" label="Narrative" value="narrative" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
      <Tab icon={<AnalyticsIcon fontSize="small" />} iconPosition="start" label="Analytics" value="analytics" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
      <Tab icon={<FlowIcon fontSize="small" />} iconPosition="start" label="Signals" value="signals" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
    </Tabs>
    {backendStatus === 'error' && <BackendStatusIndicator version={backendVersion} status={backendStatus} />}
    <IconButton
      onClick={onRefresh}
      size="small"
      sx={{
        transition: 'all 0.2s',
        '&:hover': { transform: 'rotate(180deg)', color: 'var(--color-primary)' },
      }}
      data-testid="quick-action-refresh"
      aria-label="Refresh data"
    >
      <RefreshIcon htmlColor="var(--color-text-secondary)" />
    </IconButton>
  </Box>
);

const BackendStatusIndicator: React.FC<{ version?: string; status?: 'online' | 'offline' | 'error' }> = ({ version, status = 'offline' }) => {
  const statusColors = {
    online: 'var(--color-success)',
    offline: 'var(--color-text-tertiary)',
    error: 'var(--color-error)',
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        fontSize: '0.75rem',
        color: 'var(--color-text-secondary)',
        px: 1,
        py: 0.5,
        bgcolor: 'var(--color-bg-tertiary)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--color-border-primary)',
      }}
      data-testid="backend-status"
    >
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          bgcolor: statusColors[status],
          boxShadow: status === 'online' ? `0 0 8px ${statusColors[status]}` : 'none',
        }}
      />
      <span>Backend: {status === 'online' ? 'Online' : status === 'error' ? 'Error' : 'Offline'}</span>
      {version && <span style={{ color: 'var(--color-text-tertiary)' }}>v{version}</span>}
    </Box>
  );
};

const SystemLogPanel: React.FC<{ events: RealtimeEvent[] }> = ({ events }) => (
  <Box
    sx={{
      fontFamily: 'var(--font-mono)',
      fontSize: '0.75rem',
      color: 'var(--color-text-secondary)',
      height: '100%',
      overflowY: 'auto',
      p: 1,
      bgcolor: 'var(--color-bg-tertiary)',
      borderRadius: 'var(--radius-sm)',
      border: '1px solid var(--color-border-primary)',
    }}
    data-testid="system-log"
  >
    {events.map((event, index) => (
      <Box
        key={index}
        sx={{
          mb: 0.5,
          borderBottom: '1px solid var(--color-border-primary)',
          pb: 0.5,
          '&:last-child': { borderBottom: 'none' },
        }}
        data-testid="activity-event"
      >
        <span style={{ color: 'var(--color-primary)' }}>[{new Date(event.timestamp).toLocaleTimeString()}]</span>
        <span style={{ marginLeft: '8px', color: 'var(--color-text-primary)' }}>{event.description}</span>
      </Box>
    ))}
    {events.length === 0 && (
      <Box sx={{ textAlign: 'center', color: 'var(--color-text-tertiary)', mt: 4 }}>
        System Ready. Awaiting Input.
      </Box>
    )}
  </Box>
);

const CommandDeckPanel: React.FC<{
  isLiveMode: boolean;
  onStart: () => void;
  onPause: () => void;
  onStop: () => void;
  onCreate: () => void;
}> = ({ isLiveMode, onStart, onPause, onStop, onCreate }) => (
  <Stack spacing={2} height="100%" justifyContent="center" data-testid="quick-actions">
    <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
      <Button
        variant="contained"
        color={isLiveMode ? 'warning' : 'primary'}
        startIcon={isLiveMode ? <PauseIcon /> : <PlayIcon />}
        onClick={isLiveMode ? onPause : onStart}
        fullWidth
        sx={{
          height: 48,
          backgroundColor: isLiveMode ? 'var(--color-warning)' : 'var(--color-primary)',
          color: 'var(--color-bg-primary)',
          fontWeight: 'bold',
          '&:hover': {
            backgroundColor: isLiveMode ? 'var(--color-warning-border)' : 'var(--color-primary-400)',
          },
        }}
        data-testid={isLiveMode ? 'quick-action-pause' : 'quick-action-play'}
        aria-label={isLiveMode ? 'Pause Orchestration' : 'Start Orchestration'}
      >
        {isLiveMode ? 'PAUSE' : 'START'}
      </Button>
      <Button
        variant="outlined"
        color="error"
        startIcon={<StopIcon />}
        onClick={onStop}
        disabled={!isLiveMode}
        fullWidth
        sx={{
          height: 48,
          borderColor: 'var(--color-error)',
          color: 'var(--color-error)',
        }}
        data-testid="quick-action-stop"
        aria-label="Stop Orchestration"
      >
        STOP
      </Button>
    </Box>

    <Button
      variant="outlined"
      color="secondary"
      startIcon={<AddIcon />}
      onClick={onCreate}
      fullWidth
      sx={{
        borderColor: 'var(--color-border-secondary)',
        color: 'var(--color-text-secondary)',
        '&:hover': { borderColor: 'var(--color-primary)', color: 'var(--color-primary)' },
      }}
      aria-label="Create New Operative"
    >
      New Operative
    </Button>
  </Stack>
);

const DashboardPrimaryTile: React.FC<{
  activeView: DashboardView;
  onViewChange: (_event: React.SyntheticEvent, view: DashboardView) => void;
  onRefresh: () => void;
  loading: boolean;
  error: boolean;
  pipelineStatus: PipelineState;
  onStart: () => void;
  backendStatus?: 'online' | 'offline' | 'error';
  backendVersion?: string;
}> = ({ activeView, onViewChange, onRefresh, loading, error, pipelineStatus, onStart, backendStatus, backendVersion }) => (
  <GridTile
    title="World State Visualization"
    position={{
      desktop: { column: 'span 5', row: 'span 2', height: '620px' },
      tablet: { column: 'span 8', height: '500px' },
      mobile: { column: 'span 1', height: '400px' },
    }}
    headerAction={<DashboardViewTabs activeView={activeView} onChange={onViewChange} onRefresh={onRefresh} backendStatus={backendStatus} backendVersion={backendVersion} />}
  >
    {activeView === 'world' && <WorldPanel loading={loading} error={error} />}
    {activeView === 'network' && <CharacterNetworks loading={loading} error={error} />}
    {activeView === 'timeline' && <NarrativeTimeline loading={loading} error={error} />}
    {activeView === 'narrative' && <NarrativePanel pipelineStatus={pipelineStatus} onStart={onStart} />}
    {activeView === 'analytics' && <AnalyticsDashboard loading={loading} error={error} />}
    {activeView === 'signals' && <EventCascadeFlow loading={loading} error={error} />}
  </GridTile>
);

const DashboardSecondaryTiles: React.FC<{
  loading: boolean;
  error: boolean;
  pipelineStatus: PipelineState;
  isLiveMode: boolean;
  isOnline: boolean;
  realtimeEvents: RealtimeEvent[];
  onStart: () => void;
  onPause: () => void;
  onStop: () => void;
  onCreateCharacter: () => void;
}> = ({
  loading,
  error,
  pipelineStatus,
  isLiveMode,
  isOnline,
  realtimeEvents,
  onStart,
  onPause,
  onStop,
  onCreateCharacter,
}) => (
  <>
    <GridTile
      title="Pipeline Status"
      position={{
        desktop: { column: 'span 3', height: '300px' },
        tablet: { column: 'span 4', height: '300px' },
        mobile: { column: 'span 1', height: 'auto' },
      }}
    >
      <TurnPipelineStatus
        loading={loading}
        error={error}
        status={pipelineStatus}
        isLive={isLiveMode}
        isOnline={isOnline}
      />
    </GridTile>

    <GridTile
      title="System Metrics"
      position={{
        desktop: { column: 'span 3', height: '300px' },
        tablet: { column: 'span 4', height: '300px' },
        mobile: { column: 'span 1', height: 'auto' },
      }}
    >
      <PerformanceMetrics />
    </GridTile>

    <GridTile
      title="System Log"
      position={{
        desktop: { column: 'span 4', height: '400px' },
        tablet: { column: 'span 8', height: '250px' },
        mobile: { column: 'span 1', height: '200px' },
      }}
    >
      <SystemLogPanel events={realtimeEvents} />
    </GridTile>

    <GridTile
      title="Command Deck"
      position={{
        desktop: { column: 'span 4', height: '200px' },
        tablet: { column: 'span 4', height: '200px' },
        mobile: { column: 'span 1', height: 'auto' },
      }}
    >
      <CommandDeckPanel
        isLiveMode={isLiveMode}
        onStart={onStart}
        onPause={onPause}
        onStop={onStop}
        onCreate={onCreateCharacter}
      />
    </GridTile>
  </>
);

const DashboardGrid: React.FC<{
  showFallbackAlert: boolean;
  isConnectionError: boolean;
  activeView: DashboardView;
  onViewChange: (_event: React.SyntheticEvent, view: DashboardView) => void;
  onRefresh: () => void;
  loading: boolean;
  error: boolean;
  pipelineStatus: PipelineState;
  isLiveMode: boolean;
  isOnline: boolean;
  realtimeEvents: RealtimeEvent[];
  onStart: () => void;
  onPause: () => void;
  onStop: () => void;
  onCreateCharacter: () => void;
  backendStatus?: 'online' | 'offline' | 'error';
  backendVersion?: string;
}> = ({
  showFallbackAlert,
  isConnectionError,
  activeView,
  onViewChange,
  onRefresh,
  loading,
  error,
  pipelineStatus,
  isLiveMode,
  isOnline,
  realtimeEvents,
  onStart,
  onPause,
  onStop,
  onCreateCharacter,
  backendStatus,
  backendVersion,
}) => (
  <div className="bento-grid" data-testid="bento-grid">
    {showFallbackAlert && <DashboardFallbackAlert isConnectionError={isConnectionError} />}
    <DashboardPrimaryTile
      activeView={activeView}
      onViewChange={onViewChange}
      onRefresh={onRefresh}
      loading={loading}
      error={error}
      pipelineStatus={pipelineStatus}
      onStart={onStart}
      backendStatus={backendStatus}
      backendVersion={backendVersion}
    />
    <DashboardSecondaryTiles
      loading={loading}
      error={error}
      pipelineStatus={pipelineStatus}
      isLiveMode={isLiveMode}
      isOnline={isOnline}
      realtimeEvents={realtimeEvents}
      onStart={onStart}
      onPause={onPause}
      onStop={onStop}
      onCreateCharacter={onCreateCharacter}
    />
  </div>
);

const DashboardContent: React.FC<{
  isGuest: boolean;
  workspaceId?: string;
  showEmptyState: boolean;
  onCreateCharacter: () => void;
  showFallbackAlert: boolean;
  isConnectionError: boolean;
  activeView: DashboardView;
  onViewChange: (_event: React.SyntheticEvent, view: DashboardView) => void;
  onRefresh: () => void;
  loading: boolean;
  error: boolean;
  pipelineStatus: PipelineState;
  isLiveMode: boolean;
  isOnline: boolean;
  onStart: () => void;
  onPause: () => void;
  onStop: () => void;
  realtimeEvents: RealtimeEvent[];
  backendStatus?: 'online' | 'offline' | 'error';
  backendVersion?: string;
}> = ({
  isGuest,
  workspaceId,
  showEmptyState,
  onCreateCharacter,
  showFallbackAlert,
  isConnectionError,
  activeView,
  onViewChange,
  onRefresh,
  loading,
  error,
  pipelineStatus,
  isLiveMode,
  isOnline,
  onStart,
  onPause,
  onStop,
  realtimeEvents,
  backendStatus,
  backendVersion,
}) => (
  <>
    {isGuest && <DashboardGuestBanner workspaceId={workspaceId} />}
    {showEmptyState ? (
      <DashboardEmptyState onCreate={onCreateCharacter} />
    ) : (
      <DashboardGrid
        showFallbackAlert={showFallbackAlert}
        isConnectionError={isConnectionError}
        activeView={activeView}
        onViewChange={onViewChange}
        onRefresh={onRefresh}
        loading={loading}
        error={error}
        pipelineStatus={pipelineStatus}
        isLiveMode={isLiveMode}
        isOnline={isOnline}
        realtimeEvents={realtimeEvents}
        onStart={onStart}
        onPause={onPause}
        onStop={onStop}
        onCreateCharacter={onCreateCharacter}
        backendStatus={backendStatus}
        backendVersion={backendVersion}
      />
    )}
  </>
);

const useCharacterDialog = (showNotification: (message: string) => void) => {
  const [open, setOpen] = useState(false);

  const openDialog = () => setOpen(true);
  const closeDialog = () => setOpen(false);
  const handleCreated = () => {
    closeDialog();
    showNotification('Character created successfully!');
  };

  return { open, openDialog, closeDialog, handleCreated };
};

const DashboardDialogs: React.FC<{
  characterDialogOpen: boolean;
  onCloseCharacterDialog: () => void;
  onCharacterCreated: () => void;
}> = ({ characterDialogOpen, onCloseCharacterDialog, onCharacterCreated }) => (
  <>
    <DecisionPointDialog />
    <CharacterCreationDialog
      open={characterDialogOpen}
      onClose={onCloseCharacterDialog}
      onCharacterCreated={onCharacterCreated}
    />
  </>
);

const DashboardNotifications: React.FC<{
  snackbarOpen: boolean;
  snackbarMessage: string;
  onClose: () => void;
}> = ({ snackbarOpen, snackbarMessage, onClose }) => (
  <Snackbar
    open={snackbarOpen}
    autoHideDuration={4000}
    onClose={onClose}
    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
  >
    <Alert
      onClose={onClose}
      severity="info"
      variant="filled"
      sx={{
        borderRadius: 2,
        backgroundColor: 'var(--color-bg-elevated)',
        color: 'var(--color-text-primary)',
        border: '1px solid var(--color-primary)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {snackbarMessage}
    </Alert>
  </Snackbar>
);

type DashboardLayoutProps = {
  isLoadingChars: boolean;
  loading: boolean;
  pipelineStatus: PipelineState;
  isLiveMode: boolean;
  isOnline: boolean;
  lastUpdate: Date;
  isGuest: boolean;
  workspaceId?: string;
  showEmptyState: boolean;
  onCreateCharacter: () => void;
  showFallbackAlert: boolean;
  isConnectionError: boolean;
  activeView: DashboardView;
  onViewChange: (_event: React.SyntheticEvent, view: DashboardView) => void;
  onRefresh: () => void;
  error: boolean;
  realtimeEvents: RealtimeEvent[];
  onStart: () => void;
  onPause: () => void;
  onStop: () => void;
  backendStatus?: 'online' | 'offline' | 'error';
  backendVersion?: string;
  characterDialogOpen: boolean;
  onCloseCharacterDialog: () => void;
  onCharacterCreated: () => void;
  snackbarOpen: boolean;
  snackbarMessage: string;
  onCloseSnackbar: () => void;
};

type DashboardSkeletonProps = Pick<
  DashboardLayoutProps,
  'pipelineStatus' | 'isOnline' | 'isLiveMode' | 'lastUpdate'
>;

const DashboardSkeleton: React.FC<DashboardSkeletonProps> = ({
  pipelineStatus,
  isOnline,
  isLiveMode,
  lastUpdate,
}) => (
  <>
    <CommandTopBar
      pipelineStatus={pipelineStatus}
      isOnline={isOnline}
      isLive={isLiveMode}
      lastUpdate={lastUpdate}
    />
    <SkeletonDashboard />
  </>
);

type DashboardMainProps = Omit<DashboardLayoutProps, 'isLoadingChars' | 'loading'>;

const DashboardMain: React.FC<DashboardMainProps> = ({
  pipelineStatus,
  isLiveMode,
  isOnline,
  lastUpdate,
  isGuest,
  workspaceId,
  showEmptyState,
  onCreateCharacter,
  showFallbackAlert,
  isConnectionError,
  activeView,
  onViewChange,
  onRefresh,
  error,
  realtimeEvents,
  onStart,
  onPause,
  onStop,
  backendStatus,
  backendVersion,
  characterDialogOpen,
  onCloseCharacterDialog,
  onCharacterCreated,
  snackbarOpen,
  snackbarMessage,
  onCloseSnackbar,
}) => (
  <>
    <CommandTopBar
      pipelineStatus={pipelineStatus}
      isOnline={isOnline}
      isLive={isLiveMode}
      lastUpdate={lastUpdate}
    />
    <DashboardContent
      isGuest={isGuest}
      workspaceId={workspaceId}
      showEmptyState={showEmptyState}
      onCreateCharacter={onCreateCharacter}
      showFallbackAlert={showFallbackAlert}
      isConnectionError={isConnectionError}
      activeView={activeView}
      onViewChange={onViewChange}
      onRefresh={onRefresh}
      loading={false}
      error={error}
      pipelineStatus={pipelineStatus}
      isLiveMode={isLiveMode}
      isOnline={isOnline}
      realtimeEvents={realtimeEvents}
      onStart={onStart}
      onPause={onPause}
      onStop={onStop}
      backendStatus={backendStatus}
      backendVersion={backendVersion}
    />
    <DashboardDialogs
      characterDialogOpen={characterDialogOpen}
      onCloseCharacterDialog={onCloseCharacterDialog}
      onCharacterCreated={onCharacterCreated}
    />
    <DashboardNotifications
      snackbarOpen={snackbarOpen}
      snackbarMessage={snackbarMessage}
      onClose={onCloseSnackbar}
    />
  </>
);

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  isLoadingChars,
  loading,
  ...rest
}) =>
  isLoadingChars || loading ? (
    <DashboardSkeleton
      pipelineStatus={rest.pipelineStatus}
      isOnline={rest.isOnline}
      isLiveMode={rest.isLiveMode}
      lastUpdate={rest.lastUpdate}
    />
  ) : (
    <DashboardMain {...rest} />
  );

const Dashboard: React.FC<DashboardProps> = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { isGuest, workspaceId } = useAuthContext();
  const { snackbarOpen, snackbarMessage, showNotification, handleSnackbarClose } = useSnackbar();
  const { lastUpdate, refreshNow } = useAutoRefreshTimestamp();
  const characterDialog = useCharacterDialog(showNotification);
  const { backendStatus, backendVersion } = useBackendStatus();

  const [loading, setLoading] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineState>('idle');
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [activeView, setActiveView] = useState<DashboardView>('world');

  const {
    characters,
    isLoading: isLoadingChars,
    effectiveCharacters,
    shouldShowFallbackAlert,
    error: charactersError,
  } = useDashboardCharacters();

  const onlineStatus = useOnlineStatus(showNotification);
  useLivePolling(isLiveMode, dispatch);
  const realtimeEvents = useDecisionEvents(onlineStatus, showNotification);

  useEffect(() => {
    if (!onlineStatus) {
      setIsLiveMode(false);
    }
  }, [onlineStatus]);

  const { handleStartOrchestration, handlePauseOrchestration, handleStopOrchestration, handleRefresh } =
    usePipelineActions({
      effectiveCharacters,
      setPipelineStatus,
      setIsLiveMode,
      setActiveView,
      showNotification,
      refreshTimestamp: refreshNow,
      dispatch,
      setLoading,
    });

  const showEmptyState = !isLoadingChars && (!characters || characters.length === 0);

  return (
    <DashboardLayout
      isLoadingChars={isLoadingChars}
      loading={loading}
      pipelineStatus={pipelineStatus}
      isLiveMode={isLiveMode}
      isOnline={onlineStatus}
      lastUpdate={lastUpdate}
      isGuest={isGuest}
      workspaceId={workspaceId}
      showEmptyState={showEmptyState}
      onCreateCharacter={characterDialog.openDialog}
      showFallbackAlert={shouldShowFallbackAlert}
      isConnectionError={isConnectionError(charactersError)}
      activeView={activeView}
      onViewChange={(_event, view) => setActiveView(view)}
      onRefresh={handleRefresh}
      error={Boolean(charactersError)}
      realtimeEvents={realtimeEvents}
      onStart={handleStartOrchestration}
      onPause={handlePauseOrchestration}
      onStop={handleStopOrchestration}
      backendStatus={backendStatus}
      backendVersion={backendVersion}
      characterDialogOpen={characterDialog.open}
      onCloseCharacterDialog={characterDialog.closeDialog}
      onCharacterCreated={characterDialog.handleCreated}
      snackbarOpen={snackbarOpen}
      snackbarMessage={snackbarMessage}
      onCloseSnackbar={handleSnackbarClose}
    />
  );
};

export default Dashboard;
