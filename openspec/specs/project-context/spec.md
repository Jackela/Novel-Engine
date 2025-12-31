# project-context Specification

## Purpose
TBD - created by archiving change update-openspec-project-context. Update Purpose after archive.
## Requirements
### Requirement: Project context is authoritative
The repository MUST maintain `openspec/project.md` as the authoritative project context (purpose, tech stack, conventions, and validation gates) and it MUST NOT remain a placeholder template.

#### Scenario: Project context is updated with meaningful content
- **WHEN** a contributor opens `openspec/project.md`
- **THEN** it describes the project’s purpose, primary tech stack, architecture conventions, and required CI/validation gates with concrete commands.

### Requirement: Context stays in sync with architecture decisions
Material changes to architecture patterns, API conventions, or validation gates MUST update `openspec/project.md` in the same change that introduces the new convention.

#### Scenario: New convention updates project context
- **GIVEN** a change proposal introduces a new convention (e.g., new canonical API prefix, new required CI gate)
- **WHEN** the change is implemented
- **THEN** `openspec/project.md` is updated to reflect the convention so future contributors and AI assistants have a single source of truth.

