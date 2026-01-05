import React, { useState } from 'react';
import { Box, IconButton, useTheme, useMediaQuery } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import Sidebar from './Sidebar';
import { tokens } from '@/styles/tokens';

interface CommandLayoutProps {
  children?: React.ReactNode;
}

const CommandLayout: React.FC<CommandLayoutProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: 'background.default',
        color: 'text.primary',
        display: 'flex',
        flexDirection: 'row',
        overflow: 'hidden' 
      }}
      className={isMobile ? 'dashboard-layout dashboard-layout--mobile' : 'dashboard-layout'}
      data-testid="dashboard-layout"
    >
      {/* Mobile Menu Button - Floating */}
      {isMobile && (
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={handleDrawerToggle}
          data-testid="mobile-menu-toggle"
          sx={{
            position: 'fixed',
            left: 16,
            bottom: 16, // Bottom left thumb-friendly
            zIndex: 1300,
            bgcolor: tokens.colors.primary[500],
            color: tokens.colors.text.inverse,
            boxShadow: tokens.elevation.md,
            '&:hover': { bgcolor: tokens.colors.primary[600] }
          }}
        >
          <MenuIcon />
        </IconButton>
      )}

      {/* Global Sidebar */}
      <Sidebar 
        mobileOpen={mobileOpen} 
        onMobileClose={() => setMobileOpen(false)} 
      />

      {/* Main Content Area */}
      <Box 
        component="main" 
        id="main-content" 
        sx={{ 
          flex: 1, 
          position: 'relative', 
          width: '100%', 
          height: '100vh',
          marginLeft: isMobile ? 0 : '80px', // Matches collapsed sidebar width (0 on mobile)
          transition: 'margin-left 0.3s ease',
          overflowY: 'auto',
          scrollBehavior: 'smooth',
          // Custom scrollbar
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: tokens.colors.border.tertiary,
            borderRadius: '4px',
            '&:hover': {
              background: tokens.colors.primary[700],
            },
          },
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default CommandLayout;
