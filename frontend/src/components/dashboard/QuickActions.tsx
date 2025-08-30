import React, { useState } from 'react';
import { 
  Box, 
  IconButton, 
  Tooltip, 
  Stack,
  Divider,
  Typography,
  useTheme,
  useMediaQuery 
} from '@mui/material';
import { styled } from '@mui/material/styles';
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

const ActionButton = styled(IconButton)(({ theme }) => ({
  border: `1px solid ${theme.palette.divider}`,
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
    borderColor: theme.palette.primary.main,
  },
  
  // Mobile: touch-friendly sizing, horizontal layout
  [theme.breakpoints.down('md')]: {
    width: 44,
    height: 44,
    margin: 0,
    flexShrink: 0,
    backgroundColor: theme.palette.background.paper,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
    '& .MuiSvgIcon-root': {
      fontSize: '1.2rem',
    },
  },
  
  // Desktop: larger, vertical layout
  [theme.breakpoints.up('md')]: {
    width: 40,
    height: 40,
    margin: theme.spacing(0.5, 0),
  },
}));

const SectionDivider = styled(Divider)(({ theme }) => ({
  width: '60%',
  margin: theme.spacing(1, 0),
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

  // Mobile: Essential actions only, horizontal layout
  const renderMobileActions = () => (
    <ActionsContainer>
      <Tooltip title={isRunning && !isPaused ? "Pause" : "Start"} placement="top">
        <ActionButton 
          data-testid="run-turn-button"
          onClick={handlePlayPause} 
          color="primary"
        >
          {isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
        </ActionButton>
      </Tooltip>

      <Tooltip title="Stop" placement="top">
        <ActionButton onClick={handleStop} disabled={!isRunning}>
          <StopIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Refresh" placement="top">
        <ActionButton onClick={handleRefresh}>
          <RefreshIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Save" placement="top">
        <ActionButton onClick={handleSave}>
          <SaveIcon />
        </ActionButton>
      </Tooltip>

      <Tooltip title="Settings" placement="top">
        <ActionButton onClick={handleSettings}>
          <SettingsIcon />
        </ActionButton>
      </Tooltip>
    </ActionsContainer>
  );

  // Desktop: Full actions with sections, vertical layout  
  const renderDesktopActions = () => (
    <ActionsContainer>
      <Stack direction="column" spacing={0.5} alignItems="center">
        {/* Playback Controls */}
        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
          Control
        </Typography>
        
        <Tooltip title={isRunning && !isPaused ? "Pause" : "Start"} placement="left">
          <ActionButton 
            data-testid="run-turn-button"
            onClick={handlePlayPause} 
            color="primary"
          >
            {isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
          </ActionButton>
        </Tooltip>

        <Tooltip title="Stop" placement="left">
          <ActionButton onClick={handleStop} disabled={!isRunning}>
            <StopIcon />
          </ActionButton>
        </Tooltip>

        <SectionDivider />

        {/* System Actions */}
        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
          System
        </Typography>

        <Tooltip title="Refresh Data" placement="left">
          <ActionButton onClick={handleRefresh}>
            <RefreshIcon />
          </ActionButton>
        </Tooltip>

        <Tooltip title="Save State" placement="left">
          <ActionButton onClick={handleSave}>
            <SaveIcon />
          </ActionButton>
        </Tooltip>

        <SectionDivider />

        {/* View Actions */}
        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
          View
        </Typography>

        <Tooltip title="Settings" placement="left">
          <ActionButton onClick={handleSettings}>
            <SettingsIcon />
          </ActionButton>
        </Tooltip>

        <Tooltip title="Fullscreen" placement="left">
          <ActionButton onClick={handleFullscreen}>
            <FullscreenIcon />
          </ActionButton>
        </Tooltip>

        <Tooltip title="Export Data" placement="left">
          <ActionButton onClick={handleExport}>
            <DownloadIcon />
          </ActionButton>
        </Tooltip>
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