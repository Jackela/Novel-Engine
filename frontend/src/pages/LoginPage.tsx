import React, { useState } from 'react';
import { Box, Container, Stack, Typography, Button, TextField, Alert, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { tokens } from '../styles/tokens';
import { useAuthContext } from '../contexts/AuthContext';
import config from '../config/env';
import LockPersonIcon from '@mui/icons-material/LockPerson';

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

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, enterGuestMode, isLoading, error } = useAuthContext();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ username: email, password });
      navigate('/dashboard');
    } catch {
      // Error handled by AuthContext
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        position: 'relative',
        overflow: 'hidden',
        color: 'text.primary',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
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
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
          filter: 'blur(80px)',
          zIndex: 0,
        }}
      />

      <Container maxWidth="sm" sx={{ position: 'relative', zIndex: 1 }}>
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          <Paper
            elevation={24}
            sx={{
              p: 6,
              borderRadius: 6,
              background: tokens.glass.high,
              backdropFilter: 'blur(20px)',
              border: `1px solid ${tokens.glass.border}`,
              boxShadow: tokens.elevation.xxl,
            }}
          >
            <Stack spacing={4} alignItems="center">
              <motion.div variants={itemVariants}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: '50%',
                    background: 'rgba(99, 102, 241, 0.1)',
                    color: tokens.colors.primary[500],
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: `1px solid ${tokens.colors.primary[500]}20`,
                    boxShadow: `0 0 20px ${tokens.colors.primary[500]}20`,
                  }}
                >
                  <LockPersonIcon sx={{ fontSize: 32 }} />
                </Box>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography variant="h4" component="h1" fontWeight="bold" textAlign="center" sx={{ fontFamily: 'Orbitron', letterSpacing: '0.05em' }}>
                  ACCESS COMMAND
                </Typography>
                <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ mt: 1 }}>
                  Enter credentials to access restricted systems.
                </Typography>
              </motion.div>

              <motion.div variants={itemVariants} style={{ width: '100%' }}>
                <form onSubmit={handleSubmit} style={{ width: '100%' }}>
                  <Stack spacing={3}>
                    {error && (
                      <Alert severity="error" variant="outlined" sx={{ borderRadius: 2 }}>
                        {error.message || 'Authentication failed'}
                      </Alert>
                    )}

                    <TextField
                      label="EMAIL ID"
                      type="email"
                      fullWidth
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      variant="outlined"
                      InputLabelProps={{ shrink: true, sx: { fontFamily: 'Orbitron', fontSize: '0.75rem' } }}
                    />

                    <TextField
                      label="ACCESS CODE"
                      type="password"
                      fullWidth
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      variant="outlined"
                      InputLabelProps={{ shrink: true, sx: { fontFamily: 'Orbitron', fontSize: '0.75rem' } }}
                    />

                    <Button
                      type="submit"
                      variant="contained"
                      size="large"
                      fullWidth
                      disabled={isLoading}
                      sx={{
                        py: 1.5,
                        fontSize: '1rem',
                        fontWeight: 700,
                        background: tokens.gradients.primary,
                        boxShadow: `0 0 20px ${tokens.colors.primary[500]}40`,
                        '&:hover': {
                          boxShadow: `0 0 30px ${tokens.colors.primary[500]}60`,
                        }
                      }}
                    >
                      {isLoading ? 'AUTHENTICATING...' : 'INITIATE SESSION'}
                    </Button>

                    {config.enableGuestMode && (
                      <Button
                        variant="outlined"
                        size="large"
                        fullWidth
                        onClick={() => {
                          enterGuestMode();
                          navigate('/dashboard');
                        }}
                        sx={{
                          py: 1.5,
                          fontSize: '0.9rem',
                          fontWeight: 600,
                          borderColor: tokens.colors.secondary[500],
                          color: tokens.colors.secondary[500],
                          '&:hover': {
                            borderColor: tokens.colors.secondary[400],
                            background: `${tokens.colors.secondary[500]}10`,
                          }
                        }}
                      >
                        CONTINUE AS GUEST
                      </Button>
                    )}
                  </Stack>
                </form>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Button
                  variant="text"
                  onClick={() => navigate('/')}
                  sx={{ color: 'text.secondary', fontFamily: 'Orbitron', fontSize: '0.75rem' }}
                >
                  ABORT SEQUENCE
                </Button>
              </motion.div>
            </Stack>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default LoginPage;
