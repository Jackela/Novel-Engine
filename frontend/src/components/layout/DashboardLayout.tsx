import React from 'react';
import { Box, AppBar, Toolbar, Typography, Container } from '@mui/material';
import { styled } from '@mui/material/styles';
import BentoGrid from './BentoGrid';

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  position: 'sticky',
  top: 0,
  zIndex: theme.zIndex.appBar,
  backgroundColor: '#111113',
  color: theme.palette.text.primary,
  borderBottom: '1px solid #2a2a30',
  boxShadow: 'none',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
}));

const MainContainer = styled(Container)(({ theme }) => ({
  maxWidth: '1400px !important',
  padding: theme.spacing(3),
  
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(2),
  },
}));

interface DashboardLayoutProps {
  children?: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  return (
    <Box 
      component="div"
      data-testid="dashboard-layout"
      sx={{ minHeight: '100vh', bgcolor: 'background.default' }}
    >
      <StyledAppBar component="header" role="banner">
        <Toolbar>
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            Emergent Narrative Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Novel Engine M1
          </Typography>
        </Toolbar>
      </StyledAppBar>
      
      <MainContainer component="main" role="main">
        <BentoGrid>
          {children}
        </BentoGrid>
      </MainContainer>
    </Box>
  );
};

export default DashboardLayout;