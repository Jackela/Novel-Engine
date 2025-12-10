# Frontend Refactoring Plan: "Vibe Coding" Edition

This plan aims to transition the `Novel-Engine` frontend from a standard React codebase to a **"Vibe Coding" optimized architecture**. The goal is not just clean code, but a codebase where **AI can reliably generate high-quality, consistent implementation** by following explicit constraints and standard rails.

## Phase 1: The "Rules of Engagement" (Governance & Process)

Before changing code, we define the constraints that make AI useful.

### 1.1 Establish the "Vibe Checklist"
Create `frontend/VIBE_CHECKLIST.md` to serve as the **primary context** for all future AI interactions.
*   **User Story & Flow Required:** No code without a defined user goal and 3-7 step happy path.
*   **Design System Strict Mode:** Only use components from `@mui/material` (wrapped) or `src/components/common`. No raw HTML/CSS for layout.
*   **State Law:** Business state $\to$ Redux/React Query. UI state $\to$ `useState`. No API calls in components.
*   **The 4 States of UI:** Every data component MUST handle: `Loading`, `Success`, `Empty`, `Error`.

### 1.2 Update Design System Documentation
Refine `frontend/DESIGN_SYSTEM.md` to be "Prompt-Ready".
*   Add an **"Atomic Inventory"** section listing exactly which components are Atoms (Buttons, Inputs) vs Molecules (SearchBars, Cards).
*   Add **"Forbidden Patterns"**: E.g., "Never use `fetch()` in a component. Never use `style={{ margin: ... }}`."

## Phase 2: Architectural Realignment

Reorganize the file structure to match the mental model we want the AI to have.

### 2.1 Component Library Structuring (Atomic Design)
*   **Action:** Audit `frontend/src/components`.
*   **Move:**
    *   `src/components/ui` $\to$ `src/components/atoms` (Base UI wrappers).
    *   `src/components/common` $\to$ `src/components/molecules` (Reusable composites).
    *   `CampaignList.tsx`, `CharacterCard.tsx` $\to$ `src/components/organisms` or `src/features/`.
*   **Goal:** When we ask AI for a "Molecule", it knows exactly where to look and what complexity level to aim for.

### 2.2 Feature-First Consolidation
*   **Action:** Move root components like `CampaignList.tsx` into `src/features/campaigns/components/`.
*   **Structure:**
    ```text
    src/features/campaigns/
      ├── components/   # Campaign-specific UI
      ├── hooks/        # Campaign-specific logic (useCampaigns)
      ├── slice.ts      # Redux slice (already in store/slices, consider moving or re-exporting)
      └── types.ts
    ```
*   **Goal:** Isolate context so AI doesn't hallucinate dependencies from other domains.

## Phase 3: State & Logic Hardening

Enforce the "Functional Core, Imperative Shell" equivalent in frontend.

### 3.1 The "Data Access Layer" Audit
*   **Action:** Review `src/hooks` and `src/components`.
*   **Task:** Ensure **zero** API calls exist in `.tsx` files (except in `src/services`).
*   **Pattern:** All data access must look like:
    ```typescript
    const { data, isLoading, error } = useCampaigns();
    ```
*   **Refactor:** Create missing hooks in `src/hooks` or `src/features/*/hooks` to wrap any loose `fetch`/`axios` calls.

### 3.2 Strict Typings & Enums
*   Ensure all API responses and Redux state shapes have strict TypeScript interfaces in `src/types` or `src/shared_types.py` (synced).
*   Eliminate any `any` types in the `store`.

## Phase 4: Implementation & Polish

### 4.1 "Smart" List Components
*   **Action:** Create/Refine `VirtualizedList` wrapper using `react-window`.
*   **Rule:** "Any list capable of > 50 items must use `VirtualizedList`."

### 4.2 Error Boundary & Suspense
*   Ensure a global `ErrorBoundary` and granular `Suspense` boundaries exist for main routes.

### 4.3 E2E "Guardrails"
*   Select the **Critical Path** (e.g., "Create Campaign" -> "Add Character").
*   Ensure a Playwright test exists for this specific flow.

---

## Immediate Next Step: "The Pilot"

I will execute **Phase 1.1** and **Phase 1.2** immediately to set the stage. Then I will perform a **pilot refactor** on the `Campaigns` feature (Phase 2.2) to demonstrate the pattern.

1.  Create `frontend/VIBE_CHECKLIST.md`.
2.  Update `frontend/DESIGN_SYSTEM.md`.
3.  Refactor `CampaignList.tsx` and related files into `src/features/campaigns` following the new rules.
