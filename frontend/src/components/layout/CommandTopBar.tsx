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
  ...tokens.glass.main,
  borderBottom: tokens.glass.border,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 24px',
  marginBottom: '24px',
}));

const BrandText = styled(Typography)(() => ({
  fontFamily: tokens.typography.mono,
  fontSize: '14px',
  fontWeight: 700,
  letterSpacing: '0.15em',
  color: tokens.colors.text.primary,
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  '&::before': {
    content: '""',
    display: 'block',
    width: '3px',
    height: '14px',
    backgroundColor: tokens.colors.primary[500],
    boxShadow: tokens.elevation.glow,
  }
}));

const StatusChip = styled(Chip)<{ status: string }>(({ status }) => ({
  height: 24,
  fontFamily: tokens.typography.mono,
  fontSize: '10px',
  fontWeight: 700,
  letterSpacing: '0.05em',
  borderRadius: 4,
  backgroundColor: status === 'active' ? tokens.colors.status.success.bg : 'rgba(255, 255, 255, 0.05)',
  border: `1px solid ${status === 'active' ? tokens.colors.status.success.border : 'rgba(255, 255, 255, 0.1)'}`,
  color: status === 'active' ? tokens.colors.status.success.main : tokens.colors.text.tertiary,
  '& .MuiChip-label': {
    padding: '0 8px',
  },
}));

const CommandTopBar: React.FC<CommandTopBarProps> = ({
  pipelineStatus,
  isOnline,
  isLive: _isLive,
  lastUpdate,
}) => {
  return (
    <TopBarContainer component="header">
      {/* LEFT: Brand & System Identity */}
      <Stack direction="row" spacing={3} alignItems="center">
        <BrandText variant="h6">
          MERIDIAN STATION <span style={{ opacity: 0.4 }}>//</span> COMMAND DECK
        </BrandText>

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
        </Stack>
      </Stack>

      {/* RIGHT: Utilities & User */}
      <Stack direction="row" spacing={3} alignItems="center">
        {/* Time / Sync */}
        <Stack direction="row" spacing={1} alignItems="center">
          <TimeIcon sx={{ fontSize: 16, color: tokens.colors.text.tertiary }} />
          <Typography variant="caption" sx={{ fontFamily: tokens.typography.mono, color: tokens.colors.text.secondary }}>
            SYNC: {lastUpdate.toLocaleTimeString()}
          </Typography>
        </Stack>

        {/* Connection Icon */}
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

        {/* Notifications */}
        <IconButton size="small" sx={{ color: tokens.colors.text.secondary }}>
          <Badge badgeContent={3} color="error" sx={{ '& .MuiBadge-badge': { fontSize: 9, height: 14, minWidth: 14 } }}>
            <NotificationsIcon fontSize="small" />
          </Badge>
        </IconButton>

        {/* Profile */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ borderLeft: `1px solid ${tokens.colors.border.secondary}`, pl: 3 }}>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="caption" display="block" sx={{ fontWeight: 700, color: tokens.colors.text.primary }}>
              COMMANDER
            </Typography>
            <Typography variant="caption" display="block" sx={{ fontSize: 9, color: tokens.colors.text.tertiary }}>
              LEVEL 5 ACCESS
            </Typography>
          </Box>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 4,
              bgcolor: 'rgba(255, 255, 255, 0.1)',
              border: `1px solid ${tokens.colors.border.primary}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <PersonIcon sx={{ fontSize: 18, color: tokens.colors.text.secondary }} />
          </Box>
        </Stack>
      </Stack>
    </TopBarContainer>
  );
};

export default CommandTopBar;