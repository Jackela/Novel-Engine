import React from 'react';
import { Box } from '@mui/material';
import Sidebar from './Sidebar';
import { tokens } from '@/styles/tokens';

interface CommandLayoutProps {
  children?: React.ReactNode;
}

const CommandLayout: React.FC<CommandLayoutProps> = ({ children }) => {
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
      data-testid="dashboard-layout"
    >
      {/* Global Sidebar (VisionOS Style) */}
      <Sidebar />

      {/* Main Content Area */}
      <Box 
        component="main" 
        id="main-content" 
        sx={{ 
          flex: 1, 
          position: 'relative', 
          width: '100%', 
          height: '100vh',
          marginLeft: '80px', // Matches collapsed sidebar width
          transition: 'margin-left 0.3s ease', // Smooth transition if we ever push content
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