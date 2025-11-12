import { createTheme } from '@mui/material/styles';
import { tokens } from './tokens';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: tokens.colors.primary[500],
      light: tokens.colors.primary[400],
      dark: tokens.colors.primary[600],
      contrastText: '#ffffff',
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
    h1: { fontSize: tokens.typography.size.h1, fontWeight: 700, lineHeight: tokens.typography.lineHeight.snug },
    h2: { fontSize: tokens.typography.size.h2, fontWeight: 700, lineHeight: tokens.typography.lineHeight.normal },
    h3: { fontSize: tokens.typography.size.h3, fontWeight: 600, lineHeight: tokens.typography.lineHeight.normal },
    h4: { fontSize: tokens.typography.size.h4, fontWeight: 600, lineHeight: tokens.typography.lineHeight.normal },
    h5: { fontSize: tokens.typography.size.h5, fontWeight: 500, lineHeight: tokens.typography.lineHeight.normal },
    h6: { fontSize: tokens.typography.size.h6, fontWeight: 500, lineHeight: tokens.typography.lineHeight.normal },
    body1: { fontSize: tokens.typography.size.body, lineHeight: tokens.typography.lineHeight.normal },
    body2: { fontSize: tokens.typography.size.bodySm, lineHeight: tokens.typography.lineHeight.normal },
    caption: { fontSize: tokens.typography.size.caption, lineHeight: tokens.typography.lineHeight.normal },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.colors.background.paper,
          backgroundImage: 'none',
          border: `1px solid ${tokens.colors.border.primary}`,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.colors.background.paper,
          border: `1px solid ${tokens.colors.border.primary}`,
          boxShadow: tokens.elevation.sm,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: 8,
          transition: `all ${tokens.motion.duration.standard} ${tokens.motion.easing.standard}`,
        },
      },
    },
  },
});

export default theme;
