import React from 'react';
import { Box, Typography, Button, useTheme, Paper } from '@mui/material';
import { motion } from 'framer-motion';
import RefreshIcon from '@mui/icons-material/Refresh';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  isConnectionError?: boolean;
}

const ErrorIcon: React.FC<{ isConnectionError: boolean }> = ({ isConnectionError }) => (
  <Box
    component={motion.div}
    animate={{ 
      rotate: [0, -5, 5, -5, 5, 0],
      opacity: [1, 0.8, 1] 
    }}
    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    sx={{ mb: 3, color: 'error.main' }}
  >
    {isConnectionError ? <CloudOffIcon sx={{ fontSize: 80 }} /> : <ReportProblemIcon sx={{ fontSize: 80 }} />}
  </Box>
);

const Troubleshooting: React.FC = () => {
  const theme = useTheme();
  return (
    <Box
      sx={{
        mt: 2,
        p: 2,
        bgcolor: theme.palette.background.default,
        borderRadius: 2,
        textAlign: 'left',
        border: `1px solid ${theme.palette.divider}`
      }}
    >
      <Typography
        variant="caption"
        display="block"
        sx={{ fontWeight: 'bold', mb: 1, color: 'text.primary', letterSpacing: '0.12em' }}
      >
        Troubleshooting
      </Typography>
      <Typography variant="caption" display="block">• Ensure the backend server is running (Port 8000)</Typography>
      <Typography variant="caption" display="block">• Check your local network connection</Typography>
      <Typography variant="caption" display="block">• Verify API endpoint settings in .env</Typography>
    </Box>
  );
};

const RetryButton: React.FC<{ onRetry: () => void }> = ({ onRetry }) => (
  <Button
    variant="contained"
    color="error"
    size="large"
    startIcon={<RefreshIcon />}
    onClick={onRetry}
    sx={{
      px: 6,
      py: 1.5,
      borderRadius: 2,
      fontWeight: 600,
      boxShadow: 'none',
    }}
  >
    Reconnect System
  </Button>
);

const ErrorState: React.FC<ErrorStateProps> = ({
  title = "System Anomaly Detected",
  message = "An unexpected error occurred during data retrieval.",
  onRetry,
  isConnectionError = false,
}) => {
  const theme = useTheme();

  return (
    <Box
      component={motion.div}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: '400px',
        p: 4,
        textAlign: 'center',
      }}
    >
      <Paper
        elevation={0}
        sx={{
          p: 6,
          maxWidth: 600,
          borderRadius: 4,
          background: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <ErrorIcon isConnectionError={isConnectionError} />

        <Typography variant="h4" color="error.main" gutterBottom sx={{ fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
          {title}
        </Typography>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 4, fontSize: '1.1rem' }}>
          {message}
          {isConnectionError && <Troubleshooting />}
        </Typography>

        {onRetry && <RetryButton onRetry={onRetry} />}
      </Paper>
    </Box>
  );
};

export default ErrorState;
