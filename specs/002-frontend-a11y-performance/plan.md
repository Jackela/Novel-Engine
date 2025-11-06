# Implementation Plan: Frontend Accessibility & Performance Optimization

**Branch**: `002-frontend-a11y-performance` | **Date**: 2025-11-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-frontend-a11y-performance/spec.md`

## Summary

Implement WCAG 2.1 AA accessibility compliance and React performance optimization for the Novel-Engine frontend application. This feature adds keyboard navigation, screen reader support, performance optimizations (memoization, code splitting), loading states (skeleton screens), and bundle size optimization to improve accessibility for disabled users and performance for users with slow devices or connections.

**Primary Requirements**:
- Keyboard navigation for all interactive elements with visible focus indicators
- Screen reader support with proper ARIA attributes and semantic HTML
- Performance optimization through React.memo, useCallback, useMemo, and code splitting
- Skeleton loading states matching final content layout
- Bundle size reduction via tree-shaking and vendor chunk separation

**Technical Approach**:
- Build reusable accessible component primitives (KeyboardButton, FocusTrap, SkipLink)
- Refactor existing components (CharacterSelection, Dashboard, modals) to use accessible patterns
- Implement route-based code splitting with React.lazy() and Suspense
- Add Lighthouse CI and jest-axe for automated accessibility/performance testing
- Configure ESLint jsx-a11y plugin for linting enforcement

## Technical Context

**Language/Version**: TypeScript 5.x (frontend), React 18.2+  
**Primary Dependencies**: React 18.2, React Router 6, Vite 4, Material-UI (@mui/material), i18next, React Query  
**Storage**: N/A (frontend-only feature, no backend storage changes)  
**Testing**: Vitest 4.x (unit tests with jest-axe), Playwright (E2E accessibility testing), Lighthouse CI (automated audits)  
**Target Platform**: Web browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+), ES2020+ support  
**Project Type**: Web application (frontend-only changes to existing `frontend/` directory)  
**Performance Goals**: 
- Lighthouse Accessibility score ≥ 90
- Lighthouse Performance score ≥ 90
- Initial bundle < 400KB (gzip)
- Route chunks < 200KB (gzip)
- Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
- 60fps scrolling on 4x CPU slowdown

**Constraints**:
- No breaking changes to existing component APIs
- Progressive rollout (feature flags available if needed)
- WCAG 2.1 AA compliance (not AAA)
- Modern browsers only (no IE11 polyfills)

**Scale/Scope**:
- ~30 existing components to audit/refactor
- 5 new accessible component primitives
- 3 primary routes (character selection, dashboard, story workshop)
- ~500 lines of new accessible component code
- ~1000 lines of refactored component code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Article I - Domain-Driven Design (DDD)**: 
  - **Bounded Context**: Frontend UI/UX domain only; no backend business logic changes
  - **Domain Model**: Accessible components (KeyboardButton, FocusTrap, SkipLink) are pure UI domain entities with no backend coupling
  - **Infrastructure**: Performance monitoring (web-vitals), build tooling (Vite, Lighthouse CI), testing (jest-axe) properly separated as infrastructure concerns
  - ✅ **Compliance**: No domain model contamination, infrastructure properly isolated

- **Article II - Ports & Adapters**: 
  - **Ports**: `IAccessibleComponent` interface for accessibility primitives, `IPerformanceMonitor` for metrics collection
  - **Adapters**: Concrete implementations (KeyboardButton, FocusTrap) adapt DOM/React APIs to WCAG requirements
  - **Dependency Inversion**: Components depend on WCAG abstractions (aria-* specs), not browser-specific implementations
  - ✅ **Compliance**: Proper port/adapter separation, dependencies inverted toward standards

- **Article III - Test-Driven Development (TDD)**: 
  - **Red Phase**: Write failing jest-axe tests (expect(results).toHaveNoViolations())
  - **Green Phase**: Implement ARIA attributes, keyboard handlers, focus management
  - **Refactor Phase**: Extract reusable accessible primitives, optimize performance hooks
  - **Coverage Targets**: ≥ 90% for new accessible components, ≥ 80% for refactored components
  - ✅ **Compliance**: TDD workflow followed, coverage targets defined

- **Article IV - Single Source of Truth (SSOT)**: 
  - **Database Changes**: None (frontend-only)
  - **Cache Strategy**: None (frontend-only)
  - **SSOT**: Design system CSS variables in `frontend/src/index.css` remain SSOT for focus indicators
  - **Vite Config**: `frontend/vite.config.ts` is SSOT for bundle splitting rules and performance thresholds
  - ✅ **Compliance**: No SSOT conflicts, existing sources preserved

- **Article V - SOLID Principles**: 
  - **SRP**: Each accessible component has single responsibility (KeyboardButton → activation, FocusTrap → containment)
  - **OCP**: Components open for extension (custom styling, ARIA props) but closed for modification (core a11y behavior fixed)
  - **LSP**: All accessible components implement common interface, substitutable (KeyboardButton replaces any button)
  - **ISP**: Separate interfaces for keyboard (IKeyboardHandler), focus (IFocusManager), ARIA (IAriaAnnouncer)
  - **DIP**: Components depend on WCAG abstractions, not concrete DOM APIs
  - ✅ **Compliance**: All SOLID principles applied to accessible components

- **Article VI - Event-Driven Architecture (EDA)**: 
  - **Domain Events**: None published (UI updates are synchronous React state changes, not domain events)
  - **Event Subscriptions**: None needed
  - **Kafka Topics**: N/A (frontend-only)
  - **Async Communication**: N/A (frontend-only)
  - ✅ **Compliance**: No event-driven requirements for this feature

- **Article VII - Observability**: 
  - **Structured Logging**: Log keyboard navigation errors, focus trap failures via LoggerFactory
  - **Prometheus Metrics**: Track Core Web Vitals (LCP, FID, CLS) as custom metrics
  - **OpenTelemetry Tracing**: Add spans for lazy-loaded component rendering, bundle chunk loading
  - ✅ **Compliance**: Observability integrated into accessible components and performance monitoring

- **Constitution Compliance Review Date**: 2025-11-05 (✅ No violations)

## Project Structure

### Documentation (this feature)

```text
specs/002-frontend-a11y-performance/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technology research)
├── data-model.md        # Phase 1 output (component interface contracts)
├── quickstart.md        # Phase 1 output (developer guide for accessible components)
├── contracts/           # Phase 1 output (TypeScript interfaces)
│   ├── IAccessibleComponent.ts
│   ├── IKeyboardHandler.ts
│   ├── IFocusManager.ts
│   └── IPerformanceMonitor.ts
└── checklists/
    └── requirements.md  # Quality validation checklist (completed)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── a11y/                      # NEW: Accessible component primitives
│   │   │   ├── KeyboardButton.tsx     # Keyboard-accessible button
│   │   │   ├── FocusTrap.tsx          # Focus trap for modals
│   │   │   ├── SkipLink.tsx           # Skip navigation link
│   │   │   ├── VisuallyHidden.tsx     # Screen reader-only content
│   │   │   └── index.ts               # Barrel export
│   │   ├── loading/                   # NEW: Loading state components
│   │   │   ├── SkeletonCard.tsx       # Skeleton for character cards
│   │   │   ├── SkeletonDashboard.tsx  # Skeleton for dashboard
│   │   │   └── index.ts               # Barrel export
│   │   ├── CharacterSelection.tsx     # REFACTOR: Add keyboard nav + ARIA
│   │   ├── Dashboard.tsx              # REFACTOR: Performance optimization
│   │   └── [other existing components to refactor]
│   ├── hooks/
│   │   ├── useKeyboardNav.ts          # NEW: Keyboard navigation hook
│   │   ├── useFocusTrap.ts            # NEW: Focus trap hook
│   │   └── usePerformance.ts          # NEW: Performance monitoring hook
│   ├── services/
│   │   └── performance/               # NEW: Performance monitoring
│   │       └── WebVitalsMonitor.ts    # Core Web Vitals tracking
│   └── types/
│       └── accessibility.ts           # NEW: TypeScript interfaces for a11y
├── tests/
│   ├── unit/
│   │   └── a11y/                      # NEW: Accessibility unit tests
│   │       ├── KeyboardButton.test.tsx
│   │       ├── FocusTrap.test.tsx
│   │       └── [other a11y tests]
│   ├── integration/
│   │   └── accessibility/             # NEW: Accessibility integration tests
│   │       └── keyboard-navigation.test.tsx
│   └── e2e/
│       └── accessibility.spec.ts      # NEW: Playwright accessibility tests
├── vite.config.ts                     # UPDATE: Code splitting configuration
├── .lighthouserc.json                 # NEW: Lighthouse CI configuration
├── .eslintrc.json                     # UPDATE: Add jsx-a11y plugin
└── package.json                       # UPDATE: Add dependencies (jest-axe, @axe-core/react)
```

**Structure Decision**: Web application (Option 2) - This is a frontend-only feature modifying the existing `frontend/` directory. No backend changes required. New directories: `src/components/a11y/`, `src/components/loading/`, `src/hooks/` (extended), `src/services/performance/`, `tests/unit/a11y/`, `tests/integration/accessibility/`, `tests/e2e/` (extended).

## Complexity Tracking

> **No violations requiring justification**

All Constitution articles compliant. No additional complexity introduced beyond necessary accessibility/performance infrastructure.

---

## Phase 0: Research & Technology Selection

**Goal**: Document technology choices, accessibility standards, and performance best practices.

**Output**: `research.md` containing:

### Accessibility Standards & Tools

**WCAG 2.1 AA Requirements**:
- Document specific success criteria (1.3.1 Info and Relationships, 2.1.1 Keyboard, 2.4.7 Focus Visible, 4.1.2 Name, Role, Value)
- Map requirements to implementation patterns (semantic HTML, ARIA attributes, keyboard handlers)

**Testing Tools**:
- **jest-axe** (version ^4.8.0): Automated accessibility testing in unit tests
- **@axe-core/react** (version ^4.8.0): Runtime accessibility monitoring in development
- **Lighthouse CI** (version ^0.12.0): Automated audits in CI/CD pipeline
- **Playwright** (existing): E2E keyboard navigation and screen reader testing

**Screen Readers**:
- NVDA (Windows, primary): Free, widely used, excellent ARIA support
- VoiceOver (macOS, primary): Built-in, good ARIA support
- JAWS (optional): Commercial, comprehensive but not required for WCAG 2.1 AA

### Performance Optimization Techniques

**React Performance Patterns**:
- **React.memo**: Prevent re-renders when props unchanged (use for list items, cards)
- **useCallback**: Memoize event handlers (use in parent components passing callbacks to children)
- **useMemo**: Memoize expensive calculations (use for filtering, sorting, transformations)
- **React.lazy() + Suspense**: Route-based code splitting (use for top-level pages)

**Bundle Optimization**:
- **Vite manualChunks**: Separate vendor libraries (React, MUI, Three.js, D3) into cached chunks
- **Tree-shaking**: Remove unused code (already configured in Vite, verify with bundle analyzer)
- **Terser compression**: Minify JavaScript with drop_console: true for production

**Loading States**:
- **Skeleton Screens**: Match final content layout to prevent CLS (Cumulative Layout Shift)
- **Suspense Boundaries**: Graceful loading fallbacks for lazy-loaded components
- **aria-busy + role="status"**: Accessible loading indicators

### Dependencies to Add

```json
{
  "devDependencies": {
    "jest-axe": "^4.8.0",
    "@axe-core/react": "^4.8.0",
    "eslint-plugin-jsx-a11y": "^6.8.0",
    "@lhci/cli": "^0.12.0",
    "vite-plugin-bundle-visualizer": "^1.0.0"
  },
  "dependencies": {
    "web-vitals": "^3.5.0"
  }
}
```

### Browser Support Matrix

| Browser | Version | Support Level | Notes |
|---------|---------|---------------|-------|
| Chrome | 90+ | Full | Baseline for testing |
| Edge | 90+ | Full | Chromium-based |
| Firefox | 88+ | Full | Test for ARIA differences |
| Safari | 14+ | Full | Test for VoiceOver compatibility |
| IE11 | N/A | Not supported | No polyfills needed |

### ARIA Patterns to Implement

| Pattern | Use Case | Components Affected |
|---------|----------|---------------------|
| Button (role="button") | Interactive cards | CharacterSelection cards |
| Dialog (role="dialog", aria-modal) | Modal overlays | All modals |
| Live Region (aria-live) | Dynamic updates | Selection counter, notifications |
| Tab Navigation (role="tablist") | Dashboard tabs | Dashboard component |
| Skip Links | Keyboard navigation | App.tsx (global) |

---

## Phase 1: Design & Contracts

**Goal**: Define component interfaces, data models, and developer quickstart guide.

**Outputs**: `data-model.md`, `contracts/*.ts`, `quickstart.md`

### Data Model (`data-model.md`)

**Accessible Component Interface**:
```typescript
interface IAccessibleComponent {
  // Keyboard support
  tabIndex: number;
  onKeyDown: (event: KeyboardEvent) => void;
  
  // ARIA attributes
  role: string;
  ariaLabel?: string;
  ariaPressed?: boolean;
  ariaExpanded?: boolean;
  
  // Focus management
  ref: React.RefObject<HTMLElement>;
  autoFocus?: boolean;
}
```

**Keyboard Handler Interface**:
```typescript
interface IKeyboardHandler {
  handleEnterKey: (event: KeyboardEvent) => void;
  handleSpaceKey: (event: KeyboardEvent) => void;
  handleEscapeKey: (event: KeyboardEvent) => void;
  handleArrowKeys: (event: KeyboardEvent) => void;
}
```

**Focus Manager Interface**:
```typescript
interface IFocusManager {
  trapFocus: (containerRef: React.RefObject<HTMLElement>) => void;
  restoreFocus: (previousFocusRef: React.RefObject<HTMLElement>) => void;
  getFirstFocusable: (containerRef: React.RefObject<HTMLElement>) => HTMLElement | null;
  getLastFocusable: (containerRef: React.RefObject<HTMLElement>) => HTMLElement | null;
}
```

**Performance Monitor Interface**:
```typescript
interface IPerformanceMonitor {
  trackWebVitals: () => void;
  reportMetric: (metric: PerformanceMetric) => void;
  
  // Core Web Vitals
  LCP: number; // Largest Contentful Paint
  FID: number; // First Input Delay
  CLS: number; // Cumulative Layout Shift
}

interface PerformanceMetric {
  name: 'LCP' | 'FID' | 'CLS' | 'FCP' | 'TTFB';
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
}
```

### Component Contracts (`contracts/`)

Create TypeScript interface files in `specs/002-frontend-a11y-performance/contracts/`:
- `IAccessibleComponent.ts`: Base interface for all accessible components
- `IKeyboardHandler.ts`: Keyboard event handling contract
- `IFocusManager.ts`: Focus trap and management contract
- `IPerformanceMonitor.ts`: Performance metrics tracking contract

### Developer Quickstart (`quickstart.md`)

**Content**:
1. **Setup**: Install dependencies (`npm install`)
2. **Using Accessible Components**: Import and usage examples
3. **Testing Accessibility**: Running jest-axe tests, manual keyboard testing
4. **Performance Profiling**: React DevTools Profiler, Chrome DevTools Performance
5. **Linting**: ESLint jsx-a11y rules and fixes
6. **CI/CD**: Lighthouse CI integration and thresholds

**Example Snippets**:
```tsx
// Using KeyboardButton
import { KeyboardButton } from '@/components/a11y';

<KeyboardButton
  onClick={handleClick}
  ariaLabel="Select character"
  ariaPressed={isSelected}
>
  Character Name
</KeyboardButton>
```

```tsx
// Using FocusTrap in modal
import { FocusTrap } from '@/components/a11y';

<FocusTrap>
  <div role="dialog" aria-modal="true" aria-labelledby="modal-title">
    {/* Modal content */}
  </div>
</FocusTrap>
```

```tsx
// Performance optimization with React.memo
import { memo } from 'react';

const CharacterCard = memo(({ name, isSelected, onSelect }) => {
  // Component implementation
}, (prevProps, nextProps) => {
  // Custom comparison for optimization
  return prevProps.isSelected === nextProps.isSelected;
});
```

---

## Phase 2: Implementation Roadmap

**Note**: Detailed task breakdown will be generated by `/speckit.tasks` command (not part of this plan).

### High-Level Milestones

**Week 1: Foundation (P1 - Keyboard & Screen Reader)**
- Create accessible component primitives (KeyboardButton, FocusTrap, SkipLink, VisuallyHidden)
- Implement keyboard navigation hooks (useKeyboardNav, useFocusTrap)
- Write unit tests with jest-axe
- Set up ESLint jsx-a11y plugin

**Week 2: Component Refactoring (P1-P2)**
- Refactor CharacterSelection: keyboard nav, ARIA attributes, React.memo optimization
- Refactor Dashboard: performance hooks (useMemo, useCallback), lazy loading
- Refactor modals: FocusTrap integration, aria-modal
- Add skeleton loading states (SkeletonCard, SkeletonDashboard)

**Week 3: Testing & Automation (P2-P3)**
- Set up Lighthouse CI with GitHub Actions
- Implement Core Web Vitals tracking (web-vitals library)
- Route-based code splitting with React.lazy()
- Bundle size optimization and validation
- E2E accessibility tests with Playwright

### Testing Strategy

**Unit Tests** (jest-axe):
- Every accessible component has `expect(results).toHaveNoViolations()` test
- Keyboard event handling tests (Enter, Space, Escape)
- ARIA attribute validation tests

**Integration Tests** (Vitest):
- Keyboard navigation through CharacterSelection flow
- Focus trap behavior in modals
- Screen reader announcement validation (aria-live regions)

**E2E Tests** (Playwright):
- Complete keyboard-only user journey (character selection → dashboard)
- Screen reader compatibility (VoiceOver on Mac, NVDA on Windows)
- Performance benchmarks (Core Web Vitals under 3G throttling)

**CI/CD Automation**:
- Lighthouse CI: Fail PR if accessibility score < 90 or performance score < 90
- Bundle size limits: Fail PR if initial bundle > 400KB or route chunks > 200KB
- ESLint: Fail PR on jsx-a11y rule violations

### Performance Benchmarks

**Before Optimization (Baseline)**:
- Initial bundle: ~500KB (estimated from existing Vite config)
- CharacterSelection re-render count: 30+ per selection toggle (no memoization)
- Dashboard LCP: ~3.5s on 3G (no code splitting)

**After Optimization (Targets)**:
- Initial bundle: < 400KB (20% reduction via tree-shaking + vendor chunks)
- CharacterSelection re-render count: < 15 per toggle (50% reduction via React.memo)
- Dashboard LCP: < 2.5s on 3G (30% improvement via lazy loading)

---

## Risk Mitigation

| Risk | Mitigation Strategy | Contingency Plan |
|------|---------------------|------------------|
| **Screen reader inconsistencies** (NVDA vs. JAWS vs. VoiceOver) | Follow ARIA Authoring Practices Guide (APG), use semantic HTML first | Document known differences, prioritize NVDA + VoiceOver (90% coverage) |
| **Performance regression** from ARIA live regions | Profile before/after with React DevTools, limit live region frequency | Use throttling/debouncing for frequent updates, document trade-offs |
| **Bundle size increase** from new dependencies | Tree-shake unused code, lazy-load jest-axe (dev-only), monitor with size-limit | Remove optional dependencies, use dynamic imports for heavy libraries |
| **Breaking existing functionality** during refactoring | Maintain existing component APIs, add feature flags for gradual rollout | Rollback strategy via Git, comprehensive regression testing |
| **Lighthouse CI flakiness** (score variance) | Run 3 times per PR, use median score, allow ±5 variance | Cache dependencies to reduce network variability, use stable test environment |

---

## Success Validation

**Phase 0 Complete**: Research document committed with technology choices documented  
**Phase 1 Complete**: Contracts + quickstart guide committed, agent context updated  
**Implementation Ready**: All acceptance criteria from spec.md testable, Constitution compliance verified

**Next Command**: `/speckit.tasks` to generate detailed task breakdown and implementation workflow.
