import React from 'react';
import { Box, Button, styled } from '@mui/material';
import { alpha } from '@mui/material';
import { OpenInFull as OpenInFullIcon } from '@mui/icons-material';
import WorldStateMap from '../WorldStateMap';
import { ErrorBoundary } from '@/components/error-boundaries/ErrorBoundary';
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
  fontFamily: 'var(--font-primary)',
  textTransform: 'uppercase',
  backgroundColor: alpha(theme.palette.primary.main, 0.08),
  borderColor: theme.palette.primary.main,
  color: theme.palette.primary.main,
  '&:hover': {
    backgroundColor: alpha(theme.palette.primary.main, 0.14),
    borderColor: theme.palette.primary.main,
  },
  '&:focus-visible': {
    outline: '2px solid var(--color-primary)',
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
