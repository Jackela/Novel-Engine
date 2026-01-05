import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { logger } from '@/services/logging/LoggerFactory';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Chip,
  Tooltip,
  useTheme,
} from '@mui/material';
import {
  Home as HomeIcon,
  Person as PersonIcon,
  Create as CreateIcon,
  LibraryBooks as LibraryIcon,
  Monitor as MonitorIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import api from '@/services/api';

type NavItem = {
  path: string;
  label: string;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'info' | 'success' | 'warning';
};

const NAV_ITEMS: NavItem[] = [
  {
    path: '/',
    label: 'Dashboard',
    icon: <HomeIcon />,
    color: 'primary',
  },
  {
    path: '/characters',
    label: 'Characters',
    icon: <PersonIcon />,
    color: 'secondary',
  },
  {
    path: '/workshop',
    label: 'Workshop',
    icon: <CreateIcon />,
    color: 'info',
  },
  {
    path: '/library',
    label: 'Library',
    icon: <LibraryIcon />,
    color: 'success',
  },
  {
    path: '/monitor',
    label: 'Monitor',
    icon: <MonitorIcon />,
    color: 'warning',
  },
];

const LogoBlock: React.FC = () => {
  const theme = useTheme();
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box
        sx={{
          width: 40,
          height: 40,
          borderRadius: 2,
          background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 700,
          fontSize: '1.2rem',
          boxShadow: theme.shadows[4],
        }}
      >
        NE
      </Box>
      <Box>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
          Novel Engine
        </Typography>
        <Typography variant="caption" color="text.secondary">
          AI-Powered Story Creation Platform
        </Typography>
      </Box>
    </Box>
  );
};

const NavButtons: React.FC<{
  items: NavItem[];
  activePath: string;
  onNavigate: (path: string) => void;
}> = ({ items, activePath, onNavigate }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    {items.map((item) => {
      const isActive = activePath === item.path;

      return (
        <Button
          key={item.path}
          onClick={() => onNavigate(item.path)}
          startIcon={item.icon}
          variant={isActive ? 'contained' : 'text'}
          color={isActive ? item.color : 'inherit'}
          sx={{
            minWidth: 120,
            fontWeight: isActive ? 600 : 400,
            transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              transform: isActive ? 'none' : 'translateY(-2px)',
              backgroundColor: isActive
                ? undefined
                : 'primary.main',
            },
          }}
        >
          {item.label}
        </Button>
      );
    })}
  </Box>
);

const StatusActions: React.FC<{
  isLoading: boolean;
  status: { api?: string; version?: string } | undefined;
}> = ({ isLoading, status }) => {
  const getHealthColor = () => {
    if (isLoading) return 'default';
    if (!status) return 'error';

    switch (status.api) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      default:
        return 'error';
    }
  };

  const getHealthLabel = () => {
    if (isLoading) return 'Checking...';
    if (!status) return 'Offline';

    switch (status.api) {
      case 'healthy':
        return 'Healthy';
      case 'degraded':
        return 'Degraded';
      default:
        return 'Error';
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Tooltip title={`System Status: ${getHealthLabel()}`}>
        <Chip
          label={getHealthLabel()}
          color={getHealthColor()}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 600 }}
        />
      </Tooltip>

      <Chip
        label={`v${status?.version || '1.0.0'}`}
        size="small"
        variant="outlined"
        sx={{
          fontFamily: 'monospace',
          fontWeight: 600,
        }}
      />

      <Tooltip title="Settings">
        <IconButton
          color="inherit"
          onClick={() => {
            // Future: Open settings dialog
            logger.info('Settings clicked');
          }}
          aria-label="Open settings"
        >
          <SettingsIcon />
        </IconButton>
      </Tooltip>
    </Box>
  );
};

const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Fetch system status for health indicator
  const { data: systemStatus, isLoading: statusLoading } = useQuery(
    'system-status',
    api.getHealth,
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: false,
    }
  );

  const theme = useTheme();

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: theme.palette.background.paper,
        borderBottom: `1px solid ${theme.palette.divider}`,
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        {/* Logo and Title */}
        <LogoBlock />

        {/* Navigation Items */}
        <NavButtons
          items={NAV_ITEMS}
          activePath={location.pathname}
          onNavigate={navigate}
        />

        {/* Status and Actions */}
        <StatusActions isLoading={statusLoading} status={systemStatus} />
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
