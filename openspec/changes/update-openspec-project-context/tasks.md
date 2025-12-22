## Implementation Tasks
1. Capture current reality
   - [ ] Inventory backend entrypoints (root server files vs `src/api/*`) and summarize the “current” launch path used by docs/CI.
   - [ ] Inventory frontend entrypoints, state management, and API clients/hooks currently in use.
   - [ ] Inventory persistence locations currently used (e.g., `data/`, `characters/`, `campaigns/`) and which are considered user-owned vs generated.

2. Write authoritative project context
   - [ ] Fill `openspec/project.md` with: Purpose, Tech Stack, Architecture Patterns, Testing Strategy, Git Workflow, Domain Context, Constraints, and External Dependencies.
   - [ ] Document API conventions and the decision for canonical prefixes (link to `standardize-api-surface` change).
   - [ ] Document persistence conventions (guest-first, filesystem-backed) and where data MUST live.
   - [ ] Add an “AI-friendly” section: stable boundaries, “where to add code”, and preferred patterns for new endpoints/components.

3. Validation
   - [ ] Run `openspec validate update-openspec-project-context --strict` and resolve any issues.

