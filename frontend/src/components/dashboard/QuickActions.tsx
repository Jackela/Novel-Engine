import React, { useEffect, useRef } from 'react';
import {
  Box,
  IconButton,
  Tooltip,
  Stack,
  Typography,
  useMediaQuery,
  Fade,
  Chip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Settings as SettingsIcon,
  Fullscreen as FullscreenIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';
import { telemetry } from '../../utils/telemetry';

const ActionButton = styled(motion(IconButton))<{ active?: boolean }>(({ theme, active }) => ({
  border: `1px solid ${active ? theme.palette.primary.main : theme.palette.divider}`,
  backgroundColor: active ? 'rgba(99, 102, 241, 0.1)' : theme.palette.background.paper,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: active ? 'rgba(99, 102, 241, 0.2)' : theme.palette.action.hover,
    borderColor: theme.palette.primary.main,
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(99, 102, 241, 0.2)',
  },
  '&:active': {
    transform: 'translateY(0px)',
  },
  '&.Mui-disabled': {
    opacity: 0.4,
    borderColor: theme.palette.divider,
  },
  width: 48,
  height: 48,
  margin: 0,
  flexShrink: 0,
  '& .MuiSvgIcon-root': {
    fontSize: '1.2rem',
  },
  [theme.breakpoints.up('md')]: {
    width: 52,
    height: 52,
  },
}));

export type QuickAction =
  | 'play'
  | 'pause'
  | 'stop'
  | 'refresh'
  | 'save'
  | 'settings'
  | 'fullscreen'
  | 'export';

interface QuickActionsProps {
  loading?: boolean;
  error?: boolean;
  status?: 'idle' | 'running' | 'paused' | 'stopped';
  isLive?: boolean;
  isOnline?: boolean;
  onAction?: (action: QuickAction) => void;
  variant?: 'tile' | 'inline';
  inlineTitle?: string;
  density?: 'standard' | 'compact';
  showInlineTitle?: boolean;
}

const QuickActions: React.FC<QuickActionsProps> = ({
  loading,
  error,
  status = 'idle',
  isLive = false,
  isOnline = true,
  onAction = () => {},
  variant = 'tile',
  inlineTitle = 'Quick Actions',
  density = 'standard',
  showInlineTitle = true,
}) => {
  const isMobile = useMediaQuery('(max-width:767px)');
  const isCompact = density === 'compact' && !isMobile;
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const connectionState = !isOnline
    ? 'OFFLINE'
    : isLive
      ? 'LIVE'
      : isRunning
        ? 'ONLINE'
        : 'STANDBY';
  const previousConnectionState = useRef(connectionState);

  useEffect(() => {
    if (previousConnectionState.current !== connectionState) {
      const payload = {
        status: connectionState,
        previous: previousConnectionState.current,
        pipelineStatus: status,
        timestamp: new Date().toISOString(),
      };
      if (typeof window !== 'undefined') {
        console.info('[connection-indicator]', payload);
      }
      telemetry.emit({ type: 'connection-indicator', payload });
      previousConnectionState.current = connectionState;
    }
  }, [connectionState, status]);

  const handlePlayPause = () => {
    if (isRunning && !isPaused) {
      onAction('pause');
    } else {
      onAction('play');
    }
  };

  const handleStop = () => {
    onAction('stop');
  };

  const handleRefresh = () => {
    onAction('refresh');
  };

  const handleSave = () => {
    onAction('save');
  };

  const handleSettings = () => {
    onAction('settings');
  };

  const handleFullscreen = () => {
    onAction('fullscreen');
  };

  const handleExport = () => {
    onAction('export');
  };

  const renderConnectionIndicator = (showStatusChip = true) => (
    <Box
      data-testid="connection-status"
      data-status={connectionState.toLowerCase()}
      className={`connection-status ${connectionState.toLowerCase()}`}
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: isMobile ? 1.5 : 0,
        py: isCompact ? 0.25 : 0.5,
        borderRadius: 1,
        border: (theme) => `1px solid ${theme.palette.divider}`,
        backgroundColor: 'rgba(99, 102, 241, 0.05)',
        width: '100%',
      }}
    >
      <Typography variant="caption" color="text.secondary" fontWeight={600} textTransform="uppercase">
        Connection
      </Typography>
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography
          variant="body2"
          fontWeight={700}
          color={
            connectionState === 'LIVE'
              ? 'success.main'
              : connectionState === 'OFFLINE'
                ? 'error.main'
                : 'text.primary'
          }
          data-testid="live-indicator"
          aria-live="polite"
        >
          {connectionState}
        </Typography>
        {showStatusChip && (
          <Chip
            label={!isOnline ? 'OFFLINE' : isLive ? 'LIVE' : isRunning ? 'ACTIVE' : 'STANDBY'}
            size="small"
            color={isLive ? 'success' : 'default'}
            sx={{
              fontWeight: 600,
              letterSpacing: '0.04em',
              height: 20,
              borderRadius: 1,
              ...(connectionState === 'OFFLINE'
                ? {
                    bgcolor: (theme) => theme.palette.error.light,
                    color: (theme) => theme.palette.error.contrastText,
                    borderColor: (theme) => theme.palette.error.main,
                  }
                : {}),
            }}
          />
        )}
      </Stack>
    </Box>
  );

  // Mobile: Essential actions only, horizontal layout with visual grouping
  const renderActions = (compactLayout = false) => (
    <Stack
      direction="row"
      flexWrap={compactLayout ? 'nowrap' : 'wrap'}
      gap={isMobile ? 1 : compactLayout ? 0.75 : 1.25}
      justifyContent={compactLayout ? 'flex-end' : isMobile ? 'center' : 'flex-start'}
      sx={{ width: '100%' }}
    >
      <Fade in timeout={200}>
        <Tooltip title={isRunning && !isPaused ? 'Pause' : 'Start'} placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            data-testid="quick-action-play"
            onClick={handlePlayPause}
            color="primary"
            active={isRunning && !isPaused}
            whileTap={{ scale: 0.95 }}
            aria-label={isRunning && !isPaused ? 'Pause orchestration' : 'Start orchestration'}
          >
            {isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
          </ActionButton>
        </Tooltip>
      </Fade>

      <Fade in timeout={220}>
        <Tooltip title="Stop" placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            data-testid="quick-action-stop"
            onClick={handleStop}
            disabled={!isRunning}
            whileTap={{ scale: 0.95 }}
            aria-label="Stop orchestration"
          >
            <StopIcon />
          </ActionButton>
        </Tooltip>
      </Fade>

      <Fade in timeout={260}>
        <Tooltip title="Refresh" placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            data-testid="quick-action-refresh"
            onClick={handleRefresh}
            whileTap={{ scale: 0.95 }}
            aria-label="Refresh dashboard data"
          >
            <RefreshIcon />
          </ActionButton>
        </Tooltip>
      </Fade>

      <Fade in timeout={280}>
        <Tooltip title="Save" placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            data-testid="quick-action-save"
            onClick={handleSave}
            whileTap={{ scale: 0.95 }}
            aria-label="Save current state"
          >
            <SaveIcon />
          </ActionButton>
        </Tooltip>
      </Fade>

      <Fade in timeout={320}>
        <Tooltip title="Settings" placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            data-testid="settings-button"
            onClick={handleSettings}
            whileTap={{ scale: 0.95 }}
            aria-label="Open settings"
          >
            <SettingsIcon />
          </ActionButton>
        </Tooltip>
      </Fade>

      <Fade in timeout={340}>
        <Tooltip title="Fullscreen" placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            onClick={handleFullscreen}
            whileTap={{ scale: 0.95 }}
            aria-label="Toggle fullscreen"
          >
            <FullscreenIcon />
          </ActionButton>
        </Tooltip>
      </Fade>

      <Fade in timeout={360}>
        <Tooltip title="Export" placement={isMobile ? 'top' : 'bottom'}>
          <ActionButton
            data-testid="quick-action-export"
            onClick={handleExport}
            whileTap={{ scale: 0.95 }}
            aria-label="Export data"
          >
            <DownloadIcon />
          </ActionButton>
        </Tooltip>
      </Fade>
    </Stack>
  );

  const body = isCompact ? (
    <Stack
      direction="row"
      spacing={2}
      alignItems="center"
      justifyContent="space-between"
      sx={{ width: '100%' }}
    >
      <Box sx={{ flex: '0 0 260px', minWidth: 200 }}>
        {renderConnectionIndicator(false)}
      </Box>
      <Box sx={{ flex: 1, display: 'flex', justifyContent: 'flex-end' }}>
        {renderActions(true)}
      </Box>
    </Stack>
  ) : (
    <Stack spacing={isMobile ? 1 : 1.5} sx={{ width: '100%' }}>
      {renderConnectionIndicator()}
      {renderActions()}
    </Stack>
  );

  return (
    variant === 'inline' ? (
      <Box data-testid="quick-actions" sx={{ width: '100%', minWidth: 0 }}>
        <Stack spacing={1.25}>
          {showInlineTitle && (
            <Typography variant="subtitle2" fontWeight={700}>
              {inlineTitle}
            </Typography>
          )}
          {body}
        </Stack>
      </Box>
    ) : (
      <GridTile
        title="Actions"
        data-testid="quick-actions"
        data-role="control-cluster"
        position={{
          desktop: { column: 'span 2', height: 'auto' },
          tablet: { column: 'span 2', height: 'auto' },
          mobile: { column: 'span 1', height: 'auto' },
        }}
        loading={loading}
        error={error}
      >
        {body}
      </GridTile>
    )
  );
};

export default QuickActions;
