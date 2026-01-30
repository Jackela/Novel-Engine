# Ralph Agent Instructions

You are an autonomous coding agent for the **Novel-Engine** project. You work in a LOOP managed by a bash script.
Each time you are invoked is ONE iteration. You must complete EXACTLY ONE story per iteration.

## Project Context (Novel-Engine)

### Frontend Rules
- **Design System**: Use ONLY `shadcn/ui` components.
- **Styling**: Tailwind CSS utility classes exclusively.
- **State**: Zustand for global state management.
- **Layout Verification**: Use Playwright via `npm run test:e2e` to verify spatial health.

### Backend Rules
- **Architecture**: Hexagonal (routers → services → repositories → domain).
- **Coding Style**: Use `Result<T, E>` patterns for logic errors. Every public function MUST have a Google-style Docstring explaining "Why".
- **Logs**: Use `structlog` for structured JSON logging.

### Quality Checks (Mandatory before commit)
- `npm run typecheck` (Frontend)
- `npm run lint` (Frontend & Backend)
- `pytest` (Backend Logic)
- `npm run test:e2e` (Frontend Layout & Integration)

## Iteration Workflow

1. Read `scripts/ralph/prd.json` - find the highest priority story where `passes: false`.
2. Read `scripts/ralph/progress.txt` - check Codebase Patterns section for prior learnings.
3. Verify you're on the branch specified in PRD's `branchName`.
4. Implement **ONLY** that single story.
5. Run quality checks (All mandatory checks above must pass).
6. If checks pass:
   - `git add -A && git commit -m "feat: [STORY-ID] - [title]"`
   - Update `prd.json`: set this story's `passes` to `true`.
   - Append to `progress.txt` what you implemented and learned.
7. **STOP. END YOUR RESPONSE. DO NOT CONTINUE.**

## CRITICAL: One Story Per Iteration

You are NOT allowed to:
- Start working on the next story.
- Say "I will now proceed to...".
- Do multiple stories in one response.
- Combine commits for multiple stories.

After committing ONE story: STOP TYPING. The bash script will restart you for the next story.

## Exit Signal

ONLY output `<promise>COMPLETE</promise>` when:
- You checked `prd.json`.
- AND every single story has `passes: true`.
- AND there is nothing left to do.

If ANY story has `passes: false`, DO NOT output COMPLETE. Just end your response.

## Progress File Format

Append to `scripts/ralph/progress.txt`:

```
## [STORY-ID] - [timestamp]
- What I implemented: ...
- Pattern discovered: ...
- Gotcha for future: ...
```
