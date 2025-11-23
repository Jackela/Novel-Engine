import React, { Suspense } from 'react';
import { Box, Stack, CircularProgress } from '@mui/material';
import TurnPipelineStatus from '../TurnPipelineStatus';
import RealTimeActivity from '../RealTimeActivity';

interface EnginePanelProps {
  loading: boolean;
  error: boolean;
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  isLive: boolean;
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

const EnginePanel: React.FC<EnginePanelProps> = React.memo(({ 
  loading, 
  error, 
  pipelineStatus, 
  isLive, 
  onClose 
}) => {
  return (
    <Stack spacing={3} sx={{ height: '100%', minWidth: 300 }}>
      {/* Pipeline Status */}
      <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
        <div className="command-panel-header">
          <span className="command-panel-title">Simulation Pipeline</span>
          {onClose && (
            <button 
              onClick={onClose} 
              style={{ background: 'none', border: 'none', color: 'var(--color-text-dim)', cursor: 'pointer' }}
            >
              ×
            </button>
          )}
        </div>
        <LazyWrapper>
          <TurnPipelineStatus loading={loading} error={error} status={pipelineStatus} isLive={isLive} />
        </LazyWrapper>
      </Box>

      {/* Real-time Activity */}
      <Box className="command-panel" sx={{ flex: 1, minHeight: 300 }}>
        <div className="command-panel-header">
          <span className="command-panel-title">Activity Stream</span>
        </div>
        <LazyWrapper>
          <RealTimeActivity loading={loading} error={error} density="condensed" />
        </LazyWrapper>
      </Box>
    </Stack>
  );
});

EnginePanel.displayName = 'EnginePanel';

export default EnginePanel;

