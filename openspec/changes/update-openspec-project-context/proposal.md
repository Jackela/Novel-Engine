# Proposal: Update OpenSpec Project Context

## Why
- `openspec/project.md` is still a placeholder, so contributors and AI assistants lack a single source of truth for architecture, API conventions, persistence, and CI gates.
- The repo currently contains multiple backend entrypoints, mixed API path conventions, and both guest + authenticated flows; without documented conventions, future refactors will drift.

## What Changes
1. Replace the placeholder `openspec/project.md` with project-specific context: purpose, domain model, tech stack, repo structure, and “how we build here”.
2. Document explicit conventions that make the codebase AI-friendly: stable module boundaries, naming, minimal side effects, and predictable contracts.
3. Record non-negotiable validation gates and the intended ordering between refactor proposals (API surface → backend platform → filesystem workspaces → frontend).

## Impact
- Documentation-only change inside `openspec/project.md`.
- Reduces future proposal churn caused by implicit assumptions.

## Out of Scope
- Implementing backend/frontend refactors or new features (handled by separate changes).

