import React, { useMemo, useState } from 'react';
import { Box, AppBar, Toolbar, Typography, Container, Chip, Tooltip, Alert, Button, Collapse } from '@mui/material';
import { styled } from '@mui/material/styles';
import BentoGrid from './BentoGrid';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useAuthContext } from '@/contexts/AuthContext';

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  position: 'sticky',
  top: 0,
  zIndex: theme.zIndex.appBar,
  backgroundColor: theme.palette.background.paper,
  color: theme.palette.text.primary,
  borderBottom: `1px solid ${theme.palette.divider}`,
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

const GUEST_BANNER_KEY = 'novel-engine-guest-banner-dismissed';

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const { isGuest, workspaceId } = useAuthContext();
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    try {
      // Use localStorage for persistent preference across sessions
      return window.localStorage.getItem(GUEST_BANNER_KEY) === '1';
    } catch {
      return false;
    }
  });

  const handleDismissBanner = () => {
    if (typeof window !== 'undefined') {
      try {
        // Use localStorage for persistent preference across sessions
        window.localStorage.setItem(GUEST_BANNER_KEY, '1');
      } catch {
        // ignore storage errors
      }
    }
    setBannerDismissed(true);
  };

  const guestBannerVisible = useMemo(() => isGuest && !bannerDismissed, [isGuest, bannerDismissed]);

  return (
    <Box
      component="div"
      data-testid="dashboard-layout"
      sx={{ minHeight: '100vh', bgcolor: 'background.default' }}
    >
      <StyledAppBar data-testid="header-navigation" role="banner">
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            Emergent Narrative Dashboard
          </Typography>
          {isGuest && (
            <Tooltip title={workspaceId ? `Guest workspace: ${workspaceId}` : 'Guest session active'}>
              <Chip
                label="Guest Mode"
                color="warning"
                size="small"
                icon={<InfoOutlinedIcon fontSize="small" />}
                data-testid="guest-mode-chip"
              />
            </Tooltip>
          )}
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
            Novel Engine M1
          </Typography>
        </Toolbar>
      </StyledAppBar>

      {guestBannerVisible && (
        <Box px={{ xs: 2, md: 4 }} pt={2}>
          <Collapse in={guestBannerVisible}>
            <Alert
              severity="info"
              variant="outlined"
              action={
                <Button color="inherit" size="small" onClick={handleDismissBanner}>
                  Dismiss
                </Button>
              }
              data-testid="guest-mode-banner"
            >
              You&apos;re in guest mode. Your workspace is persisted and should survive refreshes in this browser session.
            </Alert>
          </Collapse>
        </Box>
      )}

      <MainContainer role="main" id="main-content" tabIndex={-1}>
        <BentoGrid>
          {children}
        </BentoGrid>
      </MainContainer>
    </Box>
  );
};

export default DashboardLayout;
