import React from 'react';
import { Box, Stack, Typography, Chip, IconButton, Badge } from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Notifications as NotificationsIcon,
  Person as PersonIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import { tokens } from '@/styles/tokens';
import { useAuthContext } from '@/contexts/useAuthContext';

interface CommandTopBarProps {
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  isOnline: boolean;
  isLive: boolean;
  lastUpdate: Date;
}

const TopBarContainer = styled(Box)(() => ({
  position: 'sticky',
  top: 0,
  zIndex: 1100,
  width: '100%',
  height: '64px',
  backgroundColor: tokens.colors.background.paper,
  borderBottom: `1px solid ${tokens.colors.border.primary}`,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 24px',
  marginBottom: '20px',
}));

const BrandText = styled(Typography)(() => ({
  fontFamily: tokens.typography.headingFamily,
  fontSize: '16px',
  fontWeight: 600,
  letterSpacing: '0.04em',
  color: tokens.colors.text.primary,
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
}));

const StatusChip = styled(Chip)<{ status: string }>(({ status }) => ({
  height: 26,
  fontFamily: tokens.typography.mono,
  fontSize: '10px',
  fontWeight: 700,
  letterSpacing: '0.06em',
  borderRadius: 999,
  backgroundColor: status === 'active' ? tokens.colors.status.success.bg : tokens.colors.background.interactive,
  border: `1px solid ${status === 'active' ? tokens.colors.status.success.border : tokens.colors.border.primary}`,
  color: status === 'active' ? tokens.colors.status.success.text : tokens.colors.text.secondary,
  '& .MuiChip-label': {
    padding: '0 8px',
  },
}));

const StatusChips: React.FC<{
  pipelineStatus: CommandTopBarProps['pipelineStatus'];
  isOnline: boolean;
  isGuest: boolean;
  workspaceLabel: string;
}> = ({ pipelineStatus, isOnline, isGuest, workspaceLabel }) => (
  <Stack direction="row" spacing={1}>
    <StatusChip
      label={isOnline ? 'SYSTEM ONLINE' : 'OFFLINE'}
      status={isOnline ? 'active' : 'inactive'}
      size="small"
    />
    <StatusChip
      label={`RUN STATE: ${pipelineStatus.toUpperCase()}`}
      status={pipelineStatus === 'running' ? 'active' : 'inactive'}
      size="small"
    />
    <StatusChip
      label={`HEALTH: ${isOnline ? 'OK' : 'DEGRADED'}`}
      status={isOnline ? 'active' : 'inactive'}
      size="small"
      data-testid="system-health"
    />
    {isGuest && (
      <StatusChip
        label={workspaceLabel}
        status="active"
        size="small"
        data-testid="guest-mode-chip"
      />
    )}
  </Stack>
);

const SyncClock: React.FC<{ lastUpdate: Date }> = ({ lastUpdate }) => (
  <Stack direction="row" spacing={1} alignItems="center">
    <TimeIcon sx={{ fontSize: 16, color: tokens.colors.text.tertiary }} />
    <Typography variant="caption" sx={{ fontFamily: tokens.typography.mono, color: tokens.colors.text.secondary }}>
      SYNC: {lastUpdate.toLocaleTimeString()}
    </Typography>
  </Stack>
);

const ConnectionIndicator: React.FC<{ isOnline: boolean }> = ({ isOnline }) => (
  <Box 
    data-testid="connection-status" 
    data-status={isOnline ? 'online' : 'offline'}
    display="flex" 
    alignItems="center"
  >
    {isOnline ? (
      <WifiIcon sx={{ fontSize: 18, color: tokens.colors.primary[500] }} />
    ) : (
      <WifiOffIcon sx={{ fontSize: 18, color: tokens.colors.status.error.main }} />
    )}
  </Box>
);

const NotificationsButton: React.FC = () => (
  <IconButton size="small" sx={{ color: tokens.colors.text.secondary }}>
    <Badge badgeContent={3} color="error" sx={{ '& .MuiBadge-badge': { fontSize: 9, height: 14, minWidth: 14 } }}>
      <NotificationsIcon fontSize="small" />
    </Badge>
  </IconButton>
);

const ProfileBlock: React.FC<{ isGuest: boolean; workspaceLabel: string }> = ({ isGuest, workspaceLabel }) => (
  <Stack direction="row" spacing={1} alignItems="center" sx={{ borderLeft: `1px solid ${tokens.colors.border.primary}`, pl: 3 }}>
    <Box sx={{ textAlign: 'right' }}>
      <Typography variant="caption" display="block" sx={{ fontWeight: 700, color: tokens.colors.text.primary }}>
        {isGuest ? 'GUEST' : 'COMMANDER'}
      </Typography>
      <Typography variant="caption" display="block" sx={{ fontSize: 9, color: tokens.colors.text.tertiary }}>
        {isGuest ? workspaceLabel : 'LEVEL 5 ACCESS'}
      </Typography>
    </Box>
    <Box
      sx={{
        width: 32,
        height: 32,
        borderRadius: 999,
        bgcolor: tokens.colors.background.interactive,
        border: `1px solid ${tokens.colors.border.primary}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <PersonIcon sx={{ fontSize: 18, color: tokens.colors.text.secondary }} />
    </Box>
  </Stack>
);

const CommandTopBar: React.FC<CommandTopBarProps> = ({
  pipelineStatus,
  isOnline,
  isLive: _isLive,
  lastUpdate,
}) => {
  const { isGuest, workspaceId } = useAuthContext();
  const workspaceLabel = workspaceId ? `WS: ${workspaceId}` : 'GUEST SESSION';

  return (
    <TopBarContainer component="header">
      {/* LEFT: Brand & System Identity */}
      <Stack direction="row" spacing={2.5} alignItems="center">
        <BrandText variant="h6">
          Novel Engine
          <span style={{ color: tokens.colors.text.tertiary }}>Console</span>
        </BrandText>

        <StatusChips
          pipelineStatus={pipelineStatus}
          isOnline={isOnline}
          isGuest={isGuest}
          workspaceLabel={workspaceLabel}
        />
      </Stack>

      {/* RIGHT: Utilities & User */}
      <Stack direction="row" spacing={2.5} alignItems="center">
        {/* Time / Sync */}
        <SyncClock lastUpdate={lastUpdate} />

        {/* Connection Icon */}
        <ConnectionIndicator isOnline={isOnline} />

        {/* Notifications */}
        <NotificationsButton />

        {/* Profile */}
        <ProfileBlock isGuest={isGuest} workspaceLabel={workspaceLabel} />
      </Stack>
    </TopBarContainer>
  );
};

export default CommandTopBar;
