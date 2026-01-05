import React from 'react';
import { Box, Button, Typography } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

interface PanelErrorFallbackProps {
  error?: Error | null;
  onReset?: () => void;
  panelName?: string;
}

/**
 * PanelErrorFallback Component
 *
 * A compact error fallback for dashboard panels.
 * Displays a user-friendly message with retry option.
 */
const PanelErrorFallback: React.FC<PanelErrorFallbackProps> = ({
  error,
  onReset,
  panelName = 'Panel',
}) => {
  return (
    <Box
      role="alert"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: 200,
        p: 3,
        textAlign: 'center',
        bgcolor: 'var(--color-error-bg)',
        borderRadius: 1,
        border: '1px solid var(--color-error-border)',
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{
          color: 'var(--color-error-text)',
          fontFamily: 'var(--font-header)',
          textTransform: 'uppercase',
          mb: 1,
        }}
      >
        {panelName} Error
      </Typography>
      <Typography
        variant="body2"
        sx={{
          color: 'var(--color-text-secondary)',
          mb: 2,
        }}
      >
        {error?.message || 'Something went wrong'}
      </Typography>
      {onReset && (
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshIcon />}
          onClick={onReset}
          sx={{
            borderColor: 'var(--color-error)',
            color: 'var(--color-error)',
            '&:hover': {
              borderColor: 'var(--color-error-text)',
              bgcolor: 'var(--color-error-bg)',
            },
          }}
        >
          Retry
        </Button>
      )}
    </Box>
  );
};

export default PanelErrorFallback;
