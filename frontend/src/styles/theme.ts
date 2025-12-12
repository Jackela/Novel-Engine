import { createTheme } from '@mui/material/styles';
import { tokens } from './tokens';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: tokens.colors.primary[500],
      light: tokens.colors.primary[400],
      dark: tokens.colors.primary[600],
      contrastText: '#000000',
    },
    secondary: {
      main: tokens.colors.secondary[500],
      light: tokens.colors.secondary[400],
      dark: tokens.colors.secondary[600],
      contrastText: '#ffffff',
    },
    background: {
      default: tokens.colors.background.default,
      paper: tokens.colors.background.paper,
    },
    divider: tokens.colors.border.primary,
    error: { main: tokens.colors.status.error.main },
    warning: { main: tokens.colors.status.warning.main },
    info: { main: tokens.colors.status.info.main },
    success: { main: tokens.colors.status.success.main },
    text: {
      primary: tokens.colors.text.primary,
      secondary: tokens.colors.text.secondary,
      disabled: tokens.colors.text.disabled,
    },
  },
  typography: {
    fontFamily: tokens.typography.fontFamily,
    h1: { fontSize: tokens.typography.size.h1, fontWeight: 700, lineHeight: 1.1 },
    h2: { fontSize: tokens.typography.size.h2, fontWeight: 700, lineHeight: 1.2 },
    h3: { fontSize: tokens.typography.size.h3, fontWeight: 600, lineHeight: 1.25 },
    h4: { fontSize: tokens.typography.size.h4, fontWeight: 600, lineHeight: 1.3 },
    h5: { fontSize: tokens.typography.size.h5, fontWeight: 500, lineHeight: 1.4 },
    h6: { fontSize: tokens.typography.size.h6, fontWeight: 500, lineHeight: 1.4 },
    body1: { fontSize: tokens.typography.size.body, lineHeight: 1.5 },
    body2: { fontSize: tokens.typography.size.bodySm, lineHeight: 1.5 },
    caption: { fontSize: tokens.typography.size.caption, lineHeight: 1.5 },
  },
  shape: { borderRadius: 16 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage: tokens.gradients.dark,
          backgroundAttachment: 'fixed',
          scrollbarColor: `${tokens.colors.border.secondary} ${tokens.colors.background.default}`,
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: tokens.colors.background.default,
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: tokens.colors.border.secondary,
            borderRadius: '4px',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.glass.low,
          backdropFilter: 'blur(12px)',
          backgroundImage: 'none',
          border: `1px solid ${tokens.glass.border}`,
          boxShadow: 'none',
        },
        elevation1: { boxShadow: tokens.elevation.xs },
        elevation2: { boxShadow: tokens.elevation.sm },
        elevation8: {
          backgroundColor: tokens.glass.medium,
          border: `1px solid ${tokens.glass.highlight}`,
          boxShadow: `0 8px 32px 0 rgba(0, 0, 0, 0.36)`,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 4, // More futuristic sharp/rounded mix
          transition: `all ${tokens.motion.duration.standard} ${tokens.motion.easing.standard}`,
          letterSpacing: '0.02em',
        },
        containedPrimary: {
          backgroundColor: tokens.colors.primary[500],
          color: tokens.colors.background.default,
          '&:hover': {
            backgroundColor: tokens.colors.primary[400],
            boxShadow: `0 0 15px ${tokens.colors.primary[500]}66`, // 66 = 40% opacity
          },
        },
        outlined: {
          borderColor: tokens.colors.border.primary,
          '&:hover': {
            borderColor: tokens.colors.primary[500],
            backgroundColor: `${tokens.colors.primary[500]}0d`, // 0d = 5% opacity
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          fontWeight: 500,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 4,
            transition: 'all 0.2s',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            '& fieldset': {
              borderColor: tokens.colors.border.primary,
            },
            '&:hover fieldset': {
              borderColor: tokens.colors.border.secondary,
            },
            '&.Mui-focused': {
              backgroundColor: 'rgba(0, 240, 255, 0.03)',
              '& fieldset': {
                borderColor: tokens.colors.primary[500],
                boxShadow: `0 0 10px ${tokens.colors.primary[500]}40`,
              },
            },
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: tokens.glass.high,
          backdropFilter: 'blur(16px)',
          border: `1px solid ${tokens.glass.border}`,
          borderRadius: 16,
          boxShadow: tokens.elevation.xxl,
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: tokens.colors.background.interactive,
          border: `1px solid ${tokens.colors.border.secondary}`,
          color: tokens.colors.text.primary,
          fontSize: '0.75rem',
          boxShadow: tokens.elevation.md,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: tokens.colors.border.primary,
        },
      },
    },
  },
});

export default theme;
