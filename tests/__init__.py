"""
Novel Engine Test Suite
=======================

Comprehensive test suite for Novel Engine covering:
- Unit tests for all core components
- Integration tests for system interactions
- Security tests for production readiness
- Performance tests for scalability validation

Test Organization:
- unit/: Unit tests for individual components
- integration/: Integration tests for system interactions  
- security/: Security and compliance tests
- legacy/: Historical tests for compatibility
- root_tests/: Consolidated root-level tests
"""

import pytest
import asyncio
from pathlib import Path

# Test configuration
TEST_ROOT = Path(__file__).parent
PROJECT_ROOT = TEST_ROOT.parent

# Common test utilities
def get_test_config():
    """Get test-specific configuration."""
    return {
        "database_url": "sqlite:///test.db",
        "redis_url": "redis://localhost:6379/15",
        "log_level": "DEBUG"
    }

def setup_test_environment():
    """Set up test environment with necessary fixtures."""
    import os
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"