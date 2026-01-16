# Print to Logging Migration Tool

## Overview

The `migrate_print_to_logging.py` script automatically migrates `print()` statements to proper Python `logging` calls throughout the Novel-Engine codebase. It intelligently determines appropriate logging levels based on context and ensures proper logging infrastructure is in place.

## Features

- **Intelligent Level Detection**: Automatically determines logging levels (DEBUG, INFO, WARNING, ERROR) based on context
- **Safe Preview Mode**: Dry-run mode allows reviewing changes before applying them
- **Comprehensive Analysis**: Analyzes 245 Python files and identifies 251 print statements
- **Automatic Setup**: Adds `import logging` and `logger = logging.getLogger(__name__)` where needed
- **Format Preservation**: Maintains f-strings, formatting, and code structure
- **Detailed Reporting**: Provides comprehensive summary with level distribution

## Current Analysis Results

Based on the latest dry-run scan:

```
Files Analyzed:            245
Files Modified:            31
Print Statements Found:    251
Print Statements Migrated: 251

Logging Level Distribution:
  ERROR   :  14 statements
  INFO    : 236 statements
  WARNING :   1 statements
```

## Usage

### 1. Preview Changes (Recommended First Step)

```bash
python scripts/migrate_print_to_logging.py --dry-run
```

This will show you:
- Which files will be modified
- What each print statement will become
- The reasoning for each logging level choice
- A summary of all changes

### 2. Apply Migration to All Files

```bash
python scripts/migrate_print_to_logging.py
```

This will:
- Modify all Python files in the `src/` directory
- Add logging imports and logger setup where needed
- Replace all print() calls with appropriate logging calls
- Generate a final migration report

### 3. Migrate a Single File

```bash
python scripts/migrate_print_to_logging.py --file src/api/integration_tests.py
```

Useful for:
- Testing the migration on a specific file first
- Incremental migration approach
- Reviewing changes on a per-file basis

### 4. Custom Source Directory

```bash
python scripts/migrate_print_to_logging.py --src-dir custom/path
```

## Logging Level Detection Logic

The script uses intelligent pattern matching to determine appropriate logging levels:

### ERROR Level

Triggered by patterns indicating errors or failures:
- Keywords: `error`, `exception`, `failed`, `critical`, `fatal`
- Emoji indicators: `❌`
- Examples:
  ```python
  print(f"❌ FAILED: {result.error_message}")  # → logger.error(...)
  print(f"HTTP error occurred: {e}")           # → logger.error(...)
  ```

### WARNING Level

Triggered by patterns indicating caution or deprecation:
- Keywords: `warning`, `caution`, `deprecated`
- Emoji indicators: `⚠️`
- Examples:
  ```python
  print("⚠️ Warning: This feature is deprecated")  # → logger.warning(...)
  ```

### INFO Level

Triggered by patterns indicating general information or status:
- Keywords: `starting`, `running`, `completed`, `finished`, `success`
- Emoji indicators: `✅`, `🚀`, `📋`, `📊`
- Keywords: `PASSED`, `TESTING`, `Summary`
- Default level for most general output
- Examples:
  ```python
  print("🚀 Starting Novel Engine API Integration Tests")  # → logger.info(...)
  print(f"✅ PASSED ({result.duration_ms:.1f}ms)")         # → logger.info(...)
  print(f"Total Tests: {report['total_tests']}")          # → logger.info(...)
  ```

### DEBUG Level

Triggered by patterns indicating debug or verbose information:
- Keywords: `debug`, `verbose`, `trace`, `detail`
- Examples:
  ```python
  print(f"Debug: Processing {item}")  # → logger.debug(...)
  ```

## Files That Will Be Modified

The script identifies 31 files containing print statements:

### API Layer
- `api/context7_integration_api.py` (2 statements)
- `api/enhanced_documentation_system.py` (5 statements)
- `api/integration_tests.py` (17 statements)

### Core Systems
- `core/config/src/core/config/config_loader.py`
- `core/data_models.py`
- `core/emergent_narrative.py`
- `core/subjective_reality.py`
- `core/types.py`

### Memory Systems
- `memory/emotional_memory.py`
- `memory/episodic_memory.py`
- `memory/layered_memory.py`
- `memory/memory_query_engine.py`
- `memory/semantic_memory.py`
- `memory/working_memory.py`

### Templates
- `templates/dynamic_template_engine.py` (19 statements)

### Infrastructure & Database
- `database/context_db.py`
- `events/event_store.py`
- `infrastructure/observability.py`
- `infrastructure/state_store.py`

### Interactions
- `interactions/dynamic_equipment_system.py`
- `interactions/interaction_engine.py`

And many more...

## What Gets Added to Each File

For files without logging infrastructure, the script adds:

```python
import logging

logger = logging.getLogger(__name__)
```

These are inserted intelligently:
- `import logging` goes in the import section
- `logger = ...` goes after imports, before the first code

## Example Transformations

### Before
```python
def run_test_suite(self):
    print("🚀 Starting Novel Engine API Integration Tests")
    print("=" * 60)
    
    for scenario in scenarios:
        print(f"\n📋 Running: {scenario.name}")
        try:
            result = self._execute_scenario(scenario)
            if result.success:
                print(f"   ✅ PASSED ({result.duration_ms:.1f}ms)")
            else:
                print(f"   ❌ FAILED: {result.error_message}")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
```

### After
```python
import logging

logger = logging.getLogger(__name__)

def run_test_suite(self):
    logger.info("🚀 Starting Novel Engine API Integration Tests")
    logger.info("=" * 60)
    
    for scenario in scenarios:
        logger.info(f"\n📋 Running: {scenario.name}")
        try:
            result = self._execute_scenario(scenario)
            if result.success:
                logger.info(f"   ✅ PASSED ({result.duration_ms:.1f}ms)")
            else:
                logger.error(f"   ❌ FAILED: {result.error_message}")
        except Exception as e:
            logger.error(f"   ❌ ERROR: {str(e)}")
```

## Post-Migration Steps

After running the migration:

### 1. Review Changes
```bash
git diff
```

Review the changes to ensure they make sense for your use case.

### 2. Run Tests
```bash
pytest tests/
```

Ensure all tests still pass with the new logging.

### 3. Configure Logging

Add logging configuration to your main application entry points:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('novel_engine.log'),
        logging.StreamHandler()
    ]
)
```

### 4. Adjust Levels as Needed

Some statements might need manual adjustment:
- Test output that should be DEBUG in production
- Critical errors that should be CRITICAL not ERROR
- Temporary debugging that should be removed

### 5. Commit Changes
```bash
git add .
git commit -m "Migrate print() statements to logging

- Added logging infrastructure to 31 files
- Migrated 251 print statements to appropriate logging levels
- INFO: 236, ERROR: 14, WARNING: 1
- Preserves all formatting and f-strings"
```

## Edge Cases and Limitations

### Known Limitations

1. **Multi-line print statements**: The script handles single-line prints best
2. **Complex string formatting**: Some complex cases may need manual review
3. **Print with sep/end parameters**: These need manual conversion
4. **Embedded in strings**: Print statements inside string literals are detected but not converted

### Manual Review Recommended For

- `api/enhanced_documentation_system.py`: Contains prints in code examples/strings
- `templates/dynamic_template_engine.py`: Many test-related prints
- Any file with unusual print usage patterns

## Troubleshooting

### Script Errors

If you encounter errors:

```bash
# Check Python version (requires 3.7+)
python --version

# Verify file paths
python scripts/migrate_print_to_logging.py --dry-run --file src/core/types.py
```

### Unexpected Results

1. Review the dry-run output carefully
2. Start with a single file migration
3. Check git diff after each file
4. Rollback if needed: `git checkout -- src/`

## Best Practices

1. **Always run dry-run first**: Review changes before applying
2. **Test incrementally**: Migrate critical files first and test
3. **Review context**: Some prints might be better removed than converted
4. **Configure logging early**: Set up proper logging config before migration
5. **Document level choices**: Add comments for non-obvious level selections

## Script Maintenance

The script is self-contained and requires only Python 3.7+ standard library. No external dependencies.

### Future Enhancements

Potential improvements:
- Support for custom logging patterns
- Configurable level detection rules
- Multi-line print statement handling
- Integration with existing logging config
- Rollback functionality

## Contact

For issues or questions about the migration:
- Review the script source code: `scripts/migrate_print_to_logging.py`
- Check git history for examples
- Test on a single file first

