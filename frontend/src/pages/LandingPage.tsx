import React from 'react';
import { Box, Container, Stack, Typography, Button, Grid, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import LiveTvIcon from '@mui/icons-material/LiveTv';
import InsightsIcon from '@mui/icons-material/Insights';
import SecurityIcon from '@mui/icons-material/Security';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import { motion } from 'framer-motion';
import { tokens } from '../styles/tokens';
import { useAuthContext } from '../contexts/AuthContext';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 100, damping: 15 },
  },
};

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { enterGuestMode, isAuthenticated } = useAuthContext();

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  return (
    <Box
      component="main"
      id="main-content"
      sx={{
        minHeight: '100vh',
        position: 'relative',
        overflow: 'hidden',
        color: 'text.primary',
      }}
    >
      {/* Dynamic Background Elements */}
      <Box
        component={motion.div}
        animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        sx={{
          position: 'absolute',
          top: '-20%',
          left: '-10%',
          width: '60vw',
          height: '60vw',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0, 240, 255, 0.15) 0%, transparent 70%)',
          filter: 'blur(80px)',
          zIndex: 0,
        }}
      />
      <Box
        component={motion.div}
        animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0.4, 0.2] }}
        transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        sx={{
          position: 'absolute',
          bottom: '-10%',
          right: '-5%',
          width: '50vw',
          height: '50vw',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(188, 19, 254, 0.15) 0%, transparent 70%)',
          filter: 'blur(80px)',
          zIndex: 0,
        }}
      />

      <Container
        component="main"
        maxWidth="lg"
        sx={{
          position: 'relative',
          zIndex: 1,
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          py: { xs: 6, md: 10 },
        }}
      >
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          <Stack spacing={8} alignItems="center">
            {/* Hero Section */}
            <Stack spacing={4} textAlign="center" maxWidth="md" alignItems="center">
              <motion.div variants={itemVariants}>
                <Box
                  sx={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 1,
                    px: 2,
                    py: 1,
                    borderRadius: 99,
                    background: 'rgba(0, 240, 255, 0.1)',
                    border: `1px solid ${tokens.colors.primary[500]}40`,
                    color: 'primary.main',
                    fontWeight: 600,
                    fontSize: '0.875rem',
                    backdropFilter: 'blur(4px)',
                  }}
                >
                  <AutoStoriesIcon sx={{ fontSize: 18 }} />
                  <span>NOVEL ENGINE V1.0</span>
                </Box>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography
                  variant="h1"
                  component="h1"
                  sx={{
                    fontFamily: 'Orbitron',
                    fontWeight: 900,
                    fontSize: { xs: '3.5rem', md: '7rem' },
                    lineHeight: 1.1,
                    letterSpacing: '-0.02em',
                    color: 'white',
                    textTransform: 'uppercase',
                    textShadow: `0 0 40px ${tokens.colors.primary[500]}40`,
                  }}
                >
                  NARRATIVE
                  <Box component="span" sx={{ display: 'block', color: 'white', background: tokens.gradients.primary, backgroundClip: 'text', WebkitBackgroundClip: 'text' }}>
                    ENGINE
                  </Box>
                </Typography>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography
                  variant="h5"
                  sx={{
                    color: 'text.secondary',
                    maxWidth: '800px',
                    lineHeight: 1.6,
                    fontSize: { xs: '1.1rem', md: '1.25rem' },
                    fontWeight: 300,
                    textShadow: '0 2px 10px rgba(0,0,0,0.5)',
                  }}
                >
                  Orchestrate complex sci-fi storylines across Meridian Station.
                  Monitor character networks, manage event cascades, and watch your narrative evolve in real-time.
                </Typography>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => enterGuestMode()}
                  startIcon={<RocketLaunchIcon />}
                  data-testid="cta-launch"
                  sx={{
                    py: 2,
                    px: 6,
                    fontSize: '1.2rem',
                    fontWeight: 700,
                    borderRadius: 99,
                    background: tokens.gradients.primary,
                    border: '1px solid rgba(255,255,255,0.2)',
                    boxShadow: `0 0 30px ${tokens.colors.primary[500]}66`,
                    '&:hover': {
                      boxShadow: `0 0 50px ${tokens.colors.primary[500]}80`,
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  LAUNCH ENGINE
                </Button>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Button variant="text" onClick={() => navigate('/login')} sx={{ color: 'text.secondary', '&:hover': { color: 'white' } }}>
                  Already have an account? Login
                </Button>
              </motion.div>
            </Stack>

            {/* Feature Grid */}
            <motion.div variants={itemVariants} style={{ width: '100%' }}>
              <Grid container spacing={4} justifyContent="center">
                {[
                  { icon: <LiveTvIcon />, title: 'Live Orchestration', desc: 'Real-time control over narrative turns and character decisions.', color: tokens.colors.primary[500] },
                  { icon: <InsightsIcon />, title: 'Adaptive Analytics', desc: 'Deep insights into plot progression and character relationships.', color: tokens.colors.secondary[500] },
                  { icon: <SecurityIcon />, title: 'Secure Environment', desc: 'Air-gapped simulation sandbox for safe narrative testing.', color: tokens.colors.status.success.main },
                ].map((feature, index) => (
                  <Grid item xs={12} md={4} key={index}>
                    <Paper
                      className="glass-card"
                      sx={{
                        p: 4,
                        borderRadius: 4,
                        height: '100%',
                        bgcolor: tokens.glass.medium,
                        backdropFilter: 'blur(12px)',
                        border: `1px solid ${tokens.glass.border}`,
                        transition: 'all 0.3s',
                        '&:hover': {
                          bgcolor: tokens.glass.high,
                          transform: 'translateY(-5px)',
                          boxShadow: tokens.elevation.lg,
                          borderColor: feature.color,
                        },
                      }}
                    >
                      <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: `${feature.color}15`, width: 'fit-content', mb: 2, color: feature.color }}>
                        {React.cloneElement(feature.icon, { sx: { fontSize: 32 } })}
                      </Box>
                      <Typography variant="h6" fontWeight={700} gutterBottom sx={{ fontFamily: 'Orbitron' }}>
                        {feature.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                        {feature.desc}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </motion.div>
          </Stack>
        </motion.div>
      </Container>
    </Box>
  );
};

export default LandingPage;
