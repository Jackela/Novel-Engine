#!/usr/bin/env python3
"""
Backwards-compatible shared types re-export.

Historically consumers imported ``src.shared_types`` for the canonical set of
Pydantic models and enums. The canonical definitions now live in
``src.core.types.shared_types``. This module loads the canonical implementation
directly from disk so that editable installs and packaging quirks never break
legacy imports.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_TYPES_PATH = _THIS_DIR.parent / "core" / "types" / "shared_types.py"
_MODULE_NAME = "src.core.types.shared_types"

_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _TYPES_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Unable to locate core shared types at {_TYPES_PATH}")

_core_shared_types = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _core_shared_types
_spec.loader.exec_module(_core_shared_types)

# Re-export every public symbol so ``from src.shared_types import Foo`` continues
# to work for legacy modules and tests.
for _name in getattr(_core_shared_types, "__all__", []):
    globals()[_name] = getattr(_core_shared_types, _name)

__all__ = list(getattr(_core_shared_types, "__all__", []))
