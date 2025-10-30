import React, { useState } from 'react';
import { 
  Box, 
  IconButton, 
  Tooltip, 
  Stack,
  Divider,
  Typography,
  useTheme,
  useMediaQuery,
  ButtonGroup,
  Fade,
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

interface QuickActionsProps {
  loading?: boolean;
  error?: boolean;
  onAction?: (action: string) => void;
}

const QuickActions: React.FC<QuickActionsProps> = ({ 
  loading, 
  error, 
  onAction = () => {} 
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const handlePlayPause = () => {
    if (isRunning && !isPaused) {
      setIsPaused(true);
      onAction('pause');
    } else {
      setIsRunning(true);
      setIsPaused(false);
      onAction('play');
    }
  };

  const handleStop = () => {
    setIsRunning(false);
    setIsPaused(false);
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
    <ActionsContainer>
      <Tooltip title={isRunning && !isPaused ? "Pause" : "Start"} placement="top">
        <ActionButton 
          data-testid="run-turn-button"
          onClick={handlePlayPause} 
          color="primary"
          active={isRunning && !isPaused}
          whileTap={{ scale: 0.95 }}
        >
          {isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
        </ActionButton>
      </Tooltip>

      <Tooltip title="Stop" placement="top">
        <ActionButton 
          onClick={handleStop} 
          disabled={!isRunning}
          whileTap={{ scale: 0.95 }}
        >
          <StopIcon />
        </ActionButton>
      </Tooltip>

      <Divider orientation="vertical" flexItem sx={{ mx: 1, backgroundColor: 'divider' }} />

      <Tooltip title="Refresh" placement="top">
        <ActionButton onClick={handleRefresh} whileTap={{ scale: 0.95 }}>
          <RefreshIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Save" placement="top">
        <ActionButton onClick={handleSave} whileTap={{ scale: 0.95 }}>
          <SaveIcon />
        </ActionButton>
      </Tooltip>

      <Divider orientation="vertical" flexItem sx={{ mx: 1, backgroundColor: 'divider' }} />

      <Tooltip title="Settings" placement="top">
        <ActionButton onClick={handleSettings} whileTap={{ scale: 0.95 }}>
          <SettingsIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Export" placement="top">
        <ActionButton onClick={handleExport} whileTap={{ scale: 0.95 }}>
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
                data-testid="run-turn-button"
                onClick={handlePlayPause} 
                color="primary"
                active={isRunning && !isPaused}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
              </ActionButton>
            </Tooltip>

            <Tooltip title="Stop" placement="left">
              <ActionButton 
                onClick={handleStop} 
                disabled={!isRunning}
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
      position={{
        desktop: { column: '12 / 13', height: '160px' },
        tablet: { column: '8 / 9', height: '140px' },
        mobile: { column: '1', height: '200px' }, // Increased to match MobileTabbedDashboard height
      }}
      loading={loading}
      error={error}
    >
      {isMobile ? renderMobileActions() : renderDesktopActions()}
    </GridTile>
  );
};

export default QuickActions;
