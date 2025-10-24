# Print to Logging Migration - Quick Start Guide

## TL;DR

```bash
# 1. Preview all changes
python scripts/migrate_print_to_logging.py --dry-run

# 2. Apply migration
python scripts/migrate_print_to_logging.py

# 3. Test
pytest tests/

# 4. Review and commit
git diff
git add .
git commit -m "Migrate print() to logging"
```

## Current State

- **245 Python files** in src/
- **251 print statements** found
- **31 files** need modification
- **Breakdown**: 236 INFO, 14 ERROR, 1 WARNING

## Safe Migration Steps

### Step 1: Preview (Always Do This First!)

```bash
python scripts/migrate_print_to_logging.py --dry-run > migration_preview.txt
```

Review `migration_preview.txt` to see what will change.

### Step 2: Test on One File

```bash
# Pick a simple file first
python scripts/migrate_print_to_logging.py --file src/core/types.py

# Check the changes
git diff src/core/types.py

# If good, continue. If not:
git checkout -- src/core/types.py
```

### Step 3: Apply to All

```bash
python scripts/migrate_print_to_logging.py
```

### Step 4: Verify

```bash
# Check what changed
git status
git diff --stat

# Run tests
pytest tests/

# Review specific files
git diff src/api/integration_tests.py
```

### Step 5: Configure Logging

Add to your main entry point (e.g., `src/main.py` or test setup):

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## What Changes

### Before
```python
print("🚀 Starting tests")
print(f"Failed: {count} ❌")
print(f"Error: {e}")
```

### After
```python
import logging

logger = logging.getLogger(__name__)

logger.info("🚀 Starting tests")
logger.error(f"Failed: {count} ❌")
logger.error(f"Error: {e}")
```

## Files with Most Changes

1. `templates/dynamic_template_engine.py` - 19 statements
2. `api/integration_tests.py` - 17 statements  
3. `api/enhanced_documentation_system.py` - 5 statements

## Manual Review Needed

Some files contain print statements in:
- **Code examples**: `api/enhanced_documentation_system.py`
- **Test output**: `templates/dynamic_template_engine.py`
- **String literals**: These won't be converted

Review these files manually after migration.

## Rollback if Needed

```bash
# Undo all changes
git checkout -- src/

# Undo specific file
git checkout -- src/api/integration_tests.py
```

## Common Questions

**Q: Will this break my tests?**  
A: No, but test output will go to logging instead of stdout. Configure logging in test fixtures.

**Q: Can I undo specific files?**  
A: Yes, use `git checkout -- path/to/file.py`

**Q: What if I disagree with a level choice?**  
A: After migration, manually edit the file. The script is conservative (prefers INFO).

**Q: Will it handle f-strings?**  
A: Yes, all formatting is preserved exactly.

**Q: What about print statements with sep/end parameters?**  
A: These are flagged but may need manual conversion.

## Pro Tips

1. **Run dry-run multiple times** - Review output carefully
2. **Test incrementally** - Migrate critical files first
3. **Keep git clean** - Commit other changes before migration
4. **Review diffs** - Use `git diff` to check each file
5. **Configure logging** - Set up proper config before running code

## Help

```bash
python scripts/migrate_print_to_logging.py --help
```

For detailed info, see `MIGRATION_README.md`.
