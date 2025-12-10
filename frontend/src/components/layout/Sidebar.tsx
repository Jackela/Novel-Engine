import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Box, 
  IconButton, 
  Tooltip, 
  Stack, 
  Typography, 
  useTheme,
  Drawer,
  useMediaQuery,
  ButtonBase
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  AutoFixHigh as WorkshopIcon,
  LibraryBooks as LibraryIcon,
  MonitorHeart as MonitorIcon,
  Settings as SettingsIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';
import { tokens } from '@/styles/tokens';
import { motion, AnimatePresence } from 'framer-motion';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
  { path: '/characters', label: 'Operatives', icon: <PeopleIcon /> },
  { path: '/workshop', label: 'Workshop', icon: <WorkshopIcon /> },
  { path: '/library', label: 'Archives', icon: <LibraryIcon /> },
  { path: '/monitor', label: 'System', icon: <MonitorIcon /> },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onMobileClose }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(false);
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleNavigate = (path: string) => {
    navigate(path);
    if (isMobile && onMobileClose) {
      onMobileClose();
    }
  };

  const SidebarContent = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        ...(isMobile ? { bgcolor: tokens.colors.background.paper } : tokens.glass.main),
        borderRight: isMobile ? 'none' : tokens.glass.border,
      }}
    >
      {/* Logo Area */}
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', height: 80 }}>
        <Box
          component={motion.div}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          sx={{
            width: 48,
            height: 48,
            borderRadius: 3,
            background: tokens.gradients.primary,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: tokens.elevation.glow,
            cursor: 'pointer'
          }}
          onClick={() => !isMobile && setIsExpanded(!isExpanded)}
        >
          <Typography variant="h6" fontWeight="bold" color="white">NE</Typography>
        </Box>
      </Box>

      {/* Navigation Items */}
      <Stack spacing={1} sx={{ px: 2, mt: 4, flex: 1 }} role="navigation" aria-label="Main Navigation">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Tooltip key={item.path} title={isExpanded && !isMobile ? '' : item.label} placement="right">
              <ButtonBase
                onClick={() => handleNavigate(item.path)}
                sx={{
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  width: '100%',
                  height: 48,
                  borderRadius: 2,
                  px: 1.5,
                  color: isActive ? tokens.colors.primary[400] : tokens.colors.text.secondary,
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    color: tokens.colors.text.primary,
                  }
                }}
              >
                {isActive && (
                  <Box
                    component={motion.div}
                    layoutId="activePill"
                    sx={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: 3,
                      backgroundColor: tokens.colors.primary[500],
                      boxShadow: tokens.elevation.glow,
                    }}
                  />
                )}
                
                <Box sx={{ minWidth: 24, display: 'flex', justifyContent: 'center' }}>
                  {item.icon}
                </Box>

                <AnimatePresence>
                  {(isExpanded || isMobile) && (
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      style={{ marginLeft: 16, whiteSpace: 'nowrap', fontWeight: isActive ? 600 : 400 }}
                    >
                      {item.label}
                    </motion.div>
                  )}
                </AnimatePresence>
              </ButtonBase>
            </Tooltip>
          );
        })}
      </Stack>

      {/* Bottom Actions */}
      <Box sx={{ p: 2, borderTop: isMobile ? `1px solid ${tokens.colors.border.primary}` : tokens.glass.border }}>
        <Stack spacing={1}>
           <Tooltip title={isExpanded ? '' : 'Settings'} placement="right">
            <IconButton sx={{ color: tokens.colors.text.secondary }}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={isExpanded ? '' : 'Logout'} placement="right">
            <IconButton sx={{ color: tokens.colors.text.secondary }}>
               <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

       {/* Toggle Button (Desktop Only) */}
       {!isMobile && (
         <IconButton
          onClick={() => setIsExpanded(!isExpanded)}
          sx={{
            position: 'absolute',
            right: -12,
            top: '50%',
            transform: 'translateY(-50%)',
            width: 24,
            height: 24,
            bgcolor: tokens.colors.background.paper,
            border: `1px solid ${tokens.colors.border.primary}`,
            zIndex: 1300,
            '&:hover': { bgcolor: tokens.colors.primary[900] }
          }}
          aria-label={isExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
         >
           {isExpanded ? <ChevronLeftIcon sx={{ fontSize: 16 }} /> : <ChevronRightIcon sx={{ fontSize: 16 }} />}
         </IconButton>
       )}

    </Box>
  );

  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          '& .MuiDrawer-paper': { 
            width: 240, 
            boxSizing: 'border-box',
            bgcolor: tokens.colors.background.default,
            borderRight: `1px solid ${tokens.colors.border.primary}`
          },
        }}
      >
        {SidebarContent}
      </Drawer>
    );
  }

  return (
    <Box
      component={motion.div}
      initial={{ width: 80 }}
      animate={{ width: isExpanded ? 240 : 80 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      sx={{
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 1200,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {SidebarContent}
    </Box>
  );
};

export default Sidebar;