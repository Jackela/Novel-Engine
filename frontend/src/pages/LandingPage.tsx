import React from 'react';
import { Box, Container, Stack, Typography, Button, Chip, Grid } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import LiveTvIcon from '@mui/icons-material/LiveTv';
import InsightsIcon from '@mui/icons-material/Insights';
import SecurityIcon from '@mui/icons-material/Security';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import { motion } from 'framer-motion';
import { useAuthContext } from '../contexts/AuthContext';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 100,
      damping: 15,
    },
  },
};

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
        position: 'relative',
        overflow: 'hidden',
        // background: '#0a0a0b', // Removed to allow global gradient
        color: 'text.primary',
      }}
    >
      {/* Dynamic Background Elements */}
      <Box
        component={motion.div}
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        sx={{
          position: 'absolute',
          top: '-20%',
          left: '-10%',
          width: '60vw',
          height: '60vw',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
          filter: 'blur(60px)',
          zIndex: 0,
        }}
      />
      <Box
        component={motion.div}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.2, 0.4, 0.2],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 2,
        }}
        sx={{
          position: 'absolute',
          bottom: '-10%',
          right: '-5%',
          width: '50vw',
          height: '50vw',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 70%)',
          filter: 'blur(60px)',
          zIndex: 0,
        }}
      />

      <Container
        component="main"
        id="main-content"
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
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <Stack spacing={8} alignItems="center">
            {/* Hero Section */}
            <Stack spacing={4} textAlign="center" maxWidth="md" alignItems="center">
              <motion.div variants={itemVariants}>
                <Chip
                  icon={<AutoStoriesIcon sx={{ fontSize: 16 }} />}
                  label="Novel Engine v1.0"
                  sx={{
                    background: 'rgba(99, 102, 241, 0.1)',
                    color: '#818cf8',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    fontWeight: 600,
                    backdropFilter: 'blur(4px)',
                  }}
                />
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography
                  variant="h1"
                  component="h1"
                  sx={{
                    fontFamily: 'Orbitron',
                    fontWeight: 900,
                    fontSize: { xs: '4rem', md: '8rem' },
                    lineHeight: 0.9,
                    letterSpacing: '-0.05em',
                    color: 'white',
                    textTransform: 'uppercase',
                    mb: 4,
                    position: 'relative',
                    textShadow: '0 0 30px rgba(99, 102, 241, 0.4), 0 0 60px rgba(99, 102, 241, 0.2)',
                  }}
                >
                  NARRATIVE<br />
                  <span style={{ color: 'var(--color-neon-cyan)' }}>ENGINE</span>
                </Typography>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography
                  variant="h5"
                  sx={{
                    color: 'text.secondary',
                    maxWidth: '800px',
                    lineHeight: 1.6,
                    fontWeight: 400,
                    fontSize: { xs: '1.1rem', md: '1.25rem' },
                    mb: 4,
                  }}
                >
                  Orchestrate complex sci-fi storylines across Meridian Station.
                  Monitor character networks, manage event cascades, and watch your narrative evolve in real-time.
                </Typography>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  spacing={3}
                  justifyContent="center"
                  sx={{ mt: 2 }}
                >
                  <Button
                    variant="contained"
                    size="large"
                    onClick={handleDemoClick}
                    startIcon={<RocketLaunchIcon />}
                    data-testid="cta-demo"
                    sx={{
                      py: 2,
                      px: 5,
                      fontSize: '1.1rem',
                      fontWeight: 600,
                      borderRadius: '9999px',
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      boxShadow: '0 0 20px rgba(99, 102, 241, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)',
                        boxShadow: '0 0 30px rgba(99, 102, 241, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
                        transform: 'translateY(-2px)',
                      },
                    }}
                  >
                    {isAuthenticated && isGuest ? 'Resume Simulation' : 'View Demo'}
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={handleDemoClick}
                    startIcon={<SecurityIcon />}
                    sx={{
                      py: 1.5,
                      px: 4,
                      fontSize: '1.1rem',
                      borderColor: 'rgba(255, 255, 255, 0.2)',
                      color: 'text.primary',
                      '&:hover': {
                        borderColor: '#fff',
                        background: 'rgba(255, 255, 255, 0.05)',
                      },
                    }}
                  >
                    Enter Dashboard
                  </Button>
                  <Button
                    component="a"
                    href="mailto:ops@novel-engine.ai?subject=Novel%20Engine%20Access"
                    variant="text"
                    size="large"
                    sx={{
                      py: 1.5,
                      px: 4,
                      fontSize: '1rem',
                      color: 'text.secondary',
                      textDecoration: 'underline',
                      '&:hover': {
                        color: 'text.primary',
                      },
                    }}
                  >
                    Request Access
                  </Button>
                </Stack>
              </motion.div>
            </Stack>

            {/* Feature Grid */}
            <motion.div variants={itemVariants} style={{ width: '100%' }}>
              <Grid container spacing={3} justifyContent="center">
                {[
                  {
                    icon: <LiveTvIcon sx={{ fontSize: 32, color: '#6366f1' }} />,
                    title: 'Live Orchestration',
                    desc: 'Real-time control over narrative turns and character decisions.',
                  },
                  {
                    icon: <InsightsIcon sx={{ fontSize: 32, color: '#8b5cf6' }} />,
                    title: 'Adaptive Analytics',
                    desc: 'Deep insights into plot progression and character relationships.',
                  },
                  {
                    icon: <SecurityIcon sx={{ fontSize: 32, color: '#10b981' }} />,
                    title: 'Secure Environment',
                    desc: 'Air-gapped simulation sandbox for safe narrative testing.',
                  },
                ].map((feature, index) => (
                  <Grid item xs={12} md={4} key={index}>
                    <Box
                      className="glass-card"
                      sx={{
                        p: 4,
                        borderRadius: 4,
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'flex-start',
                        gap: 2,
                      }}
                    >
                      <Box
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          background: 'rgba(255, 255, 255, 0.05)',
                        }}
                      >
                        {feature.icon}
                      </Box>
                      <Typography variant="h6" fontWeight={600}>
                        {feature.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                        {feature.desc}
                      </Typography>
                    </Box>
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
