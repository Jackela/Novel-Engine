import React from 'react';
import { Box, Stack, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import QuickActions, { type QuickAction } from '../QuickActions';
import AnalyticsDashboard from '../AnalyticsDashboard';
import CharacterNetworks from '../CharacterNetworks';
import NarrativeTimeline from '../NarrativeTimeline';
import EventCascadeFlow from '../EventCascadeFlow';
import PerformanceMetrics from '../PerformanceMetrics';
import SummaryStrip from '../SummaryStrip';
import MfdModeSelector, { type MfdMode } from '../MfdModeSelector';
import SuspenseWrapper from '@/components/common/SuspenseWrapper';
import { ErrorBoundary } from '@/components/error-boundaries/ErrorBoundary';
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
  lastUpdate?: Date;
}

const CommandPanelHeader: React.FC<{
  title: string;
  onClose?: () => void;
  showClose?: boolean;
}> = ({ title, onClose, showClose }) => (
  <div className="command-panel-header">
    <span className="command-panel-title">{title}</span>
    {showClose && onClose && (
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
);

const QuickActionsPanel: React.FC<{
  loading: boolean;
  error: boolean;
  pipelineStatus: InsightsPanelProps['pipelineStatus'];
  isLive: boolean;
  isOnline: boolean;
  onQuickAction: (action: QuickAction) => void;
  onClose?: () => void;
}> = ({ loading, error, pipelineStatus, isLive, isOnline, onQuickAction, onClose }) => (
  <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
    <CommandPanelHeader title="Manual Override" onClose={onClose} showClose />
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
);

const PerformancePanel: React.FC<{ loading: boolean; error: boolean }> = ({ loading, error }) => (
  <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
    <SuspenseWrapper>
      <PerformanceMetrics loading={loading} error={error} />
    </SuspenseWrapper>
  </Box>
);

const MfdPanel: React.FC<{
  mfdMode: MfdMode;
  onMfdModeChange: (mode: MfdMode) => void;
  loading: boolean;
  error: boolean;
}> = ({ mfdMode, onMfdModeChange, loading, error }) => (
  <Box className="command-panel" sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
    <div className="command-panel-header" style={{ justifyContent: 'flex-start', gap: '1rem' }}>
      <span className="command-panel-title" style={{ marginRight: 'auto' }}>
        MFD // {mfdMode.toUpperCase()}
      </span>

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
);

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
  lastUpdate,
}) => {
  return (
    <ErrorBoundary
      componentName="InsightsPanel"
      fallback={(err, reset) => (
        <PanelErrorFallback error={err} onReset={reset} panelName="Insights" />
      )}
    >
      <Stack spacing={3} sx={{ height: '100%', minWidth: 300 }}>
        {/* Summary Strip - Command Overview */}
        <SummaryStrip
          lastUpdate={lastUpdate || new Date()}
          pipelineStatus={pipelineStatus}
          isLive={isLive}
          isOnline={isOnline}
          embedded
        />

        {/* Quick Actions (Control) - Always Visible */}
        <QuickActionsPanel
          loading={loading}
          error={error}
          pipelineStatus={pipelineStatus}
          isLive={isLive}
          isOnline={isOnline}
          onQuickAction={onQuickAction}
          onClose={onClose}
        />

        {/* Performance Metrics */}
        <PerformancePanel loading={loading} error={error} />

        {/* Multifunction Display (MFD) */}
        <MfdPanel
          mfdMode={mfdMode}
          onMfdModeChange={onMfdModeChange}
          loading={loading}
          error={error}
        />
      </Stack>
    </ErrorBoundary>
  );
});

export default InsightsPanel;
