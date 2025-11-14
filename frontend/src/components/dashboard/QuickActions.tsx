import React, { useState } from 'react';
import { 
  Box, 
  Tooltip, 
  Stack,
  Divider,
  Typography,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled, alpha } from '@mui/material/styles';
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
import type { QuickAction, RunStateSummary } from './types';

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

const ActionButton = styled(motion.button, {
  shouldForwardProp: (prop) => prop !== '$active',
})<{ $active?: boolean }>(({ theme, $active: active }) => ({
  border: `1px solid ${active ? theme.palette.primary.main : theme.palette.divider}`,
  backgroundColor: active ? 'rgba(99, 102, 241, 0.12)' : theme.palette.background.paper,
  color: theme.palette.text.primary,
  width: 44,
  height: 44,
  borderRadius: 999,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  outline: '2px solid transparent',
  outlineOffset: 4,
  position: 'relative',
  boxShadow: 'none',
  '& svg': {
    fontSize: '1.25rem',
  },
  '&:hover': {
    backgroundColor: active ? 'rgba(99, 102, 241, 0.22)' : theme.palette.action.hover,
    borderColor: theme.palette.primary.main,
    transform: 'translateY(-1px)',
    boxShadow: '0 4px 10px rgba(99, 102, 241, 0.2)',
  },
  '&:active': {
    transform: 'scale(0.97)',
  },
  '&:disabled': {
    cursor: 'not-allowed',
    opacity: 0.4,
    borderColor: theme.palette.divider,
    boxShadow: 'none',
  },
  '&:focus, &:focus-visible': {
    outlineColor: theme.palette.primary.main,
    boxShadow: `0 0 0 4px ${theme.palette.primary.main}33`,
  },
  [theme.breakpoints.down('md')]: {
    width: 52,
    height: 52,
    '& svg': {
      fontSize: '1.35rem',
    },
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

interface QuickActionsProps {
  loading?: boolean;
  error?: boolean;
  runState?: RunStateSummary;
  onAction?: (action: QuickAction) => void;
}

const defaultRunState: RunStateSummary = {
  status: 'idle',
  mode: 'simulation',
  connected: false,
  isLiveMode: false,
};

const QuickActions: React.FC<QuickActionsProps> = ({ 
  loading, 
  error, 
  runState = defaultRunState,
  onAction = () => {} 
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [announcement, setAnnouncement] = useState('');
  const isRunning = runState.status === 'running';
  const isPaused = runState.status === 'paused';
  const connectionState = runState.connected
    ? runState.isLiveMode
      ? 'LIVE'
      : 'SIM'
    : 'IDLE';

  const announce = (message: string) => {
    setAnnouncement(message);
    // keep announcement text long enough for screen readers, then clear
    setTimeout(() => setAnnouncement(''), 1200);
  };

  const handleStart = () => {
    if (isRunning && !isPaused) return;
    onAction('play');
    announce('Orchestration started');
  };

  const handlePause = () => {
    if (!isRunning || isPaused) return;
    onAction('pause');
    announce('Orchestration paused');
  };

  const handleStop = () => {
    if (!isRunning && !isPaused) return;
    onAction('stop');
    announce('Orchestration stopped');
  };

  const handleRefresh = () => {
    onAction('refresh');
    announce('Dashboard data refresh requested');
  };

  const handleSave = () => {
    onAction('save');
    announce('Current state saved');
  };

  const handleSettings = () => {
    onAction('settings');
    announce('Opening settings');
  };

  const handleFullscreen = () => {
    onAction('fullscreen');
    announce('Toggling fullscreen mode');
  };

  const handleExport = () => {
    onAction('export');
    announce('Export started');
  };

  // Mobile: Essential actions only, horizontal layout with visual grouping
  const renderMobileActions = () => (
    <ActionsContainer>
      <Tooltip title="Start" placement="top">
        <ActionButton 
          data-testid="quick-action-play"
          onClick={handleStart} 
          color="primary"
          $active={isRunning && !isPaused}
          disabled={isRunning && !isPaused}
          whileTap={{ scale: 0.95 }}
          aria-label="Start orchestration"
        >
          <PlayIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Pause" placement="top">
        <ActionButton 
          data-testid="quick-action-pause"
          onClick={handlePause} 
          disabled={!isRunning || isPaused}
          whileTap={{ scale: 0.95 }}
          aria-label="Pause orchestration"
        >
          <PauseIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Stop" placement="top">
        <ActionButton 
          data-testid="quick-action-stop"
          onClick={handleStop} 
          disabled={!isRunning && !isPaused}
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
          data-testid="quick-action-settings"
          onClick={handleSettings} 
          whileTap={{ scale: 0.95 }}
          aria-label="Open dashboard settings"
        >
          <SettingsIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Export" placement="top">
        <ActionButton 
          data-testid="quick-action-export"
          onClick={handleExport} 
          whileTap={{ scale: 0.95 }}
          aria-label="Export dashboard data"
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
            
            <Tooltip title="Start" placement="left">
              <ActionButton 
                data-testid="quick-action-play"
                onClick={handleStart} 
                color="primary"
                $active={isRunning && !isPaused}
                disabled={isRunning && !isPaused}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Start orchestration"
              >
                <PlayIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Pause" placement="left">
              <ActionButton 
                data-testid="quick-action-pause"
                onClick={handlePause} 
                disabled={!isRunning || isPaused}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                aria-label="Pause orchestration"
              >
                <PauseIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Stop" placement="left">
              <ActionButton 
                data-testid="quick-action-stop"
                onClick={handleStop} 
                disabled={!isRunning && !isPaused}
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
                data-testid="quick-action-settings"
                onClick={handleSettings}
                whileHover={{ scale: 1.05, rotate: 90 }}
                whileTap={{ scale: 0.95 }}
                transition={{ duration: 0.3 }}
                aria-label="Open dashboard settings"
              >
                <SettingsIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Fullscreen" placement="left">
              <ActionButton 
                data-testid="quick-action-fullscreen"
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
                aria-label="Export dashboard data"
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
      position={{
        desktop: { column: '12 / 13', height: '160px' },
        tablet: { column: '8 / 9', height: '140px' },
        mobile: { column: '1', height: '200px' }, // Increased to match MobileTabbedDashboard height
      }}
      loading={loading}
      error={error}
    >
      <Box sx={{ position: 'relative', width: '100%' }}>
        <Box 
          component="div"
          role="status"
          aria-live="polite"
          data-testid="quick-actions-announcer"
          sx={{
            position: 'absolute',
            width: 1,
            height: 1,
            overflow: 'hidden',
            clip: 'rect(0 0 0 0)',
            whiteSpace: 'nowrap',
          }}
        >
          {announcement}
        </Box>
        <Box
          data-testid="connection-status"
          aria-label={`Connection status: ${connectionState}`}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            position: 'absolute',
            top: (theme) => theme.spacing(1),
            right: (theme) => theme.spacing(1.5),
            backgroundColor: (theme) => alpha(theme.palette.background.default, 0.85),
            borderRadius: 999,
            padding: (theme) => theme.spacing(0.5, 1),
            border: (theme) => `1px solid ${theme.palette.divider}`,
          }}
        >
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: (theme) =>
                isRunning
                  ? theme.palette.success.main
                  : isPaused
                    ? theme.palette.warning.main
                    : theme.palette.text.disabled,
              boxShadow: (theme) =>
                isRunning ? `0 0 8px ${theme.palette.success.main}` : 'none',
            }}
          />
          <Typography variant="caption" fontWeight={600}>
            {connectionState}
          </Typography>
          {isRunning && !isPaused && runState.isLiveMode && (
            <Box
              data-testid="live-indicator"
              sx={{
                ml: 0.5,
                px: 1,
                py: 0.25,
                borderRadius: 999,
                backgroundColor: (theme) => alpha(theme.palette.success.main, 0.15),
                border: (theme) => `1px solid ${alpha(theme.palette.success.main, 0.6)}`,
              }}
            >
              <Typography
                variant="caption"
                fontWeight={700}
                letterSpacing={0.5}
                color="success.main"
              >
                LIVE
              </Typography>
            </Box>
          )}
        </Box>
        {isMobile ? renderMobileActions() : renderDesktopActions()}
      </Box>
    </GridTile>
  );
};

export default QuickActions;
