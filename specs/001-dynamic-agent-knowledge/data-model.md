# Data Model: Dynamic Agent Knowledge and Context System

**Feature**: 001-dynamic-agent-knowledge  
**Created**: 2025-11-04  
**Status**: Design Phase

## Overview

This document defines the domain models, value objects, and PostgreSQL schema for the Knowledge Management bounded context. All models follow DDD principles with pure domain logic and no infrastructure dependencies.

## Domain Models

### KnowledgeEntry (Aggregate Root)

**Purpose**: Represents a discrete piece of information about an agent, world, or game state.

**Invariants**:
- ID must be unique and immutable
- Content text cannot be empty
- Knowledge type must be valid enum value
- Created timestamp is immutable
- Last updated timestamp must be >= created timestamp
- Created by user ID is immutable

**Attributes**:
```python
@dataclass
class KnowledgeEntry:
    id: KnowledgeEntryId              # Unique identifier (UUID)
    content: str                       # Knowledge content text
    knowledge_type: KnowledgeType      # Enum: PROFILE, OBJECTIVE, MEMORY, LORE, RULES
    owning_character_id: CharacterId | None  # Character this knowledge belongs to (nullable for world knowledge)
    access_control: AccessControlRule  # Access permissions (value object)
    created_at: datetime               # Creation timestamp (immutable)
    updated_at: datetime               # Last modification timestamp
    created_by: UserId                 # User who created this entry (immutable)
    
    def update_content(self, new_content: str, updated_by: UserId) -> KnowledgeEntryUpdated:
        """Update knowledge content and return domain event."""
        if not new_content.strip():
            raise ValueError("Content cannot be empty")
        
        self.content = new_content
        self.updated_at = datetime.now(timezone.utc)
        
        return KnowledgeEntryUpdated(
            entry_id=self.id,
            updated_by=updated_by,
            timestamp=self.updated_at
        )
    
    def is_accessible_by(self, agent: AgentIdentity) -> bool:
        """Check if agent has permission to access this knowledge entry."""
        return self.access_control.permits(agent)
```

---

### AccessControlRule (Value Object)

**Purpose**: Represents the permissions model for knowledge visibility.

**Invariants**:
- Access level must be valid enum value
- If access level is ROLE_BASED, allowed_roles must be non-empty
- If access level is CHARACTER_SPECIFIC, allowed_character_ids must be non-empty
- Value object is immutable

**Attributes**:
```python
@dataclass(frozen=True)
class AccessControlRule:
    access_level: AccessLevel          # Enum: PUBLIC, ROLE_BASED, CHARACTER_SPECIFIC
    allowed_roles: tuple[str, ...] = ()  # Roles permitted (for ROLE_BASED)
    allowed_character_ids: tuple[CharacterId, ...] = ()  # Characters permitted (for CHARACTER_SPECIFIC)
    
    def __post_init__(self):
        """Validate invariants."""
        if self.access_level == AccessLevel.ROLE_BASED and not self.allowed_roles:
            raise ValueError("ROLE_BASED access requires at least one allowed role")
        if self.access_level == AccessLevel.CHARACTER_SPECIFIC and not self.allowed_character_ids:
            raise ValueError("CHARACTER_SPECIFIC access requires at least one allowed character ID")
    
    def permits(self, agent: AgentIdentity) -> bool:
        """Check if agent satisfies access control rules."""
        if self.access_level == AccessLevel.PUBLIC:
            return True
        elif self.access_level == AccessLevel.ROLE_BASED:
            return any(role in self.allowed_roles for role in agent.roles)
        elif self.access_level == AccessLevel.CHARACTER_SPECIFIC:
            return agent.character_id in self.allowed_character_ids
        return False
```

---

### AgentContext (Aggregate)

**Purpose**: Represents the assembled information provided to an agent during a simulation turn.

**Invariants**:
- Character ID must be valid
- Turn number must be non-negative
- Retrieved knowledge entries cannot contain duplicates
- Assembly timestamp is immutable

**Attributes**:
```python
@dataclass
class AgentContext:
    agent_character_id: CharacterId    # Agent receiving this context
    agent_roles: tuple[str, ...]       # Agent's roles for permission checking
    turn_number: int                   # Simulation turn number
    knowledge_entries: list[KnowledgeEntry]  # Retrieved knowledge entries
    assembled_at: datetime             # When context was assembled (immutable)
    
    def to_llm_prompt_text(self) -> str:
        """Convert knowledge entries to formatted text for LLM prompt."""
        sections = {
            KnowledgeType.PROFILE: [],
            KnowledgeType.OBJECTIVE: [],
            KnowledgeType.MEMORY: [],
            KnowledgeType.LORE: [],
            KnowledgeType.RULES: []
        }
        
        for entry in self.knowledge_entries:
            sections[entry.knowledge_type].append(entry.content)
        
        prompt_parts = []
        if sections[KnowledgeType.PROFILE]:
            prompt_parts.append("## Profile\n" + "\n".join(sections[KnowledgeType.PROFILE]))
        if sections[KnowledgeType.OBJECTIVE]:
            prompt_parts.append("## Current Objectives\n" + "\n".join(sections[KnowledgeType.OBJECTIVE]))
        if sections[KnowledgeType.MEMORY]:
            prompt_parts.append("## Memories\n" + "\n".join(sections[KnowledgeType.MEMORY]))
        if sections[KnowledgeType.LORE]:
            prompt_parts.append("## World Knowledge\n" + "\n".join(sections[KnowledgeType.LORE]))
        if sections[KnowledgeType.RULES]:
            prompt_parts.append("## Rules\n" + "\n".join(sections[KnowledgeType.RULES]))
        
        return "\n\n".join(prompt_parts)
```

---

## Enumerations

### KnowledgeType

```python
from enum import Enum

class KnowledgeType(str, Enum):
    PROFILE = "profile"          # Agent identity, background, traits
    OBJECTIVE = "objective"      # Current goals and missions
    MEMORY = "memory"            # Past events, experiences, relationships
    LORE = "lore"                # World information, setting details
    RULES = "rules"              # Game mechanics, world constraints
```

### AccessLevel

```python
from enum import Enum

class AccessLevel(str, Enum):
    PUBLIC = "public"                      # Accessible to all agents
    ROLE_BASED = "role_based"              # Accessible to agents with specific roles
    CHARACTER_SPECIFIC = "character_specific"  # Accessible to specific characters only
```

---

## PostgreSQL Schema

### Table: knowledge_entries

**Purpose**: Single Source of Truth (SSOT) for all knowledge entries per Article IV.

```sql
CREATE TABLE knowledge_entries (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL CHECK (LENGTH(TRIM(content)) > 0),
    knowledge_type VARCHAR(20) NOT NULL 
        CHECK (knowledge_type IN ('profile', 'objective', 'memory', 'lore', 'rules')),
    owning_character_id VARCHAR(255),  -- Nullable for world knowledge
    access_level VARCHAR(30) NOT NULL 
        CHECK (access_level IN ('public', 'role_based', 'character_specific')),
    allowed_roles TEXT[],               -- PostgreSQL array for role list
    allowed_character_ids TEXT[],       -- PostgreSQL array for character ID list
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    
    -- Constraints
    CONSTRAINT valid_updated_timestamp CHECK (updated_at >= created_at),
    CONSTRAINT role_based_requires_roles CHECK (
        access_level != 'role_based' OR (allowed_roles IS NOT NULL AND array_length(allowed_roles, 1) > 0)
    ),
    CONSTRAINT character_specific_requires_ids CHECK (
        access_level != 'character_specific' OR (allowed_character_ids IS NOT NULL AND array_length(allowed_character_ids, 1) > 0)
    )
);

-- Indexes for performance (SC-002: <500ms retrieval)
CREATE INDEX idx_knowledge_entries_character_id ON knowledge_entries(owning_character_id);
CREATE INDEX idx_knowledge_entries_access_level ON knowledge_entries(access_level);
CREATE INDEX idx_knowledge_entries_knowledge_type ON knowledge_entries(knowledge_type);
CREATE INDEX idx_knowledge_entries_created_at ON knowledge_entries(created_at);
CREATE INDEX idx_knowledge_entries_updated_at ON knowledge_entries(updated_at);

-- GIN index for array searches (role and character ID filtering)
CREATE INDEX idx_knowledge_entries_allowed_roles ON knowledge_entries USING GIN(allowed_roles);
CREATE INDEX idx_knowledge_entries_allowed_character_ids ON knowledge_entries USING GIN(allowed_character_ids);
```

### Table: knowledge_audit_log

**Purpose**: Audit trail for all knowledge entry changes (FR-011).

```sql
CREATE TABLE knowledge_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(255) NOT NULL,
    entry_id UUID NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('created', 'updated', 'deleted')),
    snapshot JSONB,  -- Snapshot of entry state for deleted entries
    
    -- Index for audit queries
    INDEX idx_audit_log_entry_id (entry_id),
    INDEX idx_audit_log_timestamp (timestamp),
    INDEX idx_audit_log_user_id (user_id)
);
```

---

## Domain Events

### KnowledgeEntryCreated

```python
@dataclass(frozen=True)
class KnowledgeEntryCreated:
    entry_id: KnowledgeEntryId
    knowledge_type: KnowledgeType
    owning_character_id: CharacterId | None
    created_by: UserId
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

### KnowledgeEntryUpdated

```python
@dataclass(frozen=True)
class KnowledgeEntryUpdated:
    entry_id: KnowledgeEntryId
    updated_by: UserId
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

### KnowledgeEntryDeleted

```python
@dataclass(frozen=True)
class KnowledgeEntryDeleted:
    entry_id: KnowledgeEntryId
    deleted_by: UserId
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

---

## Migration Schema

### Markdown File Structure (Legacy)

```
characters/{agent_name}/
├── {agent_name}_profile.md        → KnowledgeType.PROFILE
├── {agent_name}_objectives.md     → KnowledgeType.OBJECTIVE
├── {agent_name}_memories.md       → KnowledgeType.MEMORY
└── stats.yaml                     → (Not migrated, handled separately)
```

### Migration Mapping

| Markdown File | Knowledge Type | Owning Character ID | Access Level |
|--------------|----------------|---------------------|--------------|
| `{agent}_profile.md` | PROFILE | `agent_name` | CHARACTER_SPECIFIC (owner only) |
| `{agent}_objectives.md` | OBJECTIVE | `agent_name` | CHARACTER_SPECIFIC (owner only) |
| `{agent}_memories.md` | MEMORY | `agent_name` | CHARACTER_SPECIFIC (owner only) |

---

## Validation Rules

### Domain-Level Validation

1. **Content Validation**: Content text must not be empty after trimming whitespace
2. **Type Validation**: Knowledge type must be valid enum value
3. **Access Control Validation**: Access control rules must satisfy invariants (roles/characters for respective access levels)
4. **Timestamp Validation**: Updated timestamp must be >= created timestamp

### Infrastructure-Level Validation (PostgreSQL)

1. **SQL Injection Prevention**: Use parameterized queries only (never string concatenation)
2. **Content Sanitization**: Escape special characters before storage (handled by SQLAlchemy)
3. **Constraint Enforcement**: Database-level constraints for data integrity

### Application-Level Validation (Admin API)

1. **Authentication**: Verify user has admin or game_master role (FR-002)
2. **Input Sanitization**: Validate and sanitize all user inputs
3. **Rate Limiting**: Prevent abuse of Admin API endpoints (future enhancement)

---

## Performance Considerations

### Indexing Strategy

- **Character ID Index**: Fast retrieval of all knowledge for a specific agent
- **Access Level Index**: Optimize filtering by access level
- **Knowledge Type Index**: Support queries filtered by type
- **Timestamp Indexes**: Enable temporal queries and sorting by recency
- **GIN Indexes**: Efficient array containment checks for role/character filtering

### Query Optimization

**Typical Query (SC-002: <500ms for ≤100 entries)**:
```sql
-- Retrieve all knowledge accessible to agent with roles
SELECT * FROM knowledge_entries
WHERE 
    access_level = 'public'
    OR (access_level = 'role_based' AND allowed_roles && ARRAY['engineer', 'crew']::TEXT[])
    OR (access_level = 'character_specific' AND 'char-123' = ANY(allowed_character_ids))
ORDER BY updated_at DESC;
```

**Expected Performance**: <100ms for 10,000 entries with proper indexes

---

## Constitution Compliance

- **Article I (DDD)**: Domain models are pure with no infrastructure dependencies
- **Article II (Hexagonal)**: Domain defines models, infrastructure provides PostgreSQL persistence adapter
- **Article III (TDD)**: All models will have unit tests before implementation
- **Article IV (SSOT)**: PostgreSQL `knowledge_entries` table is authoritative source
- **Article V (SOLID)**: SRP (one model per concern), OCP (enum extension), LSP (value object immutability)
- **Article VI (EDA)**: Domain events for all mutations (Created, Updated, Deleted)
- **Article VII (Observability)**: Audit log table for compliance and debugging

---

**Next Steps**: Generate API contracts in `/contracts/` and quickstart guide in `quickstart.md`.
