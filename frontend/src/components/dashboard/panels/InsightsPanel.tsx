import React from 'react';
import { Box, Stack, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import QuickActions, { type QuickAction } from '../QuickActions';
import AnalyticsDashboard from '../AnalyticsDashboard';
import CharacterNetworks from '../CharacterNetworks';
import NarrativeTimeline from '../NarrativeTimeline';
import EventCascadeFlow from '../EventCascadeFlow';
import PerformanceMetrics from '../PerformanceMetrics';
import MfdModeSelector, { type MfdMode } from '../MfdModeSelector';
import SuspenseWrapper from '../../common/SuspenseWrapper';
import { ErrorBoundary } from '../../error-boundaries/ErrorBoundary';
import PanelErrorFallback from '../PanelErrorFallback';

interface InsightsPanelProps {
  loading: boolean;
  error: boolean;
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  isLive: boolean;
  isOnline: boolean;
  mfdMode: MfdMode;
  onMfdModeChange: (mode: MfdMode) => void;
  onQuickAction: (action: QuickAction) => void;
  onClose?: () => void;
}

const InsightsPanel: React.FC<InsightsPanelProps> = React.memo(({
  loading,
  error,
  pipelineStatus,
  isLive,
  isOnline,
  mfdMode,
  onMfdModeChange,
  onQuickAction,
  onClose,
}) => {
  return (
    <ErrorBoundary
      componentName="InsightsPanel"
      fallback={(err, reset) => (
        <PanelErrorFallback error={err} onReset={reset} panelName="Insights" />
      )}
    >
      <Stack spacing={3} sx={{ height: '100%', minWidth: 300 }}>
        {/* Quick Actions (Control) - Always Visible */}
        <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
          <div className="command-panel-header">
            <span className="command-panel-title">Manual Override</span>
            {onClose && (
              <IconButton
                onClick={onClose}
                aria-label="Close insights panel"
                size="small"
                sx={{
                  color: 'var(--color-text-dim)',
                  p: 0.5,
                  '&:hover': {
                    color: 'var(--color-text-secondary)',
                    bgcolor: 'var(--color-bg-interactive)',
                  },
                }}
              >
                <CloseIcon sx={{ fontSize: 16 }} />
              </IconButton>
            )}
          </div>
          <QuickActions
            loading={loading}
            error={error}
            status={pipelineStatus}
            isLive={isLive}
            isOnline={isOnline}
            onAction={onQuickAction}
            variant="inline"
            showInlineTitle={false}
            density="compact"
          />
        </Box>

        {/* Performance Metrics */}
        <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
          <SuspenseWrapper>
            <PerformanceMetrics loading={loading} error={error} />
          </SuspenseWrapper>
        </Box>

        {/* Multifunction Display (MFD) */}
        <Box className="command-panel" sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="command-panel-header" style={{ justifyContent: 'flex-start', gap: '1rem' }}>
            <span className="command-panel-title" style={{ marginRight: 'auto' }}>
              MFD // {mfdMode.toUpperCase()}
            </span>

            {/* MFD Selector */}
            <MfdModeSelector
              value={mfdMode}
              onChange={onMfdModeChange}
            />
          </div>

          <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden', p: 0 }}>
            <SuspenseWrapper>
              {mfdMode === 'analytics' && <AnalyticsDashboard loading={loading} error={error} />}
              {mfdMode === 'network' && <CharacterNetworks loading={loading} error={error} />}
              {mfdMode === 'timeline' && <NarrativeTimeline loading={loading} error={error} />}
              {mfdMode === 'signals' && <EventCascadeFlow loading={loading} error={error} />}
            </SuspenseWrapper>
          </Box>
        </Box>
      </Stack>
    </ErrorBoundary>
  );
});

export default InsightsPanel;
