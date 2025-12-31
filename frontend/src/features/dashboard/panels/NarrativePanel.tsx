import React from 'react';
import { Alert, Box, Button, CircularProgress, Stack, Typography } from '@mui/material';
import { useQuery } from 'react-query';
import { ErrorBoundary } from '@/components/error-boundaries/ErrorBoundary';
import PanelErrorFallback from '../PanelErrorFallback';
import { dashboardAPI } from '@/services/api/dashboardAPI';

interface NarrativePanelProps {
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  onStart?: () => void | Promise<void>;
}

const NarrativePanel: React.FC<NarrativePanelProps> = React.memo(({ pipelineStatus, onStart }) => {
  const narrativeQuery = useQuery(
    ['orchestration', 'narrative'],
    async () => {
      const res = await dashboardAPI.getNarrative();
      return res.data;
    },
    {
      refetchInterval: pipelineStatus === 'running' ? 2000 : false,
      retry: 1,
    }
  );

  return (
    <ErrorBoundary
      componentName="NarrativePanel"
      fallback={(err, reset) => (
        <PanelErrorFallback error={err} onReset={reset} panelName="Narrative Output" />
      )}
    >
      <Box
        className="command-panel"
        sx={{
          height: '100%',
          p: 2,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="caption" sx={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>
              OUTPUT
            </Typography>
            {narrativeQuery.isFetching && (
              <CircularProgress size={14} aria-label="Loading narrative" />
            )}
          </Stack>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              onClick={() => void narrativeQuery.refetch()}
              disabled={narrativeQuery.isFetching}
            >
              Refresh
            </Button>
            {onStart && pipelineStatus !== 'running' && (
              <Button
                size="small"
                variant="contained"
                onClick={() => void onStart()}
                disabled={pipelineStatus === 'paused'}
              >
                Start Run
              </Button>
            )}
          </Stack>
        </Stack>

        {narrativeQuery.isError && (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => void narrativeQuery.refetch()}>
                Retry
              </Button>
            }
          >
            {(narrativeQuery.error as Error | undefined)?.message || 'Failed to load narrative.'}
          </Alert>
        )}

        {!narrativeQuery.isError && narrativeQuery.isLoading && (
          <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        )}

        {!narrativeQuery.isError && !narrativeQuery.isLoading && (
          <>
            {!narrativeQuery.data?.data?.has_content ? (
              <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
                  No narrative output yet. Start a run to generate story content.
                </Typography>
              </Box>
            ) : (
              <Box
                sx={{
                  flex: 1,
                  overflowY: 'auto',
                  p: 2,
                  bgcolor: 'var(--color-bg-tertiary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-primary)',
                }}
              >
                <Typography
                  component="pre"
                  sx={{
                    m: 0,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.85rem',
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {narrativeQuery.data.data.story}
                </Typography>
              </Box>
            )}
          </>
        )}
      </Box>
    </ErrorBoundary>
  );
});

export default NarrativePanel;
