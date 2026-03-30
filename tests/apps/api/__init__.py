"""
Tests for API apps __init__.
"""


def test_api_imports() -> None:
    """Test that all API modules can be imported."""
    from src.apps.api import dependencies, main, router

    assert main is not None
    assert router is not None
    assert dependencies is not None
