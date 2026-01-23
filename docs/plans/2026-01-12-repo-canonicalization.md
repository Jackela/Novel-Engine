# Repo Canonicalization Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove legacy artifacts, unify agent guidance, and align documentation/scripts with the current SSOT.

**Architecture:** Keep documentation canonical in `docs/` and OpenSpec guidance in `docs/specs/openspec/`. Clean out legacy artifacts without changing runtime behavior.

**Tech Stack:** Python 3.11+, FastAPI, pytest, Node.js, npm.

### Task 1: Remove legacy artifacts and caches

**Files:**
- Remove: `docs/archive/`
- Remove: `tests/test_quality_framework.py.broken`
- Remove: `src/interactions/interaction_engine_system/queue_management/queue_manager_broken.py`
- Remove: `test.md`, `test_log.md`, `campaign_log.md`, `nonexistent_world_state.json`
- Remove: `__pycache__/`, `.pytest_cache/`, `novel_engine.egg-info/`, `logs/`, `reports/`

**Step 1: Identify legacy paths**
Run: `rg --files | rg -i "archive|broken|legacy|cache|egg-info"`
Expected: Paths listed for removal.

**Step 2: Delete legacy artifacts**
Run (PowerShell):
```powershell
Remove-Item -Recurse -Force docs/archive tests/test_quality_framework.py.broken `
  src/interactions/interaction_engine_system/queue_management/queue_manager_broken.py `
  test.md test_log.md campaign_log.md nonexistent_world_state.json `
  __pycache__ .pytest_cache novel_engine.egg-info logs reports
```
Expected: Paths removed without errors.

**Step 3: Confirm no dangling references**
Run: `rg -n "queue_manager_broken|test_quality_framework.py" docs scripts`
Expected: No matches.

### Task 2: Establish a single Agent guide and update docs

**Files:**
- Create: `AGENTS.md`
- Modify: `docs/index.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `README.en.md`

**Step 1: Add root agent guide**
Create `AGENTS.md` with SSOT workflow and contract guidance.

**Step 2: Update documentation hub**
Add links to `AGENTS.md` in `docs/index.md`.

**Step 3: Align developer guide and OpenSpec**
Update `docs/DEVELOPER_GUIDE.md` to reference `AGENTS.md`.
Add a short note in `AGENTS.md` pointing back to itself as SSOT.

**Step 4: Sync README files**
Add an AI collaboration section in `README.md` and `README.en.md`.

### Task 3: Fix script references to removed tests

**Files:**
- Modify: `scripts/validate_quality_implementation.py`
- Modify: `scripts/test_migration_utilities.py`

**Step 1: Update validation target**
Point quality test validation to `tests/unit/quality` instead of a removed file.

**Step 2: Remove legacy migration file names**
Clear the stale file list under the `quality` migration map.

### Task 4: Verify repo hygiene (targeted)

**Files:**
- Verify: `.gitignore`

**Step 1: Check .gitignore coverage**
Confirm entries for Python, Node, IDE, cache, and report artifacts are present.

**Step 2: Run targeted checks**
Run:
```
rg -n "docs/archive|queue_manager_broken|test_quality_framework.py"
```
Expected: No matches.

**Optional validation:**
```
pytest tests/unit/quality -v
```
Expected: Pass or skip with clear reasons.
