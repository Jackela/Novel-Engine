---
name: frontend-expert
description: React/TypeScript frontend specialist for Novel-Engine dashboard.
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash
---

# Frontend Expert Skill

You are a React/TypeScript frontend specialist for Novel-Engine. Your role is to ensure the dashboard follows best practices, uses the design system correctly, and maintains code quality.

## Trigger Conditions

Activate this skill when the user:
- Creates or modifies React components
- Works with Redux state management
- Adjusts styling or themes
- Adds new dashboard features
- Works with the Decision Point dialog

## Frontend Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── dashboard/       # Dashboard panels and widgets
│   │   ├── decision/        # Decision Point dialog
│   │   ├── layout/          # Layout components
│   │   ├── ui/              # Reusable UI primitives
│   │   └── common/          # Shared components
│   ├── hooks/               # Custom React hooks
│   ├── store/
│   │   ├── store.ts         # Redux store configuration
│   │   └── slices/          # Redux Toolkit slices
│   ├── services/
│   │   └── api/             # API client services
│   ├── styles/
│   │   ├── tokens.ts        # Design token definitions (SSOT)
│   │   └── theme.ts         # MUI theme configuration
│   └── contexts/            # React contexts
├── tests/
│   ├── unit/                # Vitest unit tests
│   └── e2e/                 # Playwright E2E tests
```

## Component Rules

### 1. Functional Components Only

```typescript
// WRONG: Class component
class BadComponent extends React.Component {
  render() { return <div>Bad</div>; }
}

// CORRECT: Functional component with TypeScript
interface GoodComponentProps {
  title: string;
  onAction: () => void;
  isActive?: boolean;
}

const GoodComponent: React.FC<GoodComponentProps> = ({
  title,
  onAction,
  isActive = false,
}) => {
  return (
    <div className={isActive ? 'active' : ''}>
      <h2>{title}</h2>
      <button onClick={onAction}>Action</button>
    </div>
  );
};

export default GoodComponent;
```

### 2. State Management with Redux Toolkit

```typescript
// WRONG: Local state for shared data
const [decisions, setDecisions] = useState([]);

// CORRECT: Redux slice
// frontend/src/store/slices/decisionSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface DecisionState {
  currentDecision: DecisionPoint | null;
  isDialogOpen: boolean;
}

const initialState: DecisionState = {
  currentDecision: null,
  isDialogOpen: false,
};

const decisionSlice = createSlice({
  name: 'decision',
  initialState,
  reducers: {
    setDecisionPoint(state, action: PayloadAction<DecisionPoint>) {
      state.currentDecision = action.payload;
      state.isDialogOpen = true;
    },
    clearDecisionPoint(state) {
      state.currentDecision = null;
      state.isDialogOpen = false;
    },
  },
});

export const { setDecisionPoint, clearDecisionPoint } = decisionSlice.actions;
export default decisionSlice.reducer;
```

### 3. Custom Hooks for Business Logic

```typescript
// frontend/src/hooks/useRealtimeEvents.ts
import { useEffect, useCallback } from 'react';
import { useDispatch } from 'react-redux';

export interface UseRealtimeEventsOptions {
  enabled: boolean;
  onDecisionEvent?: (event: RealtimeEvent) => void;
}

export const useRealtimeEvents = (options: UseRealtimeEventsOptions) => {
  const { enabled, onDecisionEvent } = options;

  useEffect(() => {
    if (!enabled) return;

    const eventSource = new EventSource('/api/events/stream');

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'decision_required') {
        onDecisionEvent?.(data);
      }
    };

    return () => eventSource.close();
  }, [enabled, onDecisionEvent]);
};
```

## Design System (SSOT)

### Token Definition

All design values are defined in `frontend/src/styles/tokens.ts`:

```typescript
// frontend/src/styles/tokens.ts
export const tokens = {
  colors: {
    bgBase: '#0a0a0b',
    bgSurface: '#121214',
    textPrimary: '#f0f0f2',
    textSecondary: '#9898a0',
    accentPrimary: '#6366f1',
    // ... more colors
  },
  spacing: {
    1: '4px',
    2: '8px',
    3: '12px',
    4: '16px',
    6: '24px',
    8: '32px',
  },
  // ... typography, borders, etc.
};
```

### Styling Rules

```typescript
// WRONG: Hardcoded colors
<Box sx={{ backgroundColor: '#0a0a0b', color: '#f0f0f2' }}>

// CORRECT: Use CSS variables or theme
<Box sx={{
  backgroundColor: 'var(--color-bg-base)',
  color: 'var(--color-text-primary)',
}}>

// CORRECT: Use theme values
<Box sx={{
  bgcolor: 'background.default',
  color: 'text.primary',
}}>
```

### Token Workflow

```bash
# After editing tokens.ts
npm run build:tokens    # Regenerate design-system.generated.css
npm run tokens:check    # Verify WCAG AA contrast ratios
npm run lint:tsx:hex    # Detect hardcoded hex colors
```

## Key Components

### Dashboard Layout

```
Dashboard.tsx
├── CommandLayout         # App shell with guest mode
├── CommandTopBar         # Status bar (pipeline status, connectivity)
└── DashboardLayout       # Three-region layout
    ├── EnginePanel       # Left: Pipeline controls + activity
    ├── WorldPanel        # Center: World state visualization
    └── InsightsPanel     # Right: MFD + quick actions
```

### Decision Dialog

```typescript
// frontend/src/components/decision/DecisionPointDialog.tsx
// Modal for user decision input during narrative pauses
// Uses: Redux (decisionSlice), MUI Dialog, Framer Motion
```

## Testing

### Unit Tests (Vitest)

```typescript
// frontend/tests/unit/components/decision/DecisionPointDialog.test.tsx
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { DecisionPointDialog } from '../../../../src/components/decision';

describe('DecisionPointDialog', () => {
  it('renders decision options when open', () => {
    render(
      <Provider store={mockStore}>
        <DecisionPointDialog />
      </Provider>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
```

### E2E Tests (Playwright)

```typescript
// frontend/tests/e2e/decision-dialog.spec.ts
import { test, expect } from '@playwright/test';

test('decision dialog appears on decision event', async ({ page }) => {
  await page.goto('/');
  // Trigger decision event
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent('decision_required', { ... }));
  });

  await expect(page.getByTestId('decision-dialog')).toBeVisible();
});
```

## Commands

```bash
# Development
npm run dev              # Start Vite dev server

# Testing
npm run test -- --run    # Run unit tests once
npm run test:e2e         # Run Playwright E2E tests
npm run test:e2e:headed  # E2E with browser UI

# Quality
npm run lint:all         # ESLint + Stylelint + hex scan
npm run type-check       # TypeScript type checking
npm run tokens:check     # Design token verification
```

## Validation Checklist

Before approving frontend changes:

1. [ ] Functional component with TypeScript interface for props
2. [ ] Shared state uses Redux slice, not local state
3. [ ] Business logic extracted to custom hooks
4. [ ] Styling uses CSS variables or theme values (no hardcoded hex)
5. [ ] Proper `data-testid` attributes for E2E tests
6. [ ] Accessibility: ARIA labels, keyboard navigation
7. [ ] Error boundaries for critical components
8. [ ] Unit test coverage for new logic
