# ADR-005: Zustand Store Architecture

**Status**: Accepted
**Date**: 2026-02-03
**Deciders**: Architecture Team

## Context

The Novel Engine frontend requires consistent state management across multiple concerns: authentication, orchestration, narrative decisions, and graph visualization. Several patterns were considered for organizing client-side state.

### Requirements

1. **Type Safety**: Strict TypeScript integration with no `any` types
2. **Separation of Concerns**: Clear boundaries between different state domains
3. **Testing Support**: Easy to test state mutations and selector behavior
4. **Performance**: Efficient re-renders and minimal prop drilling
5. **Scalability**: Architecture supports growth without major refactoring

## Decision

We will use **Zustand** for global UI state with a **feature-based store organization** strategy. Server state is managed by **TanStack Query**, form state by **React Hook Form**, and component-local state by `useState`.

### State Management Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    State Type Priority                      │
├─────────────────────────────────────────────────────────────┤
│  1. Server State    → TanStack Query (API data, caching)   │
│  2. Global UI State → Zustand (theme, sidebar, modals)     │
│  3. Form State      → React Hook Form (validation)         │
│  4. Local State     → useState (temporary UI only)         │
└─────────────────────────────────────────────────────────────┘
```

### Store Architecture

| Store | Location | Domain | Persistence | Exports |
|-------|----------|--------|-------------|---------|
| `authStore` | `features/auth/stores/` | Authentication | localStorage (token, user) | 5 hooks |
| `orchestrationStore` | `features/dashboard/stores/` | Pipeline UI simulation | None | 1 store |
| `decisionStore` | `features/decision/` | Narrative decisions | None | 2 exports |
| `weaverStore` | `features/weaver/store/` | React Flow graph | None | 13 hooks |

### Store Creation Guidelines

**When to Create a New Store:**

```typescript
// Create a store when:
// 1. State is shared across ≥3 components
// 2. State has complex actions (>3 related mutations)
// 3. State needs to survive component unmount
// 4. State is NOT server data (use TanStack Query)
// 5. State is NOT form data (use React Hook Form)

// ✅ Good: weaverStore manages complex graph state
interface WeaverState {
  nodes: Node[];
  edges: Edge[];
  selectedIds: string[];
  // ... 10+ related state pieces
}

// ❌ Bad: Creating store for single-component state
interface LocalToggleState {
  isOpen: boolean;  // Just use useState
}
```

**When to Extend Existing Stores:**

```typescript
// Add to existing store when logically related
// Example: Adding plotline filtering to weaverStore

interface WeaverState {
  // ... existing state
  filteredPlotlineId: string | null;  // Related to graph filtering
}
```

### Implementation Pattern

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 1. Define state and actions separately
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

type AuthStore = AuthState & AuthActions;

// 2. Create store with typed actions
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,

      // Actions
      login: async (credentials) => {
        const response = await authApi.login(credentials);
        set({ user: response.user, token: response.token, isAuthenticated: true });
      },
      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },
      setUser: (user) => {
        set({ user, isAuthenticated: !!user });
      },
    }),
    {
      name: 'auth-storage',  // localStorage key
      partialize: (state) => ({  // Only persist critical fields
        token: state.token,
        user: state.user,
      }),
    }
  )
);

// 3. Export selector hooks for common patterns
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useCurrentUser = () => useAuthStore((state) => state.user);
export const useAuthActions = () => useAuthStore((state) => ({
  login: state.login,
  logout: state.logout,
}));
```

## Alternatives Considered

### 1. **Redux with Redux Toolkit**

The industry standard for complex state management.

**Pros**:
- Large ecosystem and community
- Excellent DevTools
- Time-travel debugging
- Middleware ecosystem

**Cons**:
- Significant boilerplate
- Steeper learning curve
- Overkill for our state complexity
- Bundle size impact

**Rejected for**: Zustand provides 80% of benefits with 20% of boilerplate.

### 2. **Jotai**

Atomic state management with primitive-based atoms.

**Pros**:
- Very lightweight
- Flexible composition
- Good for fine-grained reactivity

**Cons**:
- Less opinionated structure
- Many atoms to manage for complex features
- Different paradigm from component mental model

**Rejected for**: Zustand's feature-based organization matches our folder structure better.

### 3. **Recoil**

Facebook's experimental state management library.

**Pros**:
- React-first design
- Atom-based with selectors
- Good async support

**Cons**:
- Experimental status (stability concerns)
- Less mature ecosystem
- Facebook has moved away from it

**Rejected for**: Zustand is more stable and actively maintained.

### 4. **Single Global Store**

One Zustand store for all application state.

**Pros**:
- Single source of truth
- Easy to debug (one place to look)
- Simple state sharing

**Cons**:
- Action naming conflicts as app grows
- Bundle bloat (entire state loaded)
- Team merge conflicts
- Harder to understand store boundaries

**Rejected for**: Feature-based stores provide clear ownership boundaries.

## Consequences

### Positive

1. **Low Boilerplate**: Minimal setup compared to Redux
2. **Type Safety**: Full TypeScript inference with no `any`
3. **Feature Co-location**: Stores live with their features
4. **Selector Optimization**: Hooks prevent unnecessary re-renders
5. **Simple Testing**: Easy to test with `zustand/middleware`
6. **Good Performance**: Only subscribed components re-render
7. **Clear Boundaries**: Each store has distinct responsibility

### Negative

1. **No DevTools**: Limited debugging compared to Redux DevTools
2. **Middleware Scarcity**: Fewer community middleware options
3. **Learning Curve**: Team must understand Zustand patterns
4. **Persistence Manual**: Must configure partialize for selective persistence
5. **No Time Travel**: Can't replay state changes

### Risks and Mitigation

**Risk**: Stores grow too large and become unmanageable
**Mitigation**: Split stores by sub-feature when >300 lines; use selector hooks to encapsulate complexity

**Risk**: Duplicated state across stores (drift)
**Mitigation**: State management documentation (CIT-005) audits for overlap

**Risk**: Over-reliance on global state for component-local concerns
**Mitigation**: Code review enforces useState for single-component state

**Risk**: Orchestration UI state conflicts with future SSE implementation
**Mitigation**: Documented that orchestrationStore is temporary; will migrate to TanStack Query

## Implementation Notes

### Store Splitting Decision Tree

```
                    Does state need to exist?
                          │
                    ┌─────┴─────┐
                    │           │
                   No          Yes
                    │           │
                    │           Is it server data?
                    │           │
                    │      ┌────┴────┐
                    │      │         │
                    │     Yes       No
                    │      │         │
                    │      │         Is it form data?
                    │      │         │
                    │      │    ┌────┴────┐
                    │      │    │         │
                    │      │   Yes       No
                    │      │    │         │
                    │      │    │         Shared by ≥3 components?
                    │      │    │         │
                    │      │    │    ┌────┴────┐
                    │      │    │    │         │
                    │      │    │   Yes       No
                    │      │    │    │         │
    Don't create   TanStack  RHF   Zustand   useState
                    Query   Form  Store
```

### Persistence Strategy

Only persist what's necessary for user experience:

```typescript
// ✅ Persist: Authentication token, user preferences
persist(
  (set) => ({ /* ... */ }),
  { name: 'auth-storage', partialize: (s) => ({ token: s.token, user: s.user }) }
)

// ❌ Don't persist: Loading states, temporary selections, form drafts
// These should reset on page refresh
```

### Testing Patterns

```typescript
import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from './authStore';

describe('authStore', () => {
  it('should login successfully', async () => {
    const { result } = renderHook(() => useAuthStore());

    await act(async () => {
      await result.current.login({ username: 'test', password: 'pass' });
    });

    expect(result.current.isAuthenticated).toBe(true);
  });
});
```

## Store Summaries

### authStore (388 lines)

**Purpose**: Manages user authentication and session lifecycle

**State**:
- `user: User | null` - Current authenticated user
- `token: string | null` - JWT authentication token
- `isAuthenticated: boolean` - Derived auth state
- `isLoading: boolean` - Login/logout pending state

**Actions**:
- `login(credentials)` - Authenticate and store token
- `logout()` - Clear session
- `setUser(user)` - Update user object

**Persistence**: localStorage (token, user only)

**Selector Hooks**:
- `useIsAuthenticated()`
- `useCurrentUser()`
- `useAuthActions()`

### orchestrationStore (90 lines)

**Purpose**: UI simulation of orchestration pipeline phases

**State**:
- `currentPhase: string` - Active pipeline phase
- `isRunning: boolean` - Pipeline execution state
- `completedPhases: string[]` - History of completed phases

**Note**: This is temporary UI simulation. Will migrate to TanStack Query when SSE is implemented.

### decisionStore (114 lines)

**Purpose**: Manages narrative decision flow and user input

**State**:
- `pendingDecision: Decision | null` - Current decision awaiting input
- `decisionHistory: Decision[]` - Past decisions for context

**Actions**:
- `presentDecision(decision)` - Show new decision
- `submitDecision(optionId)` - Record choice

**E2E Interface**: Exposed for testing via `window.__DECISION_STORE__`

### weaverStore (194 lines)

**Purpose**: Manages React Flow graph state for visual orchestration

**State**:
- `nodes: Node[]` - Flow graph nodes
- `edges: Edge[]` - Flow graph edges
- `selectedIds: string[]` - Selected element IDs
- `filteredPlotlineId: string | null` - Plotline filter

**Actions**:
- `setNodes(nodes)`, `setEdges(edges)` - Update graph
- `addNode(node)`, `removeNode(id)` - Mutate nodes
- `selectElements(ids)` - Handle selection

**Selector Hooks**: 13 hooks for specific graph queries

**E2E Interface**: Exposed for testing via `window.__WEAVER_STORE__`

## Related Decisions

- FE-001: Frontend styling SSOT and server-state standardization
- CIT-005: State management consolidation audit
- ADR-003: Pydantic Schema Architecture

## Status Changes

- 2026-02-03: Proposed and accepted as part of Code Citadel documentation effort
