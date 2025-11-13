import React from 'react';
import { Box, Container, Stack, Typography, Button, Chip, Divider } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import LiveTvIcon from '@mui/icons-material/LiveTv';
import InsightsIcon from '@mui/icons-material/Insights';
import SecurityIcon from '@mui/icons-material/Security';
import { useAuthContext } from '../contexts/AuthContext';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isGuest, enterGuestMode } = useAuthContext();

  const handleDemoClick = () => {
    if (!isAuthenticated || !isGuest) {
      enterGuestMode();
    }
    navigate('/dashboard', { replace: true });
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: (theme) =>
          `radial-gradient(circle at top, ${theme.palette.primary.light}1A, transparent 40%), ${theme.palette.background.default}`,
        display: 'flex',
        alignItems: 'center',
        color: 'text.primary',
      }}
    >
      <Container
        component="main"
        id="main-content"
        maxWidth="md"
        sx={{ py: { xs: 6, md: 10 } }}
      >
        <Stack spacing={5}>
          <Stack spacing={2} textAlign="center">
            <Chip label="Novel Engine" color="primary" variant="outlined" sx={{ alignSelf: 'center' }} />
            <Typography variant="h3" component="h1" fontWeight={700}>
              Explore the Emergent Narrative Dashboard
            </Typography>
            <Typography variant="h6" color="text.secondary">
              Monitor characters, orchestrate turns, and watch sci-fi storylines evolve across Meridian Station—all from one adaptive control surface.
            </Typography>
          </Stack>

          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            justifyContent="center"
            data-testid="cta-container"
          >
            <Button
              variant="contained"
              size="large"
              color="primary"
              startIcon={<RocketLaunchIcon />}
              onClick={handleDemoClick}
              data-testid="cta-demo"
            >
              {isAuthenticated && isGuest ? 'Continue to Demo' : 'View Demo'}
            </Button>
            <Button
              variant="outlined"
              size="large"
              color="inherit"
              startIcon={<SecurityIcon />}
              component="a"
              href="mailto:ops@novel-engine.ai?subject=Novel%20Engine%20Access"
              data-testid="cta-request-access"
            >
              Request Access
            </Button>
          </Stack>

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} divider={<Divider flexItem orientation="vertical" />}> 
            <Stack spacing={1} direction="row" alignItems="center">
              <LiveTvIcon color="primary" />
              <Typography variant="body1">Live turn orchestration feed</Typography>
            </Stack>
            <Stack spacing={1} direction="row" alignItems="center">
              <InsightsIcon color="primary" />
              <Typography variant="body1">Adaptive sci-fi analytics</Typography>
            </Stack>
            <Stack spacing={1} direction="row" alignItems="center">
              <SecurityIcon color="primary" />
              <Typography variant="body1">Air-gapped demo dataset</Typography>
            </Stack>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
};

export default LandingPage;
