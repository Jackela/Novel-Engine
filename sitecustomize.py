"""
Ensure stable pytest startup regardless of globally-installed plugins.

By default, pytest will auto-load all installed third-party plugins via
entry points, which can cause long startup times or even hangs if a plugin
misbehaves. Setting PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 disables this and we
explicitly enable only the plugins we rely on via config.

Python automatically imports this module (if present on sys.path) after
`site` initialization. Running `python -m pytest` keeps CWD on sys.path,
so this applies before pytest starts up.
"""

import importlib.util
import os

# Do not override if the user already decided.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

# Ensure pytest-asyncio still loads even when auto-loading is disabled so async
# tests marked with @pytest.mark.asyncio continue working in CI.
if os.environ.get("PYTEST_PLUGINS") in (None, ""):
    try:
        if importlib.util.find_spec("pytest_asyncio") is not None:
            os.environ["PYTEST_PLUGINS"] = "pytest_asyncio"
    except Exception:
        pass

_addopts = os.environ.get("PYTEST_ADDOPTS", "")
if "-p pytest_asyncio" not in _addopts:
    os.environ["PYTEST_ADDOPTS"] = f"{_addopts} -p pytest_asyncio".strip()
