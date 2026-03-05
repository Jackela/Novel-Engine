# Brain Settings Router Split Plan

## Overview

**Source File**: `src/api/routers/brain_settings.py`  
**Current Size**: 2,230 lines  
**Target Size**: <500 lines per module  
**Architecture**: Hexagonal - Router layer should only handle HTTP concerns

---

## Current Structure Analysis

### File Sections (by line number)

```
Lines   Section                          Description
-----   -------                          -----------
1-56    Header & Imports                 Module docstring, imports
57-228  Encryption Utilities             get_encryption_key, get_fernet, encrypt/decrypt
229-358 Repository Class                 InMemoryBrainSettingsRepository (130 lines)
359-622 Query Endpoints                  GET /brain/settings/*
623-938 Token Usage Analytics            Usage tracking, repositories
939-1115 Model Pricing                  Model pricing endpoints
1116-1485 Real-time Usage Streaming      SSE streaming infrastructure
1486-1599 Async Ingestion Job API        Background job processing
1600-1872 Ingestion Endpoints            POST/GET ingestion jobs
1873-1960 RAG Context Retrieval          Context retrieval endpoints
1961-2178 Chat Endpoint                  Streaming chat completion
2179-2230 Chat Session Endpoints         Session management
```

### Classes in Current File

| Class | Line Range | Lines | Responsibility |
|-------|------------|-------|----------------|
| InMemoryBrainSettingsRepository | 233-358 | 125 | Settings storage |
| InMemoryTokenUsageRepository | 648-800 | 152 | Token usage storage |
| ModelPricingResponse | 942-966 | 24 | API schema |
| RealtimeUsageBroadcaster | 1119-1265 | 146 | SSE broadcasting |
| IngestionJob | 1325-1386 | 61 | Job data model |
| IngestionJobStore | 1387-1489 | 102 | Job management |
| ChatMessage | 1876-1892 | 16 | Chat message schema |
| ChatSessionStore | 1937-1966 | 29 | Session storage |
| ChatChunk | 1967-1973 | 6 | Response chunk |
| ChatSessionListResponse | 2164-2170 | 6 | Response schema |
| ChatSessionMessagesResponse | 2171-2178 | 7 | Response schema |

### Endpoint Groups

| Group | Endpoints | Lines | Description |
|-------|-----------|-------|-------------|
| Settings CRUD | 5 | ~200 | API keys, RAG config |
| Token Usage | 6 | ~400 | Analytics, streaming |
| Ingestion | 4 | ~300 | Async job management |
| RAG Context | 1 | ~50 | Context retrieval |
| Chat | 4 | ~350 | Chat completion, sessions |

---

## Target Architecture

```
src/api/routers/brain/
├── __init__.py              # Router aggregation & exports
├── core.py                  # Shared dependencies, encryption utils
├── dependencies.py          # FastAPI dependency injection
├── repositories/
│   ├── __init__.py
│   ├── brain_settings.py    # InMemoryBrainSettingsRepository
│   ├── token_usage.py       # InMemoryTokenUsageRepository
│   └── chat_session.py      # ChatSessionStore
├── services/
│   ├── __init__.py
│   ├── encryption.py        # Encryption/decryption utilities
│   ├── usage_broadcaster.py # RealtimeUsageBroadcaster
│   └── ingestion_worker.py  # Background job processing
└── endpoints/
    ├── __init__.py
    ├── settings.py          # Settings CRUD (target: ~400 lines)
    ├── usage.py             # Token usage analytics (target: ~450 lines)
    ├── ingestion.py         # Async ingestion jobs (target: ~350 lines)
    ├── rag_context.py       # RAG context retrieval (target: ~100 lines)
    └── chat.py              # Chat & sessions (target: ~400 lines)
```

---

## Module Specifications

### 1. `brain/core.py` (~150 lines)

**Responsibilities**: Shared constants, types, encryption utilities

**Contents**:
- `_ENCRYPTION_KEY_WARNING_SHOWN` global
- `get_encryption_key()` function
- `get_fernet()` function
- `_encrypt_api_key()` function
- `_decrypt_api_key()` function
- `_mask_api_key()` function
- `_require_encryption()` function

**Imports**: `cryptography.fernet`, `os`, `logging`

### 2. `brain/dependencies.py` (~100 lines)

**Responsibilities**: FastAPI dependency injection functions

**Contents**:
- `get_brain_settings_repository()`
- `get_token_usage_repository()`
- `get_ingestion_job_store()`
- `get_ingestion_service()`
- `get_usage_broadcaster()`
- `get_context_window_manager()`

### 3. `brain/repositories/brain_settings.py` (~130 lines)

**Responsibilities**: In-memory brain settings storage

**Contents**:
- `InMemoryBrainSettingsRepository` class
- Methods: `get_settings`, `update_api_keys`, `get_api_keys`, `update_rag_config`, `get_rag_config`, `get_knowledge_base_status`

**Note**: This should eventually migrate to a proper persistence layer.

### 4. `brain/repositories/token_usage.py` (~160 lines)

**Responsibilities**: Token usage tracking and analytics

**Contents**:
- `InMemoryTokenUsageRepository` class
- Methods: `record_usage`, `get_usage_summary`, `get_daily_usage`, `get_usage_by_model`, `export_usage_csv`, `_seed_mock_data`

### 5. `brain/services/usage_broadcaster.py` (~150 lines)

**Responsibilities**: Real-time usage streaming via SSE

**Contents**:
- `RealtimeUsageBroadcaster` class
- Methods: `start_session`, `update_session`, `complete_session`, `subscribe`, `_broadcast_to_all`, `_cleanup_session`
- Global `_usage_broadcaster` instance

### 6. `brain/services/ingestion_worker.py` (~80 lines)

**Responsibilities**: Background ingestion job processing

**Contents**:
- `_run_ingestion_job()` async function
- Job state management logic

### 7. `brain/endpoints/settings.py` (~400 lines)

**Endpoints**:
```python
GET  /brain/settings                    # Get all settings
GET  /brain/settings/api-keys           # Get API keys (masked)
GET  /brain/settings/rag-config         # Get RAG configuration
PUT  /brain/settings/api-keys           # Update API keys
PUT  /brain/settings/rag-config         # Update RAG configuration
POST /brain/settings/test-connection    # Test LLM connection
```

### 8. `brain/endpoints/usage.py` (~450 lines)

**Endpoints**:
```python
GET /brain/usage/summary      # Usage summary with filters
GET /brain/usage/daily        # Daily usage aggregation
GET /brain/usage/by-model     # Usage grouped by model
GET /brain/usage/export       # CSV export
GET /brain/usage/stream       # SSE real-time stream
GET /brain/models             # Available models with pricing
```

### 9. `brain/endpoints/ingestion.py` (~350 lines)

**Contents**:
- `IngestionJob`, `IngestionJobStore` classes
- Background task management

**Endpoints**:
```python
POST /brain/ingestion         # Start async job
GET  /brain/ingestion/{id}    # Get job status
GET  /brain/ingestion         # List jobs
```

### 10. `brain/endpoints/rag_context.py` (~100 lines)

**Endpoints**:
```python
GET /brain/context            # Retrieve RAG context chunks
```

### 11. `brain/endpoints/chat.py` (~400 lines)

**Contents**:
- `ChatMessage`, `ChatChunk`, `ChatSessionStore` classes
- `ChatRequest`, `ChatSessionListResponse`, `ChatSessionMessagesResponse` schemas

**Endpoints**:
```python
POST /brain/chat                    # Streaming chat completion
GET  /brain/chat/sessions           # List chat sessions
GET  /brain/chat/sessions/{id}      # Get session messages
DELETE /brain/chat/sessions/{id}    # Delete session
```

### 12. `brain/__init__.py` (~50 lines)

**Responsibilities**: Aggregate all routers

```python
from fastapi import APIRouter
from .endpoints import settings, usage, ingestion, rag_context, chat

router = APIRouter(tags=["brain-settings"])
router.include_router(settings.router, prefix="/brain")
router.include_router(usage.router, prefix="/brain")
router.include_router(ingestion.router, prefix="/brain")
router.include_router(rag_context.router, prefix="/brain")
router.include_router(chat.router, prefix="/brain")
```

---

## Migration Steps

### Phase 1: Preparation (1 day)

1. **Create directory structure**
   ```bash
   mkdir -p src/api/routers/brain/{repositories,services,endpoints}
   touch src/api/routers/brain/__init__.py
   touch src/api/routers/brain/repositories/__init__.py
   touch src/api/routers/brain/services/__init__.py
   touch src/api/routers/brain/endpoints/__init__.py
   ```

2. **Add feature flag** (optional)
   - Add `BRAIN_ROUTER_V2=1` env var
   - Allow gradual rollout

3. **Create backup**
   ```bash
   cp src/api/routers/brain_settings.py src/api/routers/brain_settings.py.bak
   ```

### Phase 2: Extract Shared Components (Day 2-3)

1. **Extract encryption utilities** → `brain/core.py`
   - Copy functions: `get_encryption_key`, `get_fernet`, `_encrypt_api_key`, `_decrypt_api_key`, `_mask_api_key`, `_require_encryption`
   - Add comprehensive unit tests

2. **Extract repositories** → `brain/repositories/`
   - Move `InMemoryBrainSettingsRepository`
   - Move `InMemoryTokenUsageRepository`
   - Move `ChatSessionStore`
   - Ensure all imports work

3. **Extract services** → `brain/services/`
   - Move `RealtimeUsageBroadcaster`
   - Move `_run_ingestion_job` worker function

4. **Create dependencies** → `brain/dependencies.py`
   - Consolidate all dependency injection functions

### Phase 3: Extract Endpoint Modules (Day 4-6)

1. **Settings endpoints** → `brain/endpoints/settings.py`
   - Copy all settings-related routes
   - Update imports
   - Test each endpoint

2. **Usage endpoints** → `brain/endpoints/usage.py`
   - Copy usage analytics routes
   - Copy streaming endpoint
   - Copy model pricing

3. **Ingestion endpoints** → `brain/endpoints/ingestion.py`
   - Copy job management routes
   - Copy background task logic

4. **RAG context endpoints** → `brain/endpoints/rag_context.py`
   - Copy context retrieval route

5. **Chat endpoints** → `brain/endpoints/chat.py`
   - Copy chat completion route
   - Copy session management routes

### Phase 4: Integration & Testing (Day 7-8)

1. **Create main router** → `brain/__init__.py`
   - Aggregate all sub-routers
   - Ensure tag consistency

2. **Update main API** → `src/api/main.py`
   - Replace old import with new
   ```python
   # Old
   from src.api.routers.brain_settings import router as brain_settings_router
   
   # New
   from src.api.routers.brain import router as brain_settings_router
   ```

3. **Run comprehensive tests**
   ```bash
   pytest tests/api/routers/test_brain_settings.py -v
   pytest tests/ -k "brain" -v
   ```

4. **Verify no regression**
   - All existing tests pass
   - API contract unchanged (OpenAPI spec identical)

### Phase 5: Cleanup (Day 9)

1. **Remove old file**
   ```bash
   rm src/api/routers/brain_settings.py
   ```

2. **Update imports throughout codebase**
   ```bash
   grep -r "brain_settings" src/ --include="*.py" | grep -v __pycache__
   ```

3. **Update documentation**
   - ARCHITECTURE.md
   - API docs

---

## Compatibility Guarantee

### API Contract Preservation

- All endpoint paths remain identical
- All request/response schemas unchanged
- All query parameters preserved
- All status codes maintained

### Import Compatibility

```python
# These imports must continue to work:
from src.api.routers.brain_settings import router  # Via __init__.py re-export
from src.api.routers.brain_settings import InMemoryBrainSettingsRepository  # Moved
```

### Backward Compatibility Layer

Create `src/api/routers/brain_settings.py` as a re-export module (temporary):

```python
# src/api/routers/brain_settings.py
"""Backward compatibility shim - will be removed in v2.0"""
import warnings
from src.api.routers.brain import router
from src.api.routers.brain.repositories import (
    InMemoryBrainSettingsRepository,
    InMemoryTokenUsageRepository,
)

warnings.warn(
    "brain_settings module is deprecated, use brain module directly",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["router", "InMemoryBrainSettingsRepository", "InMemoryTokenUsageRepository"]
```

---

## Risk Analysis

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Import cycles | High | Medium | Careful import ordering, use TYPE_CHECKING |
| Missing dependencies | High | Low | Comprehensive test coverage before merge |
| Endpoint path changes | High | Low | Strict path preservation verification |
| Performance regression | Low | Low | Benchmark before/after |
| Schema drift | Medium | Low | Automated OpenAPI diff |
| Broken SSE streams | High | Low | Manual testing of streaming endpoints |
| Session data loss | Medium | Low | In-memory only, ephemeral by design |

---

## Testing Strategy

### Unit Tests
- Test each extracted module independently
- Mock dependencies appropriately

### Integration Tests
- Test full request/response cycle
- Verify all endpoints return expected data

### Contract Tests
```bash
# Generate OpenAPI before and after
python -c "from src.api.main import app; import json; print(json.dumps(app.openapi()))" > before.json
# ... after refactoring ...
python -c "from src.api.main import app; import json; print(json.dumps(app.openapi()))" > after.json
# Diff should be empty (or only description changes)
diff before.json after.json
```

### E2E Tests
- Run full API test suite
- Verify frontend compatibility

---

## Success Criteria

- [ ] All modules <500 lines
- [ ] All existing tests pass without modification
- [ ] OpenAPI spec identical (except descriptions)
- [ ] No import errors in codebase
- [ ] Manual smoke test of all endpoints passes
- [ ] Code review approval

---

## Post-Refactoring Opportunities

1. **Repository Pattern**: Replace in-memory repos with persistent storage
2. **Service Layer**: Extract business logic from endpoints to services
3. **Caching**: Add Redis caching for frequently accessed settings
4. **Rate Limiting**: Implement per-endpoint rate limits
5. **Observability**: Add structured logging and metrics
