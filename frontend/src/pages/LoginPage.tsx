import React, { useState } from 'react';
import {
  Alert,
  Box,
  Container,
  Stack,
  Typography,
  Button,
  TextField,
  Paper,
  Divider,
  Checkbox,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Link,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { tokens } from '../styles/tokens';
import { useAuthContext } from '@/contexts/useAuthContext';
import config from '../config/env';
import LockPersonIcon from '@mui/icons-material/LockPerson';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
};

const LoginIntroPanel: React.FC = () => (
  <motion.div variants={itemVariants}>
    <Paper
      elevation={0}
      sx={{
        p: { xs: 4, md: 5 },
        borderRadius: 4,
        border: `1px solid ${tokens.colors.border.primary}`,
        backgroundColor: tokens.colors.background.paper,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
    >
      <Stack spacing={3}>
        <Box
          sx={{
            width: 52,
            height: 52,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: tokens.colors.background.interactive,
            color: tokens.colors.primary[500],
          }}
        >
          <LockPersonIcon sx={{ fontSize: 28 }} />
        </Box>
        <Box>
          <Typography
            variant="h3"
            component="h1"
            sx={{
              fontFamily: tokens.typography.headingFamily,
              fontWeight: 600,
            }}
          >
            Access console
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
            Sign in to resume your operational workspace and manage live narratives.
          </Typography>
        </Box>
      </Stack>
    </Paper>
  </motion.div>
);

const LoginSupportPanel: React.FC<{ demoMode: boolean }> = ({ demoMode }) => (
  <Stack spacing={1.5}>
    <Typography variant="overline" sx={{ letterSpacing: '0.2em', color: 'text.secondary' }}>
      Support
    </Typography>
    {demoMode ? (
      <Alert severity="info" variant="outlined">
        Demo mode is enabled. Guest sessions are available and do not require credentials.
      </Alert>
    ) : (
      <Typography variant="body2" color="text.secondary">
        Need access? Email{' '}
        <Link href="mailto:ops@novel.engine" underline="hover" color="primary">
          ops@novel.engine
        </Link>{' '}
        or request credentials in the operator handbook.
      </Typography>
    )}
  </Stack>
);

const LoginFormFields: React.FC<{
  email: string;
  password: string;
  showPassword: boolean;
  rememberMe: boolean;
  emailError: boolean;
  passwordError: boolean;
  error: Error | null;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onEmailBlur: () => void;
  onPasswordBlur: () => void;
  onTogglePassword: () => void;
  onRememberMeChange: (value: boolean) => void;
}> = ({
  email,
  password,
  showPassword,
  rememberMe,
  emailError,
  passwordError,
  error,
  onEmailChange,
  onPasswordChange,
  onEmailBlur,
  onPasswordBlur,
  onTogglePassword,
  onRememberMeChange,
}) => (
  <>
    {error && (
      <Alert severity="error" variant="outlined">
        {error.message || 'Authentication failed'}
      </Alert>
    )}

    <TextField
      label="Email"
      type="email"
      fullWidth
      required
      value={email}
      onChange={(e) => onEmailChange(e.target.value)}
      onBlur={onEmailBlur}
      error={emailError}
      helperText={emailError ? 'Email is required.' : ' '}
      variant="outlined"
    />

    <TextField
      label="Password"
      type={showPassword ? 'text' : 'password'}
      fullWidth
      required
      value={password}
      onChange={(e) => onPasswordChange(e.target.value)}
      onBlur={onPasswordBlur}
      error={passwordError}
      helperText={passwordError ? 'Password is required.' : ' '}
      variant="outlined"
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <IconButton
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              onClick={onTogglePassword}
              edge="end"
            >
              {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
            </IconButton>
          </InputAdornment>
        ),
      }}
    />

    <FormControlLabel
      control={
        <Checkbox checked={rememberMe} onChange={(e) => onRememberMeChange(e.target.checked)} />
      }
      label="Remember this device"
    />
  </>
);

const LoginFormActions: React.FC<{
  isLoading: boolean;
  demoMode: boolean;
  onGuest: () => void;
}> = ({ isLoading, demoMode, onGuest }) => (
  <>
    <Button
      type="submit"
      variant="contained"
      size="large"
      fullWidth
      disabled={isLoading}
      sx={{
        py: 1.5,
        fontSize: '1rem',
        fontWeight: 600,
      }}
    >
      {isLoading ? 'Authenticating...' : 'Sign in'}
    </Button>

    {demoMode && (
      <Button
        variant="outlined"
        size="large"
        fullWidth
        onClick={onGuest}
        sx={{
          py: 1.5,
          fontWeight: 600,
        }}
      >
        Continue as guest
      </Button>
    )}
  </>
);

const LoginFormPanel: React.FC<{
  email: string;
  password: string;
  showPassword: boolean;
  rememberMe: boolean;
  emailError: boolean;
  passwordError: boolean;
  error: Error | null;
  isLoading: boolean;
  demoMode: boolean;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onEmailBlur: () => void;
  onPasswordBlur: () => void;
  onTogglePassword: () => void;
  onRememberMeChange: (value: boolean) => void;
  onSubmit: (event: React.FormEvent) => void;
  onGuest: () => void;
  onReturn: () => void;
}> = ({
  email,
  password,
  showPassword,
  rememberMe,
  emailError,
  passwordError,
  error,
  isLoading,
  demoMode,
  onEmailChange,
  onPasswordChange,
  onEmailBlur,
  onPasswordBlur,
  onTogglePassword,
  onRememberMeChange,
  onSubmit,
  onGuest,
  onReturn,
}) => (
  <motion.div variants={itemVariants}>
    <Paper
      elevation={0}
      sx={{
        p: { xs: 4, md: 5 },
        borderRadius: 4,
        border: `1px solid ${tokens.colors.border.primary}`,
        backgroundColor: tokens.colors.background.paper,
        height: '100%',
      }}
    >
      <Stack spacing={3}>
        <Box>
          <Typography variant="overline" sx={{ letterSpacing: '0.2em', color: 'text.secondary' }}>
            Operator login
          </Typography>
          <Typography variant="h5" sx={{ fontFamily: tokens.typography.headingFamily, fontWeight: 600 }}>
            Welcome back
          </Typography>
        </Box>

        <form onSubmit={onSubmit}>
          <Stack spacing={3}>
            <LoginFormFields
              email={email}
              password={password}
              showPassword={showPassword}
              rememberMe={rememberMe}
              emailError={emailError}
              passwordError={passwordError}
              error={error}
              onEmailChange={onEmailChange}
              onPasswordChange={onPasswordChange}
              onEmailBlur={onEmailBlur}
              onPasswordBlur={onPasswordBlur}
              onTogglePassword={onTogglePassword}
              onRememberMeChange={onRememberMeChange}
            />
            <LoginFormActions isLoading={isLoading} demoMode={demoMode} onGuest={onGuest} />
          </Stack>
        </form>

        <LoginSupportPanel demoMode={demoMode} />

        <Divider />

        <Button variant="text" onClick={onReturn} sx={{ color: 'text.secondary' }}>
          Return to overview
        </Button>
      </Stack>
    </Paper>
  </motion.div>
);

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, enterGuestMode, isLoading, error } = useAuthContext();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [submitted, setSubmitted] = useState(false);

  const demoMode = config.enableGuestMode;

  const emailError = (touched.email || submitted) && email.trim().length === 0;
  const passwordError = (touched.password || submitted) && password.trim().length === 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);

    if (emailError || passwordError) {
      return;
    }

    try {
      await login({ username: email, password });
      navigate('/dashboard');
    } catch {
      // Error handled by AuthContext
    }
  };

  return (
    <Box
      component="main"
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        py: { xs: 6, md: 10 },
      }}
    >
      <Container maxWidth="lg">
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          <Box
            sx={{
              display: 'grid',
              gap: { xs: 4, md: 6 },
              alignItems: 'stretch',
              '@media (min-width:960px)': {
                gridTemplateColumns: '1fr 1fr',
              },
            }}
          >
            <LoginIntroPanel />
            <LoginFormPanel
              email={email}
              password={password}
              showPassword={showPassword}
              rememberMe={rememberMe}
              emailError={emailError}
              passwordError={passwordError}
              error={error}
              isLoading={isLoading}
              demoMode={demoMode}
              onEmailChange={setEmail}
              onPasswordChange={setPassword}
              onEmailBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
              onPasswordBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
              onTogglePassword={() => setShowPassword((prev) => !prev)}
              onRememberMeChange={setRememberMe}
              onSubmit={handleSubmit}
              onGuest={() => {
                enterGuestMode();
                navigate('/dashboard');
              }}
              onReturn={() => navigate('/')}
            />
          </Box>
        </motion.div>
      </Container>
    </Box>
  );
};

export default LoginPage;
