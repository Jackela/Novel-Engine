/**
 * Dashboard Component
 *
 * Main dashboard view with three-region layout:
 * - Sidebar: Engine controls (Pipeline status + Activity stream)
 * - Main: World State Map (primary focus)
 * - Aside: Insights (Quick actions + MFD analytics)
 *
 * Refactored for:
 * - Better visual hierarchy
 * - Cleaner code structure
 * - Proper spacing and layout
 * - Accessibility compliance
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { Alert, Snackbar } from '@mui/material';
import CommandLayout from '../layout/CommandLayout';
import CommandTopBar from '../layout/CommandTopBar';
import DashboardLayout from './DashboardLayout';
import { logger } from '../../services/logging/LoggerFactory';
import { dashboardAPI } from '../../services/api/dashboardAPI';
import { type QuickAction } from './QuickActions';
import { DecisionPointDialog } from '../decision';
import CharacterCreationDialog from '../CharacterStudio/CharacterCreationDialog';
import { useRealtimeEvents, type RealtimeEvent } from '../../hooks/useRealtimeEvents';
import { setDecisionPoint, clearDecisionPoint, type DecisionPoint } from '../../store/slices/decisionSlice';
import type { AppDispatch } from '../../store/store';

// Import panels
import EnginePanel from './panels/EnginePanel';
import WorldPanel from './panels/WorldPanel';
import InsightsPanel from './panels/InsightsPanel';

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';

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

  // Layout state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [asideOpen, setAsideOpen] = useState(true);
  const [mfdMode, setMfdMode] = useState<'analytics' | 'network' | 'timeline' | 'signals'>('analytics');
  const [isMapExpanded, setIsMapExpanded] = useState(false);

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
          icon: opt.icon as string | undefined,
          impactPreview: opt.impact_preview as string | undefined,
          isDefault: opt.is_default as boolean | undefined,
        })),
        defaultOptionId: data.default_option_id as number | undefined,
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
  useRealtimeEvents({
    enabled: isOnline,
    onDecisionEvent: handleDecisionEvent,
  });

  // Auto-refresh timer
  useEffect(() => {
    const interval = setInterval(() => setLastUpdate(new Date()), 10000);
    return () => clearInterval(interval);
  }, []);

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

  const handleQuickAction = useCallback(async (action: QuickAction) => {
    logger.info('Quick action triggered:', { action });

    try {
      switch (action) {
        case 'play': {
          setLoading(true);
          const response = await dashboardAPI.startOrchestration();
          if (response.data.success) {
            const status = response.data.data?.status || 'running';
            setPipelineStatus(status as PipelineState);
            setIsLiveMode(status === 'running');
            showNotification('Orchestration started');
          } else {
            showNotification('Failed to start orchestration');
          }
          break;
        }
        case 'pause': {
          setPipelineStatus('paused');
          setIsLiveMode(false);
          showNotification('System paused');
          break;
        }
        case 'stop': {
          setLoading(true);
          const response = await dashboardAPI.stopOrchestration();
          if (response.data.success) {
            const status = response.data.data?.status || 'stopped';
            setPipelineStatus(status as PipelineState);
            setIsLiveMode(false);
            showNotification('Orchestration stopped');
          } else {
            showNotification('Failed to stop orchestration');
          }
          break;
        }
        case 'refresh': {
          setLoading(true);
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
          break;
        }
        case 'createCharacter': {
          setCharacterDialogOpen(true);
          break;
        }
        default:
          showNotification(`Action ${action} triggered`);
      }
    } catch (err) {
      logger.error('Quick action failed:', err as Error);
      showNotification(`Action ${action} failed: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSnackbarClose = () => setSnackbarOpen(false);

  return (
    <CommandLayout>
      {/* Top Status Bar */}
      <CommandTopBar
        pipelineStatus={pipelineStatus}
        isOnline={isOnline}
        isLive={isLiveMode}
        lastUpdate={lastUpdate}
      />

      {/* Three-Region Dashboard Layout */}
      <DashboardLayout
        sidebarOpen={sidebarOpen}
        asideOpen={asideOpen}
        onSidebarToggle={setSidebarOpen}
        onAsideToggle={setAsideOpen}
        sidebar={
          <EnginePanel
            loading={loading}
            error={!!error}
            pipelineStatus={pipelineStatus}
            isLive={isLiveMode}
          />
        }
        main={
          <WorldPanel
            loading={loading}
            error={!!error}
            onExpand={() => setIsMapExpanded(true)}
          />
        }
        aside={
          <InsightsPanel
            loading={loading}
            error={!!error}
            pipelineStatus={pipelineStatus}
            isLive={isLiveMode}
            isOnline={isOnline}
            mfdMode={mfdMode}
            onMfdModeChange={setMfdMode}
            onQuickAction={handleQuickAction}
            lastUpdate={lastUpdate}
          />
        }
      />

      {/* Map Fullscreen Overlay */}
      {isMapExpanded && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 2000,
            background: 'var(--color-bg-base, #0a0a0b)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-header)',
                fontSize: '24px',
                color: 'var(--color-accent-primary, #6366f1)',
              }}
            >
              WORLD STATE // INSPECT MODE
            </span>
            <button
              onClick={() => setIsMapExpanded(false)}
              style={{
                background: 'transparent',
                border: '1px solid var(--color-border, #2a2a30)',
                color: 'var(--color-text-primary, #f0f0f2)',
                padding: '8px 16px',
                cursor: 'pointer',
                fontFamily: 'var(--font-header)',
                borderRadius: '4px',
              }}
            >
              CLOSE [ESC]
            </button>
          </div>

          <div
            style={{
              flex: 1,
              border: '1px solid var(--color-border, #2a2a30)',
              borderRadius: '8px',
              overflow: 'hidden',
            }}
          >
            <WorldPanel loading={loading} error={!!error} />
          </div>
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
          sx={{ borderRadius: 2 }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </CommandLayout>
  );
};

export default Dashboard;
