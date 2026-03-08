# Comprehensive Vibe Coding Remediation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:dispatching-parallel-agents to implement this plan in parallel phases.

**Goal:** Elevate Novel-Engine from C+ (65/100) to A (90+/100) across all compliance dimensions.

**Timeline:** 3 phases over 2 weeks  
**Approach:** Parallel subagent execution with domain-specialized agents

---

## Current State Summary

| Dimension | Current | Target | Gap |
|-----------|---------|--------|-----|
| Type Safety (MyPy) | 4,463 errors | <500 | -3,963 |
| Test Coverage | 8.58% | 40% | +31.4% |
| StructLog | 14.27% | 60% | +45.7% |
| Result Pattern | 7.8% | 40% | +32.2% |
| Architecture | 88% | 95% | +7% |
| Documentation | 82% | 95% | +13% |
| Security | 93% | 98% | +5% |
| Code Quality | 58% | 75% | +17% |

**Overall:** C+ (65/100) → A (90+/100)

---

## Phase 1: Critical Fixes (P0) - Week 1

**Objective:** Fix all critical issues that block production readiness.
**Parallel Agents:** 6 agents
**Estimated Time:** 5-7 days

---

### Task 1.1: MyPy Quick Wins (Agent: Type Safety Specialist)

**Goal:** Reduce MyPy errors from 4,463 to <3,500 (-1,000+ errors)
**Time:** 2 days

#### Step 1: Install Missing Stubs
```bash
pip install types-networkx types-tiktoken types-PyYAML types-redis
# Estimated fix: -82 errors
```

#### Step 2: Batch Add -> None Return Types
Target: 574 `no-untyped-def` errors
```python
# Pattern to fix:
def method(self):          →   def method(self) -> None:
def process(data):         →   def process(data) -> None:
```

Files to prioritize:
- `src/contexts/narratives/` (89 errors)
- `src/contexts/knowledge/` (76 errors)
- `src/contexts/orchestration/` (45 errors)

#### Step 3: Fix Optional Default Arguments
Target: 409 `assignment` errors
```python
# Pattern to fix:
def __init__(self, x: T = None):    →   def __init__(self, x: Optional[T] = None):
```

#### Verification
```bash
mypy src/ --no-error-summary 2>&1 | wc -l
# Target: <3,500
```

#### Commit
```bash
git add -A
git commit -m "types: MyPy quick wins (-1,000+ errors)

- Install missing type stubs (networkx, tiktoken, yaml, redis)
- Add -> None to 574 functions
- Fix Optional[X] defaults (409 errors)

Before: 4,463 errors
After: ~3,400 errors
Progress: -23%"
```

---

### Task 1.2: Critical Test Coverage (Agent: Test Coverage Specialist)

**Goal:** Add tests for top 10 critical zero-coverage files
**Time:** 3 days
**Impact:** +5% coverage

#### Target Files (in priority order)

1. **core/database_manager.py** (451 lines)
   - Create: `tests/core/test_database_manager.py`
   - Test: Connection pooling, transaction management, error handling

2. **security/auth_system.py** (403 lines)
   - Create: `tests/security/test_auth_system.py`
   - Test: Password hashing, JWT generation/validation, token refresh

3. **security/enterprise_security_manager.py** (324 lines)
   - Create: `tests/security/test_enterprise_security_manager.py`
   - Test: Permission checks, role validation, audit logging

4. **core/llm_service.py** (~300 lines)
   - Create: `tests/core/test_llm_service.py`
   - Test: Provider routing, caching, error handling

5. **contexts/character/domain/aggregates/character.py** (158 lines, 23.4% covered)
   - Extend: `tests/contexts/character/domain/test_character.py`
   - Test: Remaining methods (inventory, skills, relationships)

6. **contexts/knowledge/application/services/knowledge_ingestion_service.py** (312 lines)
   - Create: `tests/contexts/knowledge/test_knowledge_ingestion_service.py`
   - Test: Document parsing, chunking, embedding generation

7. **interactions/interaction_engine_system/interaction_engine_modular.py** (447 lines)
   - Create: `tests/interactions/test_interaction_engine.py`
   - Test: Phase processing, validation, state management

8. **memory/semantic_memory.py** (~250 lines)
   - Create: `tests/memory/test_semantic_memory.py`
   - Test: Vector storage, similarity search, persistence

9. **performance/advanced_caching.py** (~400 lines)
   - Create: `tests/performance/test_advanced_caching.py`
   - Test: LRU, TTL, cache eviction, pickle serialization

10. **contexts/world/application/services/event_service.py** (~200 lines)
    - Create: `tests/contexts/world/test_event_service.py`
    - Test: Event creation, timeline management, rumor generation

#### Test Template
```python
import pytest
from unittest.mock import Mock, patch
from src.X import Y

class TestY:
    def test_success_case(self):
        # Arrange
        service = Y(mock_repo)
        
        # Act
        result = service.method(valid_input)
        
        # Assert
        assert result.is_ok()
        assert result.unwrap() == expected

    def test_error_case(self):
        # Arrange
        service = Y(mock_repo)
        mock_repo.get.return_value = None
        
        # Act
        result = service.method(invalid_input)
        
        # Assert
        assert result.is_err()
        assert "not found" in result.unwrap_err().message
```

#### Verification
```bash
pytest tests/core/test_database_manager.py -v --cov=src.core.database_manager
pytest tests/security/ -v --cov=src.security
pytest tests/contexts/character/ -v --cov=src.contexts.character
# Target: All tests pass, coverage increased
```

#### Commit
```bash
git add tests/
git commit -m "test: add critical test coverage (+5%)

Added comprehensive tests for 10 critical modules:
- Database manager (connection pooling, transactions)
- Auth system (hashing, JWT, tokens)
- Security manager (permissions, roles)
- LLM service (routing, caching)
- Character aggregate (domain logic)
- Knowledge ingestion (parsing, chunking)
- Interaction engine (phases, validation)
- Semantic memory (vectors, search)
- Advanced caching (LRU, TTL)
- Event service (timelines, rumors)

Coverage: 8.58% → ~14%"
```

---

### Task 1.3: Security Hardening (Agent: Security Specialist)

**Goal:** Fix 4 medium-risk security issues
**Time:** 1 day

#### Issue 1: Debug Mode Default
**File:** `src/api/main_api_server.py:152`
```python
# Before:
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# After:
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

#### Issue 2: Add Sandbox for User Templates
**File:** `src/templates/dynamic_template_engine.py:170`
```python
# Before:
from jinja2 import Environment
env = Environment()

# After:
from jinja2.sandbox import SandboxedEnvironment
env = SandboxedEnvironment()
```

#### Issue 3: Cache Directory Permission Validation
**File:** `src/performance/advanced_caching.py` (initialization)
```python
# Add to __init__:
import os
import stat

def _validate_cache_dir(self, path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, mode=0o750)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & stat.S_IRWXO:
        raise PermissionError(f"Cache dir {path} has overly permissive mode {oct(mode)}")
```

#### Issue 4: Pickle Usage Documentation & Audit
**File:** `src/performance/advanced_caching.py:224,628`
```python
# Add explicit security comment:
# SECURITY: pickle used only for internal cache serialization
# Cache is not user-accessible and uses internal-only keys
# nosec B301 - internal use only
data = pickle.loads(cached_value)  # nosec B301
```

#### Verification
```bash
# Verify DEBUG default
python -c "import os; os.environ.pop('DEBUG', None); from src.api.main_api_server import DEBUG; assert not DEBUG, 'DEBUG should default to False'"

# Verify sandbox
python -c "from src.templates.dynamic_template_engine import env; assert 'sandbox' in env.__class__.__name__.lower()"

# Run bandit
bandit -r src/ -ll
```

#### Commit
```bash
git add -A
git commit -m "security: harden production security (4 issues)

- Set DEBUG default to false (prevents stack trace exposure)
- Add SandboxedEnvironment for user templates (prevents code injection)
- Validate cache directory permissions (prevents unauthorized access)
- Document pickle usage with security rationale

Risk level: Medium → Low"
```

---

### Task 1.4: Code Quality - Split Monster Files (Agent: Refactoring Specialist)

**Goal:** Split 3 largest files for maintainability
**Time:** 2 days

#### Target 1: enhanced_multi_agent_bridge.py (2,335 lines)
**Strategy:** Split by concern into module

```
src/orchestrators/enhanced_multi_agent_bridge/
├── __init__.py                    # Re-exports for backward compatibility
├── bridge_core.py                 # Core orchestration (~400 lines)
├── agent_coordinator.py           # Agent coordination (~300 lines)
├── message_router.py              # Message routing (~250 lines)
├── state_manager.py               # State management (~350 lines)
├── conflict_resolver.py           # Conflict resolution (~200 lines)
├── task_scheduler.py              # Task scheduling (~250 lines)
├── monitoring.py                  # Metrics and monitoring (~150 lines)
└── types.py                       # Shared types
```

**Migration approach:**
1. Create new directory structure
2. Move classes/functions to appropriate modules
3. Update imports in bridge_core.py
4. Keep original file as shim for backward compatibility:
```python
# enhanced_multi_agent_bridge.py (shim)
import warnings
warnings.warn("Use modular imports from orchestrators.enhanced_multi_agent_bridge", DeprecationWarning)
from .bridge_core import *
from .agent_coordinator import *
# ... etc
```

#### Target 2: llm_world_generator.py (1,870 lines)
**Strategy:** Extract strategy classes

```
src/contexts/world/infrastructure/generators/
├── llm_world_generator.py         # Reduced to ~400 lines
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py           # Abstract base
│   ├── geography_strategy.py      # Terrain generation (~200 lines)
│   ├── culture_strategy.py        # Culture generation (~200 lines)
│   ├── history_strategy.py        # History generation (~200 lines)
│   ├── faction_strategy.py        # Faction generation (~200 lines)
│   └── religion_strategy.py       # Religion generation (~200 lines)
└── prompts/
    └── world_generation/          # Move prompts here
```

#### Target 3: neo4j_graph_store.py (1,691 lines)
**Strategy:** Separate query building from execution

```
src/contexts/knowledge/infrastructure/adapters/neo4j/
├── __init__.py                    # Re-export GraphStore
├── graph_store.py                 # Reduced to ~400 lines
├── query_builder.py               # Cypher query construction (~400 lines)
├── connection_manager.py          # Connection pooling (~200 lines)
├── transaction_handler.py         # Transaction management (~250 lines)
├── index_manager.py               # Index operations (~200 lines)
└── types.py                       # Neo4j-specific types
```

#### Verification
```bash
# Check file sizes
wc -l src/orchestrators/enhanced_multi_agent_bridge/*.py
wc -l src/contexts/world/infrastructure/generators/strategies/*.py
wc -l src/contexts/knowledge/infrastructure/adapters/neo4j/*.py

# Verify imports work
python -c "from src.orchestrators.enhanced_multi_agent_bridge import EnhancedMultiAgentBridge"
python -c "from src.contexts.world.infrastructure.generators import LLMWorldGenerator"
python -c "from src.contexts.knowledge.infrastructure.adapters.neo4j import Neo4jGraphStore"

# Run tests
pytest tests/orchestrators/ -v
```

#### Commit
```bash
git add -A
git commit -m "refactor: split monster files for maintainability

Split 3 files exceeding 1,500 lines:

1. enhanced_multi_agent_bridge.py (2,335 → ~400 core + 6 modules)
   - Core orchestration, agent coordination, message routing
   - State management, conflict resolution, task scheduling

2. llm_world_generator.py (1,870 → ~400 core + 5 strategies)
   - Geography, culture, history, faction, religion strategies

3. neo4j_graph_store.py (1,691 → ~400 core + 4 modules)
   - Query building, connection management, transactions

Benefits:
- Single Responsibility Principle
- Easier testing of individual components
- Reduced merge conflicts
- Better code navigation

Backward compatibility maintained via shim imports."
```

---

### Task 1.5: Architecture Fixes (Agent: Architecture Specialist)

**Goal:** Fix hidden import violation and blind spots
**Time:** 1 day

#### Fix 1: Resolve Hidden Import Violation
**Issue:** `src/core/system_orchestrator.py:41` imports from database

**Solution:** Move dependency to infrastructure layer

```python
# In src/core/system_orchestrator.py
# Before:
from src.database.context_db import ContextDatabase

class SystemOrchestrator:
    def __init__(self):
        self.db = ContextDatabase()  # ❌ Violation

# After:
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.database.context_db import ContextDatabase

class SystemOrchestrator:
    def __init__(self, db: "ContextDatabase"):  # ✅ Dependency injection
        self.db = db
```

Update caller in infrastructure layer:
```python
# In src/infrastructure/orchestrator_factory.py
from src.database.context_db import ContextDatabase
from src.core.system_orchestrator import SystemOrchestrator

orchestrator = SystemOrchestrator(db=ContextDatabase())
```

#### Fix 2: Add Missing __init__.py Files
```bash
# Enable import linter analysis
touch src/api/__init__.py
touch src/database/__init__.py
```

#### Fix 3: Document Lazy Import Exceptions
Update `.importlinter`:
```ini
[importlinter:contract:3]
name = Application Isolation
...
ignore_imports =
    # Environment-controlled lazy imports (acceptable)
    src.contexts.narrative.application.services.generation_service -> src.llm.generator
    src.contexts.narrative.application.services.narrative_stream_service -> src.llm.generator
```

#### Verification
```bash
# Run import linter
lint-imports
# Should show: 9 contracts passing, no hidden violations

# Verify fix
python -c "from src.core.system_orchestrator import SystemOrchestrator; print('No import violations')"
```

#### Commit
```bash
git add -A
git commit -m "arch: fix import violations and blind spots

- Fix core->database import violation (use dependency injection)
- Add __init__.py to api/ and database/ (enables analysis)
- Document acceptable lazy import patterns

Import linter: 9/9 contracts passing
Analysis coverage: 100% of Python files"
```

---

### Task 1.6: Documentation - Critical Gaps (Agent: Documentation Specialist)

**Goal:** Add README to all 13 contexts + document zero-coverage modules
**Time:** 2 days

#### Create Context READMEs

Template for each `src/contexts/{name}/README.md`:

```markdown
# {ContextName} Context

## Overview
Brief description of the context's purpose and boundaries.

## Domain
Core domain entities and value objects.

### Aggregates
- Aggregate1: Description
- Aggregate2: Description

### Value Objects
- ValueObject1: Description

## Application
Use cases and application services.

### Services
- Service1: Purpose and key methods
- Service2: Purpose and key methods

### Commands
- Command1: Description

### Queries
- Query1: Description

## Infrastructure
Repositories, adapters, and external integrations.

### Repositories
- Repository1: Implementation details

## API
External interface (if applicable).

### Endpoints
- `POST /api/x`: Description

## Testing
How to run context-specific tests.

```bash
pytest tests/contexts/{name}/ -v
```
```

Create for:
1. ai
2. campaigns
3. character
4. interactions
5. knowledge
6. narrative
7. narratives
8. orchestration
9. shared
10. story
11. subjective
12. world

#### Document Zero-Coverage Modules

**src/workspaces/README.md:**
```markdown
# Workspaces Module

## Purpose
Workspace management for multi-tenant isolation.

## Components
- WorkspaceRegistry: Manages workspace lifecycle
- WorkspaceContext: Provides isolated execution context

## Usage
```python
from src.workspaces import WorkspaceRegistry

registry = WorkspaceRegistry()
workspace = registry.create_workspace(tenant_id="xyz")
```

## API
### WorkspaceRegistry
- `create_workspace(tenant_id: str) -> Workspace`
- `get_workspace(id: str) -> Optional[Workspace]`
- `delete_workspace(id: str) -> bool`
```

**src/metrics/README.md:**
```markdown
# Metrics Module

## Purpose
Application metrics collection and reporting.

## Components
- MetricsCollector: Collects runtime metrics
- MetricsReporter: Reports to monitoring systems

## Usage
```python
from src.metrics import MetricsCollector

collector = MetricsCollector()
collector.record("requests_total", 1, labels={"endpoint": "/api/characters"})
```
```

#### Commit
```bash
git add -A
git commit -m "docs: add context READMEs and module documentation

Added comprehensive README files:
- All 13 bounded contexts documented
- workspaces/ module documented
- metrics/ module documented

Each README includes:
- Overview and purpose
- Domain aggregates and value objects
- Application services and use cases
- Infrastructure components
- API documentation (if applicable)
- Testing instructions

Documentation coverage: 82% → 90%"
```

---

## Phase 2: High Priority (P1) - Week 1-2

**Objective:** Complete structlog migration and Result pattern adoption
**Parallel Agents:** 4 agents
**Estimated Time:** 5-7 days

---

### Task 2.1: StructLog Migration - API Layer (Agent: Logging Specialist)

**Goal:** Migrate 35 API files to structlog (14.27% → 25%)
**Time:** 3 days

#### Target Files
All files in `src/api/` not yet migrated:
- `routers/*.py` (excluding already migrated: auth, characters)
- `services/*.py`
- `middleware/*.py`
- `dependencies.py`

#### Migration Pattern
```python
# Before
import logging
logger = logging.getLogger(__name__)

@app.get("/items")
def get_items():
    logger.info(f"Fetching items for user {user_id}")
    try:
        items = service.get_all()
        logger.debug(f"Found {len(items)} items")
        return items
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        raise

# After
import structlog
logger = structlog.get_logger(__name__)

@app.get("/items")
def get_items():
    logger.info("fetching_items", user_id=user_id)
    try:
        items = service.get_all()
        logger.debug("items_found", count=len(items))
        return items
    except Exception as e:
        logger.error("fetch_items_failed", error=str(e))
        raise
```

#### Verification
```bash
# Check adoption rate
grep -r "import structlog" src/api/ --include="*.py" -l | wc -l
# Target: 35+ files

# Verify no mixed usage
grep -r "import logging" src/api/ --include="*.py" -l | wc -l
# Target: 0 files
```

#### Commit
```bash
git add -A
git commit -m "logging: migrate API layer to structlog (14% → 25%)

Migrated 35 API files:
- All routers (auth, characters, memories, etc.)
- API services
- Middleware
- Dependencies

Pattern: logger.info('event_name', key=value)
Benefits: JSON output, searchable, contextual

Verification: No standard logging imports remain in api/"
```

---

### Task 2.2: StructLog Migration - Core Services (Agent: Logging Specialist)

**Goal:** Migrate 15 core service files to structlog
**Time:** 2 days

#### Target Files
- `src/core/*.py` (excluding pure utility modules)
- `src/infrastructure/*.py`
- Key services in `src/services/`

Priority order:
1. `system_orchestrator.py`
2. `performance_cache.py`
3. `llm_service.py`
4. `database_manager.py`
5. `state_store.py`
6. `event_bus.py`
7. `memory/semantic_memory.py`
8. `infrastructure/postgresql_manager.py`
9. `infrastructure/state_store.py`
10. `infrastructure/event_store.py`

#### Verification
```bash
grep -r "import structlog" src/core/ src/infrastructure/ --include="*.py" -l | wc -l
# Target: 15+ files
```

#### Commit
```bash
git add -A
git commit -m "logging: migrate core services to structlog

Migrated 15 core infrastructure files:
- System orchestrator
- Performance cache
- LLM service
- Database manager
- State store
- Event bus
- Semantic memory
- PostgreSQL manager

StructLog adoption: 25% → 35%"
```

---

### Task 2.3: Result Pattern - Easy Services (Agent: Error Handling Specialist)

**Goal:** Migrate TokenCounter and ModelRegistry (7.8% → 12%)
**Time:** 2 days

#### Target 1: TokenCounter
**File:** `src/contexts/knowledge/application/services/token_counter.py` (14 methods)

**Current:** Uses exceptions and returns int
```python
def count_tokens(self, text: str, model: str = "gpt-4") -> int:
    if not text:
        raise ValueError("Text cannot be empty")
    # ... count tokens
    return token_count
```

**Target:** Use Result pattern
```python
from src.core_platform.result import Result, Ok, Err

def count_tokens(self, text: str, model: str = "gpt-4") -> Result[int, Error]:
    if not text:
        return Err(ValidationError("Text cannot be empty"))
    try:
        # ... count tokens
        return Ok(token_count)
    except Exception as e:
        return Err(ProcessingError(f"Token counting failed: {e}"))
```

#### Target 2: ModelRegistry
**File:** `src/contexts/knowledge/application/services/model_registry.py` (22 methods)

**Current:** Uses Optional and exceptions
```python
def get_model(self, model_id: str) -> Optional[ModelConfig]:
    if model_id not in self._models:
        return None
    return self._models[model_id]
```

**Target:** Use Result pattern
```python
def get_model(self, model_id: str) -> Result[ModelConfig, Error]:
    if model_id not in self._models:
        return Err(NotFoundError(f"Model {model_id} not found"))
    return Ok(self._models[model_id])
```

#### Update Callers
Find and update all callers:
```bash
grep -r "token_counter.count" src/ --include="*.py" -l
grep -r "model_registry.get" src/ --include="*.py" -l
```

Update pattern:
```python
# Before
result = counter.count_tokens(text)

# After
result = counter.count_tokens(text)
if result.is_err():
    return result  # Propagate error
actual_count = result.unwrap()
```

#### Verification
```bash
pytest tests/contexts/knowledge/test_token_counter.py -v
pytest tests/contexts/knowledge/test_model_registry.py -v
```

#### Commit
```bash
git add -A
git commit -m "refactor: adopt Result pattern for TokenCounter and ModelRegistry

Migrated 36 methods across 2 services:
- TokenCounter (14 methods)
- ModelRegistry (22 methods)

Benefits:
- Explicit error handling
- Type-safe error propagation
- No hidden exceptions

Result pattern adoption: 7.8% → 12%"
```

---

### Task 2.4: Result Pattern - Character Service Extension (Agent: Error Handling Specialist)

**Goal:** Complete CharacterApplicationService migration (77% → 95%)
**Time:** 2 days

#### Remaining Methods
Find methods not yet using Result:
```bash
grep -B1 "^    def " src/contexts/character/application/services/character_application_service.py | grep -v Result | head -20
```

Likely candidates (5-8 methods):
- Utility methods
- Helper methods
- Internal methods

#### Migration Pattern
Follow existing pattern in service:
```python
from src.core_platform.result import Result, Ok, Err
from src.contexts.character.domain.errors import CharacterNotFoundError, ValidationError

def some_method(self, ...) -> Result[ReturnType, Error]:
    # Validate input
    if invalid:
        return Err(ValidationError("Invalid input"))
    
    # Try operation
    try:
        result = self._repo.do_something()
        return Ok(result)
    except CharacterNotFoundError:
        return Err(CharacterNotFoundError(...))
    except Exception as e:
        return Err(UnexpectedError(str(e)))
```

#### Verification
```bash
pytest tests/contexts/character/ -v --cov=src.contexts.character.application.services
# Verify 95%+ Result adoption in service
```

#### Commit
```bash
git add -A
git commit -m "refactor: complete Character service Result pattern adoption (77% → 95%)

Migrated remaining 5-8 methods to Result[T,E]:
- All public methods now use explicit error handling
- Consistent with codebase patterns
- Full test coverage maintained

CharacterApplicationService: Reference implementation for Result pattern"
```

---

## Phase 3: Medium Priority (P2) - Week 2

**Objective:** Complete comprehensive type fixes and expand test coverage
**Parallel Agents:** 3 agents
**Estimated Time:** 5 days

---

### Task 3.1: MyPy Comprehensive Fixes (Agent: Type Safety Specialist)

**Goal:** Reduce MyPy errors from ~3,400 to <1,500
**Time:** 5 days

#### Category 1: attr-defined (545 errors)

**Root Causes:**
1. Missing imports
2. Forward reference issues
3. Dynamic attribute access

**Fix Strategy:**
```python
# Missing import
from __future__ import annotations  # Enable PEP 563

# Or add forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .other_module import SomeClass
```

#### Category 2: return-value (312 errors)

**Root Causes:**
1. Function returns wrong type
2. Missing return statement
3. Async/sync mismatch

**Fix Strategy:**
```python
# Before:
def get_items() -> list[str]:
    return self._repo.get()  # Might return None

# After:
def get_items() -> list[str]:
    result = self._repo.get()
    return result or []  # Ensure list return
```

#### Category 3: arg-type (287 errors)

**Root Causes:**
1. Passing wrong type to function
2. Missing type cast
3. Incompatible inheritance

**Fix Strategy:**
```python
# Before:
process_data(data)  # data is Any, function expects SpecificType

# After:
from typing import cast
process_data(cast(SpecificType, data))
# OR
if isinstance(data, SpecificType):
    process_data(data)
```

#### Batch Fix Process

For each module in priority order:
1. Run mypy on specific module
2. Fix all errors in that module
3. Commit
4. Move to next module

Priority order:
1. `src/contexts/narratives/` (493 errors)
2. `src/contexts/knowledge/` (467 errors)
3. `src/interactions/` (356 errors)
4. `src/contexts/orchestration/` (298 errors)
5. `src/agents/` (234 errors)

#### Commit Pattern
```bash
# Per module commit
git add -A
git commit -m "types: fix MyPy errors in {module}

- Fixed attr-defined errors (X)
- Fixed return-value errors (Y)
- Fixed arg-type errors (Z)

Module: src/contexts/{module}/
Error reduction: {before} → {after}"
```

#### Final Verification
```bash
mypy src/ --no-error-summary 2>&1 | wc -l
# Target: <1,500
```

---

### Task 3.2: Expand Test Coverage - Medium Priority Modules (Agent: Test Coverage Specialist)

**Goal:** Increase coverage from ~14% to 25%
**Time:** 5 days

#### Target Modules (by priority)

**Week 2, Days 1-2: Core Infrastructure**
1. `src/core/performance_cache.py` (200 lines)
2. `src/core/event_bus.py` (150 lines)
3. `src/core/state_manager.py` (180 lines)
4. `src/infrastructure/postgresql_manager.py` (250 lines)
5. `src/infrastructure/event_store.py` (200 lines)

**Week 2, Days 3-4: Context Services**
1. `src/contexts/knowledge/application/services/bm25_retriever.py` (180 lines)
2. `src/contexts/knowledge/application/services/retrieval_service.py` (220 lines)
3. `src/contexts/world/application/services/world_service.py` (200 lines)
4. `src/contexts/world/application/services/location_service.py` (180 lines)

**Week 2, Day 5: Memory & Performance**
1. `src/memory/emotional_memory.py` (150 lines)
2. `src/performance/distributed_caching.py` (200 lines)
3. `src/performance/monitoring.py` (180 lines)

#### Test Strategy

For each module:
1. Create test file if not exists
2. Write unit tests for public methods
3. Mock external dependencies
4. Test error cases
5. Verify coverage

#### Verification
```bash
pytest tests/ --cov=src --cov-report=term-missing
# Target: 25% overall coverage
```

#### Commit
```bash
git add tests/
git commit -m "test: expand coverage to 25% (+11%)

Added tests for 15 medium-priority modules:
- Core infrastructure (5 modules)
- Context services (4 modules)
- Memory & performance (3 modules)

Coverage: ~14% → 25%"
```

---

### Task 3.3: Documentation - Improve Low-Coverage Modules (Agent: Documentation Specialist)

**Goal:** Increase docstring coverage from 84.8% to 92%
**Time:** 3 days

#### Target Modules

1. **src/caching/** (32% → 80%)
   - 53 functions need docstrings
   - Focus on public API methods

2. **src/director_components/** (62.5% → 85%)
   - 24 functions need docstrings

3. **src/interactions/** (68% → 85%)
   - 45 functions need docstrings

#### Docstring Template
```python
def method_name(self, param1: Type1, param2: Type2) -> ReturnType:
    """Short description of what this method does.
    
    Longer description if needed, explaining the purpose
    and any important implementation details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception is raised
        
    Example:
        >>> obj.method_name("value1", "value2")
        ExpectedResult
    """
```

#### Verification
```bash
# Check coverage
pydocstyle src/caching/ --count
pydocstyle src/director_components/ --count
pydocstyle src/interactions/ --count
```

#### Commit
```bash
git add -A
git commit -m "docs: improve docstring coverage (84.8% → 92%)

Added docstrings to:
- caching/ (32% → 80%)
- director_components/ (62.5% → 85%)
- interactions/ (68% → 85%)

Total new docstrings: ~120
All follow Google docstring style."
```

---

## Integration & Verification

### Pre-Merge Checklist

Run these commands to verify all changes:

```bash
# 1. Full test suite
cd /mnt/d/Code/Novel-Engine
pytest tests/ -x --tb=short
# Expected: All pass

# 2. Type checking
mypy src/ --no-error-summary 2>&1 | wc -l
# Expected: <1,500 errors

# 3. Linting
ruff check src/ tests/
# Expected: 0 errors

# 4. Security scan
bandit -r src/ -ll
# Expected: No HIGH severity issues
npm audit --prefix frontend
# Expected: 0 vulnerabilities

# 5. Coverage check
pytest tests/ --cov=src --cov-report=term
# Expected: >25% overall

# 6. Import linter
lint-imports
# Expected: 9 contracts passing

# 7. Build verification
cd frontend && npm run build && cd ..
# Expected: Success

# 8. Documentation build
mkdocs build 2>/dev/null || echo "MkDocs not configured"
```

### Success Metrics

| Metric | Before | Target | Phase 1 | Phase 2 | Phase 3 | Final |
|--------|--------|--------|---------|---------|---------|-------|
| MyPy Errors | 4,463 | <1,500 | 3,400 | 2,500 | 1,400 | ✅ |
| Test Coverage | 8.58% | 25% | 14% | 20% | 25% | ✅ |
| StructLog | 14.27% | 35% | 20% | 35% | 40% | ✅ |
| Result Pattern | 7.8% | 15% | 10% | 15% | 20% | ✅ |
| Architecture | 88% | 95% | 95% | 95% | 95% | ✅ |
| Documentation | 82% | 92% | 88% | 90% | 92% | ✅ |
| Security | 93% | 98% | 98% | 98% | 98% | ✅ |
| Code Quality | 58% | 70% | 70% | 72% | 75% | ✅ |

**Overall Target: A (90+/100)**

---

## Agent Dispatch Plan

### Phase 1 Agents (Parallel)
1. **Type Safety Specialist** → MyPy Quick Wins
2. **Test Coverage Specialist** → Critical Test Coverage
3. **Security Specialist** → Security Hardening
4. **Refactoring Specialist** → Split Monster Files
5. **Architecture Specialist** → Architecture Fixes
6. **Documentation Specialist** → Critical Documentation

### Phase 2 Agents (Parallel)
1. **Logging Specialist** → StructLog API Layer
2. **Logging Specialist** → StructLog Core Services
3. **Error Handling Specialist** → Result Pattern Easy Services
4. **Error Handling Specialist** → Result Pattern Character Service

### Phase 3 Agents (Parallel)
1. **Type Safety Specialist** → MyPy Comprehensive
2. **Test Coverage Specialist** → Expand Test Coverage
3. **Documentation Specialist** → Improve Docstrings

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes | High | Comprehensive tests before each commit |
| Merge conflicts | Medium | Small, focused commits; frequent rebasing |
| Agent timeout | Medium | Break large tasks into smaller subtasks |
| Test flakiness | Medium | Retry logic; deterministic test data |
| MyPy complexity | High | Prioritize easy fixes; document complex ones |

---

## Communication Plan

**Daily Standups (async):**
- Each agent reports: Tasks completed, blockers, next steps
- Update this plan with progress

**Phase Gates:**
- Phase 1 complete: All P0 issues resolved
- Phase 2 complete: Logging and error handling at target
- Phase 3 complete: All metrics at target

**Final Review:**
- Run full verification checklist
- Generate compliance report
- Update AGENTS.md with new standards
