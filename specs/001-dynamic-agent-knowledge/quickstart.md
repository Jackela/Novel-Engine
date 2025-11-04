# Quickstart Guide: Dynamic Agent Knowledge and Context System

**Feature**: 001-dynamic-agent-knowledge  
**Audience**: Developers implementing this feature  
**Prerequisites**: Python 3.11+, PostgreSQL, Kafka, React 18+, Novel Engine auth system

## Overview

This guide provides step-by-step instructions for implementing the Dynamic Agent Knowledge and Context System using Test-Driven Development (TDD) following Constitution Article III.

---

## Phase 1: Domain Layer (TDD Red-Green-Refactor)

### Step 1: KnowledgeEntry Aggregate Root

**RED - Write Failing Test**:

```python
# tests/unit/knowledge/test_knowledge_entry.py
import pytest
from datetime import datetime, timezone
from contexts.knowledge.domain.models import KnowledgeEntry, KnowledgeType, AccessControlRule, AccessLevel
from src.shared_types import KnowledgeEntryId, CharacterId, UserId

def test_knowledge_entry_update_content_should_update_timestamp():
    """RED: Test fails because KnowledgeEntry.update_content doesn't exist yet."""
    entry = KnowledgeEntry(
        id=KnowledgeEntryId("entry-123"),
        content="Original content",
        knowledge_type=KnowledgeType.PROFILE,
        owning_character_id=CharacterId("char-456"),
        access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by=UserId("user-789")
    )
    
    # Act
    event = entry.update_content("Updated content", UserId("user-999"))
    
    # Assert
    assert entry.content == "Updated content"
    assert entry.updated_at > entry.created_at
    assert event.entry_id == entry.id
```

Run: `pytest tests/unit/knowledge/test_knowledge_entry.py -v`  
Expected: **FAIL** - `AttributeError: 'KnowledgeEntry' has no attribute 'update_content'`

**GREEN - Make Test Pass**:

```python
# contexts/knowledge/domain/models/knowledge_entry.py
from dataclasses import dataclass
from datetime import datetime, timezone
from src.shared_types import KnowledgeEntryId, CharacterId, UserId
from contexts.knowledge.domain.events import KnowledgeEntryUpdated

@dataclass
class KnowledgeEntry:
    id: KnowledgeEntryId
    content: str
    knowledge_type: KnowledgeType
    owning_character_id: CharacterId | None
    access_control: AccessControlRule
    created_at: datetime
    updated_at: datetime
    created_by: UserId
    
    def update_content(self, new_content: str, updated_by: UserId) -> KnowledgeEntryUpdated:
        """Update knowledge content and return domain event."""
        self.content = new_content
        self.updated_at = datetime.now(timezone.utc)
        
        return KnowledgeEntryUpdated(
            entry_id=self.id,
            updated_by=updated_by,
            timestamp=self.updated_at
        )
```

Run: `pytest tests/unit/knowledge/test_knowledge_entry.py -v`  
Expected: **PASS**

**REFACTOR - Add Business Invariants**:

```python
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
```

**Add Test for Invariant**:

```python
def test_knowledge_entry_update_content_should_reject_empty_content():
    """Verify business invariant: content cannot be empty."""
    entry = KnowledgeEntry(...)
    
    with pytest.raises(ValueError, match="Content cannot be empty"):
        entry.update_content("   ", UserId("user-999"))
```

Run all tests: `pytest tests/unit/knowledge/ -v`  
Expected: **ALL PASS**

---

### Step 2: AccessControlRule Value Object

**RED - Write Failing Test**:

```python
# tests/unit/knowledge/test_access_control_rule.py
def test_access_control_rule_permits_should_allow_public_access():
    """RED: Test fails because AccessControlRule.permits doesn't exist."""
    rule = AccessControlRule(access_level=AccessLevel.PUBLIC)
    agent = AgentIdentity(character_id=CharacterId("char-123"), roles=["engineer"])
    
    assert rule.permits(agent) is True
```

**GREEN - Implement**:

```python
# contexts/knowledge/domain/models/access_control_rule.py
@dataclass(frozen=True)
class AccessControlRule:
    access_level: AccessLevel
    allowed_roles: tuple[str, ...] = ()
    allowed_character_ids: tuple[CharacterId, ...] = ()
    
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

**REFACTOR - Add Invariant Validation**:

```python
def __post_init__(self):
    """Validate invariants."""
    if self.access_level == AccessLevel.ROLE_BASED and not self.allowed_roles:
        raise ValueError("ROLE_BASED access requires at least one allowed role")
    if self.access_level == AccessLevel.CHARACTER_SPECIFIC and not self.allowed_character_ids:
        raise ValueError("CHARACTER_SPECIFIC access requires at least one allowed character ID")
```

---

## Phase 2: Application Layer (Use Cases)

### Step 3: CreateKnowledgeEntry Use Case

**RED - Write Failing Test**:

```python
# tests/unit/knowledge/test_create_knowledge_entry_use_case.py
from unittest.mock import AsyncMock
import pytest

@pytest.mark.asyncio
async def test_create_knowledge_entry_should_save_to_repository():
    """RED: Test fails because CreateKnowledgeEntryUseCase doesn't exist."""
    mock_repo = AsyncMock(spec=IKnowledgeRepository)
    mock_event_pub = AsyncMock(spec=IEventPublisher)
    use_case = CreateKnowledgeEntryUseCase(
        repository=mock_repo,
        event_publisher=mock_event_pub
    )
    
    result = await use_case.execute(
        content="Test content",
        knowledge_type=KnowledgeType.PROFILE,
        owning_character_id=CharacterId("char-123"),
        access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
        created_by=UserId("user-456")
    )
    
    # Assert
    mock_repo.save.assert_called_once()
    mock_event_pub.publish.assert_called_once()
    assert result.content == "Test content"
```

**GREEN - Implement**:

```python
# contexts/knowledge/application/use_cases/create_knowledge_entry.py
class CreateKnowledgeEntryUseCase:
    def __init__(
        self,
        repository: IKnowledgeRepository,
        event_publisher: IEventPublisher
    ):
        self._repo = repository
        self._event_pub = event_publisher
    
    async def execute(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        owning_character_id: CharacterId | None,
        access_control: AccessControlRule,
        created_by: UserId
    ) -> KnowledgeEntry:
        """Create new knowledge entry."""
        now = datetime.now(timezone.utc)
        entry = KnowledgeEntry(
            id=KnowledgeEntryId(str(uuid.uuid4())),
            content=content,
            knowledge_type=knowledge_type,
            owning_character_id=owning_character_id,
            access_control=access_control,
            created_at=now,
            updated_at=now,
            created_by=created_by
        )
        
        await self._repo.save(entry)
        
        event = KnowledgeEntryCreated(
            entry_id=entry.id,
            knowledge_type=entry.knowledge_type,
            owning_character_id=entry.owning_character_id,
            created_by=entry.created_by,
            timestamp=entry.created_at
        )
        await self._event_pub.publish(event)
        
        return entry
```

---

## Phase 3: Infrastructure Layer (Adapters)

### Step 4: PostgreSQL Repository Adapter

**RED - Write Failing Integration Test**:

```python
# tests/integration/knowledge/test_postgresql_repository.py
import pytest
from contexts.knowledge.infrastructure.repositories import PostgreSQLKnowledgeRepository

@pytest.mark.asyncio
async def test_postgresql_repository_should_persist_and_retrieve_entry(postgres_session):
    """Integration test with real PostgreSQL database."""
    repository = PostgreSQLKnowledgeRepository(postgres_session)
    
    entry = KnowledgeEntry(
        id=KnowledgeEntryId("entry-123"),
        content="Test content",
        knowledge_type=KnowledgeType.PROFILE,
        owning_character_id=CharacterId("char-456"),
        access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by=UserId("user-789")
    )
    
    await repository.save(entry)
    retrieved = await repository.get_by_id(KnowledgeEntryId("entry-123"))
    
    assert retrieved.id == entry.id
    assert retrieved.content == entry.content
```

**GREEN - Implement Adapter**:

```python
# contexts/knowledge/infrastructure/repositories/postgresql_knowledge_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from contexts.knowledge.application.ports import IKnowledgeRepository
from contexts.knowledge.domain.models import KnowledgeEntry

class PostgreSQLKnowledgeRepository(IKnowledgeRepository):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, entry: KnowledgeEntry) -> None:
        """Persist knowledge entry to PostgreSQL."""
        # Implementation using SQLAlchemy ORM
        # Maps domain model to database schema
        pass
    
    async def get_by_id(self, entry_id: KnowledgeEntryId) -> KnowledgeEntry | None:
        """Retrieve knowledge entry by ID."""
        # Implementation
        pass
```

---

## Phase 4: SubjectiveBriefPhase Integration

### Step 5: Integrate Knowledge Retrieval into Turn Execution

**RED - Write Failing Integration Test**:

```python
# tests/integration/knowledge/test_subjective_brief_integration.py
@pytest.mark.asyncio
async def test_subjective_brief_should_retrieve_knowledge_from_knowledge_base():
    """Integration test: SubjectiveBriefPhase uses knowledge base, not Markdown files."""
    # Setup: Create knowledge entries for agent
    # Act: Execute SubjectiveBriefPhase for agent
    # Assert: Agent context includes knowledge from database, NOT from Markdown files
    pass
```

**GREEN - Implement Adapter**:

```python
# contexts/knowledge/infrastructure/adapters/subjective_brief_phase_adapter.py
class SubjectiveBriefPhaseAdapter:
    def __init__(self, knowledge_retriever: IKnowledgeRetriever):
        self._retriever = knowledge_retriever
    
    async def assemble_agent_context(
        self,
        character_id: CharacterId,
        roles: list[str],
        turn_number: int
    ) -> AgentContext:
        """Assemble agent context from knowledge base (not Markdown files)."""
        agent_identity = AgentIdentity(character_id=character_id, roles=roles)
        knowledge_entries = await self._retriever.retrieve_for_agent(agent_identity)
        
        return AgentContext(
            agent_character_id=character_id,
            agent_roles=tuple(roles),
            turn_number=turn_number,
            knowledge_entries=knowledge_entries,
            assembled_at=datetime.now(timezone.utc)
        )
```

---

## Phase 5: Admin API and Web UI

### Step 6: Admin API Endpoints

**Contract Test**:

```python
# tests/contract/knowledge/test_admin_api_contract.py
from fastapi.testclient import TestClient

def test_create_knowledge_entry_endpoint_should_match_openapi_schema(client: TestClient):
    """Contract test - verify API matches OpenAPI spec."""
    response = client.post("/api/v1/knowledge/entries", json={
        "content": "Test content",
        "knowledge_type": "profile",
        "owning_character_id": "char-123",
        "access_control": {
            "access_level": "public"
        }
    }, headers={"Authorization": "Bearer <admin_token>"})
    
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["content"] == "Test content"
```

**Implementation**:

```python
# backend/api/routes/knowledge.py
from fastapi import APIRouter, Depends, HTTPException, status
from contexts.knowledge.application.use_cases import CreateKnowledgeEntryUseCase

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Management"])

@router.post("/entries", status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry(
    request: CreateKnowledgeEntryRequest,
    current_user: User = Depends(get_current_user),
    use_case: CreateKnowledgeEntryUseCase = Depends(get_create_use_case)
):
    """Create new knowledge entry (FR-002)."""
    if not current_user.has_role("admin") and not current_user.has_role("game_master"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    entry = await use_case.execute(
        content=request.content,
        knowledge_type=request.knowledge_type,
        owning_character_id=request.owning_character_id,
        access_control=request.access_control,
        created_by=current_user.id
    )
    
    return KnowledgeEntryResponse.from_domain(entry)
```

### Step 7: Frontend Web UI

**Component Structure**:

```tsx
// frontend/admin/knowledge/components/KnowledgeEntryForm.tsx
import React, { useState } from 'react';
import { createKnowledgeEntry } from '../services/knowledgeApi';

export const KnowledgeEntryForm: React.FC = () => {
  const [content, setContent] = useState('');
  const [knowledgeType, setKnowledgeType] = useState<KnowledgeType>('profile');
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await createKnowledgeEntry({
      content,
      knowledge_type: knowledgeType,
      access_control: { access_level: 'public' }
    });
    
    // Reset form and show success message
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <textarea value={content} onChange={(e) => setContent(e.target.value)} />
      <select value={knowledgeType} onChange={(e) => setKnowledgeType(e.target.value as KnowledgeType)}>
        <option value="profile">Profile</option>
        <option value="objective">Objective</option>
        <option value="memory">Memory</option>
        <option value="lore">Lore</option>
        <option value="rules">Rules</option>
      </select>
      <button type="submit">Create Entry</button>
    </form>
  );
};
```

---

## Phase 6: Migration

### Step 8: Markdown Migration Adapter

**Implementation**:

```python
# contexts/knowledge/infrastructure/adapters/markdown_migration_adapter.py
import shutil
from pathlib import Path

class MarkdownMigrationAdapter:
    def __init__(self, knowledge_repo: IKnowledgeRepository):
        self._repo = knowledge_repo
    
    async def migrate_all_agents(self, characters_dir: Path, backup_dir: Path) -> MigrationResult:
        """Migrate all Markdown files to knowledge base (FR-016, FR-017)."""
        # Step 1: Create backup
        timestamp = datetime.now(timezone.utc).isoformat()
        backup_location = backup_dir / f"markdown_backup_{timestamp}"
        shutil.copytree(characters_dir, backup_location)
        
        # Step 2: Migrate all character directories
        migrated_count = 0
        errors = []
        
        for agent_dir in characters_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            try:
                await self._migrate_agent(agent_dir)
                migrated_count += 1
            except Exception as e:
                errors.append(MigrationError(file_path=str(agent_dir), error_message=str(e)))
        
        return MigrationResult(
            entries_migrated=migrated_count,
            backup_location=str(backup_location),
            errors=errors
        )
    
    async def _migrate_agent(self, agent_dir: Path) -> None:
        """Migrate single agent's Markdown files."""
        agent_name = agent_dir.name
        
        # Migrate profile
        profile_path = agent_dir / f"{agent_name}_profile.md"
        if profile_path.exists():
            content = profile_path.read_text()
            entry = KnowledgeEntry(
                id=KnowledgeEntryId(str(uuid.uuid4())),
                content=content,
                knowledge_type=KnowledgeType.PROFILE,
                owning_character_id=CharacterId(agent_name),
                access_control=AccessControlRule(
                    access_level=AccessLevel.CHARACTER_SPECIFIC,
                    allowed_character_ids=(CharacterId(agent_name),)
                ),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=UserId("migration_system")
            )
            await self._repo.save(entry)
        
        # Repeat for objectives, memories...
```

---

## Running the Full Test Suite

### Unit Tests (Fast, <10ms per test)
```bash
pytest tests/unit/knowledge/ -v
```

### Integration Tests (Slower, <500ms per test)
```bash
pytest tests/integration/knowledge/ -v --run-integration
```

### Contract Tests (API schema validation)
```bash
pytest tests/contract/knowledge/ -v
```

### All Tests with Coverage
```bash
pytest tests/knowledge/ --cov=contexts/knowledge --cov-report=html --cov-report=term
```

**Coverage Targets**:
- Domain layer: ≥80%
- Application layer: ≥70%
- Infrastructure layer: ≥60%

---

## Development Workflow Summary

1. **RED**: Write failing test for next feature
2. **GREEN**: Write minimal code to pass test
3. **REFACTOR**: Improve code quality, add invariants
4. **Repeat**: Continue TDD cycle for next feature
5. **Integration**: Test with real infrastructure (PostgreSQL, Kafka)
6. **Contract**: Validate API matches OpenAPI schema
7. **Deploy**: Merge to main after all tests pass

---

## Next Steps

After implementing all phases:

1. Run migration for existing agents (FR-016)
2. Verify migrated data (FR-019)
3. Update SubjectiveBriefPhase to use knowledge base (FR-007)
4. Monitor observability metrics (Article VII)
5. Measure success criteria (SC-001 to SC-008)

---

**Constitution Compliance**: This quickstart follows strict TDD (Article III), implements hexagonal architecture (Article II), and maintains domain purity (Article I).
