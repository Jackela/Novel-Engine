import React from 'react';
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
import type { DensityMode } from '@/utils/density';

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

type PipelineStatus = 'idle' | 'running' | 'paused';

interface QuickActionsProps {
  loading?: boolean;
  error?: boolean;
  onAction?: (action: string) => void;
  status?: PipelineStatus;
  isLive?: boolean;
  runSummary?: {
    phase: string;
    completed: number;
    total: number;
    lastSignal?: string;
  };
  density?: DensityMode;
}

const QuickActions: React.FC<QuickActionsProps> = ({ 
  loading, 
  error, 
  onAction = () => {},
  status = 'idle',
  isLive = false,
  runSummary,
  density = 'relaxed',
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const statusLabel = isRunning ? 'Running' : isPaused ? 'Paused' : 'Idle';
  const statusChipColor: 'default' | 'success' | 'warning' = isRunning ? 'success' : isPaused ? 'warning' : 'default';

  const handlePlayPause = () => {
    if (isRunning) {
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

  // Mobile: Essential actions only, horizontal layout with visual grouping
  const renderMobileActions = () => (
    <ActionsContainer data-testid="quick-actions">
      <Tooltip title={isRunning && !isPaused ? "Pause" : "Start"} placement="top">
        <ActionButton 
          data-testid={isRunning ? 'quick-action-pause' : 'quick-action-play'}
          onClick={handlePlayPause} 
          color="primary"
          active={isRunning}
          whileTap={{ scale: 0.95 }}
        >
          {isRunning ? <PauseIcon /> : <PlayIcon />}
        </ActionButton>
      </Tooltip>

      <Tooltip title="Stop" placement="top">
        <ActionButton 
          data-testid="quick-action-stop"
          onClick={handleStop} 
          disabled={status === 'idle'}
          whileTap={{ scale: 0.95 }}
        >
          <StopIcon />
        </ActionButton>
      </Tooltip>

      <Divider orientation="vertical" flexItem sx={{ mx: 1, backgroundColor: 'divider' }} />

        <Tooltip title="Refresh" placement="top">
        <ActionButton data-testid="quick-action-refresh" onClick={handleRefresh} whileTap={{ scale: 0.95 }}>
          <RefreshIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Save" placement="top">
        <ActionButton onClick={handleSave} whileTap={{ scale: 0.95 }}>
          <SaveIcon />
        </ActionButton>
      </Tooltip>
    </ActionsContainer>
  );

  // Desktop: Full actions with sections, vertical layout with enhanced grouping
  const renderDesktopActions = () => (
    <ActionsContainer data-testid="quick-actions">
      <Stack direction="column" spacing={0} alignItems="center" sx={{ width: '100%', py: 1 }}>
        {/* Playback Controls */}
        <Fade in timeout={300}>
          <ActionGroup>
            <GroupLabel>Control</GroupLabel>
            
            <Tooltip title={isRunning ? "Pause" : "Start"} placement="left">
              <ActionButton 
                data-testid={isRunning ? 'quick-action-pause' : 'quick-action-play'}
                onClick={handlePlayPause} 
                color="primary"
                active={isRunning}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isRunning ? <PauseIcon /> : <PlayIcon />}
              </ActionButton>
            </Tooltip>

            <Tooltip title="Stop" placement="left">
              <ActionButton 
                data-testid="quick-action-stop"
                onClick={handleStop} 
                disabled={status === 'idle'}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
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
              >
                <RefreshIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Save State" placement="left">
              <ActionButton 
                onClick={handleSave}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
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
                onClick={handleSettings}
                whileHover={{ scale: 1.05, rotate: 90 }}
                whileTap={{ scale: 0.95 }}
                transition={{ duration: 0.3 }}
              >
                <SettingsIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Fullscreen" placement="left">
              <ActionButton 
                onClick={handleFullscreen}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <FullscreenIcon />
              </ActionButton>
            </Tooltip>

            <Tooltip title="Export Data" placement="left">
              <ActionButton 
                onClick={handleExport}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
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
      className="quick-actions-tile"
      position={{
        desktop: { column: '9 / 13', height: '220px' },
        tablet: { column: '6 / 9', height: '180px' },
        mobile: { column: '1', height: '200px' }, // Increased to match MobileTabbedDashboard height
      }}
      loading={loading}
      error={error}
    >
      <Box data-density={density} data-testid="quick-actions-density">
      <Stack spacing={density === 'compact' ? 0.75 : isMobile ? 1 : 2}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip
            label={statusLabel}
            size="small"
            color={statusChipColor === 'default' ? 'default' : statusChipColor}
            sx={{ fontWeight: 600, height: 22 }}
          />
          {isLive && isRunning && (
            <Chip
              label="LIVE"
              size="small"
              color="error"
              data-testid="live-indicator"
              sx={{ fontWeight: 600, height: 22 }}
            />
          )}
        </Stack>
        <Typography variant="caption" color="text.secondary">
          {isLive ? 'Live orchestration in progress' : 'Live mode disabled'}
        </Typography>
        <Stack
          spacing={0.5}
          direction={isMobile ? 'column' : 'row'}
          alignItems={isMobile ? 'flex-start' : 'center'}
          justifyContent="space-between"
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            p: density === 'compact' ? 0.75 : 1,
            backgroundColor: (theme) => theme.palette.background.default,
          }}
        >
          <Box>
            <Typography variant="caption" color="text.secondary">
              Current phase
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {runSummary?.phase ?? 'Idle'}
            </Typography>
          </Box>
          <Box textAlign={isMobile ? 'left' : 'right'}>
            <Typography variant="caption" color="text.secondary">
              Completed
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {runSummary ? `${runSummary.completed}/${runSummary.total}` : '0/0'}
            </Typography>
          </Box>
          {runSummary?.lastSignal && (
            <Box textAlign={isMobile ? 'left' : 'right'}>
              <Typography variant="caption" color="text.secondary">
                Last signal
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {runSummary.lastSignal}
              </Typography>
            </Box>
          )}
        </Stack>
        {isMobile ? renderMobileActions() : renderDesktopActions()}
      </Stack>
      </Box>
    </GridTile>
  );
};

export default QuickActions;
