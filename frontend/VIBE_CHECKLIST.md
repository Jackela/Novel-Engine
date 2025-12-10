# Vibe Coding Checklist (The AI Guardrails)

**STOP. READ THIS BEFORE GENERATING CODE.**

This project follows "Vibe Coding" principles. Your goal is NOT to be creative with architecture, but to be a **reliable implementation engine** within strict constraints.

## 0. The Golden Rule
**Spec First, Code Second.**
Never generate a component implementation without first confirming:
1.  **User Story:** Who is using this and why?
2.  **Happy Path:** What are the 3-5 steps to success?
3.  **UI States:** Have you planned for `Loading`, `Empty`, `Error`, and `Success`?

## 1. Design System Strict Mode
*   **Aesthetic:** "VisionOS / Glassmorphism". Use `tokens.glass.main` for containers.
*   **Motion:** "Everything flows." Lists must cascade in. Use `framer-motion` for entrances.
*   **Typography:** Hierarchy is king. Use `tokens.typography` sizes.
*   **Source of Truth:** Use `src/styles/theme.ts` and `src/styles/tokens.ts` for ALL styling.
*   **Components:** prefer `@mui/material` components or our local `src/components/atoms`.
*   **Spacing:** ONLY use `theme.spacing()`. NEVER use raw pixels (e.g., `margin: "15px"` is FORBIDDEN).
*   **Colors:** ONLY use `theme.palette.*`. NEVER use raw hex codes (e.g., `#ccc` is FORBIDDEN).
*   **Layout:** Use `Box`, `Stack`, `Grid` (MUI). Avoid custom CSS classes for basic layout.

## 2. Architecture & State Law
*   **No API in UI:** Components must NEVER make API calls (fetch/axios) directly.
    *   ✅ `const { data } = useCampaigns();`
    *   ❌ `useEffect(() => { fetch('/api/...') }, [])`
*   **State Ownership:**
    *   **Business Logic:** Belongs in Redux Slices or Custom Hooks.
    *   **UI State:** Belongs in `useState` inside the component (e.g., `isModalOpen`).
*   **Atomic Hierarchy:**
    *   **Atoms:** Dumb, stylistic wrappers (Button, Input).
    *   **Molecules:** Reusable composites (SearchBar, UserCard).
    *   **Organisms:** Business-aware blocks (CampaignList, Header).
    *   **Pages:** Orchestration only.

## 3. Implementation Standards
*   **The 4-State Rule:** Every data-fetching component MUST explicitly render:
    1.  `<LoadingSkeleton />` (while fetching)
    2.  `<ErrorState />` (if API fails)
    3.  `<EmptyState />` (if list is empty)
    4.  `<TheContent />` (success)
*   **Performance:**
    *   Lists > 50 items MUST use `react-window` or similar virtualization.
    *   Heavy components MUST be lazy-loaded.

## 4. Verification
*   **Accessibility:** All inputs have labels? All images have alt text? Keyboard navigable?
*   **Types:** NO `any`. Define strict interfaces in `types.ts`.

---
**Copy this context into your prompt when asking for new features.**
