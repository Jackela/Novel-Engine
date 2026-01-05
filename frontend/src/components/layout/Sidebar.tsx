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

type NavItem = {
  path: string;
  label: string;
  icon: React.ReactNode;
};

const SidebarLogo: React.FC<{
  isMobile: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ isMobile, isExpanded, onToggle }) => (
  <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', height: 80 }}>
    <Box
      component={motion.div}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      sx={{
        width: 48,
        height: 48,
        borderRadius: '50%',
        backgroundColor: tokens.colors.background.interactive,
        border: `1px solid ${tokens.colors.border.primary}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer'
      }}
      onClick={() => !isMobile && onToggle()}
      aria-label={isExpanded ? 'Collapse Sidebar' : 'Expand Sidebar'}
    >
      <Typography variant="subtitle1" fontWeight={600} color={tokens.colors.text.primary}>NE</Typography>
    </Box>
  </Box>
);

const NavList: React.FC<{
  items: NavItem[];
  activePath: string;
  isExpanded: boolean;
  isMobile: boolean;
  onNavigate: (path: string) => void;
}> = ({ items, activePath, isExpanded, isMobile, onNavigate }) => (
  <Stack spacing={1} sx={{ px: 2, mt: 4, flex: 1 }} role="navigation" aria-label="Main Navigation" data-testid="sidebar-navigation">
    {items.map((item) => {
      const isActive = activePath === item.path;
      return (
        <Tooltip key={item.path} title={isExpanded && !isMobile ? '' : item.label} placement="right">
          <ButtonBase
            onClick={() => onNavigate(item.path)}
            aria-label={item.label}
            sx={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              width: '100%',
              height: 48,
              borderRadius: 2,
              px: 1.5,
              color: isActive ? tokens.colors.primary[500] : tokens.colors.text.secondary,
              transition: 'all 0.2s',
              '&:hover': {
                backgroundColor: tokens.colors.background.interactive,
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
                  width: 2,
                  backgroundColor: tokens.colors.primary[500],
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
);

const SidebarActions: React.FC<{ isExpanded: boolean }> = ({ isExpanded }) => (
  <Box sx={{ p: 2, borderTop: `1px solid ${tokens.colors.border.primary}` }}>
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
);

const SidebarToggle: React.FC<{
  isExpanded: boolean;
  isMobile: boolean;
  onToggle: () => void;
}> = ({ isExpanded, isMobile, onToggle }) => {
  if (isMobile) return null;
  return (
    <IconButton
      onClick={onToggle}
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
        '&:hover': { bgcolor: tokens.colors.background.interactive }
      }}
      aria-label={isExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
    >
      {isExpanded ? <ChevronLeftIcon sx={{ fontSize: 16 }} /> : <ChevronRightIcon sx={{ fontSize: 16 }} />}
    </IconButton>
  );
};

const SidebarContent: React.FC<{
  isMobile: boolean;
  isExpanded: boolean;
  activePath: string;
  onNavigate: (path: string) => void;
  onToggle: () => void;
}> = ({ isMobile, isExpanded, activePath, onNavigate, onToggle }) => (
  <Box
    sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: tokens.colors.background.paper,
      borderRight: isMobile ? 'none' : `1px solid ${tokens.colors.border.primary}`,
    }}
  >
    <SidebarLogo isMobile={isMobile} isExpanded={isExpanded} onToggle={onToggle} />
    <NavList
      items={NAV_ITEMS}
      activePath={activePath}
      isExpanded={isExpanded}
      isMobile={isMobile}
      onNavigate={onNavigate}
    />
    <SidebarActions isExpanded={isExpanded} />
    <SidebarToggle isExpanded={isExpanded} isMobile={isMobile} onToggle={onToggle} />
  </Box>
);

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

  const sidebarContent = (
    <SidebarContent
      isMobile={isMobile}
      isExpanded={isExpanded}
      activePath={location.pathname}
      onNavigate={handleNavigate}
      onToggle={() => setIsExpanded(!isExpanded)}
    />
  );

  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        PaperProps={{ 'data-testid': 'sidebar-drawer' }}
        sx={{
          '& .MuiDrawer-paper': {
            width: 240,
            boxSizing: 'border-box',
            bgcolor: tokens.colors.background.default,
            borderRight: `1px solid ${tokens.colors.border.primary}`
          },
        }}
      >
        {sidebarContent}
      </Drawer>
    );
  }

  return (
    <Box
      component={motion.div}
      initial={{ width: 80 }}
      animate={{ width: isExpanded ? 240 : 80 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      data-testid="sidebar-desktop"
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
      {sidebarContent}
    </Box>
  );
};

export default Sidebar;
