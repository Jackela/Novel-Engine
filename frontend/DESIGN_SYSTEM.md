# Novel Engine - Design System (SSOT)

This design system is driven by a Single Source of Truth for tokens. Author tokens in `src/styles/tokens.ts`, generate CSS variables (`src/styles/design-system.generated.css`) via `scripts/build-tokens.mjs`, then import the generated CSS before `src/styles/design-system.css`. Components consume tokens through the MUI theme defined in `src/styles/theme.ts`.

## Token Update Workflow (SSOT)

1) Edit tokens in `src/styles/tokens.ts`
   - Colors, spacing, typography, radii, motion
   - Avoid editing generated files directly

2) Build generated CSS from tokens
   - `npm run build:tokens` produces `src/styles/design-system.generated.css`
   - App imports generated CSS first (see `src/App.tsx`), then `design-system.css`

3) Verify consistency and accessibility
   - Run `npm run tokens:check` to detect drift and WCAG AA contrast regressions
   - Run `npm run lint:all` to ensure no hard-coded hex leaks into TSX in in-scope dirs

4) Commit both source and generated outputs
   - Include `src/styles/tokens.ts` and `src/styles/design-system.generated.css`

5) Update documentation if adding/removing tokens
   - Link changes back to `specs/002-ts-ssot-frontend/spec.md` and `quickstart.md`

---

## Technology Stack

- **UI Framework**: Material-UI v5
- **Animation**: Framer Motion
- **Language**: TypeScript
- **Build Tool**: Vite
- **React**: v18

---

## Color Palette

### Primary Colors

```typescript
const colors = {
  // Backgrounds
  primaryBg: '#0a0a0b',        // Main background
  secondaryBg: '#111113',      // Card backgrounds
  tertiaryBg: '#1a1a1d',       // Hover states
  border: '#2a2a30',           // Borders and dividers
  
  // Brand Colors
  primary: '#6366f1',          // Indigo - primary actions
  primaryHover: '#4f46e5',     // Darker indigo for hover
  
  // Status Colors
  success: '#10b981',          // Green - completed, active
  warning: '#f59e0b',          // Amber - pending, neutral
  error: '#ef4444',            // Red - errors, hostile
  info: '#3b82f6',             // Blue - informational
  
  // Text Colors
  textPrimary: '#ffffff',      // Primary text (90% opacity)
  textSecondary: '#808088',    // Secondary text (60% opacity)
  textDisabled: '#4a4a50',     // Disabled text (40% opacity)
};
```

### Color Usage Guidelines

- **Primary Background** (`#0a0a0b`): Main page background, dashboard base
- **Secondary Background** (`#111113`): Cards, panels, containers
- **Tertiary Background** (`#1a1a1d`): Hover states, elevated surfaces
- **Border** (`#2a2a30`): All borders, dividers, separators
- **Primary** (`#6366f1`): Buttons, links, active states, focus indicators
- **Success** (`#10b981`): Completed tasks, active characters, positive status
- **Warning** (`#f59e0b`): Pending states, neutral characters, cautions
- **Error** (`#ef4444`): Errors, hostile characters, critical alerts

---

## Typography

### Font Stack

```typescript
const typography = {
  fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
  monospaceFontFamily: '"Fira Code", "Consolas", monospace',
  storyFontFamily: '"Georgia", "Times New Roman", serif',
};
```

### Font Sizes & Weights

```typescript
const fontSizes = {
  xs: '0.75rem',      // 12px - captions, badges
  sm: '0.875rem',     // 14px - body small, helper text
  base: '1rem',       // 16px - body text
  lg: '1.125rem',     // 18px - large body text
  xl: '1.25rem',      // 20px - small headings
  '2xl': '1.5rem',    // 24px - h6
  '3xl': '1.875rem',  // 30px - h5
  '4xl': '2.25rem',   // 36px - h4
  '5xl': '3rem',      // 48px - h3
};

const fontWeights = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
};
```

### Typography Hierarchy

- **H3**: 3rem (48px), weight 700 - Page titles
- **H4**: 2.25rem (36px), weight 700 - Section titles
- **H5**: 1.875rem (30px), weight 600 - Card titles
- **H6**: 1.5rem (24px), weight 600 - Component headers
- **Body1**: 1rem (16px), weight 400 - Primary body text
- **Body2**: 0.875rem (14px), weight 400 - Secondary text
- **Caption**: 0.75rem (12px), weight 400 - Small labels
- **Button**: 0.875rem (14px), weight 600 - Button text

---

## Spacing System

Based on Material-UI's 8px base unit.

```typescript
const spacing = {
  0: '0px',
  0.5: '4px',
  1: '8px',
  1.5: '12px',
  2: '16px',
  2.5: '20px',
  3: '24px',
  4: '32px',
  5: '40px',
  6: '48px',
  8: '64px',
  10: '80px',
};
```

### Spacing Usage

- **Component padding**: theme.spacing(2) = 16px
- **Card padding**: theme.spacing(3) = 24px
- **Section margins**: theme.spacing(3-4) = 24-32px
- **Grid gaps**: theme.spacing(2-3) = 16-24px
- **Icon gaps**: theme.spacing(1) = 8px
- **List item spacing**: theme.spacing(0.5-1) = 4-8px

---

## Animation System

### Easing Functions

```typescript
const easing = {
  standard: 'cubic-bezier(0.4, 0, 0.2, 1)',  // Material Design standard
  enter: 'cubic-bezier(0.0, 0, 0.2, 1)',     // Elements entering
  exit: 'cubic-bezier(0.4, 0, 1, 1)',        // Elements exiting
  sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',     // Quick transitions
};
```

### Duration

```typescript
const duration = {
  shortest: '150ms',
  shorter: '200ms',
  short: '250ms',
  standard: '300ms',
  complex: '375ms',
  enteringScreen: '225ms',
  leavingScreen: '195ms',
};
```

### Common Animations

#### Hover Transform

```typescript
// Standard hover lift
'&:hover': {
  transform: 'translateY(-2px)',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
}
```

#### Pulse Animation (Framer Motion)

```typescript
animate={{
  scale: [1, 1.1, 1],
}}
transition={{
  duration: 2,
  repeat: Infinity,
  ease: 'easeInOut',
}}
```

#### Fade In/Out

```typescript
initial={{ opacity: 0, y: 20 }}
animate={{ opacity: 1, y: 0 }}
exit={{ opacity: 0, y: -20 }}
transition={{ duration: 0.25, ease: 'cubic-bezier(0.4, 0, 0.2, 1)' }}
```

#### Scale on Hover

```typescript
whileHover={{ 
  scale: 1.05,
  transition: { duration: 0.2 }
}}
```

---

## Responsive Breakpoints

Material-UI breakpoints:

```typescript
const breakpoints = {
  xs: 0,      // Mobile portrait
  sm: 600,    // Mobile landscape
  md: 900,    // Tablet
  lg: 1200,   // Desktop
  xl: 1536,   // Large desktop
};
```

### Responsive Strategy

**Mobile First Approach**: Design for mobile, enhance for larger screens.

```typescript
// Mobile: <900px (xs, sm)
// Tablet: 900-1200px (md)
// Desktop: >1200px (lg, xl)
```

### Common Responsive Patterns

#### Layout Direction

```typescript
// Mobile: vertical, Desktop: horizontal
[theme.breakpoints.down('md')]: {
  flexDirection: 'column',
},
[theme.breakpoints.up('md')]: {
  flexDirection: 'row',
},
```

#### Padding Responsive

```typescript
padding: {
  xs: theme.spacing(2),  // 16px mobile
  sm: theme.spacing(3),  // 24px desktop
}
```

#### Grid Columns

```typescript
<Grid item xs={12} sm={6} md={4} lg={3}>
  // 1 col mobile, 2 col tablet, 3 col desktop, 4 col large
</Grid>
```

---

## Component Patterns

### Card Pattern

```typescript
const StyledCard = styled(Card)(({ theme }) => ({
  backgroundColor: '#111113',
  border: `1px solid #2a2a30`,
  borderRadius: theme.shape.borderRadius,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: '#1a1a1d',
    borderColor: '#6366f1',
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(99, 102, 241, 0.2)',
  },
}));
```

### Chip Pattern (Status)

```typescript
const StatusChip = styled(Chip)<{ status: string }>(({ theme, status }) => ({
  backgroundColor: 
    status === 'completed' ? 'rgba(16, 185, 129, 0.15)' :
    status === 'error' ? 'rgba(239, 68, 68, 0.15)' :
    status === 'pending' ? 'rgba(245, 158, 11, 0.15)' :
    'rgba(99, 102, 241, 0.15)',
  color:
    status === 'completed' ? theme.palette.success.main :
    status === 'error' ? theme.palette.error.main :
    status === 'pending' ? theme.palette.warning.main :
    theme.palette.primary.main,
  borderColor: 
    status === 'completed' ? '#10b981' :
    status === 'error' ? '#ef4444' :
    status === 'pending' ? '#f59e0b' :
    '#6366f1',
  fontWeight: 600,
}));
```

### Progress Bar Pattern

```typescript
const StyledProgress = styled(LinearProgress)<{ value: number }>(({ theme, value }) => ({
  height: 4,
  borderRadius: 2,
  backgroundColor: '#2a2a30',
  '& .MuiLinearProgress-bar': {
    borderRadius: 2,
    backgroundColor: 
      value >= 80 ? '#10b981' :
      value >= 60 ? '#6366f1' :
      value >= 40 ? '#f59e0b' :
      '#ef4444',
  },
}));
```

### Button Pattern

```typescript
const StyledButton = styled(Button)(({ theme }) => ({
  borderRadius: theme.shape.borderRadius,
  textTransform: 'none',
  fontWeight: 600,
  padding: theme.spacing(1, 3),
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(99, 102, 241, 0.3)',
  },
}));
```

### List Item Pattern (with left border)

```typescript
const StyledListItem = styled(ListItem)<{ status: string }>(({ theme, status }) => ({
  padding: theme.spacing(1, 0),
  borderBottom: `1px solid #2a2a30`,
  borderLeft: `3px solid ${
    status === 'active' ? '#6366f1' :
    status === 'completed' ? '#10b981' :
    status === 'error' ? '#ef4444' :
    '#808088'
  }`,
  paddingLeft: theme.spacing(1),
  borderRadius: theme.shape.borderRadius / 2,
  marginBottom: theme.spacing(0.5),
  background: status === 'active' ? 'rgba(99, 102, 241, 0.05)' : 'transparent',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: status === 'active' ? 'rgba(99, 102, 241, 0.1)' : '#1a1a1d',
    borderLeftWidth: '4px',
  },
}));
```

---

## Accessibility Standards

### WCAG 2.1 AA Compliance

- **Color Contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Focus Indicators**: All interactive elements must have visible focus states
- **Keyboard Navigation**: All actions accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and semantic HTML

### Focus States

```typescript
'&:focus-visible': {
  outline: `2px solid #6366f1`,
  outlineOffset: '2px',
}
```

### ARIA Labels

```typescript
<IconButton aria-label="Close dialog">
  <CloseIcon />
</IconButton>
```

### Semantic HTML

- Use proper heading hierarchy (h1 → h2 → h3)
- Use `<nav>`, `<main>`, `<section>`, `<article>` appropriately
- Use `<button>` for actions, `<a>` for navigation

---

## Theme Configuration

### Material-UI Theme Setup

```typescript
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#6366f1',
      light: '#818cf8',
      dark: '#4f46e5',
    },
    success: {
      main: '#10b981',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#ef4444',
    },
    background: {
      default: '#0a0a0b',
      paper: '#111113',
    },
    text: {
      primary: 'rgba(255, 255, 255, 0.9)',
      secondary: 'rgba(255, 255, 255, 0.6)',
      disabled: 'rgba(255, 255, 255, 0.4)',
    },
    divider: '#2a2a30',
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
    h3: {
      fontSize: '3rem',
      fontWeight: 700,
    },
    h4: {
      fontSize: '2.25rem',
      fontWeight: 700,
    },
    h5: {
      fontSize: '1.875rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '1rem',
      fontWeight: 400,
    },
    body2: {
      fontSize: '0.875rem',
      fontWeight: 400,
    },
  },
  shape: {
    borderRadius: 8,
  },
  spacing: 8,
});

export default theme;
```

---

## Custom Scrollbar

```typescript
const customScrollbar = {
  '&::-webkit-scrollbar': {
    width: '6px',
    height: '6px',
  },
  '&::-webkit-scrollbar-track': {
    background: '#1a1a1d',
    borderRadius: '3px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: '#6366f1',
    borderRadius: '3px',
    '&:hover': {
      background: '#4f46e5',
    },
  },
};
```

---

## Best Practices

### 1. Component Composition

- Use Material-UI components as base
- Extend with `styled()` API for custom styling
- Use Framer Motion for animations
- Keep styles close to components

### 2. Performance

- Use `React.memo()` for expensive components
- Lazy load heavy components
- Optimize re-renders with proper state management
- Use CSS transitions for simple animations, Framer Motion for complex

### 3. Code Organization

```
components/
  ├── dashboard/           # Dashboard-specific components
  ├── StoryWorkshop/       # Story workshop components
  ├── layout/              # Layout components
  └── common/              # Reusable components
```

### 4. Naming Conventions

- **Components**: PascalCase (e.g., `TurnPipelineStatus`)
- **Styled Components**: Prefix with `Styled` (e.g., `StyledCard`)
- **Props Interfaces**: Suffix with `Props` (e.g., `TurnPipelineStatusProps`)
- **Types**: PascalCase (e.g., `StoryProject`)

### 5. TypeScript Usage

- Always define prop interfaces
- Use strict typing for styled component props
- Avoid `any` - use proper types or `unknown`

---

## Migration Checklist

When refactoring a component to this design system:

- [ ] Replace Tailwind/custom CSS with Material-UI components
- [ ] Use `styled()` API for custom styling
- [ ] Apply color palette from this SSOT
- [ ] Use spacing system (theme.spacing)
- [ ] Add proper animations (hover, transitions)
- [ ] Implement responsive breakpoints
- [ ] Add proper TypeScript types
- [ ] Include accessibility attributes
- [ ] Test keyboard navigation
- [ ] Verify color contrast (WCAG AA)

---

## Version History

- **v1.0** (2025-01-XX): Initial SSOT creation
  - Unified color palette
  - Typography system
  - Animation patterns
  - Component patterns
  - Accessibility standards
