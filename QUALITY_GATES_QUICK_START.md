# Quality Gates Quick Start Guide

## TL;DR - What You Need to Know

The Novel Engine project now has CI quality gates that ensure:
1. Test pyramid health (70% unit, 20% integration, 10% e2e)
2. All tests are properly categorized
3. Fast CI feedback with parallel test execution

## 60-Second Setup

```bash
# 1. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 2. Before every commit (recommended)
./scripts/local-ci.sh --fast

# 3. Before every push
./scripts/local-ci.sh
```

That's it! You're now protected by quality gates.

## Essential Commands

### Before Committing
```bash
./scripts/local-ci.sh --fast  # 1-2 minutes
```

### Before Pushing
```bash
./scripts/local-ci.sh  # 5-10 minutes
```

### Check Your Tests
```bash
# View pyramid status
python scripts/testing/test-pyramid-monitor-fast.py

# Validate markers
python scripts/testing/validate-test-markers.py --all
```

## Adding Markers to Tests

Every test needs ONE of these markers:

```python
@pytest.mark.unit         # Fast, isolated, no external deps
@pytest.mark.integration  # Uses database, API, file system
@pytest.mark.e2e          # Complete user workflows
```

### Example
```python
@pytest.mark.unit
def test_character_name_validation():
    """Unit test - fast and isolated."""
    character = Character(name="Hero")
    assert character.validate_name()

@pytest.mark.integration
async def test_save_character_to_db():
    """Integration test - uses database."""
    character = Character(name="Hero")
    await character.save()
    assert character.id is not None

@pytest.mark.e2e
async def test_complete_quest_workflow():
    """E2E test - full user workflow."""
    response = await client.post("/character", json={"name": "Hero"})
    character_id = response.json()["id"]
    response = await client.post(f"/character/{character_id}/quest")
    assert response.status_code == 200
```

## CI Pipeline

When you push, CI runs:
1. Test Pyramid Check (must pass)
2. Marker Validation (must pass)
3. Unit Tests (must pass)
4. Integration Tests (must pass)
5. E2E Tests (must pass)
6. Speed Regression (warning only)

## Common Issues

### "Pyramid score too low"
**Fix**: Add missing markers to tests
```bash
python scripts/testing/validate-test-markers.py --all --verbose
```

### "Missing markers"
**Fix**: Add @pytest.mark.unit/integration/e2e to tests
```bash
# Find which tests need markers
python scripts/testing/validate-test-markers.py --all --verbose
```

### "Pre-commit hook failed"
**Fix**: Run the suggested commands in the error message
```bash
# Or temporarily bypass (use sparingly)
git commit --no-verify -m "message"
```

## Bypass Options (Emergency Only)

```bash
# Skip pre-commit hooks (use for WIP commits)
git commit --no-verify -m "WIP: feature"

# Skip specific hook
SKIP=validate-test-markers git commit -m "message"

# Include bypass keyword
git commit -m "temporary fix [skip-marker-check]"
```

**Never bypass on main/develop branches!**

## Quick Reference

| Command | Purpose | Time | When |
|---------|---------|------|------|
| `./scripts/local-ci.sh --fast` | Quick validation | 1-2 min | Before commit |
| `./scripts/local-ci.sh` | Full validation | 5-10 min | Before push |
| `./scripts/local-ci.sh --pyramid` | Pyramid check only | 10 sec | Check score |
| `./scripts/local-ci.sh --markers` | Marker validation | 5 sec | Check markers |
| `python scripts/testing/test-pyramid-monitor-fast.py` | View pyramid | 10 sec | Status check |
| `python scripts/testing/validate-test-markers.py --all` | Find unmarked | 5 sec | Find issues |

## Help

- **Full Guide**: `docs/testing/QUALITY_GATES.md`
- **Implementation Details**: `CI_QUALITY_GATES_IMPLEMENTATION.md`
- **Scripts Reference**: `scripts/testing/README.md`
- **Tool Help**: Run any script with `--help`

## Success Metrics

You're doing great when:
- Local CI passes before you push
- Pre-commit hooks run automatically
- Your tests have proper markers
- CI passes on first try

## Team Goals

- [ ] Pyramid score > 7.0
- [ ] All tests have markers
- [ ] Everyone uses local CI
- [ ] Everyone has pre-commit hooks installed
- [ ] Test distribution at 70/20/10 target

## Questions?

1. Check `docs/testing/QUALITY_GATES.md`
2. Run tool with `--help`
3. Ask team members
4. Review CI logs

Remember: Quality gates help us maintain code quality. Use them!
