import React, { useEffect, useRef } from 'react';
import { 
  Box, 
  IconButton, 
  Tooltip, 
  Stack,
  Divider,
  Typography,
  useTheme,
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

const ActionsContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  height: '100%',
  
  // Mobile: horizontal layout with scrolling and optimized compact height
  [theme.breakpoints.down('md')]: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-start',
    overflowX: 'auto',
    gap: theme.spacing(1.5),
    paddingLeft: theme.spacing(1.5), // Reduced padding for more space
    paddingRight: theme.spacing(1.5),
    paddingTop: theme.spacing(0.75), // Reduced padding for more space  
    paddingBottom: theme.spacing(0.75),
    minHeight: '56px', // Reduced to be more compact while maintaining 44px button + minimal padding
    scrollBehavior: 'smooth',
    '&::-webkit-scrollbar': {
      height: '4px',
    },
    '&::-webkit-scrollbar-track': {
      backgroundColor: 'transparent',
    },
    '&::-webkit-scrollbar-thumb': {
      backgroundColor: theme.palette.divider,
      borderRadius: '2px',
    },
  },
  
  // Desktop: vertical layout
  [theme.breakpoints.up('md')]: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'flex-start',
  },
}));

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
  
  // Mobile: touch-friendly sizing, horizontal layout
  [theme.breakpoints.down('md')]: {
    width: 48,
    height: 48,
    margin: 0,
    flexShrink: 0,
    '& .MuiSvgIcon-root': {
      fontSize: '1.3rem',
    },
  },
  
  // Desktop: larger, vertical layout
  [theme.breakpoints.up('md')]: {
    width: 44,
    height: 44,
    margin: theme.spacing(0.5, 0),
  },
}));

const SectionDivider = styled(Divider)(({ theme }) => ({
  width: '60%',
  margin: theme.spacing(1.5, 0),
  backgroundColor: theme.palette.divider,
}));

const ActionGroup = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: theme.spacing(0.5),
}));

const GroupLabel = styled(Typography)(({ theme }) => ({
  fontSize: '0.65rem',
  fontWeight: 600,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  color: 'var(--color-text-tertiary)',
  marginBottom: theme.spacing(0.5),
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
}

const QuickActions: React.FC<QuickActionsProps> = ({ 
  loading, 
  error, 
  status = 'idle',
  isLive = false,
  isOnline = true,
  onAction = () => {} 
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
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

  const renderConnectionIndicator = () => (
    <Box
      data-testid="connection-status"
      data-status={connectionState.toLowerCase()}
      className={`connection-status ${connectionState.toLowerCase()}`}
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: isMobile ? 1.5 : 0,
        py: 0.5,
        borderRadius: 1,
        border: (theme) => `1px solid ${theme.palette.divider}`,
        backgroundColor: 'rgba(99, 102, 241, 0.05)',
        width: '100%'
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
        <Chip 
          label={
            !isOnline ? 'OFFLINE' : isLive ? 'LIVE' : isRunning ? 'ACTIVE' : 'STANDBY'
          }
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
      </Stack>
    </Box>
  );

  // Mobile: Essential actions only, horizontal layout with visual grouping
  const renderMobileActions = () => (
    <ActionsContainer>
      <Tooltip title={isRunning && !isPaused ? "Pause" : "Start"} placement="top">
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

      <Tooltip title="Stop" placement="top">
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

      <Divider orientation="vertical" flexItem sx={{ mx: 1, backgroundColor: 'divider' }} />

      <Tooltip title="Refresh" placement="top">
        <ActionButton 
          data-testid="quick-action-refresh"
          onClick={handleRefresh} 
          whileTap={{ scale: 0.95 }}
          aria-label="Refresh dashboard data"
        >
          <RefreshIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Save" placement="top">
        <ActionButton 
          data-testid="quick-action-save"
          onClick={handleSave} 
          whileTap={{ scale: 0.95 }}
          aria-label="Save current state"
        >
          <SaveIcon />
        </ActionButton>
      </Tooltip>

      <Divider orientation="vertical" flexItem sx={{ mx: 1, backgroundColor: 'divider' }} />

      <Tooltip title="Settings" placement="top">
        <ActionButton 
          data-testid="settings-button"
          onClick={handleSettings} 
          whileTap={{ scale: 0.95 }}
          aria-label="Open settings"
        >
          <SettingsIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Export" placement="top">
        <ActionButton 
          data-testid="quick-action-export"
          onClick={handleExport} 
          whileTap={{ scale: 0.95 }}
          aria-label="Export data"
        >
          <DownloadIcon />
        </ActionButton>
      </Tooltip>
    </ActionsContainer>
  );

  // Desktop: Full actions with sections, vertical layout with enhanced grouping
  const renderDesktopActions = () => (
    <ActionsContainer>
      <Stack direction="column" spacing={0} alignItems="center" sx={{ width: '100%', py: 1 }}>
        {/* Playback Controls */}
        <Fade in timeout={300}>
          <ActionGroup>
            <GroupLabel>Control</GroupLabel>
            
            <Tooltip title={isRunning && !isPaused ? "Pause" : "Start"} placement="left">
              <ActionButton 
                data-testid="quick-action-play"
                onClick={handlePlayPause} 
                color="primary"
                active={isRunning && !isPaused}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label={isRunning && !isPaused ? 'Pause orchestration' : 'Start orchestration'}
              >
                {isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
              </ActionButton>
            </Tooltip>

            <Tooltip title="Stop" placement="left">
              <ActionButton 
                data-testid="quick-action-stop"
                onClick={handleStop} 
                disabled={!isRunning}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Stop orchestration"
              >
                <StopIcon />
              </ActionButton>
            </Tooltip>
          </ActionGroup>
        </Fade>

        <SectionDivider />

        {/* System Actions */}
        <Fade in timeout={400}>
          <ActionGroup>
            <GroupLabel>System</GroupLabel>

            <Tooltip title="Refresh Data" placement="left">
              <ActionButton 
                data-testid="quick-action-refresh"
                onClick={handleRefresh}
                whileHover={{ scale: 1.05, rotate: 180 }}
                whileTap={{ scale: 0.95 }}
                transition={{ duration: 0.3 }}
                aria-label="Refresh dashboard data"
              >
                <RefreshIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Save State" placement="left">
              <ActionButton 
                data-testid="quick-action-save"
                onClick={handleSave}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Save current state"
              >
                <SaveIcon />
              </ActionButton>
            </Tooltip>
          </ActionGroup>
        </Fade>

        <SectionDivider />

        {/* View Actions */}
        <Fade in timeout={500}>
          <ActionGroup>
            <GroupLabel>View</GroupLabel>

            <Tooltip title="Settings" placement="left">
              <ActionButton 
                data-testid="settings-button"
                onClick={handleSettings}
                whileHover={{ scale: 1.05, rotate: 90 }}
                whileTap={{ scale: 0.95 }}
                transition={{ duration: 0.3 }}
                aria-label="Open settings"
              >
                <SettingsIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Fullscreen" placement="left">
              <ActionButton 
                onClick={handleFullscreen}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Toggle fullscreen"
              >
                <FullscreenIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Export Data" placement="left">
              <ActionButton 
                data-testid="quick-action-export"
                onClick={handleExport}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Export data"
              >
                <DownloadIcon />
              </ActionButton>
            </Tooltip>
          </ActionGroup>
        </Fade>
      </Stack>
    </ActionsContainer>
  );

  return (
    <GridTile
      title="Actions"
      data-testid="quick-actions"
      data-role="control-cluster"
      position={{
        desktop: { column: '12 / 13', height: '160px' },
        tablet: { column: '8 / 9', height: '140px' },
        mobile: { column: '1', height: '200px' },
      }}
      loading={loading}
      error={error}
    >
      <Stack spacing={isMobile ? 1 : 1.5} sx={{ height: '100%' }}>
        {renderConnectionIndicator()}
        {isMobile ? renderMobileActions() : renderDesktopActions()}
      </Stack>
    </GridTile>
  );
};

export default QuickActions;
