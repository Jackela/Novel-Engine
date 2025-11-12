import React from 'react';
import { Box, CircularProgress, Alert } from '@mui/material';

interface AsyncStatesProps {
  isLoading?: boolean;
  error?: unknown;
  children: React.ReactNode;
  height?: number | string;
}

export default function AsyncStates({ isLoading, error, children, height = '200px' }: AsyncStatesProps) {
  if (isLoading) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" minHeight={height}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    const message = error instanceof Error ? error.message : 'Error loading data';
    return (
      <Box p={2}>
        <Alert severity="error">{message}</Alert>
      </Box>
    );
  }

  return <>{children}</>;
}

