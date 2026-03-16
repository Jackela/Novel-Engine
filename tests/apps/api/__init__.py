"""
Tests for API apps __init__.
"""


def test_api_imports():
    """Test that all API modules can be imported."""
    from src.apps.api import main
    from src.apps.api import router
    from src.apps.api import dependencies

    assert main is not None
    assert router is not None
    assert dependencies is not None
