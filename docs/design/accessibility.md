# Accessibility Guide

## Overview

This application is designed with accessibility as a core feature, not an afterthought. We follow WCAG 2.1 Level AA standards to ensure all users can interact with the application effectively.

## Keyboard Navigation

### Global Shortcuts

- **Tab**: Navigate forward through interactive elements
- **Shift + Tab**: Navigate backward through interactive elements
- **Enter**: Activate buttons, links, and submit forms
- **Space**: Toggle checkboxes, select items, activate buttons
- **Escape**: Close modals, cancel operations, exit focus traps

### Skip Links

Every page includes a "Skip to main content" link as the first focusable element. Press **Tab** on page load to access it, then **Enter** to jump directly to the main content area, bypassing navigation.

### Character Selection Screen

- **Tab/Shift+Tab**: Navigate between character cards and action buttons
- **Arrow Keys**: Navigate within the character grid
  - **Left/Right**: Move between characters in the same row
  - **Up/Down**: Move between rows
- **Enter/Space**: Select or deselect a character
- **Home**: Jump to first character
- **End**: Jump to last character

### Focus Management

- Visual focus indicators are always visible (2px solid outline)
- Focus order follows logical reading order (left-to-right, top-to-bottom)
- Focus traps are implemented in modals to prevent focus from escaping
- Focus is restored to the triggering element when modals close

## Screen Reader Support

### Tested Screen Readers

- **NVDA** (Windows) - Primary test target
- **JAWS** (Windows) - Secondary test target
- **VoiceOver** (macOS/iOS) - Supported
- **TalkBack** (Android) - Supported

### Screen Reader Features

#### Live Regions

The application uses ARIA live regions to announce dynamic content changes:

- **Selection Counter**: `aria-live="polite"` - Announces character selection count changes
- **Validation Errors**: `aria-live="assertive"` - Immediately announces form errors
- **Loading States**: `role="status" aria-busy="true"` - Announces loading progress

#### Semantic HTML

We use semantic HTML5 elements for proper document structure:
- `<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<footer>`
- Headings follow hierarchical order (H1 → H2 → H3)
- Buttons use `<button>` elements (never clickable `<div>` elements)

#### ARIA Attributes

All interactive elements include appropriate ARIA attributes:

```html
<!-- Character Card Example -->
<div
  role="button"
  tabIndex={0}
  aria-label="Select character Aragorn"
  aria-pressed="false"
  data-testid="character-card-aragorn"
>
  ...
</div>
```

### Screen Reader Testing Checklist

- [ ] All images have descriptive alt text
- [ ] Form inputs have associated labels
- [ ] Error messages are announced
- [ ] Dynamic content changes are announced via live regions
- [ ] Modal dialogs trap focus and announce their purpose
- [ ] Loading states are announced
- [ ] Navigation landmarks are properly labeled

## Visual Accessibility

### Color Contrast

All text meets WCAG AA contrast requirements:
- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text** (18pt+): Minimum 3:1 contrast ratio
- **UI components**: Minimum 3:1 contrast ratio

Use `npm run tokens:check` to validate color contrast ratios.

### High Contrast Mode

The application supports Windows High Contrast Mode and macOS Increase Contrast:
- All UI elements remain visible
- Focus indicators are enhanced
- Custom colors are overridden by system colors

Test in:
- **Windows**: Settings → Ease of Access → High Contrast
- **macOS**: System Preferences → Accessibility → Display → Increase Contrast

### Reduced Motion

Users who prefer reduced motion see minimal or no animations:
- `@media (prefers-reduced-motion: reduce)` disables animations
- Skeleton loading screens use static states instead of pulse animations
- Page transitions are instant instead of animated

Test by enabling:
- **Windows**: Settings → Ease of Access → Display → Show animations
- **macOS**: System Preferences → Accessibility → Display → Reduce motion

## Component Usage Examples

### Accessible Button

```tsx
import React from 'react';

// Good - Accessible button
<button
  onClick={handleClick}
  aria-label="Delete character Aragorn"
  disabled={isProcessing}
>
  Delete
</button>

// Bad - Inaccessible div
<div onClick={handleClick}>Delete</div>
```

### Accessible Form Input

```tsx
import React from 'react';

// Good - Accessible input with label
<div>
  <label htmlFor="character-name">Character Name</label>
  <input
    id="character-name"
    type="text"
    value={name}
    onChange={handleChange}
    aria-required="true"
    aria-invalid={hasError}
    aria-describedby={hasError ? 'name-error' : undefined}
  />
  {hasError && (
    <span id="name-error" role="alert">
      Character name is required
    </span>
  )}
</div>
```

### Accessible Modal

```tsx
import React, { useEffect, useRef } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';

const Modal: React.FC = ({ isOpen, onClose, children }) => {
  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(modalRef, isOpen);

  useEffect(() => {
    if (isOpen) {
      // Set focus to first focusable element
      modalRef.current?.querySelector('button')?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <h2 id="modal-title">Modal Title</h2>
      {children}
      <button onClick={onClose}>Close</button>
    </div>
  );
};
```

## Performance Profiling

### Core Web Vitals Targets

- **LCP (Largest Contentful Paint)**: < 2.5s
- **FID (First Input Delay)**: < 100ms
- **CLS (Cumulative Layout Shift)**: < 0.1
- **FCP (First Contentful Paint)**: < 1.8s
- **TTFB (Time to First Byte)**: < 600ms

### Performance Testing

1. **Local Testing**:
```bash
cd frontend
npm run build
npm run preview
# Open Chrome DevTools → Lighthouse
```

2. **CI Testing**:
```bash
# Lighthouse CI runs automatically on PRs
# Check .lighthouseci/reports/ for results
```

3. **Production Monitoring**:
```tsx
// Web Vitals are automatically tracked in production
// Check browser console for metrics
// Metrics are sent to LoggerFactory
```

### Performance Optimization Checklist

- [ ] Images are optimized and lazy-loaded
- [ ] Code splitting is implemented (React.lazy)
- [ ] Bundle size < 400KB gzip (initial)
- [ ] Route chunks < 200KB gzip each
- [ ] Skeleton screens prevent layout shift (CLS < 0.1)
- [ ] React.memo used for expensive components
- [ ] useMemo/useCallback prevent unnecessary re-renders

## WCAG 2.1 AA Compliance Checklist

### Perceivable

- [ ] 1.1.1 Non-text Content: All images have alt text
- [ ] 1.3.1 Info and Relationships: Semantic HTML used
- [ ] 1.4.3 Contrast (Minimum): 4.5:1 for normal text, 3:1 for large text
- [ ] 1.4.11 Non-text Contrast: 3:1 for UI components

### Operable

- [ ] 2.1.1 Keyboard: All functionality available via keyboard
- [ ] 2.1.2 No Keyboard Trap: Focus can move away from all elements
- [ ] 2.4.3 Focus Order: Logical tab order
- [ ] 2.4.7 Focus Visible: Clear focus indicators

### Understandable

- [ ] 3.1.1 Language of Page: `lang` attribute set on `<html>`
- [ ] 3.2.1 On Focus: No context changes on focus
- [ ] 3.3.1 Error Identification: Errors clearly described
- [ ] 3.3.2 Labels or Instructions: Form inputs have labels

### Robust

- [ ] 4.1.2 Name, Role, Value: ARIA attributes correctly used
- [ ] 4.1.3 Status Messages: Live regions for dynamic content

## Testing Tools

### Automated Testing

```bash
# Run accessibility tests
cd frontend
npm test -- accessibility

# Run Lighthouse audit
npm run build
npx lighthouse http://localhost:3000 --view

# Check bundle sizes
npm run size
```

### Manual Testing

1. **Keyboard Navigation**: Navigate entire app using only keyboard
2. **Screen Reader**: Test with NVDA/JAWS/VoiceOver
3. **High Contrast**: Enable system high contrast mode
4. **Zoom**: Test at 200% zoom level
5. **Reduced Motion**: Enable prefers-reduced-motion

### Browser Extensions

- **axe DevTools**: Automated accessibility testing
- **WAVE**: Visual accessibility evaluation
- **Lighthouse**: Performance and accessibility audits
- **HeadingsMap**: Verify heading structure

## Resources

### WCAG Guidelines
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM WCAG Checklist](https://webaim.org/standards/wcag/checklist)

### Testing Tools
- [NVDA Screen Reader](https://www.nvaccess.org/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)

### Best Practices
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)
- [Inclusive Components](https://inclusive-components.design/)

## Support

If you encounter accessibility issues, please report them via:
- GitHub Issues: Tag with `accessibility` label
- Include browser, screen reader, and operating system details
- Provide steps to reproduce the issue
