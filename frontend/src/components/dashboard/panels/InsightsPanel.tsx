import React, { lazy, Suspense } from 'react';
import { Box, Stack, CircularProgress } from '@mui/material';
import QuickActions, { type QuickAction } from '../QuickActions';
import AnalyticsDashboard from '../AnalyticsDashboard';
import CharacterNetworks from '../CharacterNetworks';
import NarrativeTimeline from '../NarrativeTimeline';
import EventCascadeFlow from '../EventCascadeFlow';
import PerformanceMetrics from '../PerformanceMetrics';

// These lazy imports were in Dashboard.tsx, keeping them here
// const AnalyticsDashboard = lazy(() => import('../AnalyticsDashboard'));
// const CharacterNetworks = lazy(() => import('../CharacterNetworks'));
// const EventCascadeFlow = lazy(() => import('../EventCascadeFlow'));
// const NarrativeTimeline = lazy(() => import('../NarrativeTimeline'));

interface InsightsPanelProps {
  loading: boolean;
  error: boolean;
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  isLive: boolean;
  isOnline: boolean;
  mfdMode: 'analytics' | 'network' | 'timeline' | 'signals';
  onMfdModeChange: (mode: 'analytics' | 'network' | 'timeline' | 'signals') => void;
  onQuickAction: (action: QuickAction) => void;
  onClose?: () => void;
}

const LazyWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense
    fallback={
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
        <CircularProgress size={24} sx={{ color: 'var(--color-accent-primary)' }} />
      </Box>
    }
  >
    {children}
  </Suspense>
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
  onClose
}) => {
  return (
    <Stack spacing={3} sx={{ height: '100%', minWidth: 300 }}>
      {/* Quick Actions (Control) - Always Visible */}
      <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
        <div className="command-panel-header">
          <span className="command-panel-title">Manual Override</span>
          {onClose && (
            <button 
              onClick={onClose} 
              style={{ background: 'none', border: 'none', color: 'var(--color-text-dim)', cursor: 'pointer' }}
            >
              ×
            </button>
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

      {/* Performance Metrics - Added */}
      <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
        <LazyWrapper>
          <PerformanceMetrics loading={loading} error={error} />
        </LazyWrapper>
      </Box>

      {/* Multifunction Display (MFD) */}
      <Box className="command-panel" sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="command-panel-header" style={{ justifyContent: 'flex-start', gap: '1rem' }}>
          <span className="command-panel-title" style={{ marginRight: 'auto' }}>MFD // {mfdMode.toUpperCase()}</span>
          
          {/* MFD Selector */}
          <Stack direction="row" spacing={1}>
            {[
              { id: 'analytics', label: 'DATA' },
              { id: 'network', label: 'NET' },
              { id: 'timeline', label: 'TIME' },
              { id: 'signals', label: 'SIG' }
            ].map((mode) => (
              <button
                key={mode.id}
                onClick={() => onMfdModeChange(mode.id as any)}
                style={{
                  background: mfdMode === mode.id ? 'var(--color-accent-primary)' : 'transparent',
                  color: mfdMode === mode.id ? '#000' : 'var(--color-text-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  fontSize: '10px',
                  fontFamily: 'var(--font-header)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {mode.label}
              </button>
            ))}
          </Stack>
        </div>
        
        <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden', p: 0 }}>
          <LazyWrapper>
            {mfdMode === 'analytics' && <AnalyticsDashboard loading={loading} error={error} />}
            {mfdMode === 'network' && <CharacterNetworks loading={loading} error={error} />}
            {mfdMode === 'timeline' && <NarrativeTimeline loading={loading} error={error} />}
            {mfdMode === 'signals' && <EventCascadeFlow loading={loading} error={error} />}
          </LazyWrapper>
        </Box>
      </Box>
    </Stack>
  );
});

InsightsPanel.displayName = 'InsightsPanel';

export default InsightsPanel;

