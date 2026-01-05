import { createTheme } from '@mui/material/styles';
import { tokens } from './tokens';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: tokens.colors.primary[500],
      light: tokens.colors.primary[300],
      dark: tokens.colors.primary[600],
      contrastText: tokens.colors.text.inverse,
    },
    secondary: {
      main: tokens.colors.secondary[500],
      light: tokens.colors.secondary[400],
      dark: tokens.colors.secondary[600],
      contrastText: tokens.colors.text.inverse,
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
    h1: { fontSize: tokens.typography.size.h1, fontWeight: 700, lineHeight: 1.1, fontFamily: tokens.typography.headingFamily },
    h2: { fontSize: tokens.typography.size.h2, fontWeight: 700, lineHeight: 1.2, fontFamily: tokens.typography.headingFamily },
    h3: { fontSize: tokens.typography.size.h3, fontWeight: 600, lineHeight: 1.25, fontFamily: tokens.typography.headingFamily },
    h4: { fontSize: tokens.typography.size.h4, fontWeight: 600, lineHeight: 1.3, fontFamily: tokens.typography.headingFamily },
    h5: { fontSize: tokens.typography.size.h5, fontWeight: 600, lineHeight: 1.4, fontFamily: tokens.typography.headingFamily },
    h6: { fontSize: tokens.typography.size.h6, fontWeight: 600, lineHeight: 1.4, fontFamily: tokens.typography.headingFamily },
    body1: { fontSize: tokens.typography.size.body, lineHeight: 1.5 },
    body2: { fontSize: tokens.typography.size.bodySm, lineHeight: 1.5 },
    caption: { fontSize: tokens.typography.size.caption, lineHeight: 1.5 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: tokens.colors.background.default,
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
          backgroundColor: tokens.colors.background.paper,
          backgroundImage: 'none',
          border: `1px solid ${tokens.colors.border.primary}`,
          boxShadow: tokens.elevation.xs,
        },
        elevation1: { boxShadow: tokens.elevation.xs },
        elevation2: { boxShadow: tokens.elevation.sm },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 10,
          transition: `all ${tokens.motion.duration.standard} ${tokens.motion.easing.standard}`,
          letterSpacing: '0.01em',
        },
        containedPrimary: {
          backgroundColor: tokens.colors.primary[500],
          color: tokens.colors.text.inverse,
          '&:hover': {
            backgroundColor: tokens.colors.primary[400],
            boxShadow: tokens.elevation.sm,
          },
        },
        outlined: {
          borderColor: tokens.colors.border.primary,
          color: tokens.colors.text.primary,
          '&:hover': {
            borderColor: tokens.colors.primary[500],
            backgroundColor: `${tokens.colors.primary[500]}0d`,
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
            borderRadius: 10,
            transition: 'all 0.2s',
            backgroundColor: tokens.colors.background.paper,
            '& fieldset': {
              borderColor: tokens.colors.border.primary,
            },
            '&:hover fieldset': {
              borderColor: tokens.colors.border.secondary,
            },
            '&.Mui-focused': {
              '& fieldset': {
                borderColor: tokens.colors.primary[500],
                boxShadow: tokens.elevation.focus,
              },
            },
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: tokens.colors.background.paper,
          border: `1px solid ${tokens.colors.border.primary}`,
          borderRadius: 16,
          boxShadow: tokens.elevation.lg,
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
