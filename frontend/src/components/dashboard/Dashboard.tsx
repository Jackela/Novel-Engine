/**
 * Dashboard Component
 *
 * Premium Command Center for the Novel Engine.
 * Features a simplified, glassmorphic UI with focused "World State" visualization.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { Alert, Snackbar, Box, Button, IconButton, Tabs, Tab, Stack } from '@mui/material';
import CommandLayout from '../layout/CommandLayout';
import CommandTopBar from '../layout/CommandTopBar';
import GridTile from '../layout/GridTile';
import { logger } from '@/services/logging/LoggerFactory';
import { dashboardAPI } from '@/services/api/dashboardAPI';
import { DecisionPointDialog } from '../decision';
import CharacterCreationDialog from '../features/characters/CharacterCreationDialog';
import { useRealtimeEvents, type RealtimeEvent } from '@/hooks/useRealtimeEvents';
import { setDecisionPoint, clearDecisionPoint, type DecisionPoint } from '@/store/slices/decisionSlice';
import { fetchDashboardData } from '@/store/slices/dashboardSlice';
import type { AppDispatch } from '@/store/store';
import { useCharactersQuery } from '@/services/queries';
import EmptyState from '../common/EmptyState';

// Import panels
import WorldPanel from './panels/WorldPanel';
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
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon,
  AccountTree as FlowIcon,
  PersonAdd as PersonAddIcon,
} from '@mui/icons-material';

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';
type DashboardView = 'world' | 'network' | 'timeline' | 'analytics' | 'signals';

interface DashboardProps {
  userId?: string;
  campaignId?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ userId: _userId, campaignId: _campaignId }) => {
  const dispatch = useDispatch<AppDispatch>();

  // Core state
  const [loading, setLoading] = useState(false);
  const [error, _setError] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineState>('idle');
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [activeView, setActiveView] = useState<DashboardView>('world');

  // Character creation dialog state
  const [characterDialogOpen, setCharacterDialogOpen] = useState(false);

  // Connection state
  const [isOnline, setIsOnline] = useState(() => {
    if (typeof navigator === 'undefined') return true;
    return navigator.onLine;
  });

  // Notification state
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  // Data Query
  const { data: characters, isLoading: isLoadingChars } = useCharactersQuery();



  // Handle decision events from SSE
  const handleDecisionEvent = useCallback((event: RealtimeEvent) => {
    logger.info('Decision event received in Dashboard:', { type: event.type, id: event.id });



    if (event.type === 'decision_required' && event.data) {
      // Transform SSE event data to DecisionPoint format
      const data = event.data as Record<string, unknown>;
      const decisionPoint: DecisionPoint = {
        decisionId: data.decision_id as string,
        decisionType: data.decision_type as DecisionPoint['decisionType'],
        turnNumber: data.turn_number as number,
        title: data.title as string,
        description: data.description as string,
        narrativeContext: data.narrative_context as string || '',
        options: ((data.options as Array<Record<string, unknown>>) || []).map((opt) => ({
          optionId: opt.option_id as number,
          label: opt.label as string,
          description: opt.description as string,
          ...(opt.icon ? { icon: opt.icon as string } : {}),
          ...(opt.impact_preview ? { impactPreview: opt.impact_preview as string } : {}),
          ...(opt.is_default !== undefined ? { isDefault: opt.is_default as boolean } : {}),
        })),
        ...(data.default_option_id !== undefined ? { defaultOptionId: data.default_option_id as number } : {}),
        timeoutSeconds: data.timeout_seconds as number || 120,
        dramaticTension: data.dramatic_tension as number || 7,
        emotionalIntensity: data.emotional_intensity as number || 7,
        createdAt: data.created_at as string,
        expiresAt: data.expires_at as string,
      };
      dispatch(setDecisionPoint(decisionPoint));
      showNotification('Decision point reached - your input is needed!');
    } else if (event.type === 'decision_accepted' || event.type === 'decision_finalized') {
      dispatch(clearDecisionPoint());
    }
  }, [dispatch]);

  // Subscribe to SSE events with decision handler
  const { events: realtimeEvents } = useRealtimeEvents({
    enabled: isOnline,
    onDecisionEvent: handleDecisionEvent,
  });

  // Auto-refresh timer for local update timestamp
  useEffect(() => {
    const interval = setInterval(() => setLastUpdate(new Date()), 10000);
    return () => clearInterval(interval);
  }, []);

  // Polling for pipeline status when live
  useEffect(() => {
    let pollingInterval: NodeJS.Timeout;

    if (isLiveMode) {
      pollingInterval = setInterval(() => {
        dispatch(fetchDashboardData());
      }, 3000); // Poll every 3 seconds
    }

    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [isLiveMode, dispatch]);

  // Online/offline detection
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      setIsOnline(true);
      showNotification('Connection restored.');
    };

    const handleOffline = () => {
      setIsOnline(false);
      setIsLiveMode(false);
      showNotification('Connection lost.');
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

  const handleStartOrchestration = async () => {
    setLoading(true);
    try {
      const characterNames = characters || [];
      if (characterNames.length === 0) {
        showNotification('No characters available to start simulation');
        setLoading(false);
        return;
      }

      const response = await dashboardAPI.startOrchestration({
        character_names: characterNames,
        total_turns: 3
      });

      if (response.data.success) {
        const status = response.data.data?.status || 'running';
        setPipelineStatus(status as PipelineState);
        setIsLiveMode(status === 'running');
        dispatch(fetchDashboardData());
        showNotification(`Orchestration started with ${characterNames.length} characters`);
      } else {
        showNotification('Failed to start orchestration');
      }
    } catch (err) {
      showNotification(`Failed to start: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePauseOrchestration = async () => {
    setLoading(true);
    try {
      const response = await dashboardAPI.pauseOrchestration();
      if (response.data.success) {
        setPipelineStatus('paused');
        setIsLiveMode(false);
        dispatch(fetchDashboardData());
        showNotification('Orchestration paused');
      }
    } catch (err) {
      showNotification(`Failed to pause: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopOrchestration = async () => {
    setLoading(true);
    try {
      const response = await dashboardAPI.stopOrchestration();
      if (response.data.success) {
        setPipelineStatus('stopped');
        setIsLiveMode(false);
        dispatch(fetchDashboardData());
        showNotification('Orchestration stopped');
      }
    } catch (err) {
      showNotification(`Failed to stop: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const [_statusRes, orchestrationRes] = await Promise.all([
        dashboardAPI.getSystemStatus(),
        dashboardAPI.getOrchestrationStatus(),
      ]);
      if (orchestrationRes.data.success && orchestrationRes.data.data) {
        setPipelineStatus(orchestrationRes.data.data.status as PipelineState);
        setIsLiveMode(orchestrationRes.data.data.status === 'running');
      }
      setLastUpdate(new Date());
      showNotification('Data refreshed');
    } catch (err) {
      showNotification('Failed to refresh data');
    } finally {
      setLoading(false);
    }
  };

  const handleSnackbarClose = () => setSnackbarOpen(false);

  const handleViewChange = (_event: React.SyntheticEvent, newValue: DashboardView) => {
    setActiveView(newValue);
  };

  return (
    <>
      {/* Top Status Bar */}
      <CommandTopBar
        pipelineStatus={pipelineStatus}
        isOnline={isOnline}
        isLive={isLiveMode}
        lastUpdate={lastUpdate}
      />

      {/* Main Content Area */}
      {!isLoadingChars && (!characters || characters.length === 0) ? (
        <Box sx={{ height: 'calc(100vh - 120px)', p: 4, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <EmptyState
            title="System Standby: No Operatives Detected"
            description="The command deck requires at least one active operative to initialize the world simulation. Create a character to bring the system online."
            actionLabel="Initialize Operative"
            onAction={() => setCharacterDialogOpen(true)}
            icon={<PersonAddIcon />}
          />
        </Box>
      ) : (
        <div className="bento-grid" data-testid="bento-grid" style={{ height: 'calc(100vh - 100px)', overflow: 'hidden' }}>

          {/* LEFT COLUMN: Main World State Visualization (Span 5) */}
          <GridTile
            title="World State Visualization"
            position={{
              desktop: { column: 'span 5', row: 'span 2', height: '620px' },
              tablet: { column: 'span 8', height: '500px' },
              mobile: { column: 'span 1', height: '400px' }
            }}
            headerAction={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Tabs
                  value={activeView}
                  onChange={handleViewChange}
                  textColor="primary"
                  indicatorColor="primary"
                  sx={{ minHeight: '36px' }}
                >
                  <Tab icon={<MapIcon fontSize="small" />} iconPosition="start" label="Map" value="world" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
                  <Tab icon={<HubIcon fontSize="small" />} iconPosition="start" label="Network" value="network" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
                  <Tab icon={<TimelineIcon fontSize="small" />} iconPosition="start" label="Timeline" value="timeline" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
                  <Tab icon={<AnalyticsIcon fontSize="small" />} iconPosition="start" label="Analytics" value="analytics" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
                  <Tab icon={<FlowIcon fontSize="small" />} iconPosition="start" label="Signals" value="signals" sx={{ minHeight: '36px', textTransform: 'none', fontWeight: 600 }} />
                </Tabs>
                <IconButton onClick={handleRefresh} size="small" sx={{
                  transition: 'all 0.2s',
                  '&:hover': { transform: 'rotate(180deg)', color: 'var(--color-primary)' }
                }}
                  data-testid="quick-action-refresh"
                  aria-label="Refresh data"
                >
                  <RefreshIcon htmlColor="var(--color-text-secondary)" />
                </IconButton>
              </Box>
            }
          >
            {activeView === 'world' && <WorldPanel loading={loading} error={!!error} />}
            {activeView === 'network' && <CharacterNetworks loading={loading} error={!!error} />}
            {activeView === 'timeline' && <NarrativeTimeline loading={loading} error={!!error} />}
            {activeView === 'analytics' && <AnalyticsDashboard loading={loading} error={!!error} />}
            {activeView === 'signals' && <EventCascadeFlow loading={loading} error={!!error} />}
          </GridTile>

          {/* CENTER COLUMN: Pipeline & Metrics (Span 3) */}
          <GridTile
            title="Pipeline Status"
            position={{
              desktop: { column: 'span 3', height: '300px' },
              tablet: { column: 'span 4', height: '300px' },
              mobile: { column: 'span 1', height: 'auto' }
            }}
          >
            <TurnPipelineStatus
              loading={loading}
              error={!!error}
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
              mobile: { column: 'span 1', height: 'auto' }
            }}
          >
            <PerformanceMetrics />
          </GridTile>

          {/* RIGHT COLUMN: Log & Command (Span 4) */}
          <GridTile
            title="System Log"
            position={{
              desktop: { column: 'span 4', height: '400px' },
              tablet: { column: 'span 8', height: '250px' },
              mobile: { column: 'span 1', height: '200px' }
            }}
          >
            <Box sx={{
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
              {realtimeEvents.map((event, i) => (
                <Box key={i} sx={{
                  mb: 0.5,
                  borderBottom: '1px solid var(--color-border-primary)',
                  pb: 0.5,
                  '&:last-child': { borderBottom: 'none' }
                }}
                  data-testid="activity-event"
                >
                  <span style={{ color: 'var(--color-primary)' }}>[{new Date(event.timestamp).toLocaleTimeString()}]</span>
                  <span style={{ marginLeft: '8px', color: 'var(--color-text-primary)' }}>{event.description}</span>
                </Box>
              ))}
              {realtimeEvents.length === 0 && (
                <Box sx={{ textAlign: 'center', color: 'var(--color-text-tertiary)', mt: 4 }}>
                  System Ready. Awaiting Input.
                </Box>
              )}
            </Box>
          </GridTile>

          <GridTile
            title="Command Deck"
            position={{
              desktop: { column: 'span 4', height: '200px' },
              tablet: { column: 'span 4', height: '200px' },
              mobile: { column: 'span 1', height: 'auto' }
            }}
          >
            <Stack spacing={2} height="100%" justifyContent="center" data-testid="quick-actions">
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <Button
                  variant="contained"
                  color={isLiveMode ? "warning" : "primary"}
                  startIcon={isLiveMode ? <PauseIcon /> : <PlayIcon />}
                  onClick={isLiveMode ? handlePauseOrchestration : handleStartOrchestration}
                  fullWidth
                  sx={{
                    height: 48,
                    backgroundColor: isLiveMode ? 'var(--color-warning)' : 'var(--color-primary)',
                    color: 'var(--color-bg-primary)',
                    fontWeight: 'bold',
                    '&:hover': { backgroundColor: isLiveMode ? 'var(--color-warning-border)' : 'var(--color-primary-400)' }
                  }}
                  data-testid={isLiveMode ? "quick-action-pause" : "quick-action-play"}
                  aria-label={isLiveMode ? "Pause Orchestration" : "Start Orchestration"}
                >
                  {isLiveMode ? "PAUSE" : "START"}
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<StopIcon />}
                  onClick={handleStopOrchestration}
                  disabled={!isLiveMode}
                  fullWidth
                  sx={{
                    height: 48,
                    borderColor: 'var(--color-error)',
                    color: 'var(--color-error)'
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
                onClick={() => setCharacterDialogOpen(true)}
                fullWidth
                sx={{
                  borderColor: 'var(--color-border-secondary)',
                  color: 'var(--color-text-secondary)',
                  '&:hover': { borderColor: 'var(--color-primary)', color: 'var(--color-primary)' }
                }}
                aria-label="Create New Operative"
              >
                New Operative
              </Button>
            </Stack>
          </GridTile>
        </div>
      )}

      {/* Decision Point Dialog - Modal for user interaction */}
      <DecisionPointDialog />

      {/* Character Creation Dialog */}
      <CharacterCreationDialog
        open={characterDialogOpen}
        onClose={() => setCharacterDialogOpen(false)}
        onCharacterCreated={() => {
          setCharacterDialogOpen(false);
          showNotification('Character created successfully!');
        }}
      />

      {/* Notification Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity="info"
          variant="filled"
          sx={{
            borderRadius: 2,
            backgroundColor: 'var(--color-bg-elevated)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-primary)',
            boxShadow: '0 0 10px var(--color-primary-glow)'
          }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </>
  );
};

export default Dashboard;
