import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Chip,
  Tooltip,
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
import api from '../services/api';

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

  const navItems = [
    {
      path: '/',
      label: 'Dashboard',
      icon: <HomeIcon />,
      color: 'primary' as const,
    },
    {
      path: '/characters',
      label: 'Characters',
      icon: <PersonIcon />,
      color: 'secondary' as const,
    },
    {
      path: '/workshop',
      label: 'Workshop',
      icon: <CreateIcon />,
      color: 'info' as const,
    },
    {
      path: '/library',
      label: 'Library',
      icon: <LibraryIcon />,
      color: 'success' as const,
    },
    {
      path: '/monitor',
      label: 'Monitor',
      icon: <MonitorIcon />,
      color: 'warning' as const,
    },
  ];

  const getHealthColor = () => {
    if (statusLoading) return 'default';
    if (!systemStatus) return 'error';
    
    switch (systemStatus.api) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      default:
        return 'error';
    }
  };

  const getHealthLabel = () => {
    if (statusLoading) return 'Checking...';
    if (!systemStatus) return 'Offline';
    
    switch (systemStatus.api) {
      case 'healthy':
        return 'Healthy';
      case 'degraded':
        return 'Degraded';
      default:
        return 'Error';
    }
  };

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{ 
        backgroundColor: '#111113',
        borderBottom: '1px solid #2a2a30',
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        {/* Logo and Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 700,
              fontSize: '1.2rem',
              boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
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

        {/* Navigation Items */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            
            return (
              <Button
                key={item.path}
                onClick={() => navigate(item.path)}
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
                      : 'rgba(99, 102, 241, 0.1)',
                  },
                }}
              >
                {item.label}
              </Button>
            );
          })}
        </Box>

        {/* Status and Actions */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* System Health Status */}
          <Tooltip title={`System Status: ${getHealthLabel()}`}>
            <Chip
              label={getHealthLabel()}
              color={getHealthColor()}
              size="small"
              variant="outlined"
              sx={{ fontWeight: 600 }}
            />
          </Tooltip>

          {/* System Version */}
          <Chip
            label={`v${systemStatus?.version || '1.0.0'}`}
            size="small"
            variant="outlined"
            sx={{ 
              fontFamily: 'monospace',
              fontWeight: 600,
            }}
          />

          {/* Settings Icon */}
          <Tooltip title="Settings">
            <IconButton
              color="inherit"
              onClick={() => {
                // Future: Open settings dialog
                console.log('Settings clicked');
              }}
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;