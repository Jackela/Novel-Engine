# Novel Engine - Vibe Coding Protocols

## I. Core Philosophy
- **Text-Driven**: Rely on structured constraints, not visual feedback.
- **Contract-First**: Types (Pydantic/Zod) and Tests are the absolute truth.
- **Strict Layering**: Enforce Hexagonal Architecture boundaries strictly.

## II. Frontend Rules (The "Eyes")
- **Design System**: Use ONLY `shadcn/ui` components. Do NOT create custom CSS classes unless absolutely necessary.
- **Styling**: Use Tailwind CSS utility classes exclusively.
  - Spacing: strict scale (space-y-4, gap-6, p-8). No arbitrary pixels (e.g., `margin: 13px`).
  - Layout: Flexbox and Grid only. Max nesting depth: 3.
- **Layout Verification**: All UI components must pass `npm run test:e2e` (Playwright) which checks for overlaps and overflow.
- **State**: Use Zustand for global state. No complex `useEffect` chains.

## III. Backend Rules (The "Brain")
- **Architecture**:
  - `routers/`: Input validation -> Service call -> Response formatting. NO business logic.
  - `services/`: Pure business logic.
  - `repositories/`: Database interaction only.
  - `domain/`: Pure Python entities (Pydantic).
- **Coding Style**:
  - Explicit is better than implicit.
  - Return `Result<T, E>` patterns instead of throwing raw exceptions for logic errors.
  - Every public function MUST have a Docstring explaining "Why", not just "What".
- **Logs**: Use `structlog`. All logs must be structured JSON.

## IV. The Feedback Loop
Before marking a task as complete, you MUST run:
1. `npm run typecheck` (Frontend)
2. `npm run lint` (Frontend & Backend)
3. `pytest` (Backend Logic)
4. `npm run test:e2e` (Frontend Layout & Integration)

## V. Workflow Instructions (The Algorithm)

1. **Read State**: Check `prd.json` and `git status`.
2. **Cleanup Check**: 
   - IF all stories in `prd.json` are `passes: true` AND `git status` shows changes:
   - **ACTION**: `git add . && git commit -m "chore: finalize all tasks"`
   - **THEN**: Output `<promise>COMPLETE</promise>` immediately.
3. **Work Check**:
   - IF there is a story with `passes: false`:
   - Pick the highest priority one.
   - Implement it.
   - Run tests (IV. The Feedback Loop).
   - `git add . && git commit -m "feat: [ID] ..."`
   - Update `prd.json` to `passes: true`.
   - Output `<promise>COMPLETE</promise>` ONLY if this was the last story.

## ⚡️ CRITICAL INSTRUCTION - EXECUTE IMMEDIATELY ⚡️

**DO NOT** ask for permission.
**DO NOT** ask "What should I do?".
**ACT** like a senior engineer who knows what needs to be done.

If tasks are done but code is uncommitted -> **COMMIT IT**.
If everything is clean and done -> **OUTPUT <promise>COMPLETE</promise>**.

--> **GO!** <--