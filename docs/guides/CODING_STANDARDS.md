# Novel Engine Coding Standards

## Overview

This document establishes professional coding standards for the Novel Engine project to ensure maintainable, readable, and consistent code across all contributors.

## 🎯 Core Principles

1. **Clarity over Cleverness** - Write code that's easy to understand
2. **Consistency over Convenience** - Follow established patterns
3. **Simplicity over Complexity** - Prefer simple, direct solutions
4. **Testability over Performance** - Write testable code first, optimize second

## 📝 Documentation Standards

### Docstring Format
Use Google-style docstrings:

```python
def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two text strings.
    
    Args:
        text1: First text string for comparison
        text2: Second text string for comparison
        
    Returns:
        Similarity score between 0.0 and 1.0
        
    Raises:
        ValueError: If either text string is empty
    """
```

### Comments
- Use comments to explain **why**, not **what**
- Keep comments concise and professional
- Update comments when code changes
- Avoid religious/fantasy terminology

### Professional Language
- Use professional terminology in all code, comments, and documentation
- Avoid themed language (religious, fantasy, etc.)
- Use clear, descriptive variable and function names

## 🏗️ Code Structure

### File Organization
```
src/
├── core/          # Core system components
├── api/           # API endpoints and routing
├── memory/        # Memory management systems
├── templates/     # Template engines
└── shared/        # Shared utilities and types
```

### Class Design
- Single Responsibility Principle
- Maximum 30 methods per class
- Maximum 500 lines per class
- Use composition over inheritance

### Function Design
- Maximum 50 lines per function
- Maximum 5 parameters per function
- Use type hints for all parameters and returns
- One responsibility per function

## 🔧 Naming Conventions

### Variables and Functions
```python
# Good
user_count = 10
def calculate_total_score() -> int:

# Bad
uc = 10
def calcTotScr() -> int:
```

### Classes
```python
# Good
class DatabaseConnection:
class UserManager:

# Bad
class DB:
class UsrMgr:
```

### Constants
```python
# Good
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30

# Bad
MAX_RETRY = 3
timeout = 30
```

## 📊 Type Hints

Always use type hints:

```python
from typing import List, Dict, Optional, Union

def process_users(users: List[Dict[str, str]]) -> Optional[bool]:
    """Process a list of user dictionaries."""
    pass
```

## 🎨 Code Formatting

### Use Black for Python formatting:
```bash
black --line-length 100 src/
```

### Import Organization:
```python
# Standard library
import os
import sys
from typing import Dict, List

# Third-party
import numpy as np
import pandas as pd

# Local imports
from src.core.database import DatabaseManager
from src.shared.types import UserData
```

## ⚠️ Error Handling

### Use specific exceptions:
```python
# Good
try:
    user = database.get_user(user_id)
except UserNotFoundError:
    logger.warning(f\"User {user_id} not found\")
    return None
except DatabaseConnectionError:
    logger.error(\"Database connection failed\")
    raise

# Bad
try:
    user = database.get_user(user_id)
except Exception:
    pass
```

### Logging Standards:
```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug(\"Debug information for developers\")
logger.info(\"General information about program execution\")
logger.warning(\"Something unexpected happened but program continues\")
logger.error(\"A serious error occurred\")
logger.critical(\"A very serious error occurred\")
```

## 🧪 Testing Standards

### Test File Naming
```
tests/
├── unit/
│   ├── test_user_manager.py
│   └── test_database.py
├── integration/
│   └── test_api_endpoints.py
└── fixtures/
    └── sample_data.py
```

### Test Function Naming
```python
def test_user_creation_with_valid_data():
    \"\"\"Test that user creation succeeds with valid input data.\"\"\"
    pass

def test_user_creation_fails_with_invalid_email():
    \"\"\"Test that user creation fails when email format is invalid.\"\"\"
    pass
```

## 🚀 Performance Guidelines

### Database Queries
- Use connection pooling
- Implement query timeout limits
- Avoid N+1 query problems
- Use indexes appropriately

### Memory Management
- Clean up resources in finally blocks or context managers
- Avoid memory leaks in long-running processes
- Use generators for large datasets

### Caching
- Cache expensive computations
- Implement cache invalidation strategies
- Use appropriate cache expiration times

## 🔒 Security Standards

### Input Validation
```python
def process_user_input(user_input: str) -> str:
    \"\"\"Process user input with proper validation.\"\"\"
    if not user_input or len(user_input) > 1000:
        raise ValueError(\"Invalid input length\")
    
    # Sanitize input
    sanitized = html.escape(user_input.strip())
    return sanitized
```

### Environment Variables
```python
import os

# Good
SECRET_KEY = os.getenv(\"SECRET_KEY\")
if not SECRET_KEY:
    raise ValueError(\"SECRET_KEY environment variable is required\")

# Bad
SECRET_KEY = \"hardcoded-secret-key\"
```

## 📋 Code Review Checklist

### Before Committing
- [ ] Code follows naming conventions
- [ ] All functions have type hints
- [ ] Docstrings are complete and accurate
- [ ] No hardcoded secrets or credentials
- [ ] Error handling is appropriate
- [ ] Tests cover new functionality
- [ ] Performance impact considered
- [ ] Security implications reviewed

### File Size Limits
- Maximum 1000 lines per Python file
- Break large files into logical components
- Use composition and dependency injection

## 🛠️ Tools and Automation

### Required Tools
```bash
# Code formatting
pip install black isort

# Type checking
pip install mypy

# Linting
pip install flake8 pylint

# Security scanning
pip install bandit safety
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        line_length: 100
        
  - repo: https://github.com/PyCQA/isort
    rev: 5.10.1
    hooks:
      - id: isort
        
  - repo: https://github.com/PyCQA/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
```

## 📈 Continuous Improvement

### Metrics to Track
- Code coverage percentage
- Cyclomatic complexity
- Technical debt ratio
- Performance benchmarks

### Regular Reviews
- Monthly code quality assessments
- Quarterly architecture reviews
- Annual standard updates

## 🔗 References

- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Clean Code Principles](https://clean-code-developer.com/)

---

**Note**: These standards are living guidelines that should evolve with the project and team needs.