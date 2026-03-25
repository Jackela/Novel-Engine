"""
Tests for API middleware __init__.
"""


def test_middleware_imports():
    """Test that all middleware modules can be imported."""
    from src.apps.api.middleware import cors, error_handler, logging

    assert error_handler is not None
    assert logging is not None
    assert cors is not None
