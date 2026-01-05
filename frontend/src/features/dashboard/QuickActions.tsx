import React, { useEffect, useRef } from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Fade from '@mui/material/Fade';
import Chip from '@mui/material/Chip';
import useMediaQuery from '@mui/material/useMediaQuery';
import { styled, alpha } from '@mui/material/styles';
import { motion } from 'framer-motion';
import PlayIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import StopIcon from '@mui/icons-material/Stop';
import RefreshIcon from '@mui/icons-material/Refresh';
import SaveIcon from '@mui/icons-material/Save';
import SettingsIcon from '@mui/icons-material/Settings';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import DownloadIcon from '@mui/icons-material/Download';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import GridTile from '@/components/layout/GridTile';
import { telemetry } from '../../utils/telemetry';

const ActionButton = styled(motion(IconButton))(({ theme }) => ({
  border: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.paper,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: theme.palette.background.default,
    borderColor: theme.palette.primary.main,
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[2],
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.info.main}`,
    outlineOffset: 2,
  },
  '&:focus:not(:focus-visible)': {
    outline: 'none',
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
  '&[data-active="true"]': {
    borderColor: theme.palette.primary.main,
    backgroundColor: alpha(theme.palette.primary.main, 0.12),
    '&:hover': {
      backgroundColor: alpha(theme.palette.primary.main, 0.18),
      borderColor: theme.palette.primary.main,
    },
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
  | 'export'
  | 'createCharacter';

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

const TooltipWrapper = styled('span', {
  shouldForwardProp: (prop: PropertyKey) => prop !== '$disabled',
})<{ $disabled?: boolean }>(({ theme, $disabled }) => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  pointerEvents: 'auto',
  '& > *': {
    pointerEvents: $disabled ? 'none' : 'auto',
  },
  ...($disabled
    ? {
      cursor: 'not-allowed',
      padding: theme.spacing(2, 3),
      background: theme.palette.background.paper,
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: theme.shape.borderRadius * 2,
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      '&:hover': {
        background: theme.palette.background.default,
        borderColor: theme.palette.primary.main,
      },
      color: theme.palette.action.disabled,
    }
    : {}),
}));

interface ActionButtonProps {
  tooltip: string;
  placement: 'top' | 'bottom';
  onClick: () => void;
  icon: React.ReactElement;
  ariaLabel: string;
  testId?: string;
  disabled?: boolean;
  active?: boolean;
  ariaPressed?: boolean;
  color?: 'primary' | 'inherit';
  fadeMs?: number;
}

const QuickActionButton: React.FC<ActionButtonProps> = ({
  tooltip,
  placement,
  onClick,
  icon,
  ariaLabel,
  testId,
  disabled,
  active,
  ariaPressed,
  color,
  fadeMs = 200,
}) => (
  <Fade in timeout={fadeMs}>
    <Tooltip title={tooltip} placement={placement}>
      <TooltipWrapper $disabled={disabled}>
        <ActionButton
          data-testid={testId}
          onClick={onClick}
          disabled={disabled}
          aria-disabled={disabled || undefined}
          data-active={active ? 'true' : 'false'}
          whileTap={{ scale: 0.95 }}
          aria-label={ariaLabel}
          aria-pressed={ariaPressed}
          color={color}
        >
          {icon}
        </ActionButton>
      </TooltipWrapper>
    </Tooltip>
  </Fade>
);

const ConnectionIndicator: React.FC<{
  connectionState: string;
  isLive: boolean;
  isRunning: boolean;
  isOnline: boolean;
  isCompact: boolean;
  isMobile: boolean;
  showStatusChip?: boolean;
}> = ({ connectionState, isLive, isRunning, isOnline, isCompact, isMobile, showStatusChip = true }) => (
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
      backgroundColor: 'rgba(255, 255, 255, 0.03)',
      backdropFilter: 'blur(4px)',
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
          label={!isOnline ? 'OFFLINE' : isLive ? 'LIVE' : isRunning ? 'ACTIVE' : 'ONLINE'}
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
    <Typography variant="caption" color="text.secondary">
      Demo actions are simulated; spatial/network tiles may use live API data.
    </Typography>
  </Box>
);

const ACTION_ITEMS: Array<{
  action: QuickAction;
  tooltip: string;
  testId: string;
  ariaLabel: string;
  icon: React.ReactElement;
  fadeMs: number;
}> = [
  {
    action: 'refresh',
    tooltip: 'Refresh',
    testId: 'quick-action-refresh',
    ariaLabel: 'Refresh dashboard data',
    icon: <RefreshIcon />,
    fadeMs: 260,
  },
  {
    action: 'save',
    tooltip: 'Save',
    testId: 'quick-action-save',
    ariaLabel: 'Save current state',
    icon: <SaveIcon />,
    fadeMs: 280,
  },
  {
    action: 'settings',
    tooltip: 'Settings',
    testId: 'settings-button',
    ariaLabel: 'Open settings',
    icon: <SettingsIcon />,
    fadeMs: 320,
  },
  {
    action: 'fullscreen',
    tooltip: 'Fullscreen',
    testId: 'quick-action-fullscreen',
    ariaLabel: 'Toggle fullscreen',
    icon: <FullscreenIcon />,
    fadeMs: 340,
  },
  {
    action: 'export',
    tooltip: 'Export',
    testId: 'quick-action-export',
    ariaLabel: 'Export data',
    icon: <DownloadIcon />,
    fadeMs: 360,
  },
  {
    action: 'createCharacter',
    tooltip: 'Create Character',
    testId: 'quick-action-create-character',
    ariaLabel: 'Create new character',
    icon: <PersonAddIcon />,
    fadeMs: 380,
  },
];

const useConnectionIndicatorState = ({
  status,
  isOnline,
  isLive,
}: {
  status: QuickActionsProps['status'];
  isOnline: boolean;
  isLive: boolean;
}) => {
  const isRunning = status === 'running';
  const connectionState = !isOnline
    ? 'OFFLINE'
    : isLive || isRunning
      ? 'LIVE'
      : 'ONLINE';
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

  return connectionState;
};

const ActionCluster: React.FC<{
  isMobile: boolean;
  compactLayout: boolean;
  isRunning: boolean;
  isPaused: boolean;
  onAction: (action: QuickAction) => void;
}> = ({ isMobile, compactLayout, isRunning, isPaused, onAction }) => {
  const placement = isMobile ? 'top' : 'bottom';
  const handlePlayPause = () => {
    if (isRunning && !isPaused) {
      onAction('pause');
    } else {
      onAction('play');
    }
  };

  const handleAction = (action: QuickAction) => () => onAction(action);

  return (
    <Stack
      direction="row"
      flexWrap={compactLayout ? 'nowrap' : 'wrap'}
      gap={isMobile ? 1 : compactLayout ? 0.75 : 1.25}
      justifyContent={compactLayout ? 'flex-end' : isMobile ? 'center' : 'flex-start'}
      sx={{ width: '100%' }}
    >
      <QuickActionButton
        tooltip={isRunning && !isPaused ? 'Pause' : 'Start'}
        placement={placement}
        onClick={handlePlayPause}
        ariaLabel={isRunning && !isPaused ? 'Pause orchestration' : 'Start orchestration'}
        testId="quick-action-play"
        icon={isRunning && !isPaused ? <PauseIcon /> : <PlayIcon />}
        color="primary"
        active={isRunning && !isPaused}
        ariaPressed={isRunning && !isPaused}
        fadeMs={200}
      />

      <QuickActionButton
        tooltip="Stop"
        placement={placement}
        onClick={handleAction('stop')}
        ariaLabel="Stop orchestration"
        testId="quick-action-stop"
        icon={<StopIcon />}
        disabled={!isRunning}
        fadeMs={220}
      />

      {ACTION_ITEMS.map((item) => (
        <QuickActionButton
          key={item.action}
          tooltip={item.tooltip}
          placement={placement}
          onClick={handleAction(item.action)}
          ariaLabel={item.ariaLabel}
          testId={item.testId}
          icon={item.icon}
          fadeMs={item.fadeMs}
        />
      ))}
    </Stack>
  );
};

const QuickActionsBody: React.FC<{
  isCompact: boolean;
  isMobile: boolean;
  connectionState: string;
  isLive: boolean;
  isRunning: boolean;
  isOnline: boolean;
  onAction: (action: QuickAction) => void;
  isPaused: boolean;
}> = ({ isCompact, isMobile, connectionState, isLive, isRunning, isOnline, onAction, isPaused }) =>
  isCompact ? (
    <Stack
      direction="row"
      spacing={2}
      alignItems="center"
      justifyContent="space-between"
      sx={{ width: '100%' }}
    >
      <Box sx={{ flex: '0 0 260px', minWidth: 200 }}>
        <ConnectionIndicator
          connectionState={connectionState}
          isLive={isLive}
          isRunning={isRunning}
          isOnline={isOnline}
          isCompact={isCompact}
          isMobile={isMobile}
          showStatusChip={false}
        />
      </Box>
      <Box sx={{ flex: 1, display: 'flex', justifyContent: 'flex-end' }}>
        <ActionCluster
          compactLayout
          isMobile={isMobile}
          isRunning={isRunning}
          isPaused={isPaused}
          onAction={onAction}
        />
      </Box>
    </Stack>
  ) : (
    <Stack spacing={isMobile ? 1 : 1.5} sx={{ width: '100%' }}>
      <ConnectionIndicator
        connectionState={connectionState}
        isLive={isLive}
        isRunning={isRunning}
        isOnline={isOnline}
        isCompact={isCompact}
        isMobile={isMobile}
      />
      <ActionCluster
        compactLayout={false}
        isMobile={isMobile}
        isRunning={isRunning}
        isPaused={isPaused}
        onAction={onAction}
      />
    </Stack>
  );

const QuickActions: React.FC<QuickActionsProps> = ({
  loading,
  error,
  status = 'idle',
  isLive = false,
  isOnline = true,
  onAction = () => { },
  variant = 'tile',
  inlineTitle = 'Quick Actions',
  density = 'standard',
  showInlineTitle = true,
}) => {
  const isMobile = useMediaQuery('(max-width:767px)');
  const isCompact = density === 'compact' && !isMobile;
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const connectionState = useConnectionIndicatorState({ status, isOnline, isLive });
  const body = (
    <QuickActionsBody
      isCompact={isCompact}
      isMobile={isMobile}
      connectionState={connectionState}
      isLive={isLive}
      isRunning={isRunning}
      isOnline={isOnline}
      isPaused={isPaused}
      onAction={onAction}
    />
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
        loading={loading || false}
        error={!!error}
      >
        {body}
      </GridTile>
    )
  );
};

export default QuickActions;
