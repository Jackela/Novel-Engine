import React from 'react';
import { Box, Stack, Typography, Chip, IconButton, Badge } from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Notifications as NotificationsIcon,
  Person as PersonIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  AccessTime as TimeIcon
} from '@mui/icons-material';

interface CommandTopBarProps {
  pipelineStatus: 'idle' | 'running' | 'paused' | 'stopped';
  isOnline: boolean;
  isLive: boolean;
  lastUpdate: Date;
}

const TopBarContainer = styled(Box)(({ theme: _theme }) => ({
  position: 'sticky',
  top: 0,
  zIndex: 1100,
  width: '100%',
  height: 'var(--header-height)',
  backgroundColor: 'rgba(14, 15, 17, 0.95)', // var(--color-bg-base) with opacity
  backdropFilter: 'blur(12px)',
  borderBottom: '1px solid var(--color-border)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 24px',
  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
}));

const BrandText = styled(Typography)(({ theme: _theme }) => ({
  fontFamily: 'var(--font-header)',
  fontSize: '16px',
  fontWeight: 700,
  letterSpacing: '0.15em',
  color: 'var(--color-text-primary)',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  '&::before': {
    content: '""',
    display: 'block',
    width: '4px',
    height: '16px',
    backgroundColor: 'var(--color-accent-primary)',
    boxShadow: '0 0 8px var(--color-accent-primary)',
  }
}));

const StatusChip = styled(Chip)<{ status: string }>(({ status }) => ({
  height: 24,
  fontFamily: 'var(--font-header)',
  fontSize: '11px',
  fontWeight: 700,
  letterSpacing: '0.05em',
  borderRadius: 4,
  backgroundColor: status === 'active' ? 'rgba(0, 255, 198, 0.1)' : 'rgba(255, 255, 255, 0.05)',
  border: `1px solid ${status === 'active' ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
  color: status === 'active' ? 'var(--color-accent-primary)' : 'var(--color-text-dim)',
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
    <TopBarContainer>
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
          <TimeIcon sx={{ fontSize: 16, color: 'var(--color-text-dim)' }} />
          <Typography variant="caption" className="text-mono" sx={{ color: 'var(--color-text-secondary)' }}>
            SYNC: {lastUpdate.toLocaleTimeString()}
          </Typography>
        </Stack>

        {/* Connection Icon */}
        {isOnline ? (
          <WifiIcon sx={{ fontSize: 18, color: 'var(--color-accent-primary)' }} />
        ) : (
          <WifiOffIcon sx={{ fontSize: 18, color: 'var(--color-accent-error)' }} />
        )}

        {/* Notifications */}
        <IconButton size="small" sx={{ color: 'var(--color-text-secondary)' }}>
          <Badge badgeContent={3} color="error" sx={{ '& .MuiBadge-badge': { fontSize: 9, height: 14, minWidth: 14 } }}>
            <NotificationsIcon fontSize="small" />
          </Badge>
        </IconButton>

        {/* Profile */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ borderLeft: '1px solid var(--color-border)', pl: 3 }}>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="caption" display="block" sx={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>
              COMMANDER
            </Typography>
            <Typography variant="caption" display="block" sx={{ fontSize: 9, color: 'var(--color-text-dim)' }}>
              LEVEL 5 ACCESS
            </Typography>
          </Box>
          <Box 
            sx={{ 
              width: 32, 
              height: 32, 
              borderRadius: 4, 
              bgcolor: 'var(--color-bg-panel)', 
              border: '1px solid var(--color-border)',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}
          >
            <PersonIcon sx={{ fontSize: 18, color: 'var(--color-text-secondary)' }} />
          </Box>
        </Stack>
      </Stack>
    </TopBarContainer>
  );
};

export default CommandTopBar;
