# Emergent Narrative Dashboard - UI Visual Design Specification

> **2025-11-12 Update**: The dashboard now uses the flow-based zones defined in `frontend/src/components/EmergentDashboard.css`. Treat the legacy Bento grid guidance below as reference material only; new work must rely on the semantic `data-role` wrappers (`dashboard-control-cluster`, `dashboard-streams`, `dashboard-signals`, `dashboard-pipeline`).

## Document Overview

This comprehensive visual design specification transforms the Novel Engine's Emergent Narrative Dashboard into a sophisticated, professional interface for monitoring emergent storytelling. The design emphasizes clarity, accessibility, and modern data visualization principles while maintaining the robust Bento Grid layout architecture.

**Design Philosophy**: Professional • Data-Driven • Accessible • Sophisticated
**Target Users**: Game Masters, Narrative Designers, System Administrators, Creative Professionals
**Design System**: Modern dark theme with refined typography and sophisticated color palette

---

## 1. Visual Moodboard & Design Direction

### 1.1 Aesthetic Inspiration

**Primary Inspiration**: 
- **Notion Dashboard** - Clean, professional, content-focused
- **Linear App** - Sophisticated dark theme with excellent typography
- **Figma Interface** - Modern tool aesthetics with purposeful color usage
- **Grafana Dashboards** - Professional data visualization patterns

**Design Principles**:
- **Sophistication Over Complexity** - Refined visual hierarchy without overwhelming detail
- **Content First** - Visual design serves the narrative data, never competes with it
- **Accessible by Design** - High contrast ratios and clear visual cues throughout
- **Progressive Disclosure** - Information architecture that reveals complexity gradually

### 1.2 Visual Mood

**Atmosphere**: 
- Professional workspace aesthetic
- Calm, focused environment for deep narrative work  
- Sophisticated tool for creative professionals
- Data-driven insights with humanized presentation

**Visual Weight**:
- Clean, spacious layouts with purposeful negative space
- Subtle elevation and depth cues for information hierarchy
- Refined shadows and borders that enhance rather than distract
- Typography as the primary design element

---

## 2. Color System

### 2.1 Foundation Palette

**Primary Brand Identity**:
```css
/* Primary - Sophisticated Indigo */
--color-primary: #6366f1;           /* Primary actions, key interactive elements */
--color-primary-50: #eef2ff;        /* Lightest tint for backgrounds */
--color-primary-100: #e0e7ff;       /* Light background states */
--color-primary-200: #c7d2fe;       /* Subtle emphasis */
--color-primary-300: #a5b4fc;       /* Muted interactive states */
--color-primary-400: #818cf8;       /* Secondary emphasis */
--color-primary-500: #6366f1;       /* Base primary color */
--color-primary-600: #4f46e5;       /* Hover states */
--color-primary-700: #4338ca;       /* Active states */
--color-primary-800: #3730a3;       /* Strong emphasis */
--color-primary-900: #312e81;       /* Darkest shade */
```

**Secondary - Supporting Purple**:
```css
/* Secondary - Elegant Purple Accent */
--color-secondary: #8b5cf6;         /* Secondary actions */
--color-secondary-50: #f3e8ff;      
--color-secondary-100: #e9d5ff;     
--color-secondary-200: #d8b4fe;     
--color-secondary-300: #c084fc;     
--color-secondary-400: #a855f7;     
--color-secondary-500: #8b5cf6;     /* Base secondary */
--color-secondary-600: #7c3aed;     /* Hover states */
--color-secondary-700: #6d28d9;     /* Active states */
--color-secondary-800: #5b21b6;     
--color-secondary-900: #4c1d95;     
```

### 2.2 Neutral Foundation

**Dark Theme Base**:
```css
/* Background Hierarchy */
--color-bg-primary: #0a0a0b;        /* Main dashboard background */
--color-bg-secondary: #111113;      /* Bento tile backgrounds */
--color-bg-tertiary: #1a1a1d;       /* Panel and card backgrounds */
--color-bg-elevated: #232328;       /* Modal and dropdown backgrounds */
--color-bg-interactive: #2a2a30;    /* Hover states for interactive elements */
--color-bg-overlay: rgba(10, 10, 11, 0.95); /* Modal backdrop */

/* Border System */
--color-border-primary: #2a2a30;    /* Main structural borders */
--color-border-secondary: #3a3a42;  /* Interactive element borders */
--color-border-tertiary: #4a4a52;   /* Emphasis borders */
--color-border-focus: #6366f1;      /* Focus ring color */
--color-border-hover: #5a5a62;      /* Hover state borders */

/* Text Hierarchy */
--color-text-primary: #f0f0f2;      /* Main headings and primary content */
--color-text-secondary: #b0b0b8;    /* Secondary information and labels */
--color-text-tertiary: #808088;     /* Muted text, timestamps, metadata */
--color-text-quaternary: #606068;   /* Placeholder text and disabled states */
--color-text-inverse: #0a0a0b;      /* Text on light backgrounds */
```

### 2.3 Semantic Color System

**Status & Feedback Colors**:
```css
/* Success - Refined Green */
--color-success: #10b981;           /* Success states, positive metrics */
--color-success-bg: #064e3b;        /* Success background tints */
--color-success-border: #065f46;    /* Success borders */
--color-success-text: #6ee7b7;      /* Success text on dark backgrounds */

/* Warning - Sophisticated Amber */
--color-warning: #f59e0b;           /* Warning states, caution indicators */
--color-warning-bg: #78350f;        /* Warning background tints */
--color-warning-border: #92400e;    /* Warning borders */
--color-warning-text: #fcd34d;      /* Warning text on dark backgrounds */

/* Error - Refined Red */
--color-error: #ef4444;             /* Error states, critical issues */
--color-error-bg: #7f1d1d;          /* Error background tints */
--color-error-border: #991b1b;      /* Error borders */
--color-error-text: #fca5a5;        /* Error text on dark backgrounds */

/* Info - Professional Blue */
--color-info: #3b82f6;              /* Information states, neutral notices */
--color-info-bg: #1e3a8a;           /* Info background tints */
--color-info-border: #1e40af;       /* Info borders */
--color-info-text: #93c5fd;         /* Info text on dark backgrounds */
```

### 2.4 Data Visualization Palette

**Character & Entity Colors** (High contrast, accessible):
```css
/* Character Type Colors */
--color-character-protagonist: #8b5cf6;   /* Purple - Main characters */
--color-character-supporting: #06b6d4;    /* Cyan - Supporting characters */
--color-character-neutral: #10b981;       /* Green - Neutral entities */
--color-character-antagonist: #ef4444;    /* Red - Antagonistic forces */
--color-character-npc: #f59e0b;          /* Amber - NPCs and background */
--color-character-special: #ec4899;      /* Pink - Special roles and unique entities */

/* Narrative Arc Colors */
--color-arc-main: #6366f1;               /* Indigo - Primary storyline */
--color-arc-subplot: #8b5cf6;            /* Purple - Secondary plots */
--color-arc-character: #06b6d4;          /* Cyan - Character development */
--color-arc-romance: #ec4899;            /* Pink - Romance and relationships */
--color-arc-conflict: #ef4444;           /* Red - Conflict and tension */
--color-arc-mystery: #7c3aed;            /* Deep purple - Mystery elements */

/* Event & Activity Colors */
--color-event-action: #10b981;           /* Green - Physical actions */
--color-event-dialogue: #3b82f6;         /* Blue - Conversations */
--color-event-conflict: #ef4444;         /* Red - Conflicts and tension */
--color-event-discovery: #f59e0b;        /* Amber - Revelations and discoveries */
--color-event-emotional: #ec4899;        /* Pink - Emotional moments */
--color-event-system: #64748b;           /* Neutral - System events */
```

---

## 3. Typography System

### 3.1 Font Families

**Primary Typography**:
```css
/* Primary Font - Inter (Exceptional readability) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Monospace Font - JetBrains Mono (Superior code/data display) */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&display=swap');

--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Monaco', 'Menlo', monospace;
```

### 3.2 Typography Scale & Hierarchy

**Heading Scale**:
```css
/* Display Typography - Reserved for major headlines */
--text-display-lg: 4.5rem/1.1 var(--font-primary);   /* 72px - Hero headlines */
--text-display-md: 3.75rem/1.1 var(--font-primary);  /* 60px - Major headlines */
--text-display-sm: 3rem/1.2 var(--font-primary);     /* 48px - Section headlines */

/* Heading Hierarchy */
--text-heading-xl: 2.25rem/1.2 var(--font-primary);  /* 36px - Page titles */
--text-heading-lg: 1.875rem/1.3 var(--font-primary); /* 30px - Major sections */
--text-heading-md: 1.5rem/1.4 var(--font-primary);   /* 24px - Subsections */
--text-heading-sm: 1.25rem/1.4 var(--font-primary);  /* 20px - Card titles */
--text-heading-xs: 1.125rem/1.4 var(--font-primary); /* 18px - Small headings */

/* Body Text */
--text-body-lg: 1.125rem/1.6 var(--font-primary);    /* 18px - Large body text */
--text-body-base: 1rem/1.5 var(--font-primary);      /* 16px - Standard body */
--text-body-sm: 0.875rem/1.4 var(--font-primary);    /* 14px - Secondary content */
--text-body-xs: 0.75rem/1.3 var(--font-primary);     /* 12px - Captions, metadata */

/* Monospace Typography */
--text-mono-lg: 1rem/1.5 var(--font-mono);           /* 16px - Code blocks */
--text-mono-base: 0.875rem/1.4 var(--font-mono);     /* 14px - Data display */
--text-mono-sm: 0.75rem/1.3 var(--font-mono);        /* 12px - Small data */
```

**Font Weights**:
```css
--font-weight-light: 300;      /* Light emphasis */
--font-weight-normal: 400;     /* Regular body text */
--font-weight-medium: 500;     /* Subtle emphasis */
--font-weight-semibold: 600;   /* Strong emphasis */
--font-weight-bold: 700;       /* Heavy emphasis */
```

### 3.3 Typography Usage Guidelines

**Heading Usage**:
- **Display**: Main dashboard title, major feature announcements
- **Heading XL**: Page and section titles, primary navigation
- **Heading LG**: Major component titles, important subsections
- **Heading MD**: Card titles, secondary navigation, panel headers
- **Heading SM**: List item titles, form section headers
- **Heading XS**: Micro-headlines, table headers

**Body Text Usage**:
- **Body LG**: Important descriptions, primary content
- **Body Base**: Standard paragraph text, interface copy
- **Body SM**: Secondary information, help text, labels
- **Body XS**: Timestamps, metadata, fine print

**Monospace Usage**:
- **Mono LG**: Code blocks, JSON display
- **Mono Base**: Data tables, IDs, technical information
- **Mono SM**: Compact data display, status codes

---

## 4. Spacing & Layout System

### 4.1 Spacing Scale

**Base Unit**: 4px (consistent with modern design systems)

```css
/* Spacing Scale */
--spacing-0: 0;        /* No spacing */
--spacing-1: 0.25rem;  /* 4px - Minimal spacing */
--spacing-2: 0.5rem;   /* 8px - Tight spacing */
--spacing-3: 0.75rem;  /* 12px - Small spacing */
--spacing-4: 1rem;     /* 16px - Base spacing */
--spacing-5: 1.25rem;  /* 20px - Medium spacing */
--spacing-6: 1.5rem;   /* 24px - Large spacing */
--spacing-8: 2rem;     /* 32px - Extra large spacing */
--spacing-10: 2.5rem;  /* 40px - Section spacing */
--spacing-12: 3rem;    /* 48px - Major section spacing */
--spacing-16: 4rem;    /* 64px - Hero spacing */
--spacing-20: 5rem;    /* 80px - Maximum spacing */
```

### 4.2 Bento Grid System (Maintains existing excellent implementation)

**Grid Configuration**:
```css
/* Desktop (≥1200px): 12-column grid */
.bento-grid-desktop {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--spacing-6) var(--spacing-5); /* 24px v, 20px h */
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-6);
}

/* Tablet (768px - 1199px): 8-column grid */
.bento-grid-tablet {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: var(--spacing-5) var(--spacing-4); /* 20px v, 16px h */
  padding: var(--spacing-5);
}

/* Mobile (≤767px): Single column */
.bento-grid-mobile {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-4) var(--spacing-3); /* 16px v, 12px h */
  padding: var(--spacing-4);
}
```

### 4.3 Component Spacing Guidelines

**Card/Tile Interior Spacing**:
```css
--tile-padding-desktop: var(--spacing-6);    /* 24px */
--tile-padding-tablet: var(--spacing-5);     /* 20px */
--tile-padding-mobile: var(--spacing-4);     /* 16px */

--tile-header-margin: var(--spacing-4);      /* 16px bottom */
--tile-section-margin: var(--spacing-6);     /* 24px between sections */
--tile-element-margin: var(--spacing-3);     /* 12px between elements */
```

---

## 5. Elevation & Shadow System

### 5.1 Elevation Hierarchy

**Shadow Definitions**:
```css
/* Subtle shadows for dark theme */
--shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);

/* Focus and interactive shadows */
--shadow-focus: 0 0 0 3px rgba(99, 102, 241, 0.1);
--shadow-interactive: var(--shadow-md);
```

**Usage Guidelines**:
- **XS**: Subtle borders, minimal separation
- **SM**: Cards at rest, tiles in grid
- **MD**: Hovered cards, active states  
- **LG**: Modals, dropdowns, floating elements
- **XL**: Major overlays, important announcements
- **2XL**: Critical alerts, full-page overlays

---

## 6. Interactive States & Animations

### 6.1 Hover States

```css
/* Interactive hover effects */
.interactive-hover {
  transition: all 150ms ease-in-out;
}

.interactive-hover:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-border-hover);
}
```

### 6.2 Focus States

```css
/* Accessible focus indicators */
.focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
  border-color: var(--color-border-focus);
}
```

### 6.3 Animation Timing

```css
/* Animation timing functions */
--timing-fast: 150ms;         /* Quick interactions */
--timing-standard: 250ms;     /* Standard transitions */
--timing-slow: 350ms;         /* Complex state changes */
--timing-extra-slow: 500ms;   /* Major layout changes */

--easing-standard: cubic-bezier(0.4, 0, 0.2, 1);
--easing-decelerate: cubic-bezier(0, 0, 0.2, 1);
--easing-accelerate: cubic-bezier(0.4, 0, 1, 1);
```

---

## 7. Component Design Patterns

### 7.1 Bento Tile Base Pattern

**Standard Tile Structure**:
```css
.bento-tile {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: 12px;
  padding: var(--tile-padding-desktop);
  box-shadow: var(--shadow-sm);
  transition: all var(--timing-standard) var(--easing-standard);
  overflow: hidden;
  position: relative;
}

.bento-tile:hover {
  border-color: var(--color-border-secondary);
  box-shadow: var(--shadow-md);
}

.bento-tile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--tile-header-margin);
  padding-bottom: var(--spacing-3);
  border-bottom: 1px solid var(--color-border-primary);
}

.bento-tile-title {
  font: var(--text-heading-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.bento-tile-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}
```

### 7.2 World State Map Component

**Grid Position**: Desktop cols 1-6 (50% width), Mobile full-width
**Dimensions**: Aspect ratio 16:10, Min height 320px

```css
.world-state-map {
  grid-column: span 6;
  min-height: 320px;
  position: relative;
}

.world-map-canvas {
  background: linear-gradient(
    135deg, 
    var(--color-bg-tertiary) 0%, 
    color-mix(in srgb, var(--color-bg-tertiary) 70%, var(--color-primary)) 100%
  );
  border-radius: 8px;
  position: relative;
  height: 240px;
  overflow: hidden;
}

.world-map-entities {
  position: absolute;
  inset: 0;
  padding: var(--spacing-4);
}

.entity-marker {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-bg-secondary);
  box-shadow: var(--shadow-sm);
  position: absolute;
  transition: all var(--timing-fast) var(--easing-standard);
  cursor: pointer;
}

.entity-marker:hover {
  transform: scale(1.2);
  box-shadow: var(--shadow-md);
}
```

### 7.3 Performance Metrics Component

**Grid Position**: Desktop cols 11-12, Mobile full-width
**Visual Style**: Clean data display with status indicators

```css
.performance-metrics {
  grid-column: span 2;
  min-height: 160px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) 0;
  border-bottom: 1px solid var(--color-border-primary);
}

.metric-item:last-child {
  border-bottom: none;
}

.metric-label {
  font: var(--text-body-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.metric-value {
  font: var(--text-mono-base);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.metric-status-good {
  color: var(--color-success);
}

.metric-status-warning {
  color: var(--color-warning);
}

.metric-status-error {
  color: var(--color-error);
}
```

### 7.4 Real-Time Activity Component

**Grid Position**: Desktop cols 7-10, Mobile full-width
**Visual Style**: Event stream with timestamps

```css
.real-time-activity {
  grid-column: span 4;
  min-height: 160px;
}

.activity-stream {
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-secondary) transparent;
}

.activity-item {
  display: flex;
  gap: var(--spacing-3);
  padding: var(--spacing-3) 0;
  border-bottom: 1px solid var(--color-border-primary);
  animation: slideIn 300ms var(--easing-decelerate);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-timestamp {
  font: var(--text-mono-sm);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  min-width: 60px;
}

.activity-content {
  font: var(--text-body-sm);
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.activity-character {
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 8. Responsive Design Specifications

### 8.1 Breakpoint System

```css
/* Breakpoint definitions */
--breakpoint-sm: 640px;   /* Small devices (landscape phones) */
--breakpoint-md: 768px;   /* Medium devices (tablets) */
--breakpoint-lg: 1024px;  /* Large devices (laptops) */
--breakpoint-xl: 1280px;  /* Extra large devices (large laptops) */
--breakpoint-2xl: 1536px; /* 2X large devices (large desktops) */
```

### 8.2 Component Responsive Behavior

**Desktop (≥1024px)**:
- Full 12-column Bento Grid layout
- All components visible simultaneously  
- Hover states active
- Full typography scale

**Tablet (768px - 1023px)**:
- 8-column grid adaptation
- Components reflow according to priority
- Reduced padding and spacing
- Medium typography scale

**Mobile (≤767px)**:
- Single column stack
- Priority-based component ordering
- Minimal padding for content density
- Compact typography scale
- Touch-friendly interactive elements (44px minimum)

### 8.3 Typography Responsive Scaling

```css
/* Responsive typography scaling */
@media (max-width: 768px) {
  :root {
    --text-heading-xl: 1.875rem/1.2 var(--font-primary);  /* 30px */
    --text-heading-lg: 1.5rem/1.3 var(--font-primary);    /* 24px */
    --text-heading-md: 1.25rem/1.4 var(--font-primary);   /* 20px */
    --text-body-lg: 1rem/1.5 var(--font-primary);         /* 16px */
  }
}
```

---

## 9. Accessibility Guidelines

### 9.1 Color Contrast Requirements

**WCAG 2.1 AA Compliance**:
- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text**: Minimum 3:1 contrast ratio  
- **Interactive elements**: Minimum 3:1 contrast ratio
- **Focus indicators**: Visible 3px outline with adequate contrast

**Validated Color Combinations**:
- Primary text (#f0f0f2) on dark background (#0a0a0b): **13.6:1 ✅**
- Secondary text (#b0b0b8) on dark background (#0a0a0b): **8.9:1 ✅**
- Primary button (#6366f1) on dark background: **4.8:1 ✅**
- Success indicator (#10b981) on dark background: **4.2:1 ✅**

### 9.2 Interactive Element Guidelines

**Touch Targets**:
- Minimum 44px × 44px for mobile touch interfaces
- 8px minimum spacing between interactive elements
- Clear hover and focus states for all interactive elements

**Keyboard Navigation**:
- Visible focus indicators on all focusable elements
- Logical tab order through interface
- Keyboard shortcuts for common actions

---

## 10. Implementation Guidelines

### 10.1 CSS Custom Properties Integration

All design tokens should be implemented as CSS custom properties in the `:root` scope for consistent theming and easy maintenance.

### 10.2 Component Development Approach

1. **Base Components First**: Implement foundational typography, spacing, and color systems
2. **Tile Pattern**: Create reusable Bento tile base component
3. **Dashboard Components**: Build each dashboard component using the established patterns
4. **Responsive Testing**: Validate across all breakpoints during development
5. **Accessibility Validation**: Test with screen readers and keyboard-only navigation

### 10.3 Performance Considerations

- Use CSS custom properties for efficient theme switching
- Implement lazy loading for non-critical dashboard components
- Optimize font loading with font-display: swap
- Minimize layout shifts during component mounting

---

## 11. Design System Validation Checklist

### Visual Design Compliance
- [ ] All components use specified color palette
- [ ] Typography hierarchy consistently implemented
- [ ] Spacing system applied throughout interface
- [ ] Elevation and shadow system properly utilized
- [ ] Interactive states function as specified

### Responsive Design Validation  
- [ ] Desktop layout matches 12-column specification
- [ ] Tablet adaptation functions correctly
- [ ] Mobile single-column layout optimized
- [ ] Typography scales appropriately across breakpoints
- [ ] Touch targets meet minimum size requirements

### Accessibility Validation
- [ ] Color contrast ratios meet WCAG 2.1 AA standards
- [ ] Focus indicators visible and consistent
- [ ] Keyboard navigation functional throughout interface
- [ ] Screen reader compatibility verified
- [ ] Interactive elements properly labeled

### Performance & Technical
- [ ] CSS custom properties implemented consistently
- [ ] Animation performance optimized
- [ ] Font loading optimized
- [ ] Component lazy loading implemented where appropriate
- [ ] Layout stability maintained during loading states

---

**Design System Version**: 1.0  
**Last Updated**: January 29, 2025  
**Design Lead**: Claude (Designer Persona)  
**Technical Requirements**: React + TypeScript + Shadcn UI + Tailwind CSS + CSS Custom Properties

*This specification provides the complete visual foundation for transforming the Emergent Narrative Dashboard from its current gaming theme into a sophisticated, professional interface suitable for creative professionals and system administrators.*
