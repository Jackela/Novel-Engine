# Feature Specification: Dynamic Agent Knowledge and Context System

**Feature Branch**: `001-dynamic-agent-knowledge`  
**Created**: 2025-11-04  
**Status**: Draft  
**Input**: User description: "Feature: Dynamic Agent Knowledge and Context System - Purpose: To replace the current static, file-based (Markdown) context engineering system with a dynamic, centralized, and permission-controlled knowledge base."

## Clarifications

### Session 2025-11-04

- Q: What type of management interface should Game Masters use to manage knowledge entries? → A: Layered approach: (1) Foundation: Admin API (RESTful/GraphQL) providing CRUD endpoints for knowledge entries, (2) Primary Interface: Web UI in frontend/admin/knowledge route calling the Admin API, (3) Optional: CLI tool for developer debugging only (not end-user deliverable)
- Q: How should the system authenticate and authorize Game Masters who access the Admin API and Web UI? → A: Use existing Novel Engine authentication system (check for admin/game_master role)
- Q: How should the migration from Markdown files to the knowledge base be triggered and managed? → A: Manual migration triggered by Game Master command (with pre-migration backup and rollback capability)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Centralized Knowledge Management (Priority: P1)

As a Game Master (Admin), I want to manage all agent knowledge (profiles, objectives, memories, world lore) in a central system, so that I can dynamically update an agent's context or add new information at any time, replacing the need to manually edit Markdown files.

**Why this priority**: This is the foundational capability that enables dynamic agent context without code redeployment. Without this, all other features cannot function. It directly addresses the core problem of static file-based management.

**Independent Test**: Can be fully tested by creating, updating, and deleting knowledge entries for multiple agents through the management interface, then verifying that changes are immediately available to the system without any file edits or code deployments.

**Acceptance Scenarios**:

1. **Given** an agent 'Aria' exists in the system with profile information stored in `/characters/aria/aria_profile.md`, **When** a Game Master creates a new knowledge entry "Aria's Engineering Background" with content "Aria graduated top of her class from the Imperial Academy", **Then** the system must store this knowledge entry and make it available for retrieval without touching the original Markdown file
2. **Given** an agent 'Aria' has an objective stored as "Find the medbay key", **When** a Game Master updates this objective to "Sabotage the reactor", **Then** the new objective must be immediately available for the next simulation turn without any code deployment
3. **Given** multiple knowledge entries exist for different agents, **When** a Game Master views the knowledge management interface, **Then** all entries must be displayed with their metadata (type, owner, access level, creation date)
4. **Given** a knowledge entry "World Lore: Reactor Protocols" exists, **When** a Game Master deletes this entry, **Then** it must no longer appear in any agent's context retrieval

---

### User Story 2 - Permission-Controlled Knowledge Access (Priority: P2)

As a Game Master (Admin), I want to define access rules for each piece of knowledge (e.g., public, role-based, or agent-specific), so that I can control what information agents are exposed to and maintain information asymmetry between characters.

**Why this priority**: Access control is critical for maintaining narrative tension and preventing information leakage between characters. This must be in place before the system replaces static files to ensure agents don't accidentally gain knowledge they shouldn't have.

**Independent Test**: Can be fully tested by creating knowledge entries with different access levels (public, role-specific, agent-specific), then verifying that each agent only retrieves knowledge matching their permissions during simulation turns.

**Acceptance Scenarios**:

1. **Given** a knowledge entry "Reactor Sabotage Plan" is tagged with `allowed_character_ids: ['Kael']`, **When** agent 'Aria' requests relevant knowledge during her turn, **Then** this entry must NOT be included in Aria's context
2. **Given** a knowledge entry "Engineering Protocols" is tagged with `allowed_roles: ['Engineer']`, **When** agent 'Aria' (role: Engineer) requests knowledge, **Then** this entry must be included in her context
3. **Given** a knowledge entry "Ship Navigation Status" is tagged with `access_level: 'public'`, **When** any agent requests knowledge, **Then** this entry must be available to all agents regardless of their role or identity
4. **Given** a knowledge entry has both `allowed_roles: ['Engineer']` and `allowed_character_ids: ['Kael']`, **When** agent 'Aria' (role: Engineer, id: 'Aria') requests knowledge, **Then** this entry must be included because Aria matches the role requirement

---

### User Story 3 - Automatic Agent Context Retrieval (Priority: P1)

As an AI Agent (Character), I want to automatically retrieve the most current and relevant information for my decision-making, including my personal profile, my current objectives, and any world knowledge I am allowed to know, so that I can make informed decisions during my simulation turn.

**Why this priority**: This is co-equal P1 with Story 1 because it represents the consumption side of the dynamic knowledge system. Without this integration, the centralized knowledge management provides no value to the simulation.

**Independent Test**: Can be fully tested by running a simulation turn for an agent (e.g., Aria) and verifying that the context provided to the agent includes current knowledge from the centralized system and excludes static Markdown file content.

**Acceptance Scenarios**:

1. **Given** an agent 'Aria' is instantiated for a simulation turn, **When** the SubjectiveBriefPhase executes for Aria, **Then** the system must NOT read context from the `/characters/aria/*.md` directory
2. **Given** the SubjectiveBriefPhase is executing for agent 'Aria', **When** the system retrieves Aria's context, **Then** it must query the centralized knowledge base and retrieve all knowledge entries matching Aria's character ID, Aria's roles, or public access level
3. **Given** agent 'Aria' has knowledge entries for profile, objectives, and memories in the centralized system, **When** Aria's context is assembled for the turn, **Then** all relevant entries must be included in the prompt sent to the decision-making system
4. **Given** the knowledge base contains an entry "Objective: Sabotage the reactor" for Aria with timestamp T1, and the previous turn had "Objective: Find the medbay key" at timestamp T0, **When** the next turn's SubjectiveBriefPhase executes, **Then** the new objective from T1 must be used, not the old one from T0

---

### User Story 4 - Semantic Knowledge Retrieval (Priority: P3)

As an AI Agent (Character), I want the system to retrieve knowledge based on semantic relevance to my current situation or query, so that I receive the most pertinent information even if the exact keywords don't match.

**Why this priority**: While valuable for enhanced decision-making, semantic retrieval is not essential for the initial MVP. The system can function with simpler retrieval mechanisms (e.g., retrieve all knowledge for an agent) before adding semantic filtering.

**Independent Test**: Can be fully tested by creating knowledge entries with semantically similar but lexically different content, then verifying that queries retrieve relevant entries even without exact keyword matches.

**Acceptance Scenarios**:

1. **Given** knowledge entries exist for "Medical bay location" and "Infirmary access codes", **When** an agent queries for "health facility information", **Then** both entries should be retrieved due to semantic similarity
2. **Given** an agent's current objective is "repair the navigation system", **When** the system retrieves relevant world knowledge, **Then** entries about "ship navigation", "control systems", and "technical repairs" should be prioritized over unrelated lore

---

### Edge Cases

- What happens when a Game Master updates a knowledge entry mid-simulation (between turns)? The next turn should use the updated content, but the current turn should complete with its already-loaded context.
- How does the system handle conflicting knowledge entries (e.g., two entries both claiming to be Aria's current objective)? The system should use the most recently created/updated entry and log a warning about the conflict.
- What happens when an agent has no accessible knowledge entries? The system should provide a minimal default context (agent identity and role) to prevent decision-making failures.
- How does the system handle extremely large knowledge bases (thousands of entries)? Retrieval performance must not degrade below acceptable thresholds (see Success Criteria).
- What happens when a knowledge entry is deleted while an agent is mid-turn? The agent should continue with its already-loaded context for that turn.
- How does the system handle malformed or corrupted knowledge entries? The system should skip corrupted entries, log the error, and continue with valid entries to maintain system availability.
- What happens if migration fails partway through (e.g., only 50% of agents migrated)? The system should halt migration, maintain the backup, and allow rollback to restore original Markdown-based operation. Partially migrated data should be clearly flagged in the system.
- What happens if a Game Master modifies Markdown files after migration is complete? The system should ignore Markdown files for migrated agents (FR-006), and log a warning if file modification is detected, suggesting the Game Master use the knowledge base instead.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store knowledge entries with the following metadata: content text, knowledge type (profile/objective/memory/lore), owning character ID (if applicable), access level (public/role-based/character-specific), allowed roles list, allowed character IDs list, creation timestamp, last updated timestamp
- **FR-002**: System MUST provide an Admin API (RESTful or GraphQL) with endpoints to create new knowledge entries with all required metadata fields, protected by existing Novel Engine authentication requiring admin or game_master role, and a Web UI (frontend/admin/knowledge) that calls this API for Game Master use
- **FR-003**: System MUST provide an Admin API endpoint to update existing knowledge entries (preserving creation timestamp while updating last modified timestamp), accessible through the Web UI
- **FR-004**: System MUST provide an Admin API endpoint to delete knowledge entries, accessible through the Web UI
- **FR-005**: System MUST retrieve knowledge entries for a given agent based on access control rules: include entries where (access_level = 'public') OR (agent's character_id IN allowed_character_ids) OR (agent's role IN allowed_roles)
- **FR-006**: System MUST NOT read agent context from static Markdown files (`/characters/{agent_name}/*.md`) when the dynamic knowledge system is enabled for that agent
- **FR-007**: System MUST integrate knowledge retrieval into the SubjectiveBriefPhase of turn execution, providing retrieved knowledge to the agent's decision-making prompt
- **FR-008**: System MUST support the following knowledge types: Agent Profile, Agent Objectives, Agent Memories, World Lore, World Rules
- **FR-009**: System MUST enforce access control rules such that agents cannot retrieve knowledge entries they are not authorized to access
- **FR-010**: System MUST support queries for knowledge entries filtered by: character ID, role, knowledge type, access level, and timestamp range
- **FR-011**: System MUST maintain an audit log of all knowledge entry changes (create, update, delete) including: timestamp, authenticated user ID (from Novel Engine auth system), entry ID, and change type
- **FR-012**: System MUST retrieve knowledge entries in order of relevance (with semantic retrieval as optional P3 enhancement, fallback to timestamp ordering for MVP)
- **FR-013**: System MUST handle concurrent updates to knowledge entries without data corruption or loss
- **FR-014**: System MUST provide feedback to Game Masters confirming successful create/update/delete operations
- **FR-015**: System MUST validate knowledge entry content to prevent injection attacks or system-breaking content
- **FR-016**: System MUST provide a migration command accessible to Game Masters that reads all existing Markdown files (`/characters/*/` directories), converts them to knowledge entries, and stores them in the knowledge base
- **FR-017**: System MUST create a backup of all Markdown files before migration begins, timestamped and stored in a designated backup location
- **FR-018**: System MUST provide a rollback capability that can restore the system to use Markdown files if migration fails or produces incorrect results
- **FR-019**: System MUST support a verification mode where Game Masters can compare Markdown file content against migrated knowledge base entries before completing migration

### Key Entities

- **Knowledge Entry**: Represents a discrete piece of information about an agent, world, or game state. Attributes: unique ID, content text, knowledge type, owning character ID (nullable), access level, allowed roles list, allowed character IDs list, creation timestamp, last updated timestamp, created by user ID
- **Agent Context**: Represents the assembled information provided to an agent during a simulation turn. Attributes: agent character ID, agent roles, turn number, retrieved knowledge entries list, assembly timestamp
- **Access Control Rule**: Represents the permissions model for knowledge visibility. Attributes: access level (public/role-based/character-specific), allowed roles list (for role-based), allowed character IDs list (for character-specific)
- **Knowledge Type**: Enumeration of knowledge categories. Values: Agent Profile, Agent Objectives, Agent Memories, World Lore, World Rules

## Constitution Alignment *(mandatory)*

- **Article I - Domain-Driven Design (DDD)**: New bounded context "Knowledge Management" for managing agent knowledge and context. Domain models: KnowledgeEntry (aggregate root), AccessControlRule (value object), AgentContext (aggregate). Domain must remain pure with no direct file I/O or LLM dependencies.

- **Article II - Ports & Adapters**: Ports to define: IKnowledgeRepository (knowledge entry persistence), IKnowledgeRetriever (query interface), IAccessControlService (permission checking), IContextAssembler (agent context building). Adapters to create: KnowledgeRepositoryAdapter (persistence implementation - PostgreSQL in MVP), MarkdownMigrationAdapter (migrate static files), SubjectiveBriefPhaseAdapter (inject context into turn execution - SubjectiveBriefPhase integration).

- **Article III - Test-Driven Development (TDD)**: Red-Green-Refactor plan: (1) Write failing tests for knowledge CRUD operations, (2) Implement domain models and repository, (3) Write failing tests for access control filtering, (4) Implement access control service, (5) Write failing tests for SubjectiveBriefPhase integration, (6) Implement context assembly and injection. Coverage targets: Domain ≥80%, Application ≥70%, Infrastructure ≥60%.

- **Article IV - Single Source of Truth (SSOT)**: Knowledge entries stored in PostgreSQL as authoritative SSOT. Markdown files become read-only archive. During migration phase, dual-read (knowledge base + markdown fallback) with knowledge base taking precedence. No Redis caching for MVP to ensure consistency.

- **Article V - SOLID Principles**: SRP - KnowledgeEntry manages knowledge data, AccessControlRule manages permissions separately. OCP - New knowledge types can be added without modifying core logic. LSP - All knowledge retrievers implement IKnowledgeRetriever interface. ISP - Separate interfaces for read (IKnowledgeRetriever) and write (IKnowledgeRepository). DIP - SubjectiveBriefPhase depends on IKnowledgeRetriever abstraction, not concrete implementation.

- **Article VI - Event-Driven Architecture (EDA)**: Domain events to publish: KnowledgeEntryCreated, KnowledgeEntryUpdated, KnowledgeEntryDeleted. Events enable audit logging, cache invalidation (future), and notification systems. No synchronous cross-context calls - use events for integration with other bounded contexts.

- **Article VII - Observability**: Structured logging for all knowledge operations with correlation IDs and character context. Prometheus metrics: knowledge_entry_created_total, knowledge_entry_updated_total, knowledge_retrieval_duration_seconds, knowledge_retrieval_count_total, access_denied_total. OpenTelemetry tracing for knowledge retrieval during SubjectiveBriefPhase.

- **Constitution Compliance Review Date**: 2025-11-04 (no violations, greenfield feature)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Game Masters can create, update, and delete knowledge entries through the management interface in under 30 seconds per operation, with immediate confirmation of success or failure
- **SC-002**: Knowledge retrieval during SubjectiveBriefPhase completes in under 500 milliseconds for agents with up to 100 accessible knowledge entries, with no degradation in turn execution time
- **SC-003**: 100% of agent context is sourced from the centralized knowledge base (0% from static Markdown files) for migrated agents, verifiable through system logs showing no file read operations for agent context
- **SC-004**: Access control enforcement prevents 100% of unauthorized knowledge access attempts, with all denied access logged for audit purposes
- **SC-005**: Knowledge updates made by Game Masters are reflected in the next simulation turn for affected agents (turn N sees update made during or after turn N-1)
- **SC-006**: System maintains 99.9% availability for knowledge retrieval operations during simulation execution, with graceful degradation to in-memory context from current turn if retrieval fails (note: external Redis caching deferred to post-MVP per Article IV)
- **SC-007**: Manual migration from static Markdown files to centralized knowledge base completes for all existing agents within 1 hour of migration command execution, with zero data loss, automatic backup creation, and successful verification of migrated content before finalization
- **SC-008**: Knowledge base supports storage of at least 10,000 knowledge entries across all agents and world lore without performance degradation below SC-002 threshold

