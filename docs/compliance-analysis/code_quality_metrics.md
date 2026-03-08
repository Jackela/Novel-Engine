# Code Quality Metrics Report

**Generated:** 2026-03-04

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Python Files | 834 |
| Total Lines of Code | 277,484 |
| Total Classes | 2,213 |
| Total Functions | 517 |
| Total Methods | 5,661 |
| Quality Score | **C+** (Requires Refactoring) |

---

## Size Metrics

| Metric | Value |
|--------|-------|
| Total Python Files | 834 |
| Total Lines of Code | 277,484 |
| Average File Size | 333 lines |
| Largest File | 2,335 lines (`src/orchestrators/enhanced_multi_agent_bridge.py`) |
| Median File Size | ~200 lines (estimated) |

### Size Distribution

| Size Range | Count | Percentage |
|------------|-------|------------|
| 0-100 lines | ~180 | 21.6% |
| 100-250 lines | ~250 | 30.0% |
| 250-500 lines | ~185 | 22.2% |
| 500-750 lines | ~110 | 13.2% |
| 750-1000 lines | ~82 | 9.8% |
| 1000-1500 lines | ~22 | 2.6% |
| 1500+ lines | ~5 | 0.6% |

---

## Structure Metrics

| Metric | Value |
|--------|-------|
| Total Classes | 2,213 |
| Total Functions (module-level) | 517 |
| Total Methods (class-level) | 5,661 |
| Total Functions + Methods | 6,178 |
| Average Functions per File | 7.4 |
| Average Classes per File | 2.7 |
| Methods per Class (avg) | 2.6 |

---

## Complexity Indicators

### File Size Complexity

| Metric | Count | Percentage |
|--------|-------|------------|
| Files >500 lines | 219 | 26.3% |
| Files >1000 lines | 27 | 3.2% |
| Files >1500 lines | 5 | 0.6% |

### Function Length Complexity

| Metric | Count |
|--------|-------|
| Functions >50 lines | 1,283 |
| Functions >100 lines | 496 |
| Longest function | 2,269 lines (`create_enhanced_multi_agent_bridge`) |

### Most Complex Files (by length)

| Rank | File | Lines | Risk Level |
|------|------|-------|------------|
| 1 | `src/orchestrators/enhanced_multi_agent_bridge.py` | 2,335 | 🔴 Critical |
| 2 | `src/contexts/world/infrastructure/generators/llm_world_generator.py` | 1,870 | 🔴 Critical |
| 3 | `src/contexts/knowledge/infrastructure/adapters/neo4j_graph_store.py` | 1,691 | 🔴 Critical |
| 4 | `src/api/main_api_server.py` | 1,534 | 🔴 Critical |
| 5 | `src/contexts/character/domain/aggregates/character.py` | 1,521 | 🔴 Critical |
| 6 | `src/api/services/prompt_router_service.py` | 1,408 | 🟠 High |
| 7 | `src/contexts/interactions/domain/services/negotiation_service.py` | 1,388 | 🟠 High |
| 8 | `src/contexts/world/application/services/world_simulation_service.py` | 1,371 | 🟠 High |
| 9 | `src/contexts/knowledge/infrastructure/adapters/networkx_graph_store.py` | 1,317 | 🟠 High |
| 10 | `src/contexts/world/infrastructure/persistence/postgres_world_state_repo.py` | 1,281 | 🟠 High |

---

## Directory Size Distribution

### Top-Level Directories

| Directory | Files | Lines | % of Codebase |
|-----------|-------|-------|---------------|
| src/contexts/ | 459 | 140,980 | 50.8% |
| src/api/ | 107 | 35,106 | 12.6% |
| src/core/ | 48 | 21,603 | 7.8% |
| src/interactions/ | 52 | 11,928 | 4.3% |
| src/security/ | 14 | 9,425 | 3.4% |
| src/agents/ | 19 | 9,309 | 3.4% |
| src/performance/ | 10 | 6,591 | 2.4% |
| src/infrastructure/ | 7 | 5,720 | 2.1% |
| src/performance_optimizations/ | 7 | 5,212 | 1.9% |
| src/director_components/ | 9 | 4,636 | 1.7% |
| src/templates/ | 15 | 4,035 | 1.5% |
| src/prompts/ | 14 | 3,147 | 1.1% |
| src/bridges/ | 12 | 2,846 | 1.0% |
| src/memory/ | 7 | 2,733 | 1.0% |
| src/quality/ | 3 | 2,377 | 0.9% |
| src/orchestrators/ | 2 | 2,336 | 0.8% |
| src/decision/ | 6 | 1,769 | 0.6% |
| src/events/ | 6 | 1,752 | 0.6% |
| src/caching/ | 13 | 1,503 | 0.5% |
| Others | 24 | 6,422 | 2.3% |

### Largest Sub-Directories (Context Modules)

| Directory | Files | Lines | % of Contexts |
|-----------|-------|-------|---------------|
| src/contexts/knowledge/ | 125 | 43,690 | 31.0% |
| src/contexts/world/ | 95 | 32,128 | 22.8% |
| src/contexts/orchestration/ | 45 | 18,466 | 13.1% |
| src/contexts/narratives/ | 40 | 11,181 | 7.9% |
| src/contexts/character/ | 35 | 11,181 | 7.9% |
| src/contexts/interactions/ | 30 | 9,703 | 6.9% |
| src/contexts/subjective/ | 27 | 5,842 | 4.1% |
| src/contexts/ai/ | 25 | 5,456 | 3.9% |

---

## Largest Files (Refactor Targets)

### Priority 1: Critical (>1500 lines)

| File | Lines | Recommendation |
|------|-------|----------------|
| `src/orchestrators/enhanced_multi_agent_bridge.py` | 2,335 | Split into module with separate bridge components |
| `src/contexts/world/infrastructure/generators/llm_world_generator.py` | 1,870 | Extract generator strategies into separate classes |
| `src/contexts/knowledge/infrastructure/adapters/neo4j_graph_store.py` | 1,691 | Split adapter into query builders and connection handlers |
| `src/api/main_api_server.py` | 1,534 | Decompose into smaller router modules |
| `src/contexts/character/domain/aggregates/character.py` | 1,521 | Separate domain logic into value objects |

### Priority 2: High (1000-1500 lines)

| File | Lines | Recommendation |
|------|-------|----------------|
| `src/api/services/prompt_router_service.py` | 1,408 | Split routing logic into dedicated handlers |
| `src/contexts/interactions/domain/services/negotiation_service.py` | 1,388 | Extract negotiation strategies |
| `src/contexts/world/application/services/world_simulation_service.py` | 1,371 | Separate simulation engines |
| `src/contexts/knowledge/infrastructure/adapters/networkx_graph_store.py` | 1,317 | Refactor into smaller adapter classes |
| `src/contexts/world/infrastructure/persistence/postgres_world_state_repo.py` | 1,281 | Split query methods into repositories |
| `src/agents/director_agent_integrated.py` | 1,277 | Decompose agent logic into components |
| `src/infrastructure/state_store.py` | 1,219 | Extract storage backends |
| `src/security/enterprise_security_manager.py` | 1,207 | Split into security modules |
| `src/templates/context_renderer.py` | 1,203 | Separate renderer strategies |
| `src/infrastructure/observability.py` | 1,170 | Split metrics, logging, tracing |
| `src/contexts/knowledge/application/services/multi_hop_retriever.py` | 1,170 | Extract retriever strategies |
| `src/core/system_orchestrator.py` | 1,160 | Decompose orchestration logic |
| `src/contexts/character/application/services/context_loader.py` | 1,150 | Split loading strategies |
| `src/security/auth_system.py` | 1,149 | Separate auth providers |
| `src/contexts/knowledge/application/services/model_registry.py` | 1,102 | Split registry operations |

---

## Code Smells

| Type | Count | Notes |
|------|-------|-------|
| TODO comments | 8 | Low count - good maintenance |
| FIXME comments | 2 | Very low - excellent |
| XXX comments | 1 | Minimal technical debt markers |

### TODO Locations

TODO comments are distributed across the codebase with only 8 instances, indicating good code maintenance practices.

---

## Cyclomatic Complexity

**Status:** `radon` not installed in environment.

**Recommendation:** Install `radon` to get accurate cyclomatic complexity metrics:
```bash
pip install radon
radon cc src/ -a -nc
```

**Estimated Complexity:** Based on function lengths and file sizes, estimated average complexity is **MODERATE-HIGH**.

---

## Function Analysis

### Longest Functions (by line count within function)

| Function | Lines | File |
|----------|-------|------|
| `create_enhanced_multi_agent_bridge` | 2,269 | `src/orchestrators/enhanced_multi_agent_bridge.py` |
| `get_enterprise_security_manager` | 1,179 | Security module |
| `create_unified_state_manager` | 1,152 | State management |
| `create_observability_manager` | 1,119 | Observability |
| `create_model_registry` | 1,072 | Model registry |
| `create_s3_config_from_env` | 918 | Configuration |
| `get_llm_cache` | 907 | Caching layer |
| `get_database_manager` | 865 | Database |
| `create_model_router` | 861 | API routing |

---

## Quality Score Calculation

### Scoring Criteria

| Metric | Score | Weight | Weighted |
|--------|-------|--------|----------|
| File organization | 6/10 | 15% | 0.9 |
| Average file size | 5/10 | 15% | 0.75 |
| Large files (>500) | 4/10 | 20% | 0.8 |
| Function length | 4/10 | 20% | 0.8 |
| TODO/FIXME density | 9/10 | 15% | 1.35 |
| Documentation | N/A | 15% | 0.75* |
| **TOTAL** | | **100%** | **5.35/10** |

*Estimated based on patterns observed

### Grade: **C+ (5.4/10)**

### Interpretation
- **A (8-10):** Excellent - Well-organized, maintainable codebase
- **B (6-8):** Good - Minor refactoring needed
- **C (4-6):** Average - Significant refactoring recommended ⚠️
- **D (2-4):** Poor - Major overhaul needed
- **F (0-2):** Critical - Immediate attention required

---

## Recommendations

### Immediate (High Priority)

1. **Refactor Critical Files**: Split the 5 files >1500 lines into smaller, focused modules
   - Priority: `enhanced_multi_agent_bridge.py` (2,335 lines)
   - Priority: `llm_world_generator.py` (1,870 lines)
   - Priority: `neo4j_graph_store.py` (1,691 lines)

2. **Address Long Functions**: Break down 496 functions >100 lines into smaller, testable units

3. **Install Radon**: Set up cyclomatic complexity monitoring in CI/CD
   ```bash
   pip install radon
   radon cc src/ -a -nc --json > complexity_report.json
   ```

### Short-term (Medium Priority)

4. **Standardize File Sizes**: Aim for 80% of files under 500 lines
   - Current: 73.7% under 500 lines
   - Target: 80% under 500 lines
   - Action needed: Refactor 48 files to reach target

5. **Module Reorganization**: Consider splitting `src/contexts/knowledge/` (43,690 lines, 125 files) into sub-modules

6. **Function Size Standards**: Enforce 50-line limit for new functions
   - Current violations: 1,283 functions
   - Target: <200 functions exceeding limit

### Long-term (Low Priority)

7. **Architecture Review**: Evaluate if the Hexagonal Architecture boundaries are being respected
   - `src/contexts/` contains 50.8% of all code - ensure domain logic is properly isolated

8. **Test Coverage**: Ensure the 6,178 functions/methods have adequate test coverage
   - Consider prioritizing tests for the 496 long functions

9. **Documentation**: Add module-level docstrings to the 219 large files explaining their purpose

---

## Comparison with Industry Standards

| Metric | This Project | Recommended | Status |
|--------|--------------|-------------|--------|
| Avg file size | 333 lines | <200 lines | ⚠️ High |
| Files >500 lines | 26.3% | <10% | ⚠️ High |
| Functions >50 lines | ~20% | <10% | ⚠️ High |
| TODO density | 0.003% | <0.01% | ✅ Good |

---

## Metrics Summary

```
╔══════════════════════════════════════════════════════════╗
║                CODE QUALITY METRICS SUMMARY              ║
╠══════════════════════════════════════════════════════════╣
║  Total LOC:           277,484 lines                      ║
║  Total Files:         834 Python files                   ║
║  Total Classes:       2,213                              ║
║  Total Functions:     6,178 (funcs + methods)            ║
║                                                          ║
║  LARGE FILES (>500 lines):                               ║
║  • Total: 219 files (26.3% of codebase)                  ║
║  • Critical (>1500): 5 files                             ║
║  • High (1000-1500): 22 files                            ║
║                                                          ║
║  TOP 3 COMPLEXITY CONCERNS:                              ║
║  1. enhanced_multi_agent_bridge.py (2,335 lines)         ║
║  2. llm_world_generator.py (1,870 lines)                 ║
║  3. neo4j_graph_store.py (1,691 lines)                   ║
║                                                          ║
║  QUALITY SCORE: C+ (5.4/10)                              ║
║  STATUS: Refactoring Recommended                         ║
╚══════════════════════════════════════════════════════════╝
```

---

## Next Steps for Improvement

1. Create refactoring tickets for the top 10 largest files
2. Set up automated complexity checking in pre-commit hooks
3. Establish coding standards documentation with file size limits
4. Schedule regular code quality reviews

---

*Report generated by Code Quality Metrics Analyst*
