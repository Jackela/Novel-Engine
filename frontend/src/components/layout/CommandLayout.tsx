import React, { useMemo, useState } from 'react';
import { Box, Collapse, Alert, Button, Chip, Tooltip, Stack } from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useAuthContext } from '../../contexts/AuthContext';

interface CommandLayoutProps {
  children?: React.ReactNode;
}

const GUEST_BANNER_KEY = 'novel-engine-guest-banner-dismissed';

const CommandLayout: React.FC<CommandLayoutProps> = ({ children }) => {
  const { isGuest } = useAuthContext();
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      return window.sessionStorage.getItem(GUEST_BANNER_KEY) === '1';
    } catch {
      return false;
    }
  });

  const handleDismissBanner = () => {
    if (typeof window !== 'undefined') {
      try {
        window.sessionStorage.setItem(GUEST_BANNER_KEY, '1');
      } catch {
        // ignore
      }
    }
    setBannerDismissed(true);
  };

  const guestBannerVisible = useMemo(() => isGuest && !bannerDismissed, [isGuest, bannerDismissed]);

  return (
    <Box 
      sx={{ 
        minHeight: '100vh', 
        bgcolor: 'var(--color-bg-base)',
        color: 'var(--color-text-primary)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden' // Prevent body scroll, let dashboard handle it
      }}
    >
      {/* Guest Mode Chip - visible when in guest mode */}
      {isGuest && (
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="center"
          sx={{
            position: 'absolute',
            top: 8,
            right: 16,
            zIndex: 2001
          }}
        >
          <Tooltip title="Demo mode: curated sci-fi data">
            <Chip
              label="Demo Mode"
              color="warning"
              size="small"
              icon={<InfoOutlinedIcon fontSize="small" />}
              data-testid="guest-mode-chip"
            />
          </Tooltip>
        </Stack>
      )}

      {/* Guest Banner Overlay or Top Insert */}
      {guestBannerVisible && (
        <Box sx={{ position: 'relative', zIndex: 2000, bgcolor: 'background.paper' }}>
          <Collapse in={guestBannerVisible}>
            <Alert
              severity="info"
              variant="filled"
              data-testid="guest-mode-banner"
              action={
                <Button color="inherit" size="small" onClick={handleDismissBanner}>
                  Dismiss
                </Button>
              }
              sx={{ borderRadius: 0 }}
            >
              You're in the demo shell. Actions remain simulated; data may include live API feeds.
            </Alert>
          </Collapse>
        </Box>
      )}

      {/* Main Content Area - Full Width/Height */}
      <Box sx={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
        {children}
      </Box>
    </Box>
  );
};

export default CommandLayout;
