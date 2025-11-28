import React from 'react';
import { Box, Button, styled } from '@mui/material';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';
import WorldStateMap from '../WorldStateMapV2';
import { ErrorBoundary } from '../../error-boundaries/ErrorBoundary';
import PanelErrorFallback from '../PanelErrorFallback';

interface WorldPanelProps {
  loading: boolean;
  error: boolean;
  onExpand?: () => void;
}

const ExpandButton = styled(Button)(({ theme }) => ({
  position: 'absolute',
  top: theme.spacing(1),
  right: theme.spacing(6), // Leave space for GridTile options button
  zIndex: 10,
  minWidth: 'auto',
  padding: theme.spacing(0.5, 1),
  fontSize: '10px',
  fontFamily: 'var(--font-header)',
  textTransform: 'uppercase',
  backgroundColor: 'color-mix(in srgb, var(--color-accent-primary) 10%, transparent)',
  borderColor: 'var(--color-accent-primary)',
  color: 'var(--color-accent-primary)',
  '&:hover': {
    backgroundColor: 'color-mix(in srgb, var(--color-accent-primary) 20%, transparent)',
    borderColor: 'var(--color-accent-primary)',
  },
  '&:focus-visible': {
    outline: '2px solid var(--color-accent-primary)',
    outlineOffset: '2px',
  },
}));

const WorldPanel: React.FC<WorldPanelProps> = React.memo(({ loading, error, onExpand }) => {
  return (
    <ErrorBoundary
      componentName="WorldPanel"
      fallback={(err, reset) => (
        <PanelErrorFallback error={err} onReset={reset} panelName="World State" />
      )}
    >
      <Box
        className="command-panel"
        sx={{
          height: '100%',
          p: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}
      >
        {/* Expand button overlay - positioned in top right */}
        {onExpand && (
          <ExpandButton
            variant="outlined"
            size="small"
            onClick={onExpand}
            aria-label="Expand world map"
            startIcon={<OpenInFullIcon sx={{ fontSize: '12px !important' }} />}
          >
            Expand
          </ExpandButton>
        )}

        {/* Map takes full height of center column */}
        <WorldStateMap loading={loading} error={error} />
      </Box>
    </ErrorBoundary>
  );
});

export default WorldPanel;
