/**
 * Design Tokens
 * CSS variables and theme tokens for the application
 */

// Color tokens
export const colors = {
  // Primary colors
  primary: 'hsl(var(--primary))',
  primaryForeground: 'hsl(var(--primary-foreground))',

  // Secondary colors
  secondary: 'hsl(var(--secondary))',
  secondaryForeground: 'hsl(var(--secondary-foreground))',

  // Background colors
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',

  // Card colors
  card: 'hsl(var(--card))',
  cardForeground: 'hsl(var(--card-foreground))',

  // Muted colors
  muted: 'hsl(var(--muted))',
  mutedForeground: 'hsl(var(--muted-foreground))',

  // Accent colors
  accent: 'hsl(var(--accent))',
  accentForeground: 'hsl(var(--accent-foreground))',

  // Destructive colors
  destructive: 'hsl(var(--destructive))',
  destructiveForeground: 'hsl(var(--destructive-foreground))',

  // Border and input
  border: 'hsl(var(--border))',
  input: 'hsl(var(--input))',
  ring: 'hsl(var(--ring))',
} as const;

// Spacing tokens (based on 4px grid)
export const spacing = {
  0: '0',
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
} as const;

// Border radius tokens
export const radius = {
  sm: 'calc(var(--radius) - 4px)',
  md: 'calc(var(--radius) - 2px)',
  lg: 'var(--radius)',
  xl: 'calc(var(--radius) + 4px)',
  full: '9999px',
} as const;

// Font size tokens
export const fontSize = {
  xs: '0.75rem',
  sm: '0.875rem',
  base: '1rem',
  lg: '1.125rem',
  xl: '1.25rem',
  '2xl': '1.5rem',
  '3xl': '1.875rem',
  '4xl': '2.25rem',
} as const;

// Font weight tokens
export const fontWeight = {
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
} as const;

// Animation tokens
export const animation = {
  fast: '150ms',
  normal: '300ms',
  slow: '500ms',
} as const;

// Z-index tokens
export const zIndex = {
  dropdown: 50,
  sticky: 100,
  fixed: 150,
  overlay: 200,
  modal: 300,
  popover: 400,
  tooltip: 500,
} as const;

// Export all tokens
const tokens = {
  colors,
  spacing,
  radius,
  fontSize,
  fontWeight,
  animation,
  zIndex,
};

export default tokens;
