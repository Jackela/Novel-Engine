# Frontend Design Guide & Vibe Coding Standards

## Core Philosophy: "Constraints > Speed"
We do not guess specific implementations. We define strict boundaries (Layouts, Tokens, State Ownership) and let execution fill the gaps within those rails.

---

## 0. Vibe Coding Protocol
Before writing any component or page, we must define the following artifacts. No code without specs.

### 0.1 Required Pre-Coding Artifacts
*   **User Story:** Who is this for? What problem does it solve?
    *   Example: "As a Commander, I need to see turn progress so I know if the simulation is stalled."
*   **Happy Path Flow:** Step-by-step user journey.
    *   Example: "1. Open Dashboard -> 2. See 'Processing' badge -> 3. Badge turns 'Active'."
*   **Layout Map:** Abstract structural definition using existing shells.
    *   Example:
        ```
        CommandLayout
         -> top: CommandTopBar -> main: PerformanceMetrics | WorldStateMap
        ```

---

## 1. Design System Constraints (The "Lego" Kit)
**Rule:** Use existing components. Do not invent ad-hoc HTML/CSS.

### 1.1 Core Components (Atoms)
*   **Buttons:** Always use `<Button>`, never `<button>`. Variants: `contained`, `outlined`, `text`.
*   **Text:** Always use `<Typography>` with `variant` (h1-h6, body1, caption). No raw font-size.
*   **Layout:** Use `<Stack>` (1D) or `<Grid>` (2D). Avoid raw `div` with flex styles if possible.
*   **Inputs:** `<TextField>`, `<Select>`, `<Checkbox>`.

### 1.2 Spacing & Styling
*   **Tokens Only:** All colors, spacing, and borders MUST come from `theme.ts` / `tokens.ts`.
    *   ❌ `margin: '13px'`, `color: '#333'`
    *   ✅ `m: 2`, `color: 'text.primary'`
*   **Glassmorphism:** Use `tokens.glass` for standardized transparency effects.

### 1.3 Component Hierarchy
*   **Atoms:** `Button`, `Icon`, `Badge` (Unbreakable units)
*   **Molecules:** `SearchBar` (Input + Button), `MetricCard` (Paper + Icon + Typography)
*   **Organisms:** `CharacterList`, `TurnPipelineStatus` (Complex logic containers)
*   **Templates:** `CommandLayout` (Global App Shell - Persists Sidebar), `AuthLayout` (Page shells)

---

## 2. State & Data Architecture
**Rule:** Single Source of Truth (SSOT).

### 2.1 State Ownership
*   **Business Truth:** Global stores (`store/*.ts`, `hooks/use*.ts`).
    *   Examples: User session, Campaign data, WebSocket events.
    *   **Constraint:** Never fetch business data in deep child components. Pass it down or use a selector hook.
*   **UI State:** Local `useState` inside components.
    *   Examples: Modal open/close, Form input value, active tab.

### 2.2 Data Fetching
*   All data interaction goes through Services (`services/api/*.ts`) -> Hooks (`hooks/queries.ts`) -> UI.
*   **Strict States:** Every data view must implement:
    *   **Loading:** (Skeleton / Spinner)
    *   **Success:** (The Content)
    *   **Empty:** (EmptyState component)
    *   **Error:** (ErrorBanner / retry action)

---

## 3. Performance & Stability Rails
### 3.1 Render Performance
*   **Lists:** use `react-window` or virtualized lists for any table > 100 rows.
*   **Lazy Load:** Heavy charts or 3D views must be explicitly lazy loaded (`React.lazy`).

### 3.2 Feedback Loops
*   **Interactability:** Every click must provide feedback (ripple, hover state, disabled state during loading).
*   **Destructive Actions:** Must use `ConfirmDialog` or have an Undo mechanism.

---

## 4. Verification Standards
*   **A11y:** All interactive elements need `aria-label` if no text is visible. Keyboard navigation (Tab index, Focus trap) is mandatory for modals.
*   **E2E:** Critical User Flows (Login, Start Turn, Character Creation) must have a Playwright test.
*   **Visual Check:** "Does it look like the Antigravity Command Deck?" (Neon, Glass, Dark Mode).

---

## 5. Development Checklist
Copy this into the `task.md` for every frontend task:

```
- [ ] Define User Story & Layout Map
- [ ] Check `theme.ts` for available tokens (No magic values)
- [ ] Identify State Ownership (Store vs Local)
- [ ] Implement Loading/Error/Empty states
- [ ] Add/Update E2E Test
- [ ] Verify Accessibility (Keyboard/Screen Reader)
```