# Large File Refactoring - Implementation Roadmap

## Executive Summary

This document outlines the plan for refactoring two oversized files in the Novel Engine codebase to improve maintainability, testability, and adherence to hexagonal architecture principles.

| File | Current Size | Target Structure | Est. Effort |
|------|--------------|------------------|-------------|
| `brain_settings.py` | 2,230 lines | 12 modules (~200-450 lines each) | 8-9 days |
| `chunking_strategy_adapters.py` | 2,531 lines | 12 modules (~100-630 lines each) | 6 days |
| **Total** | **4,761 lines** | **24 modules** | **14-15 days** |

---

## Priority Matrix

### Impact vs Effort Analysis

```
                    EFFORT
                Low ◄─────────► High
              ┌─────────┬─────────┐
         High │ Chunking│ Brain   │
              │Strategy │Settings│
    I         │ (P1)    │ (P2)   │
    M   ──────┼─────────┼─────────┼──────
    P    Low  │ Utils   │ Legacy  │
    A         │Extract  │ Cleanup │
    C         │ (P1)    │ (P3)   │
    T         └─────────┴─────────┘
```

### Recommended Priority Order

1. **P1 - High Impact, Low Effort** (Week 1)
   - Chunking strategy refactor (Strategy Pattern)
   - Utility extraction

2. **P2 - High Impact, High Effort** (Week 2-3)
   - Brain settings router split
   - Dependency reorganization

3. **P3 - Low Impact, Various Effort** (Week 4)
   - Legacy cleanup
   - Documentation updates
   - Import optimization

---

## Detailed Roadmap

### Phase 1: Foundation (Week 1, Days 1-2)

#### Day 1: Project Setup

**Morning (4h)**
- [ ] Create feature branch: `refactor/large-file-cleanup`
- [ ] Set up directory structure for both refactors
- [ ] Create backup of source files
- [ ] Run baseline tests and record metrics

**Afternoon (4h)**
- [ ] Extract shared utilities from chunking file
  - Create `chunking/utils.py`
  - Move regex patterns and helper functions
- [ ] Create base strategy class
  - `chunking/base.py` with `BaseChunkingStrategy`

**Deliverables**:
- Directory structure created
- Utility modules with tests passing

#### Day 2: Chunking - Simple Strategies

**Morning (4h)**
- [ ] Extract `FixedChunkingStrategy` → `chunking/strategies/fixed.py`
- [ ] Extract `SentenceChunkingStrategy` → `chunking/strategies/sentence.py`
- [ ] Unit tests for both strategies

**Afternoon (4h)**
- [ ] Extract `ParagraphChunkingStrategy` → `chunking/strategies/paragraph.py`
- [ ] Extract shared components
  - `chunking/coherence.py` (CoherenceScore, ChunkCoherenceAnalyzer)
  - `chunking/content_type.py` (ContentType enum)

**Deliverables**:
- 3 simple strategies extracted and tested
- Shared components isolated

---

### Phase 2: Chunking Completion (Week 1, Days 3-4)

#### Day 3: Complex Strategies

**Morning (4h)**
- [ ] Extract `SemanticChunkingStrategy` → `chunking/strategies/semantic.py`
- [ ] Extract `NarrativeFlowChunkingStrategy` → `chunking/strategies/narrative.py`

**Afternoon (4h)**
- [ ] Extract `AutoChunkingStrategy` → `chunking/strategies/auto.py`
- [ ] Create strategy factory
  - `chunking/factory.py`
  - Auto-registration of strategies

**Deliverables**:
- All 6 strategies in separate modules
- Factory pattern implemented

#### Day 4: Chunking Integration

**Morning (4h)**
- [ ] Create `chunking/__init__.py` with public exports
- [ ] Create backward compatibility shim
- [ ] Update all imports throughout codebase

**Afternoon (4h)**
- [ ] Comprehensive testing
  - All chunking tests pass
  - Performance benchmark comparison
  - Import cycle detection
- [ ] Code review preparation

**Deliverables**:
- Chunking refactor complete
- All tests passing
- PR ready for review

---

### Phase 3: Brain Settings - Preparation (Week 2, Days 5-6)

#### Day 5: Structure & Shared Components

**Morning (4h)**
- [ ] Create directory structure
  ```
  src/api/routers/brain/
  ├── __init__.py
  ├── core.py
  ├── dependencies.py
  ├── repositories/
  ├── services/
  └── endpoints/
  ```
- [ ] Extract encryption utilities → `brain/core.py`

**Afternoon (4h)**
- [ ] Extract repositories
  - `brain/repositories/brain_settings.py`
  - `brain/repositories/token_usage.py`
- [ ] Create dependency injection module
  - `brain/dependencies.py`

**Deliverables**:
- Directory structure created
- Core utilities and repositories extracted

#### Day 6: Services & Background Workers

**Morning (4h)**
- [ ] Extract services
  - `brain/services/usage_broadcaster.py`
  - `brain/services/ingestion_worker.py`

**Afternoon (4h)**
- [ ] Unit tests for services
- [ ] Mock repository implementations
- [ ] Service integration tests

**Deliverables**:
- Services module complete with tests

---

### Phase 4: Brain Settings - Endpoints (Week 2-3, Days 7-9)

#### Day 7: Settings & Usage Endpoints

**Morning (4h)**
- [ ] Extract settings endpoints → `brain/endpoints/settings.py`
  - 6 endpoints for settings CRUD
- [ ] Test settings endpoints

**Afternoon (4h)**
- [ ] Extract usage endpoints → `brain/endpoints/usage.py`
  - 6 endpoints for analytics & streaming
- [ ] Test usage endpoints

**Deliverables**:
- Settings and usage endpoints migrated

#### Day 8: Ingestion & RAG Endpoints

**Morning (4h)**
- [ ] Extract ingestion endpoints → `brain/endpoints/ingestion.py`
  - 4 endpoints for async jobs
- [ ] Test ingestion endpoints

**Afternoon (4h)**
- [ ] Extract RAG context endpoint → `brain/endpoints/rag_context.py`
- [ ] Extract chat endpoints → `brain/endpoints/chat.py`
- [ ] Test RAG and chat endpoints

**Deliverables**:
- All endpoint modules migrated

#### Day 9: Integration & Aggregation

**Morning (4h)**
- [ ] Create main router aggregator
  - `brain/__init__.py` with router composition
- [ ] Update main API imports
- [ ] OpenAPI spec comparison

**Afternoon (4h)**
- [ ] Comprehensive testing
  - All API tests pass
  - Integration tests
  - E2E smoke tests

**Deliverables**:
- Brain settings refactor complete
- All tests passing

---

### Phase 5: Cleanup & Validation (Week 3-4, Days 10-14)

#### Day 10: Documentation & Review

**Morning (4h)**
- [ ] Update ARCHITECTURE.md
- [ ] Update API documentation
- [ ] Add migration guide

**Afternoon (4h)**
- [ ] Code review for both refactors
- [ ] Address review feedback
- [ ] Performance validation

**Deliverables**:
- Documentation updated
- Code review complete

#### Day 11: Legacy Cleanup

**Morning (4h)**
- [ ] Remove old files
  - `chunking_strategy_adapters.py`
  - `brain_settings.py`

**Afternoon (4h)**
- [ ] Final import cleanup
- [ ] Remove backward compatibility shims (if approved)

**Deliverables**:
- Old files removed
- Clean codebase

#### Day 12-14: Buffer & Polish

**Activities**:
- [ ] Address any remaining issues
- [ ] Final testing
- [ ] Merge preparation
- [ ] Team knowledge transfer

---

## Risk Mitigation Timeline

| Risk | Detection Point | Mitigation Action | Owner |
|------|-----------------|-------------------|-------|
| Import cycles | Day 2, 6 | Add TYPE_CHECKING guards, restructure | Developer |
| Test failures | Day 4, 9, 11 | Rollback, fix, re-test | Developer |
| Performance regression | Day 4, 10 | Profile, optimize bottlenecks | Developer |
| Circular dependencies | Day 6 | Dependency injection refactor | Developer |
| Schema drift | Day 9 | OpenAPI diff validation | Developer |

---

## Success Metrics

### Quantitative Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Max file size | 2,531 lines | <500 lines | Line count |
| Test coverage | TBD | No decrease | Coverage report |
| Import time | TBD | <5% increase | Import profiler |
| API response time | TBD | <5% increase | Benchmark |
| Cyclomatic complexity | TBD | Decrease | Radon/mccabe |

### Qualitative Metrics

- [ ] Code review approval from 2+ senior engineers
- [ ] No critical or high security issues
- [ ] Documentation complete and accurate
- [ ] Team comfortable with new structure

---

## Resource Requirements

### Personnel

| Role | Effort | Responsibility |
|------|--------|----------------|
| Senior Engineer | 14 days | Implementation, review |
| Code Reviewer | 3 days | PR reviews |
| QA Engineer | 2 days | Testing validation |
| Tech Lead | 1 day | Architecture sign-off |

### Tools

- Profiling: `py-spy`, `cProfile`
- Complexity: `radon`, `xenon`
- Testing: `pytest`, `pytest-benchmark`
- Import analysis: `import-linter`

---

## Rollback Plan

### Rollback Triggers

1. Critical test failures not resolvable within 4 hours
2. Performance regression >10%
3. Security vulnerabilities introduced
4. Production incidents linked to changes

### Rollback Procedure

```bash
# 1. Revert to backup files
cp chunking_strategy_adapters.py.bak chunking_strategy_adapters.py
cp brain_settings.py.bak brain_settings.py

# 2. Remove new directories
rm -rf src/contexts/knowledge/infrastructure/adapters/chunking/
rm -rf src/api/routers/brain/

# 3. Restore imports
# (Revert import changes in dependent files)

# 4. Verify
git diff --stat
pytest tests/ -x
```

---

## Post-Implementation Monitoring

### Week 1 After Merge

- [ ] Daily error log review
- [ ] Performance metrics comparison
- [ ] Developer feedback collection

### Month 1 After Merge

- [ ] Maintainability metrics review
- [ ] Bug count analysis
- [ ] Onboarding time measurement

---

## Appendix: File Structure After Refactoring

```
src/
├── api/
│   └── routers/
│       └── brain/
│           ├── __init__.py              # 50 lines
│           ├── core.py                  # 150 lines
│           ├── dependencies.py          # 100 lines
│           ├── repositories/
│           │   ├── __init__.py
│           │   ├── brain_settings.py    # 130 lines
│           │   ├── chat_session.py      # 50 lines
│           │   └── token_usage.py       # 160 lines
│           ├── services/
│           │   ├── __init__.py
│           │   ├── ingestion_worker.py  # 80 lines
│           │   └── usage_broadcaster.py # 150 lines
│           └── endpoints/
│               ├── __init__.py
│               ├── settings.py          # 400 lines
│               ├── usage.py             # 450 lines
│               ├── ingestion.py         # 350 lines
│               ├── rag_context.py       # 100 lines
│               └── chat.py              # 400 lines
└── contexts/
    └── knowledge/
        └── infrastructure/
            └── adapters/
                └── chunking/
                    ├── __init__.py              # 80 lines
                    ├── base.py                  # 100 lines
                    ├── coherence.py             # 350 lines
                    ├── content_type.py          # 50 lines
                    ├── factory.py               # 100 lines
                    ├── utils.py                 # 80 lines
                    └── strategies/
                        ├── __init__.py
                        ├── auto.py              # 380 lines
                        ├── fixed.py             # 200 lines
                        ├── narrative.py         # 630 lines
                        ├── paragraph.py         # 230 lines
                        ├── semantic.py          # 400 lines
                        └── sentence.py          # 230 lines
```

**Total Files Created**: 26 modules  
**Total Lines (before)**: 4,761 lines in 2 files  
**Total Lines (after)**: ~4,900 lines in 26 files  
**Lines per module (max)**: 630 lines (narrative strategy)  
**Average lines per module**: ~190 lines

---

## Approval Checklist

- [ ] Architecture review approved
- [ ] Security review completed
- [ ] Performance baseline recorded
- [ ] Test plan reviewed
- [ ] Rollback plan tested
- [ ] Documentation reviewed
- [ ] Team briefed on changes
