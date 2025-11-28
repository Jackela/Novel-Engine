import React from 'react';
import { Box, Stack, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import TurnPipelineStatus from '../TurnPipelineStatus';
import RealTimeActivity from '../RealTimeActivity';
import SuspenseWrapper from '../../common/SuspenseWrapper';
import { ErrorBoundary } from '../../error-boundaries/ErrorBoundary';
import PanelErrorFallback from '../PanelErrorFallback';

interface EnginePanelProps {
  loading: boolean;
  error: boolean;
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  isLive: boolean;
  onClose?: () => void;
}

const EnginePanel: React.FC<EnginePanelProps> = React.memo(({
  loading,
  error,
  pipelineStatus,
  isLive,
  onClose,
}) => {
  return (
    <ErrorBoundary
      componentName="EnginePanel"
      fallback={(err, reset) => (
        <PanelErrorFallback error={err} onReset={reset} panelName="Engine" />
      )}
    >
      <Stack spacing={3} sx={{ height: '100%', minWidth: 300 }}>
        {/* Pipeline Status */}
        <Box className="command-panel" sx={{ flex: '0 0 auto' }}>
          <div className="command-panel-header">
            <span className="command-panel-title">Simulation Pipeline</span>
            {onClose && (
              <IconButton
                onClick={onClose}
                aria-label="Close engine panel"
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
          <SuspenseWrapper>
            <TurnPipelineStatus
              loading={loading}
              error={error}
              status={pipelineStatus}
              isLive={isLive}
            />
          </SuspenseWrapper>
        </Box>

        {/* Real-time Activity */}
        <Box className="command-panel" sx={{ flex: 1, minHeight: 300 }}>
          <div className="command-panel-header">
            <span className="command-panel-title">Activity Stream</span>
          </div>
          <SuspenseWrapper>
            <RealTimeActivity loading={loading} error={error} density="condensed" />
          </SuspenseWrapper>
        </Box>
      </Stack>
    </ErrorBoundary>
  );
});

export default EnginePanel;
