#!/usr/bin/env python3
"""
Config Loader - Backward Compatibility Interface

This module maintains backward compatibility by importing and exposing the
config loader from the core config module. This ensures existing imports continue
to work while providing the benefits of modular architecture.

Development Phase: Phase 1 Validation - Import Compatibility
"""

try:
    # Try to import from the core config module
    from src.core.config.config_loader import *
    CORE_CONFIG_AVAILABLE = True
except ImportError:
    # Fallback implementation if core config not available
    CORE_CONFIG_AVAILABLE = False
    
    def get_config():
        """Fallback config loader that returns empty config."""
        return {}
    
    def load_config(config_path=None):
        """Fallback config loader that returns empty config."""
        return {}

# Re-export for backward compatibility
__all__ = ['get_config', 'load_config', 'CORE_CONFIG_AVAILABLE']