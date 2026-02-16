# State Management Architecture

## Overview

This document describes the Zustand store architecture for the Novel Engine frontend, including each store's purpose, state shape, actions, and consolidation strategy.

## Store Inventory

### 1. Auth Store

**Location:** `frontend/src/features/auth/stores/authStore.ts`

**Purpose:** Manages authentication state including logged-in users, guest sessions, and token lifecycle.

**State Shape:**
```typescript
interface AuthState {
  // Authentication status
  isAuthenticated: boolean;
  isGuest: boolean;
  isLoading: boolean;
  isInitialized: boolean;

  // Session data
  token: AuthToken | null;
  workspaceId: string | null;
  error: Error | null;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  enterGuestMode: () => Promise<void>;
  refreshToken: () => Promise<void>;
  clearError: () => void;
  initialize: () => Promise<void>;
}
```

**Key Features:**
- Persistent storage using Zustand `persist` middleware
- Automatic token refresh on initialization
- Guest mode support for E2E testing
- Exposes selector hooks for common use cases

**Selector Hooks:**
- `useIsAuthenticated()`
- `useIsGuest()`
- `useAuthLoading()`
- `useAuthUser()`
- `useAuthError()`

**Data Source:** Server state (auth API)

---

### 2. Orchestration Store

**Location:** `frontend/src/features/dashboard/stores/orchestrationStore.ts`

**Purpose:** Manages orchestration pipeline state, tracking phases and run status for the dashboard.

**State Shape:**
```typescript
interface OrchestrationState {
  runState: 'idle' | 'running' | 'paused';
  live: boolean;
  phases: PipelinePhase[];

  start: () => void;
  pause: () => void;
  stop: () => void;
  reset: () => void;
}

type PhaseStatus = 'pending' | 'processing' | 'completed';

interface PipelinePhase {
  name: string;
  status: PhaseStatus;
}
```

**Phases:**
1. World Update
2. Subjective Brief
3. Interaction Orchestration
4. Event Integration
5. Narrative Integration

**Key Features:**
- Simulates orchestration pipeline phases with timers
- Demo/simulation mode (400ms per phase)
- No server synchronization - purely UI state

**Data Source:** UI state (local simulation)

---

### 3. Decision Store

**Location:** `frontend/src/features/decision/decisionStore.ts`

**Purpose:** Manages narrative decision points presented to users during story execution, including option selection, free-text input, and negotiation results.

**State Shape:**
```typescript
interface DecisionState {
  // Current decision
  currentDecision: DecisionPoint | null;
  pauseState: string;

  // User input
  selectedOptionId: number | null;
  freeTextInput: string;
  inputMode: 'options' | 'freeText';
  remainingSeconds: number;

  // Submission state
  submitting: boolean;
  errorMessage: string | null;
  negotiationResult: NegotiationResult | null;

  // Actions
  setDecisionPoint: (decision: DecisionPoint) => void;
  clearDecisionPoint: () => void;
  selectOption: (optionId: number | null) => void;
  setInputMode: (mode: InputMode) => void;
  setFreeText: (text: string) => void;
  setRemainingSeconds: (seconds: number) => void;
  setSubmitting: (value: boolean) => void;
  setErrorMessage: (message: string | null) => void;
  setNegotiationResult: (result: NegotiationResult | null) => void;
}
```

**Related Types:**
```typescript
interface DecisionPoint {
  decisionId: string;
  decisionType: string;
  turnNumber: number;
  title: string;
  description: string;
  narrativeContext?: string;
  options: DecisionOption[];
  defaultOptionId?: number | null;
  timeoutSeconds: number;
  createdAt?: string;
  expiresAt?: string;
}

interface NegotiationResult {
  decisionId: string;
  feasibility: 'minor_adjustment' | 'not_possible' | 'accepted';
  explanation: string;
  adjustedAction?: string;
  alternatives?: string[];
}
```

**E2E Support:** `exposeDecisionStore.ts` provides a Redux-like interface for E2E testing.

**Data Source:** Hybrid - initial data from server (SSE), user input captured locally

---

### 4. Weaver Store

**Location:** `frontend/src/features/weaver/store/weaverStore.ts`

**Purpose:** Manages the React Flow graph state for the Weaver node-based orchestration UI, including nodes, edges, and orchestration parameters.

**State Shape:**
```typescript
type WeaverState = {
  nodes: WeaverNode[];
  edges: Edge[];
  startParams: Pick<OrchestrationStartRequest, 'total_turns' | 'setting' | 'scenario'>;
  filteredPlotlineId: string | null;

  setNodes: (nodes: WeaverNode[]) => void;
  setEdges: (edges: Edge[]) => void;
  setStartParams: (params: Partial<WeaverState['startParams']>) => void;
  setFilteredPlotlineId: (plotlineId: string | null) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: (connection: Connection) => void;
  addNode: (node: WeaverNode) => void;
  updateNode: (nodeId: string, updater: (node: WeaverNode) => WeaverNode) => void;
  getOrchestrationStartRequest: () => OrchestrationStartRequest;
};
```

**Node Types:**
- `character` - Character nodes with name, role, traits, status
- `location` - Setting/location nodes
- `event` - Event/scenario nodes
- `faction` - Faction nodes
- `world` - World-building nodes
- `scene` - Scene nodes (with plotline filtering)

**Selector Hooks (17 exported):**
- `useWeaverNodes()`
- `useWeaverEdges()`
- `useWeaverOnNodesChange()`
- `useWeaverOnEdgesChange()`
- `useWeaverOnConnect()`
- `useWeaverAddNode()`
- `useWeaverUpdateNode()`
- `useWeaverStartParams()`
- `useWeaverOrchestrationRequest()`
- `useWeaverNodeCount()`
- `useWeaverEdgeCount()`
- `useWeaverFilteredPlotlineId()`
- `useWeaverSetFilteredPlotlineId()`
- `useSelectedCharacterNode()`
- ... (plus internal access)

**E2E Support:** Exposes `window.__weaverStore` in dev mode.

**Data Source:** UI state (graph editor state)

---

## Store Responsibilities Matrix

| Store | Server State | UI State | Form State | Persistent | E2E Exposed |
|-------|-------------|----------|------------|------------|-------------|
| authStore | ✅ | ⚠️ (loading flags) | ❌ | ✅ (localStorage) | ❌ |
| orchestrationStore | ❌ | ✅ | ❌ | ❌ | ❌ |
| decisionStore | ⚠️ (initial) | ✅ | ✅ | ❌ | ✅ |
| weaverStore | ❌ | ✅ | ❌ | ❌ | ✅ |

---

## Overlapping Responsibilities Analysis

### 1. No Significant Overlap Detected

After analyzing all stores, **no direct overlapping responsibilities were found**. Each store has a distinct domain:

| Domain | Store |
|--------|-------|
| Authentication | authStore |
| Orchestration Pipeline UI | orchestrationStore |
| Narrative Decision Flow | decisionStore |
| Graph Editor State | weaverStore |

### 2. Potential Concerns (Non-Critical)

1. **Orchestration naming collision:**
   - `orchestrationStore` manages pipeline UI simulation
   - `weaverStore` has `getOrchestrationStartRequest()` for building API payloads
   - **Impact:** Low - different concerns (UI status vs. data preparation)

2. **Run state duplication risk:**
   - `orchestrationStore` has `runState: 'idle' | 'running' | 'paused'`
   - If we add live orchestration later, `decisionStore` might need similar state
   - **Impact:** Low - currently stores are independent

---

## Consolidation Strategy

### Recommendation: KEEP ALL STORES

**Rationale:**
1. Each store has a distinct, non-overlapping domain
2. Stores follow the feature-based organization pattern
3. No duplicated state or responsibilities found
4. Breaking them apart would violate the "one store per feature domain" principle

### Store Verdicts

| Store | Decision | Reasoning |
|-------|----------|-----------|
| authStore | **KEEP** | Well-scoped, follows auth best practices, properly persisted |
| orchestrationStore | **KEEP** | Separate concern from actual orchestration logic (UI simulation only) |
| decisionStore | **KEEP** | Distinct domain (narrative decisions), clean interface |
| weaverStore | **KEEP** | Manages complex graph state, many selectors, distinct purpose |

### No Migration Needed

Since no stores are being merged, split, or deprecated, **no migration is required**.

---

## State Management Best Practices

### When to Create a New Store

Create a new Zustand store when:

1. **Feature has complex state** (more than 3-4 related state variables)
2. **State needs to be shared** across multiple components in different parts of the tree
3. **State has complex actions** (business logic, computations)
4. **State should be persisted** across sessions

### When NOT to Create a Store

Avoid creating a store for:

1. **Server state** - Use TanStack Query (`@tanstack/react-query`) instead
2. **Form state** - Use React Hook Form for form handling
3. **Component-local state** - Use `useState` for temporary UI state
4. **Derived state** - Compute from existing state instead of storing

### Store Naming Conventions

- File: `{feature}Store.ts` or `{domain}/stores/{feature}Store.ts`
- Hook: `use{Feature}Store()` for full store access
- Selectors: `use{Feature}{Property}()` for specific state slices

---

## Future Considerations

### Potential Store Additions

1. **Director Store** - For the Director workflow orchestration (if state becomes complex)
2. **Narrative Store** - For editor state across scenes/chapters (if not using TanStack Query)

### Potential Store Migrations

1. **OrchestrationStore → TanStack Query**
   - When real orchestration status is connected to backend
   - Move from simulation to real-time SSE updates

2. **DecisionStore → TanStack Query for initial data**
   - Keep local form state in Zustand
   - Fetch decision points via React Query

---

## Related Documentation

- [CONVENTIONS.md](../../CONVENTIONS.md) - Frontend Architecture section
- [DESIGN_SYSTEM.md](../../DESIGN_SYSTEM.md) - State Management Hierarchy
- [ADR-005-state-management.md](../adr/ADR-005-state-management.md) - (To be created in CIT-008)

---

## Appendix: Store Metrics

| Store | Lines of Code | Exports | Selector Hooks | Persistence |
|-------|---------------|---------|----------------|-------------|
| authStore | 388 | 6 hooks + store | 5 | ✅ localStorage |
| orchestrationStore | 90 | 1 store | 0 | ❌ |
| decisionStore | 114 | 2 exports | 0 | ❌ |
| weaverStore | 194 | 1 store + 13 hooks | 13 | ❌ |
| **Total** | **786** | **23** | **18** | **1** |

Last updated: 2026-02-03 (CIT-005)
