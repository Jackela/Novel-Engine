import React from 'react';
import { Alert, Box, Container, Stack, Typography, Button, Grid, Paper, Divider } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import LiveTvIcon from '@mui/icons-material/LiveTv';
import InsightsIcon from '@mui/icons-material/Insights';
import SecurityIcon from '@mui/icons-material/Security';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import { motion } from 'framer-motion';
import { tokens } from '../styles/tokens';
import { useAuthContext } from '@/contexts/useAuthContext';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: 'easeOut' },
  },
};

const FEATURES = [
  {
    icon: <LiveTvIcon />,
    title: 'Live Orchestration',
    desc: 'Real-time control over narrative turns and character decisions.',
  },
  {
    icon: <InsightsIcon />,
    title: 'Adaptive Analytics',
    desc: 'Deep insight into plot progression and character relationships.',
  },
  {
    icon: <SecurityIcon />,
    title: 'Secure Environment',
    desc: 'Air-gapped simulation sandbox for safe narrative testing.',
  },
];

const FeatureCard: React.FC<{ icon: React.ReactElement; title: string; desc: string }> = ({
  icon,
  title,
  desc,
}) => (
  <Grid item xs={12} data-testid="feature-card">
    <Stack direction="row" spacing={2} alignItems="flex-start">
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: tokens.colors.background.interactive,
          color: tokens.colors.primary[500],
        }}
      >
        {React.cloneElement(icon, { sx: { fontSize: 18 } })}
      </Box>
      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {desc}
        </Typography>
      </Box>
    </Stack>
  </Grid>
);

const FeaturePanel: React.FC = () => (
  <motion.div variants={itemVariants}>
    <Paper
      elevation={0}
      sx={{
        p: { xs: 3, md: 4 },
        borderRadius: 4,
        border: `1px solid ${tokens.colors.border.primary}`,
        backgroundColor: tokens.colors.background.paper,
      }}
    >
      <Stack spacing={3}>
        <Stack spacing={1}>
          <Typography variant="overline" sx={{ letterSpacing: '0.2em', color: 'text.secondary' }}>
            Capabilities
          </Typography>
          <Typography variant="h6" sx={{ fontFamily: tokens.typography.headingFamily, fontWeight: 600 }}>
            Built for operators, not dashboards.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Minimal surfaces, precise hierarchy, and legible telemetry across every scale.
          </Typography>
        </Stack>

        <Divider />

        <Grid container spacing={2}>
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </Grid>
      </Stack>
    </Paper>
  </motion.div>
);

const HeroBadge: React.FC = () => (
  <motion.div variants={itemVariants}>
    <Box
      data-testid="version-chip"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 1,
        px: 2,
        py: 0.75,
        borderRadius: 99,
        border: `1px solid ${tokens.colors.border.primary}`,
        backgroundColor: tokens.colors.background.paper,
        color: 'text.secondary',
        fontWeight: 600,
        fontSize: '0.8rem',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}
    >
      <AutoStoriesIcon sx={{ fontSize: 16, color: tokens.colors.primary[500] }} />
      Novel Engine
    </Box>
  </motion.div>
);

const HeroTitle: React.FC = () => (
  <motion.div variants={itemVariants}>
    <Typography
      variant="h1"
      component="h1"
      sx={{
        fontFamily: tokens.typography.headingFamily,
        fontWeight: 600,
        fontSize: { xs: '2.8rem', sm: '3.4rem', md: '4.5rem' },
        lineHeight: 1.05,
        letterSpacing: '-0.02em',
      }}
    >
      Narrative Engine
      <Box component="span" sx={{ display: 'block', color: tokens.colors.primary[500] }}>
        calm control for complex stories.
      </Box>
    </Typography>
  </motion.div>
);

const HeroDescription: React.FC = () => (
  <motion.div variants={itemVariants}>
    <Typography
      variant="h5"
      sx={{
        color: 'text.secondary',
        maxWidth: 560,
        lineHeight: 1.6,
        fontSize: { xs: '1rem', md: '1.15rem' },
        fontWeight: 400,
      }}
    >
      Direct complex storylines across Meridian Station. Monitor character networks, guide event
      cascades, and watch your narrative evolve in real time.
    </Typography>
  </motion.div>
);

const HeroActions: React.FC<{
  isLoading: boolean;
  error: Error | null;
  enterGuestMode: () => Promise<void>;
}> = ({ isLoading, error, enterGuestMode }) => {
  const navigate = useNavigate();

  return (
    <motion.div variants={itemVariants}>
      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2, textAlign: 'left', maxWidth: 640 }}
          action={
            <Button color="inherit" size="small" onClick={() => void enterGuestMode()} disabled={isLoading}>
              Retry
            </Button>
          }
        >
          {error.message || 'Failed to connect to backend.'}
        </Alert>
      )}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
        <Button
          variant="contained"
          size="large"
          onClick={() => void enterGuestMode()}
          startIcon={<RocketLaunchIcon />}
          data-testid="cta-launch"
          disabled={isLoading}
          sx={{
            px: 4,
            py: 1.6,
            fontSize: '1rem',
            fontWeight: 600,
            borderRadius: 999,
            boxShadow: tokens.elevation.sm,
          }}
        >
          {isLoading ? 'Launching...' : 'Launch Engine'}
        </Button>
        <Button variant="text" onClick={() => navigate('/login')} sx={{ color: 'text.secondary' }}>
          Already have an account? Login
        </Button>
      </Stack>
    </motion.div>
  );
};

const HeroPanel: React.FC<{
  isLoading: boolean;
  error: Error | null;
  enterGuestMode: () => Promise<void>;
}> = ({ isLoading, error, enterGuestMode }) => (
  <Stack spacing={4}>
    <HeroBadge />
    <HeroTitle />
    <HeroDescription />
    <HeroActions isLoading={isLoading} error={error} enterGuestMode={enterGuestMode} />
  </Stack>
);

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { enterGuestMode, isAuthenticated, isLoading, error } = useAuthContext();

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  React.useEffect(() => {
    void import('../features/dashboard/Dashboard');
  }, []);

  return (
    <Box
      component="main"
      id="main-content"
      sx={{
        minHeight: '100vh',
        color: 'text.primary',
        display: 'flex',
        alignItems: 'center',
        py: { xs: 8, md: 10 },
      }}
    >
      <Container maxWidth="lg">
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          <Grid container spacing={{ xs: 6, md: 10 }} alignItems="center">
            <Grid item xs={12} md={7}>
              <HeroPanel isLoading={isLoading} error={error} enterGuestMode={enterGuestMode} />
            </Grid>

            <Grid item xs={12} md={5}>
              <FeaturePanel />
            </Grid>
          </Grid>
        </motion.div>
      </Container>
    </Box>
  );
};

export default LandingPage;
