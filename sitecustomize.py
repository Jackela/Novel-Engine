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

import os

# Do not override if the user already decided.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

